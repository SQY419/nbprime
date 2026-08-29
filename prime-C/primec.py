# PrimeC: small self-hosted C compiler for HP Prime (ARM926EJ-S / ARMv5TEJ).
# v0.3: int/char/void types, pointers, arrays, string literals, globals,
#       full control flow (break/continue/do-while), ++/--, compound
#       assignment, bitwise/shift ops, ternary, short-circuit &&/||,
#       firmware syscall builtins __svc()/__sleep().
# Runs under MicroPython. No external packages.
import ustruct as struct

PT_LOAD = 1
PT_DYNAMIC = 2
DT_NULL = 0
DT_REL = 17
DT_RELSZ = 18
DT_RELENT = 19
DT_RELCOUNT = 0x6FFFFFFA
R_ARM_RELATIVE = 23

T_INT = 'int'
T_CHAR = 'char'
T_VOID = 'void'

ASSIGN_OPS = ('=', '+=', '-=', '*=', '/=', '%=', '<<=', '>>=', '&=', '|=', '^=')

# struct layout tables (reset per compilation)
STRUCT_MEMBERS = {}   # name -> [(member, type, offset)]
STRUCT_SIZES = {}     # name -> total size (4-aligned)


class CompileError(Exception):
    pass


# ---------- types ----------
def is_ptr(t):
    return isinstance(t, tuple) and t[0] == 'ptr'


def is_arr(t):
    return isinstance(t, tuple) and t[0] == 'arr'


def is_struct(t):
    return isinstance(t, tuple) and t[0] == 'struct'


def align_up(x, a):
    return (x + a - 1) & ~(a - 1)


def struct_size(t):
    # t must be a ('struct', name) type
    if t[1] not in STRUCT_SIZES:
        raise CompileError('struct %s not defined' % t[1])
    return STRUCT_SIZES[t[1]]


def type_align(t):
    # alignment requirement of a type
    if t == T_CHAR:
        return 1
    if t == T_INT or is_ptr(t):
        return 4
    if is_arr(t):
        return type_align(t[1])
    if is_struct(t):
        return 4
    return 4


def storage_size(t):
    if t == T_CHAR:
        return 1
    if t == T_INT or is_ptr(t):
        return 4
    if is_arr(t):
        if t[2] is None:
            raise CompileError('array size required (only globals may omit it)')
        return t[2] * storage_size(t[1])
    if is_struct(t):
        return struct_size(t)
    return 0  # void


def base_size(b):
    # size of the pointee/element type b (used for pointer arithmetic)
    if b == T_CHAR:
        return 1
    if b == T_INT or is_ptr(b):
        return 4
    if is_arr(b) or is_struct(b):
        return storage_size(b)
    return 4


def struct_member(t, mname):
    members = STRUCT_MEMBERS.get(t[1])
    if members is None:
        raise CompileError('unknown struct ' + t[1])
    for mn, mt, mo in members:
        if mn == mname:
            return mt, mo
    raise CompileError('no member %s in struct %s' % (mname, t[1]))


# ---------- Lexer ----------
class Tok:
    __slots__ = ('k', 'v', 'pos')

    def __init__(self, k, v, pos=0):
        self.k, self.v, self.pos = k, v, pos


KEYWORDS = {
    'int': 'INT', 'char': 'CHAR', 'void': 'VOID',
    'return': 'RETURN', 'if': 'IF', 'else': 'ELSE',
    'while': 'WHILE', 'for': 'FOR', 'do': 'DO',
    'break': 'BREAK', 'continue': 'CONTINUE',
    'struct': 'STRUCT', 'switch': 'SWITCH', 'case': 'CASE',
    'default': 'DEFAULT', 'sizeof': 'SIZEOF', 'static': 'STATIC',
}

ESCAPES = {'n': 10, 't': 9, 'r': 13, '0': 0, 'a': 7, 'b': 8, 'f': 12,
           'v': 11, '\\': 92, "'": 39, '"': 34}


class Lexer:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def lex(self):
        s = self.s
        n = self.n
        out = []
        while self.i < n:
            c = s[self.i]
            if c.isspace():
                self.i += 1
                continue
            if c == '/' and self.i + 1 < n and s[self.i + 1] == '/':
                self.i += 2
                while self.i < n and s[self.i] not in '\r\n':
                    self.i += 1
                continue
            if c == '/' and self.i + 1 < n and s[self.i + 1] == '*':
                self.i += 2
                while self.i + 1 < n and not (s[self.i] == '*' and s[self.i + 1] == '/'):
                    self.i += 1
                if self.i + 1 >= n:
                    raise CompileError('unterminated comment')
                self.i += 2
                continue
            if c == '"':
                self.i += 1
                buf = bytearray()
                while True:
                    if self.i >= n:
                        raise CompileError('unterminated string')
                    ch = s[self.i]
                    if ch == '"':
                        self.i += 1
                        break
                    if ch == '\\':
                        self.i += 1
                        if self.i >= n:
                            raise CompileError('unterminated string')
                        e = s[self.i]
                        if e == 'x':
                            self.i += 1
                            hx = ''
                            while self.i < n and len(hx) < 2 and (s[self.i].isdigit() or s[self.i].lower() in 'abcdef'):
                                hx += s[self.i]
                                self.i += 1
                            if not hx:
                                raise CompileError('bad \\x escape')
                            buf.append(int(hx, 16) & 0xFF)
                        elif e in ESCAPES:
                            buf.append(ESCAPES[e])
                            self.i += 1
                        else:
                            raise CompileError('unknown escape \\%s' % e)
                    else:
                        buf.extend(ch.encode('utf-8'))
                        self.i += 1
                out.append(Tok('STR', bytes(buf), self.i))
                continue
            if c == "'":
                self.i += 1
                if self.i >= n:
                    raise CompileError('unterminated char literal')
                ch = s[self.i]
                if ch == '\\':
                    self.i += 1
                    if self.i >= n:
                        raise CompileError('bad char literal')
                    e = s[self.i]
                    if e == 'x':
                        self.i += 1
                        hx = ''
                        while self.i < n and len(hx) < 2 and (s[self.i].isdigit() or s[self.i].lower() in 'abcdef'):
                            hx += s[self.i]
                            self.i += 1
                        if not hx:
                            raise CompileError('bad \\x escape')
                        v = int(hx, 16)
                        self.i += 1
                    elif e in ESCAPES:
                        v = ESCAPES[e]
                        self.i += 1
                    else:
                        raise CompileError('unknown escape \\%s' % e)
                else:
                    v = ord(ch)
                    self.i += 1
                if self.i >= n or s[self.i] != "'":
                    raise CompileError('unterminated char literal')
                self.i += 1
                out.append(Tok('NUM', v, self.i))
                continue
            if c.isalpha() or c == '_':
                st = self.i
                self.i += 1
                while self.i < n and (s[self.i].isalpha() or s[self.i].isdigit() or s[self.i] == '_'):
                    self.i += 1
                w = s[st:self.i]
                out.append(Tok(KEYWORDS.get(w, 'ID'), w, st))
                continue
            if c.isdigit():
                st = self.i
                if c == '0' and self.i + 1 < n and s[self.i + 1] in 'xX':
                    self.i += 2
                    while self.i < n and (s[self.i].isdigit() or s[self.i].lower() in 'abcdef'):
                        self.i += 1
                    v = int(s[st:self.i], 16)
                else:
                    self.i += 1
                    while self.i < n and s[self.i].isdigit():
                        self.i += 1
                    v = int(s[st:self.i], 10)
                out.append(Tok('NUM', v, st))
                continue
            three = s[self.i:self.i + 3]
            if three in ('<<=', '>>=', '...'):
                out.append(Tok(three, three, self.i))
                self.i += 3
                continue
            two = s[self.i:self.i + 2]
            if two in ('==', '!=', '<=', '>=', '&&', '||', '<<', '>>',
                       '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '++', '--',
                       '->'):
                out.append(Tok(two, two, self.i))
                self.i += 2
                continue
            if c in '+-*/%<>=!;(),{}[]?:&|^~.':
                out.append(Tok(c, c, self.i))
                self.i += 1
                continue
            raise CompileError('unexpected character %r at %d' % (c, self.i))
        out.append(Tok('EOF', '', n))
        return out


# ---------- Parser ----------
class Parser:
    def __init__(self, t):
        self.t = t
        self.i = 0
        self.strings = []

    def cur(self):
        return self.t[self.i]

    def accept(self, k):
        if self.cur().k == k:
            x = self.cur()
            self.i += 1
            return x
        return None

    def expect(self, k):
        x = self.accept(k)
        if x is None:
            raise CompileError('expected %s, got %s at %d' % (k, self.cur().k, self.cur().pos))
        return x

    # --- declarations ---
    def type_spec(self):
        if self.accept('INT'):
            return T_INT
        if self.accept('CHAR'):
            return T_CHAR
        if self.accept('VOID'):
            return T_VOID
        if self.accept('STRUCT'):
            name = self.expect('ID').v
            if name not in STRUCT_MEMBERS:
                raise CompileError('unknown struct ' + name)
            return ('struct', name)
        raise CompileError('expected a type, got %s at %d' % (self.cur().k, self.cur().pos))

    def declarator(self, base):
        # returns (name, type); supports int a[2][3] (arrays of arrays)
        n = 0
        while self.accept('*'):
            n += 1
        name = self.expect('ID').v
        dims = []
        brackets = False
        while self.accept('['):
            brackets = True
            if self.cur().k == 'NUM':
                dims.append(self.expect('NUM').v)
            elif self.cur().k == ']':
                dims.append(None)
            else:
                raise CompileError('expected array size')
            self.expect(']')
        t = base
        for _ in range(n):
            t = ('ptr', t)
        if brackets:
            for d in reversed(dims):
                t = ('arr', t, d)
        return name, t

    def struct_def(self):
        # 'struct' keyword already consumed
        name = self.expect('ID').v
        if name in STRUCT_MEMBERS:
            raise CompileError('duplicate struct ' + name)
        STRUCT_MEMBERS[name] = []
        self.expect('{')
        while self.cur().k != '}':
            if self.cur().k == 'EOF':
                raise CompileError('unterminated struct')
            base = self.type_spec()
            while True:
                mn, mt = self.declarator(base)
                if mt == T_VOID:
                    raise CompileError('void struct member')
                if is_arr(mt) and mt[2] is None:
                    raise CompileError('array size required in struct')
                if is_struct(mt) and mt[1] not in STRUCT_SIZES:
                    raise CompileError('recursive or forward-referenced struct %s' % mt[1])
                STRUCT_MEMBERS[name].append((mn, mt, 0))
                if not self.accept(','):
                    break
            self.expect(';')
        self.expect('}')
        self.expect(';')
        # compute member offsets and total size (4-aligned)
        off = 0
        for i in range(len(STRUCT_MEMBERS[name])):
            mn, mt, _ = STRUCT_MEMBERS[name][i]
            sz = storage_size(mt)
            off = align_up(off, type_align(mt))
            STRUCT_MEMBERS[name][i] = (mn, mt, off)
            off += sz
        STRUCT_SIZES[name] = align_up(off, 4)

    def is_function_def(self):
        # after a type spec, is the next declarator followed by '(' ?
        # (handles pointer return types: `char* f(...)`)
        t = self.t
        i = self.i
        while i < len(t) and t[i].k == '*':
            i += 1
        if i < len(t) and t[i].k == 'ID':
            i += 1
            if i < len(t) and t[i].k == '(':
                return True
        return False

    def parse(self):
        functions = []
        globals_ = []
        while self.cur().k != 'EOF':
            self.accept('STATIC')        # file-scope static: no linkage model
            if self.cur().k == 'STRUCT' and self.t[self.i + 2].k == '{':
                self.i += 1            # consume 'struct'
                self.struct_def()
                continue
            base = self.type_spec()
            if self.is_function_def():
                # function definition (may return a pointer)
                name, ret = self.declarator(base)
                if is_arr(ret):
                    raise CompileError('functions cannot return arrays')
                self.expect('(')
                params = []
                variadic = False
                if self.cur().k != ')':
                    while True:
                        if self.cur().k == '...':
                            self.i += 1
                            variadic = True
                            break
                        pb = self.type_spec()
                        if pb == T_VOID:
                            # 'void' alone as a parameter list means empty
                            break
                        pn, pt = self.declarator(pb)
                        if is_arr(pt):
                            pt = ('ptr', pt[1])  # array params decay to pointers
                        if is_struct(pt):
                            raise CompileError('struct %s passed by value; use a pointer' % pn)
                        params.append((pn, pt))
                        if not self.accept(','):
                            break
                if len(params) > 4:
                    raise CompileError('maximum 4 parameters (variadic extras go on the stack)')
                self.expect(')')
                functions.append(('fn', name, ret, params, self.block(), variadic))
            else:
                # global variable declaration: name [, name]... ;
                while True:
                    nm, tp = self.declarator(base)
                    init = None
                    if self.accept('='):
                        if self.cur().k == '{':
                            self.i += 1
                            vals = []
                            if self.cur().k != '}':
                                while True:
                                    v = self.expect('NUM').v
                                    vals.append(v)
                                    if not self.accept(','):
                                        break
                            self.expect('}')
                            init = ('arr_init', vals)
                        else:
                            init = ('e', self.expr())
                    globals_.append((nm, tp, init))
                    if not self.accept(','):
                        break
                self.expect(';')
        return functions, globals_, self.strings

    # --- statements ---
    def block(self):
        self.expect('{')
        out = []
        while self.cur().k != '}':
            if self.cur().k == 'EOF':
                raise CompileError('unterminated block')
            out.append(self.stmt())
        self.expect('}')
        return out

    def fix_decl_type(self, tp, init):
        # incomplete array [] with an initializer gets its size inferred
        if is_arr(tp) and tp[2] is None:
            if init is not None and init[0] == 'e' and init[1][0] == 'str':
                return ('arr', tp[1], len(self.strings[init[1][1]]) + 1)
            if init is not None and init[0] == 'arr_init':
                return ('arr', tp[1], len(init[1]))
            raise CompileError('array size required')
        return tp

    def stmt(self):
        if self.accept(';'):
            return ('empty',)
        if self.cur().k == '{':
            return ('block', self.block())
        if self.cur().k == 'STRUCT' and self.t[self.i + 1].k == '{':
            raise CompileError('struct definitions are only supported at top level')
        if self.accept('STATIC'):
            base = self.type_spec()
            nm, tp = self.declarator(base)
            if tp == T_VOID:
                raise CompileError('cannot declare a void variable')
            init = None
            if self.accept('='):
                if self.cur().k == '{':
                    self.i += 1
                    vals = []
                    if self.cur().k != '}':
                        while True:
                            vals.append(self.expect('NUM').v)
                            if not self.accept(','):
                                break
                    self.expect('}')
                    init = ('arr_init', vals)
                else:
                    init = ('e', self.expr())
            tp = self.fix_decl_type(tp, init)
            self.expect(';')
            return ('static_decl', nm, tp, init)
        if self.cur().k in ('INT', 'CHAR', 'VOID', 'STRUCT'):
            base = self.type_spec()
            out = []
            while True:
                nm, tp = self.declarator(base)
                if tp == T_VOID:
                    raise CompileError('cannot declare a void variable')
                init = None
                if self.accept('='):
                    if self.cur().k == '{':
                        self.i += 1
                        vals = []
                        if self.cur().k != '}':
                            while True:
                                vals.append(self.expect('NUM').v)
                                if not self.accept(','):
                                    break
                        self.expect('}')
                        init = ('arr_init', vals)
                    else:
                        init = ('e', self.expr())
                tp = self.fix_decl_type(tp, init)
                out.append(('decl', nm, tp, init))
                if not self.accept(','):
                    break
            self.expect(';')
            if len(out) == 1:
                return out[0]
            return ('decls', out)
        if self.accept('RETURN'):
            x = None if self.cur().k == ';' else self.expr()
            self.expect(';')
            return ('return', x)
        if self.accept('IF'):
            self.expect('(')
            c = self.expr()
            self.expect(')')
            a = self.stmt()
            b = self.stmt() if self.accept('ELSE') else None
            return ('if', c, a, b)
        if self.accept('WHILE'):
            self.expect('(')
            c = self.expr()
            self.expect(')')
            return ('while', c, self.stmt())
        if self.accept('DO'):
            body = self.stmt()
            self.expect('WHILE')
            self.expect('(')
            c = self.expr()
            self.expect(')')
            self.expect(';')
            return ('dowhile', body, c)
        if self.accept('BREAK'):
            self.expect(';')
            return ('break',)
        if self.accept('CONTINUE'):
            self.expect(';')
            return ('continue',)
        if self.accept('FOR'):
            self.expect('(')
            init = None
            cond = None
            inc = None
            if self.cur().k in ('INT', 'CHAR', 'VOID', 'STRUCT'):
                base = self.type_spec()
                nm, tp = self.declarator(base)
                if tp == T_VOID:
                    raise CompileError('cannot declare a void variable')
                iv = None
                if self.accept('='):
                    iv = ('e', self.expr())
                tp = self.fix_decl_type(tp, iv)
                init = ('decl', nm, tp, iv)
            elif self.cur().k != ';':
                init = ('e', self.expr())
            self.expect(';')
            if self.cur().k != ';':
                cond = self.expr()
            self.expect(';')
            if self.cur().k != ')':
                inc = self.expr()
            self.expect(')')
            return ('for', init, cond, inc, self.stmt())
        if self.accept('SWITCH'):
            self.expect('(')
            c = self.expr()
            self.expect(')')
            self.expect('{')
            items = []        # body statements in order
            labels = []       # (case_value_or_None, item_index)
            while self.cur().k != '}':
                if self.cur().k == 'EOF':
                    raise CompileError('unterminated switch')
                if self.accept('CASE'):
                    neg = self.accept('-')
                    v = self.expect('NUM').v
                    if neg:
                        v = -v
                    self.expect(':')
                    labels.append((v, len(items)))
                elif self.accept('DEFAULT'):
                    self.expect(':')
                    labels.append((None, len(items)))
                else:
                    items.append(self.stmt())
            self.expect('}')
            return ('switch', c, labels, items)
        x = self.expr()
        self.expect(';')
        return ('e', x)

    # --- expressions (C precedence) ---
    def expr(self):
        return self.assign()

    def assign(self):
        x = self.ternary()
        if self.cur().k in ASSIGN_OPS:
            op = self.cur().k
            self.i += 1
            if not self.is_lvalue(x):
                raise CompileError('left side of %s must be a variable, *p or a[i]' % op)
            return ('assign', op, x, self.assign())
        return x

    def is_lvalue(self, x):
        k = x[0]
        if k == 'var':
            return True
        if k == 'un' and x[1] == '*':
            return True
        if k == 'index':
            return True
        if k == 'member':
            return True
        return False

    def ternary(self):
        x = self.logic_or()
        if self.accept('?'):
            a = self.expr()
            self.expect(':')
            b = self.ternary()
            return ('tern', x, a, b)
        return x

    def logic_or(self):
        x = self.logic_and()
        while self.accept('||'):
            x = ('bin', '||', x, self.logic_and())
        return x

    def logic_and(self):
        x = self.bitor()
        while self.accept('&&'):
            x = ('bin', '&&', x, self.bitor())
        return x

    def bitor(self):
        x = self.bitxor()
        while self.accept('|'):
            x = ('bin', '|', x, self.bitxor())
        return x

    def bitxor(self):
        x = self.bitand()
        while self.accept('^'):
            x = ('bin', '^', x, self.bitand())
        return x

    def bitand(self):
        x = self.eq()
        while self.accept('&'):
            x = ('bin', '&', x, self.eq())
        return x

    def eq(self):
        x = self.rel()
        while self.cur().k in ('==', '!='):
            op = self.cur().k
            self.i += 1
            x = ('bin', op, x, self.rel())
        return x

    def rel(self):
        x = self.shift()
        while self.cur().k in ('<', '>', '<=', '>='):
            op = self.cur().k
            self.i += 1
            x = ('bin', op, x, self.shift())
        return x

    def shift(self):
        x = self.add()
        while self.cur().k in ('<<', '>>'):
            op = self.cur().k
            self.i += 1
            x = ('bin', op, x, self.add())
        return x

    def add(self):
        x = self.mul()
        while self.cur().k in ('+', '-'):
            op = self.cur().k
            self.i += 1
            x = ('bin', op, x, self.mul())
        return x

    def mul(self):
        x = self.unary()
        while self.cur().k in ('*', '/', '%'):
            op = self.cur().k
            self.i += 1
            x = ('bin', op, x, self.unary())
        return x

    def parse_type_name(self):
        # parse a type-name used by casts and sizeof: base type + '*'s
        if self.cur().k in ('INT', 'CHAR', 'VOID'):
            base = self.type_spec()
            while self.accept('*'):
                base = ('ptr', base)
            return base
        if self.cur().k == 'STRUCT':
            base = self.type_spec()
            while self.accept('*'):
                base = ('ptr', base)
            return base
        return None

    def unary(self):
        if self.accept('SIZEOF'):
            if self.cur().k == '(':
                self.i += 1
                save = self.i
                tp = self.parse_type_name()
                if tp is not None and self.accept(')'):
                    return ('sizeof', ('t', tp))
                self.i = save
                x = self.expr()
                self.expect(')')
                return ('sizeof', ('e', x))
            return ('sizeof', ('e', self.unary()))   # sizeof expr (no parens)
        if self.cur().k == '(' and self.t[self.i + 1].k in ('INT', 'CHAR', 'VOID', 'STRUCT'):
            save = self.i
            self.i += 1                       # consume '('
            tp = self.parse_type_name()
            if tp is not None and self.accept(')'):
                return ('cast', tp, self.unary())
            self.i = save                     # not a cast: plain grouping
        if self.accept('++'):
            return ('incdec', True, '+', self.unary())
        if self.accept('--'):
            return ('incdec', True, '-', self.unary())
        if self.accept('-'):
            return ('un', '-', self.unary())
        if self.accept('!'):
            return ('un', '!', self.unary())
        if self.accept('~'):
            return ('un', '~', self.unary())
        if self.accept('*'):
            return ('un', '*', self.unary())
        if self.accept('&'):
            return ('un', '&', self.unary())
        if self.accept('+'):
            return self.unary()
        return self.postfix()

    def postfix(self):
        x = self.primary()
        while True:
            if self.accept('['):
                idx = self.expr()
                self.expect(']')
                x = ('index', x, idx)
            elif self.accept('.'):
                mname = self.expect('ID').v
                x = ('member', x, mname, False)
            elif self.accept('->'):
                mname = self.expect('ID').v
                x = ('member', x, mname, True)
            elif self.accept('++'):
                if not self.is_lvalue(x):
                    raise CompileError('++ needs an lvalue')
                x = ('incdec', False, '+', x)
            elif self.accept('--'):
                if not self.is_lvalue(x):
                    raise CompileError('-- needs an lvalue')
                x = ('incdec', False, '-', x)
            else:
                break
        return x

    def primary(self):
        x = self.accept('NUM')
        if x is not None:
            return ('num', x.v)
        x = self.accept('STR')
        if x is not None:
            self.strings.append(x.v)
            return ('str', len(self.strings) - 1)
        x = self.accept('ID')
        if x is not None:
            if self.accept('('):
                args = []
                if self.cur().k != ')':
                    while True:
                        args.append(self.expr())
                        if not self.accept(','):
                            break
                self.expect(')')
                return ('call', x.v, args)
            return ('var', x.v)
        if self.accept('('):
            x = self.expr()
            self.expect(')')
            return x
        raise CompileError('expected expression at %d' % self.cur().pos)


# ---------- ARM instruction encoders ----------
def ror32(x, n):
    if n:
        return ((x >> n) | (x << (32 - n))) & 0xffffffff
    return x & 0xffffffff


def arm_imm12(v):
    v &= 0xffffffff
    for rot in range(16):
        for imm8 in range(256):
            if ror32(imm8, 2 * rot) == v:
                return imm8 | (rot << 8)
    return None


def dp_imm(opcode, rn, rd, imm, S=0, cond=14):
    x = arm_imm12(imm)
    if x is None:
        return None
    return (cond << 28) | (1 << 25) | (opcode << 21) | (S << 20) | (rn << 16) | (rd << 12) | x


def dp_reg(opcode, rn, rd, rm, S=0, cond=14):
    return (cond << 28) | (opcode << 21) | (S << 20) | (rn << 16) | (rd << 12) | rm


def cmp_imm(rn, imm):
    return dp_imm(10, rn, 0, imm, S=1)


def dp_shift_imm(opcode, rn, rd, rm, shift_type, shift, S=0, cond=14):
    return ((cond << 28) | (opcode << 21) | (S << 20) | (rn << 16) | (rd << 12) |
            ((shift & 31) << 7) | (shift_type << 5) | rm)


def mov_lsl(e, rd, rm, sh):
    e.emit(dp_shift_imm(13, 0, rd, rm, 0, sh))


def mov_lsr(e, rd, rm, sh):
    e.emit(dp_shift_imm(13, 0, rd, rm, 1, sh))


def push(mask):
    return 0xE92D0000 | mask


def pop(mask):
    return 0xE8BD0000 | mask


def ldr_str(load, rn, rd, off):
    # word load/store with immediate offset (pre-indexed), U bit set for >=0
    if abs(off) > 4095:
        raise CompileError('stack offset too large')
    u = 1 if off >= 0 else 0
    base = 0xE5100000 if load else 0xE5000000
    if u:
        base |= (1 << 23)
    return base | (rn << 16) | (rd << 12) | abs(off)


def ldrb_str(load, rn, rd, off):
    # byte load/store with immediate offset
    if abs(off) > 4095:
        raise CompileError('stack offset too large')
    u = 1 if off >= 0 else 0
    base = 0xE5500000 if load else 0xE5400000
    if u:
        base |= (1 << 23)
    return base | (rn << 16) | (rd << 12) | abs(off)


def enc_cmp_reg(rn, rm):
    return (14 << 28) | (1 << 20) | (10 << 21) | (rn << 16) | rm


class Emitter:
    def __init__(self):
        self.w = []
        self.labels = {}
        self.fixes = []
        self.pool = []           # pending literal requests: (ldr_pos, rd, kind, key)
        self.pool_entries = []   # emitted pool words: (word_idx, kind, key)
        self.pool_ok = False

    def off(self):
        return len(self.w) * 4

    def emit(self, x):
        self.w.append(x & 0xffffffff)

    def label(self, n):
        self.labels[n] = self.off()

    def branch(self, cond, label, link=False):
        pos = self.off()
        self.emit(0)
        self.fixes.append((pos, cond, label, link))

    def begin_fn(self):
        self.pool = []
        self.pool_ok = True

    def lit(self, rd, kind, key):
        # load address/constant from the function literal pool into rd
        if not self.pool_ok:
            raise CompileError('literal pool not available here')
        pos = self.off()
        self.emit(0)
        self.pool.append((pos, rd, kind, key))

    def emit_pool(self):
        for (pos, rd, kind, key) in self.pool:
            idx = len(self.w)
            if kind == 'c':
                self.w.append(key & 0xffffffff)
                self.pool_entries.append((idx, None, None))
            else:
                self.w.append(0)
                self.pool_entries.append((idx, kind, key))
            off = idx * 4 - (pos + 8)
            if off < 0 or off > 4095:
                raise CompileError('literal pool entry too far')
            self.w[pos // 4] = 0xE59F0000 | (rd << 12) | off
        self.pool = []

    def resolve_branches(self):
        for pos, cond, label, link in self.fixes:
            if label not in self.labels:
                raise CompileError('unknown label ' + label)
            delta = (self.labels[label] - (pos + 8)) // 4
            if delta < -0x800000 or delta >= 0x800000:
                raise CompileError('branch out of range')
            op = (0xEB000000 if link else 0xEA000000) | (delta & 0xffffff)
            self.w[pos // 4] = (cond << 28) | (op & 0x0fffffff)


def mov_imm(e, rd, val, pool_ok=True):
    val &= 0xffffffff
    c = dp_imm(13, 0, rd, val)
    if c is not None:
        e.emit(c)
        return
    cands = []
    for sh in (0, 8, 16, 24):
        b = (val >> sh) & 255
        if b:
            cands.append((sh, b))
    encs = []
    ok = True
    for sh, b in cands:
        if not encs:
            c = dp_imm(13, 0, rd, b << sh)        # mov rd, #b<<sh
        else:
            c = dp_imm(12, rd, rd, b << sh)        # orr rd, rd, #b<<sh
        if c is None:
            ok = False
            break
        encs.append(c)
    if ok and encs:
        for c in encs:
            e.emit(c)
        return
    if not cands:
        e.emit(dp_imm(13, 0, rd, 0))
        return
    if pool_ok:
        e.lit(rd, 'c', val)
        return
    raise CompileError('cannot encode constant 0x%08X' % val)


def rsb_zero(e, rd):
    e.emit(dp_imm(3, rd, rd, 0))


# ---------- Code generation ----------
class FnCtx:
    def __init__(self, name, ret, params, body):
        self.name = name
        self.ret = ret
        self.params = params
        self.body = body
        self.frame = 0

    def alloc(self, t):
        # returns negative frame offset for a new slot of type t
        sz = storage_size(t)
        al = 4 if (t == T_INT or is_ptr(t)) else 1
        if is_arr(t):
            al = base_size(t[1])
        f = self.frame
        if al == 4:
            f = (f + 3) & ~3
        off = -(f + sz)
        self.frame = f + sz
        return off


BUILTINS = ('__svc', '__sleep')


class CodeGen:
    def __init__(self, functions, globals_, strings):
        self.functions = {}
        for f in functions:
            if f[1] in self.functions:
                raise CompileError('duplicate function ' + f[1])
            if f[1] in BUILTINS:
                raise CompileError('cannot redefine builtin ' + f[1])
            self.functions[f[1]] = f
        if 'main' not in self.functions:
            raise CompileError('main() required')
        self.globals = {}
        for g in globals_:
            if g[0] in self.globals:
                raise CompileError('duplicate global ' + g[0])
            self.globals[g[0]] = g
        self.strings = strings
        self.e = Emitter()
        self.labels = 0
        self.scopes = [{}]     # scope stack: dict name -> (offset, type)
        self.scope_of = {}     # id(block/for tuple) -> its scope dict (shared between passes)
        self.cur = None
        self.breaks = []      # stack of break-target labels (loops and switches)
        self.continues = []  # stack of continue-target labels (loops only)
        self.svc_wrappers = {} # syscall immediate -> wrapper label

    def new(self, p):
        self.labels += 1
        return '.L_%s_%d' % (p, self.labels)

    # --- symbol resolution ---
    def lookup(self, name):
        for sc in reversed(self.scopes):
            if name in sc:
                return sc[name]
        return None

    def var_info(self, name):
        # scope entries: ('l', offset, type) locals, ('g', gname, type) statics
        loc = self.lookup(name)
        if loc is not None:
            if loc[0] == 'g':
                return ('global', loc[1], loc[2])
            return ('local', loc[1], loc[2])
        if name in self.globals:
            return ('global', name, self.globals[name][1])
        raise CompileError('unknown variable ' + name)

    def var_type(self, name):
        return self.var_info(name)[2]

    def typeof(self, x):
        k = x[0]
        if k == 'num':
            return T_INT
        if k == 'str':
            return ('ptr', T_CHAR)
        if k == 'var':
            t = self.var_type(x[1])
            if is_arr(t):
                return ('ptr', t[1])
            return t
        if k == 'sizeof':
            kind, val = x[1]
            if kind == 't':
                return T_INT
            return T_INT
        if k == 'member':
            bt = self.typeof(x[1])
            if x[3]:                                  # ->
                if not is_ptr(bt) or not is_struct(bt[1]):
                    raise CompileError('-> requires a pointer to a struct')
                bt = bt[1]
            elif not is_struct(bt):
                raise CompileError('. requires a struct value')
            mt, _ = struct_member(bt, x[2])
            if is_arr(mt):
                return ('ptr', mt[1])
            return mt
        if k == 'call':
            if x[1] in BUILTINS:
                return T_INT
            return self.functions[x[1]][1]
        if k == 'un':
            op = x[1]
            if op == '*':
                t = self.typeof(x[2])
                if not is_ptr(t):
                    raise CompileError('cannot dereference non-pointer')
                return t[1]
            if op == '&':
                t = self.var_type(x[2][1]) if x[2][0] == 'var' else self.typeof(x[2])
                return ('ptr', t)
            return T_INT
        if k == 'index':
            t = self.typeof(x[1])
            if is_ptr(t):
                return t[1]
            if is_arr(t):
                return t[1]
            raise CompileError('cannot index non-array')
        if k == 'cast':
            return x[1]
        if k == 'bin':
            op = x[1]
            lt = self.typeof(x[2])
            rt = self.typeof(x[3])
            if op in ('+', '-'):
                if is_ptr(lt):
                    return lt
                if op == '+' and is_ptr(rt):
                    return rt
            return T_INT
        if k == 'assign':
            return self.typeof(x[2])
        if k == 'tern':
            lt = self.typeof(x[2])
            rt = self.typeof(x[3])
            if is_ptr(lt) and is_ptr(rt):
                return lt
            return T_INT
        if k == 'incdec':
            return self.typeof(x[3])
        raise CompileError('bad expression node')

    # --- frame pre-pass: allocate locals into fn.frame + scope tables ---
    def alloc_pass(self, stmts):
        for s in stmts:
            k = s[0]
            if k == 'decl':
                if s[1] in self.scopes[-1]:
                    raise CompileError('redeclaration of ' + s[1])
                off = self.cur.alloc(s[2])
                self.scopes[-1][s[1]] = ('l', off, s[2])
            elif k == 'static_decl':
                # static local: storage lives in .data, one copy per function
                gname = self.cur.name + '.' + s[1]
                init = s[3]
                if init is not None and init[0] == 'e':
                    init = init[1]
                if init is not None and init[0] not in ('num', 'str', 'arr_init'):
                    raise CompileError('static initializer must be constant')
                self.globals[gname] = (gname, s[2], init)
                self.scopes[-1][s[1]] = ('g', gname, s[2])
            elif k == 'decls':
                for d in s[1]:
                    if d[1] in self.scopes[-1]:
                        raise CompileError('redeclaration of ' + d[1])
                    off = self.cur.alloc(d[2])
                    self.scopes[-1][d[1]] = ('l', off, d[2])
            elif k == 'block':
                sc = {}
                self.scope_of[id(s)] = sc
                self.scopes.append(sc)
                self.alloc_pass(s[1])
                self.scopes.pop()
            elif k == 'if':
                self.alloc_pass([s[2]])
                if s[3]:
                    self.alloc_pass([s[3]])
            elif k == 'while':
                self.alloc_pass([s[2]])
            elif k == 'dowhile':
                self.alloc_pass([s[1]])
            elif k == 'for':
                sc = {}
                self.scope_of[id(s)] = sc
                self.scopes.append(sc)
                if s[1] and s[1][0] == 'decl':
                    off = self.cur.alloc(s[1][2])
                    sc[s[1][1]] = ('l', off, s[1][2])
                self.alloc_pass([s[4]])
                self.scopes.pop()
            elif k == 'switch':
                self.alloc_pass(s[3])

    def compile(self):
        e = self.e
        main_idx = None
        for f in self.functions.values():
            self.gen_fn(f)
            if f[1] == 'main':
                main_idx = e.labels[f[1]]
        # runtime helpers (no literal pools)
        e.pool_ok = False
        self.gen_idiv_helper('__aeabi_idiv', False)
        self.gen_idiv_helper('__aeabi_idivmod', True)
        # firmware syscall wrappers: push {r0}; push {lr}; svc
        for imm in sorted(self.svc_wrappers):
            lab = self.svc_wrappers[imm]
            e.label(lab)
            e.emit(push(1 << 0))              # push {r0}  (firmware expects r0 on stack)
            e.emit(push(1 << 14))             # push {lr}  (handler returns via this)
            e.emit(0xEF000000 | (imm & 0xFFFFFF))
        e.pool_ok = True
        e.resolve_branches()
        return e.w, main_idx, e.pool_entries

    def svc_wrapper(self, imm):
        imm &= 0xFFFFFF
        if imm not in self.svc_wrappers:
            self.svc_wrappers[imm] = '.Lsvc_%06X' % imm
        return self.svc_wrappers[imm]

    def gen_fn(self, f):
        e = self.e
        name = f[1]
        ret = f[2]
        e.begin_fn()
        e.label(name)
        self.cur = FnCtx(name, ret, f[3], f[4])
        e.emit(push((1 << 4) | (1 << 11) | (1 << 14)))   # push {r4, fp, lr}
        e.emit(dp_reg(13, 0, 11, 13))                     # mov fp, sp
        pro = e.off()
        for _ in range(8):                                # prologue sub sp slots
            e.emit(0xE1A00000)                            # nop placeholder
        # params (base scope)
        self.scopes = [{}]
        self.scope_of = {}
        for i, (pn, pt) in enumerate(f[3]):
            if pn in self.scopes[0]:
                raise CompileError('duplicate parameter ' + pn)
            off = self.cur.alloc(pt)
            self.scopes[0][pn] = ('l', off, pt)
            if pt == T_CHAR:
                e.emit(ldrb_str(False, 11, i, off))
            else:
                e.emit(ldr_str(False, 11, i, off))
        # locals (allocation pass then codegen pass, same scope objects)
        self.alloc_pass(f[4])
        self.gen_stmts(f[4])
        # default return
        if ret != T_VOID:
            mov_imm(e, 0, 0)
        retl = '.Lret_' + name
        e.branch(14, retl)
        e.label(retl)
        self.adjust_sp(self.cur.frame)
        e.emit(pop((1 << 4) | (1 << 11) | (1 << 15)))
        # patch prologue subs (max 8 * 0x1000 = 32 KB frame)
        subs = []
        frm = self.cur.frame
        while frm >= 0x1000:
            subs.append(0x1000)
            frm -= 0x1000
        if frm:
            subs.append(frm)
        if len(subs) > 8:
            raise CompileError('frame too large')
        for i in range(8):
            if i < len(subs):
                c = dp_imm(2, 13, 13, subs[i])
                if c is None:
                    raise CompileError('frame too large')
                e.w[pro // 4 + i] = c
            else:
                e.w[pro // 4 + i] = 0xE1A00000
        e.emit_pool()
        self.cur = None

    def adjust_sp(self, delta):
        # add sp, sp, #delta at function end
        e = self.e
        while delta >= 0x1000:
            e.emit(dp_imm(4, 13, 13, 0x1000))
            delta -= 0x1000
        if delta:
            c = dp_imm(4, 13, 13, delta)
            if c is None:
                raise CompileError('frame too large')
            e.emit(c)

    def gen_idiv_helper(self, name, want_rem):
        # Signed restoring division: r0=a, r1=b. Result in r0.
        # Preserves r4-r10 (callee-saved). Division by zero returns 0.
        e = self.e
        e.label(name)
        e.emit(push((1 << 4) | (1 << 5) | (1 << 6) | (1 << 7) |
                    (1 << 8) | (1 << 9) | (1 << 10) | (1 << 14)))
        e.emit(dp_reg(13, 0, 4, 0))   # mov r4, r0   (a)
        e.emit(dp_reg(13, 0, 5, 1))   # mov r5, r1   (b)
        mov_imm(e, 6, 0)
        zero = self.new('dz')
        e.emit(cmp_imm(5, 0))
        e.branch(0, zero)
        # r8 = dividend negative flag, r6 = quotient negative flag
        mov_imm(e, 8, 0)
        apos = self.new('dap')
        e.emit(cmp_imm(4, 0))
        e.branch(10, apos)
        mov_imm(e, 8, 1)
        rsb_zero(e, 4)
        mov_imm(e, 6, 1)
        e.label(apos)
        bpos = self.new('dbp')
        e.emit(cmp_imm(5, 0))
        e.branch(10, bpos)
        rsb_zero(e, 5)
        e.emit(cmp_imm(6, 0))
        tog0 = self.new('dt0')
        e.branch(0, tog0)
        mov_imm(e, 6, 0)
        aft = self.new('dat')
        e.branch(14, aft)
        e.label(tog0)
        mov_imm(e, 6, 1)
        e.label(aft)
        e.label(bpos)
        # r3=quotient r7=remainder r9=count r10=topbit
        mov_imm(e, 3, 0)
        mov_imm(e, 7, 0)
        mov_imm(e, 9, 32)
        loop = self.new('dlp')
        nosub = self.new('dns')
        finish = self.new('dfn')
        e.label(loop)
        mov_lsl(e, 3, 3, 1)        # q <<= 1
        mov_lsr(e, 10, 4, 31)
        mov_lsl(e, 7, 7, 1)
        e.emit(dp_reg(4, 7, 7, 10))    # add r7, r7, r10
        mov_lsl(e, 4, 4, 1)
        e.emit(enc_cmp_reg(7, 5))      # cmp r7, r5  (sets flags)
        e.branch(3, nosub)             # blo (unsigned): skip subtract
        e.emit(dp_reg(2, 7, 7, 5))     # sub r7, r7, r5
        e.emit(dp_imm(12, 3, 3, 1))    # orr r3, r3, #1
        e.label(nosub)
        e.emit(dp_imm(2, 9, 9, 1, S=1))  # subs r9, r9, #1
        e.branch(1, loop)              # bne loop
        e.emit(cmp_imm(6, 0))
        qpos = self.new('dqp')
        e.branch(0, qpos)
        rsb_zero(e, 3)
        e.label(qpos)
        if want_rem:
            rpos = self.new('drp')
            e.emit(cmp_imm(8, 0))
            e.branch(0, rpos)
            rsb_zero(e, 7)
            e.label(rpos)
            e.emit(dp_reg(13, 0, 0, 7))   # mov r0, r7 (remainder)
        else:
            e.emit(dp_reg(13, 0, 0, 3))   # mov r0, r3 (quotient)
        e.branch(14, finish)
        e.label(zero)
        mov_imm(e, 0, 0)
        e.label(finish)
        e.emit(pop((1 << 4) | (1 << 5) | (1 << 6) | (1 << 7) |
                   (1 << 8) | (1 << 9) | (1 << 10) | (1 << 15)))

    # ---------- statements ----------
    def gen_stmts(self, stmts):
        for s in stmts:
            self.gen_stmt(s)

    def gen_stmt(self, s):
        e = self.e
        k = s[0]
        if k == 'empty':
            return
        if k == 'block':
            self.scopes.append(self.scope_of.get(id(s), {}))
            self.gen_stmts(s[1])
            self.scopes.pop()
            return
        if k == 'decl':
            if is_struct(s[2]):
                # struct variables: no initializer (contents undefined) or
                # a struct-copy initializer `struct P t = other;`
                if s[3] is not None:
                    self.gen_struct_copy(('var', s[1]), s[3][1], s[2])
                return
            if is_arr(s[2]):
                if s[3] is None:
                    return  # uninitialized local array (contents undefined, as in C)
                ex = s[3]
                if ex[0] == 'e':
                    ex = ex[1]
                off = self.var_info(s[1])[1]
                if ex[0] == 'str':
                    # copy the string literal (including NUL) into the array
                    b = self.strings[ex[1]]
                    for i in range(len(b)):
                        mov_imm(e, 0, b[i])
                        e.emit(ldrb_str(False, 11, 0, off + i))
                    mov_imm(e, 0, 0)
                    e.emit(ldrb_str(False, 11, 0, off + len(b)))
                    return
                if ex[0] == 'arr_init':
                    vals = ex[1]
                    sz = base_size(s[2][1])
                    for i, v in enumerate(vals):
                        mov_imm(e, 0, v)
                        if sz == 1:
                            e.emit(ldrb_str(False, 11, 0, off + i))
                        else:
                            e.emit(ldr_str(False, 11, 0, off + i * 4))
                    return
                raise CompileError('local array initializers not supported')
            if s[3] is not None:
                self.gen_expr(s[3][1])
                self.store_var(s[1])
            return
        if k == 'static_decl':
            # storage is in .data, initialized at load time - nothing to emit
            return
        if k == 'decls':
            for d in s[1]:
                self.gen_stmt(d)
            return
        if k == 'e':
            self.gen_expr(s[1])
            return
        if k == 'return':
            if s[1] is None:
                if self.cur.ret != T_VOID:
                    mov_imm(e, 0, 0)
            else:
                if self.cur.ret == T_VOID:
                    raise CompileError('void function cannot return a value')
                self.gen_expr(s[1])
            e.branch(14, '.Lret_' + self.cur.name)
            return
        if k == 'if':
            lel = self.new('el')
            lend = self.new('ie')
            self.gen_expr(s[1])
            e.emit(cmp_imm(0, 0))
            e.branch(0, lel)
            self.gen_stmt(s[2])
            e.branch(14, lend)
            e.label(lel)
            if s[3]:
                self.gen_stmt(s[3])
            e.label(lend)
            return
        if k == 'while':
            lt = self.new('wl')
            le = self.new('we')
            e.label(lt)
            self.gen_expr(s[1])
            e.emit(cmp_imm(0, 0))
            e.branch(0, le)
            self.breaks.append(le)
            self.continues.append(lt)
            self.gen_stmt(s[2])
            self.breaks.pop()
            self.continues.pop()
            e.branch(14, lt)
            e.label(le)
            return
        if k == 'dowhile':
            lt = self.new('dl')
            lc = self.new('dc')
            le = self.new('de')
            e.label(lt)
            self.breaks.append(le)
            self.continues.append(lc)
            self.gen_stmt(s[1])
            self.breaks.pop()
            self.continues.pop()
            e.label(lc)
            self.gen_expr(s[2])
            e.emit(cmp_imm(0, 0))
            e.branch(1, lt)
            e.label(le)
            return
        if k == 'for':
            self.scopes.append(self.scope_of.get(id(s), {}))
            if s[1]:
                self.gen_stmt(s[1])
            lt = self.new('fl')
            lc = self.new('fc')
            le = self.new('fe')
            e.label(lt)
            if s[2]:
                self.gen_expr(s[2])
                e.emit(cmp_imm(0, 0))
                e.branch(0, le)
            self.breaks.append(le)
            self.continues.append(lc)
            self.gen_stmt(s[4])
            self.breaks.pop()
            self.continues.pop()
            e.label(lc)
            if s[3]:
                self.gen_expr(s[3])
            e.branch(14, lt)
            e.label(le)
            self.scopes.pop()
            return
        if k == 'switch':
            # switch value kept in r4 (callee-saved, untouched by expression
            # code and preserved across function calls)
            self.gen_expr(s[1])
            e.emit(dp_reg(13, 0, 4, 0))        # mov r4, r0
            labels = s[2]
            lend = self.new('sw')
            case_labels = [self.new('cs') for _ in labels]
            for i, (v, _idx) in enumerate(labels):
                if v is not None:
                    mov_imm(e, 0, v)
                    e.emit(enc_cmp_reg(0, 4))  # cmp r0, r4
                    e.branch(0, case_labels[i])
            def_idx = None
            for i, (v, _idx) in enumerate(labels):
                if v is None:
                    def_idx = i
                    break
            if def_idx is not None:
                e.branch(14, case_labels[def_idx])
            else:
                e.branch(14, lend)
            self.breaks.append(lend)
            by_idx = {}
            for i, (v, idx) in enumerate(labels):
                by_idx.setdefault(idx, []).append(case_labels[i])
            for k2, st in enumerate(s[3]):
                for lab in by_idx.get(k2, []):
                    e.label(lab)
                self.gen_stmt(st)
            for lab in by_idx.get(len(s[3]), []):
                e.label(lab)
            self.breaks.pop()
            e.label(lend)
            return
        if k == 'break':
            if not self.breaks:
                raise CompileError('break outside loop or switch')
            e.branch(14, self.breaks[-1])
            return
        if k == 'continue':
            if not self.continues:
                raise CompileError('continue outside loop')
            e.branch(14, self.continues[-1])
            return
        raise CompileError('unsupported statement ' + k)

    # ---------- load/store helpers ----------
    def addr_of_var(self, name):
        # r0 = address of a local or global (or static) variable
        e = self.e
        info = self.var_info(name)
        if info[0] == 'local':
            off = info[1]
            if off < 0:
                c = dp_imm(2, 11, 0, -off)   # sub r0, fp, #-off
            else:
                c = dp_imm(4, 11, 0, off)    # add r0, fp, #off
            if c is None:
                # frame offset not encodable as an immediate: use a register
                mov_imm(e, 1, abs(off))
                if off < 0:
                    e.emit(dp_reg(2, 11, 0, 1))   # sub r0, fp, r1
                else:
                    e.emit(dp_reg(4, 11, 0, 1))   # add r0, fp, r1
            else:
                e.emit(c)
        else:
            e.lit(0, 'g', info[1])           # ldr r0, [pc, #lit] -> base+g_off

    def load_deref(self, t):
        # r0 = *r0, element type t
        e = self.e
        if t == T_CHAR:
            e.emit(0xE5D00000)               # ldrb r0, [r0]
        else:
            e.emit(ldr_str(True, 0, 0, 0))   # ldr r0, [r0]

    def store_var(self, name):
        # store r0 into variable (scalar only)
        e = self.e
        info = self.var_info(name)
        t = info[2]
        if is_arr(t):
            raise CompileError('cannot assign to array ' + name)
        if info[0] == 'local':
            if t == T_CHAR:
                e.emit(ldrb_str(False, 11, 0, info[1]))
            else:
                e.emit(ldr_str(False, 11, 0, info[1]))
        else:
            e.emit(push(1 << 0))             # save value
            self.addr_of_var(name)           # r0 = address
            e.emit(pop(1 << 1))              # r1 = value
            if t == T_CHAR:
                e.emit(0xE5C01000)           # strb r1, [r0]
            else:
                e.emit(ldr_str(False, 0, 1, 0))  # str r1, [r0]

    # ---------- expressions ----------
    def gen_ptr_value(self, base):
        # evaluate 'base' to a pointer VALUE (used as the start of a[i])
        # arrays decay to their address; pointer/scalar variables load their value
        if base[0] == 'var':
            t = self.var_type(base[1])
            if is_arr(t):
                self.addr_of_var(base[1])
            else:
                self.gen_expr(base)
        else:
            self.gen_expr(base)

    def gen_addr(self, x):
        # r0 = address of lvalue x
        e = self.e
        k = x[0]
        if k == 'var':
            self.addr_of_var(x[1])
            return
        if k == 'un' and x[1] == '*':
            self.gen_expr(x[2])
            return
        if k == 'index':
            base, idx = x[1], x[2]
            t = self.typeof(base)
            self.gen_ptr_value(base)
            e.emit(push(1 << 0))
            self.gen_expr(idx)
            e.emit(pop(1 << 1))
            elem = t[1] if (is_ptr(t) or is_arr(t)) else T_INT
            self.emit_scale_add(base_size(elem))
            return
        if k == 'member':
            bt = self.typeof(x[1])
            if x[3]:                              # p->m
                if not is_ptr(bt) or not is_struct(bt[1]):
                    raise CompileError('-> requires a pointer to a struct')
                self.gen_expr(x[1])               # r0 = struct pointer
            else:
                if not is_struct(bt):
                    raise CompileError('. requires a struct value')
                self.gen_addr(x[1])               # r0 = struct address
            _, moff = struct_member(bt[1] if x[3] else bt, x[2])
            if moff:
                c = dp_imm(4, 0, 0, moff)
                if c is None:
                    raise CompileError('member offset too large')
                e.emit(c)                         # add r0, r0, #moff
            return
        raise CompileError('not an lvalue')

    def emit_scale_add(self, size):
        # r1 = base, r0 = index -> r0 = base + index*size
        e = self.e
        if size == 1:
            e.emit(dp_reg(4, 1, 0, 0))            # add r0, r1, r0
        elif size & (size - 1) == 0:              # power of two
            n = 0
            t = size
            while t > 1:
                t >>= 1
                n += 1
            e.emit(dp_shift_imm(4, 1, 0, 0, 0, n))  # add r0, r1, r0, lsl #n
        else:
            mov_imm(e, 2, size)
            e.emit(0xE0000092)                    # mul r0, r0, r2
            e.emit(dp_reg(4, 1, 0, 0))            # add r0, r1, r0

    def gen_expr(self, x):
        e = self.e
        k = x[0]
        if k == 'num':
            mov_imm(e, 0, x[1])
            return
        if k == 'str':
            e.lit(0, 's', x[1])
            return
        if k == 'var':
            t = self.var_type(x[1])
            if is_struct(t):
                raise CompileError('struct value used where a value is required; use s.m or a pointer')
            if is_arr(t):
                self.addr_of_var(x[1])   # decay to address
                return
            self.addr_of_var(x[1])
            self.load_deref(t)
            return
        if k == 'un':
            op = x[1]
            if op == '&':
                self.gen_addr(x[2])
                return
            if op == '*':
                t = self.typeof(x[2])
                if not is_ptr(t):
                    raise CompileError('cannot dereference non-pointer')
                self.gen_expr(x[2])
                self.load_deref(t[1])
                return
            if op == '-':
                self.gen_expr(x[2])
                rsb_zero(e, 0)
                return
            if op == '~':
                self.gen_expr(x[2])
                e.emit(dp_reg(15, 0, 0, 0))   # mvn r0, r0
                return
            if op == '!':
                self.gen_expr(x[2])
                e.emit(cmp_imm(0, 0))
                mov_imm(e, 0, 0)
                l1 = self.new('n1')
                le = self.new('n2')
                e.branch(0, l1)
                e.branch(14, le)
                e.label(l1)
                mov_imm(e, 0, 1)
                e.label(le)
                return
            if op == '+':
                self.gen_expr(x[2])
                return
            raise CompileError('bad unary operator')
        if k == 'cast':
            # (int)/(char)/(T*)/(void) expression
            self.gen_expr(x[2])
            if x[1] == T_CHAR:
                e.emit(dp_imm(0, 0, 0, 255))   # and r0, r0, #255
            return
        if k == 'sizeof':
            kind, val = x[1]
            if kind == 't':
                mov_imm(e, 0, storage_size(val))
            else:
                mov_imm(e, 0, storage_size(self.typeof(val)))
            return
        if k == 'member':
            bt = self.typeof(x[1])
            if x[3]:                              # p->m
                if not is_ptr(bt) or not is_struct(bt[1]):
                    raise CompileError('-> requires a pointer to a struct')
                self.gen_expr(x[1])               # r0 = struct pointer
                st = bt[1]
            else:
                if not is_struct(bt):
                    raise CompileError('. requires a struct value')
                self.gen_addr(x[1])               # r0 = struct address
                st = bt
            mt, moff = struct_member(st, x[2])
            if moff:
                c = dp_imm(4, 0, 0, moff)
                if c is None:
                    raise CompileError('member offset too large')
                e.emit(c)
            if is_struct(mt):
                raise CompileError('struct member used as a value; use .m or a pointer')
            if is_arr(mt):
                return                            # array member decays to address
            self.load_deref(mt)
            return
        if k == 'index':
            t = self.typeof(x)     # element type
            self.gen_addr(x)       # r0 = element address
            if is_arr(t) or is_struct(t):
                return             # array/struct element decays to its address
            self.load_deref(t)     # r0 = element value
            return
        if k == 'tern':
            lel = self.new('tl')
            lend = self.new('te')
            self.gen_expr(x[1])
            e.emit(cmp_imm(0, 0))
            e.branch(0, lel)
            self.gen_expr(x[2])
            e.branch(14, lend)
            e.label(lel)
            self.gen_expr(x[3])
            e.label(lend)
            return
        if k == 'incdec':
            self.gen_incdec(x)
            return
        if k == 'call':
            self.gen_call(x)
            return
        if k == 'bin':
            self.gen_bin(x)
            return
        if k == 'assign':
            self.gen_assign(x)
            return
        raise CompileError('bad expression node')

    def gen_incdec(self, x):
        # ('incdec', pre, op, lvalue)  op in ('+','-')
        e = self.e
        pre = x[1]
        op = x[2]
        t = self.typeof(x[3])
        self.gen_addr(x[3])
        e.emit(push(1 << 0))                 # [sp] = addr
        if t == T_CHAR:
            e.emit(0xE5D00000)               # ldrb r0, [r0]
        else:
            e.emit(ldr_str(True, 0, 0, 0))   # ldr r0, [r0]
        if not pre:
            e.emit(push(1 << 0))             # [sp]=old, [sp+4]=addr
        delta = base_size(t[1]) if is_ptr(t) else 1
        if op == '+':
            c = dp_imm(4, 0, 0, delta)       # add r0, r0, #delta
        else:
            c = dp_imm(2, 0, 0, delta)       # sub r0, r0, #delta
        if c is None:
            raise CompileError('cannot encode inc/dec')
        e.emit(c)                            # r0 = new
        if t == T_CHAR:
            e.emit(dp_imm(0, 0, 0, 255))     # and r0, r0, #255
        if not pre:
            e.emit(dp_reg(13, 0, 1, 0))      # mov r1, r0  (new)
            e.emit(pop(1 << 0))              # r0 = old (result); [sp] = addr
            e.emit(ldr_str(True, 13, 2, 0))  # ldr r2, [sp]  (addr)
            if t == T_CHAR:
                e.emit(0xE5C21000)           # strb r1, [r2]
            else:
                e.emit(ldr_str(False, 2, 1, 0))  # str r1, [r2]
            e.emit(dp_imm(4, 13, 13, 4))     # add sp, sp, #4
        else:
            e.emit(ldr_str(True, 13, 1, 0))  # ldr r1, [sp]  (addr)
            if t == T_CHAR:
                e.emit(0xE5C10000)           # strb r0, [r1]
            else:
                e.emit(ldr_str(False, 1, 0, 0))  # str r0, [r1]
            e.emit(dp_imm(4, 13, 13, 4))     # add sp, sp, #4

    def gen_bin(self, x):
        e = self.e
        op = x[1]
        if op in ('&&', '||'):
            # short-circuit with the lhs kept on the stack so both
            # exit paths pop exactly one word.
            self.gen_expr(x[2])
            e.emit(push(1 << 0))
            e.emit(cmp_imm(0, 0))
            lskip = self.new('lsk')
            if op == '&&':
                e.branch(0, lskip)      # lhs false -> result 0
            else:
                e.branch(1, lskip)      # lhs true  -> result 1
            self.gen_expr(x[3])
            e.emit(cmp_imm(0, 0))
            if op == '&&':
                e.branch(0, lskip)
            else:
                e.branch(1, lskip)
            e.emit(pop(1 << 1))         # balance stack
            if op == '&&':
                mov_imm(e, 0, 1)        # both operands true -> 1
            else:
                mov_imm(e, 0, 0)        # both operands false -> 0
            ldone = self.new('ldn')
            e.branch(14, ldone)
            e.label(lskip)
            e.emit(pop(1 << 1))         # balance stack (lhs still pushed)
            if op == '&&':
                mov_imm(e, 0, 0)        # one operand false -> 0
            else:
                mov_imm(e, 0, 1)        # one operand true -> 1
            e.label(ldone)
            return
        lt = self.typeof(x[2])
        rt = self.typeof(x[3])
        self.gen_expr(x[2])
        e.emit(push(1 << 0))
        self.gen_expr(x[3])
        e.emit(pop(1 << 1))       # r1 = lhs, r0 = rhs
        self.emit_bin(op, lt, rt)

    def emit_bin(self, op, lt, rt):
        # computes op between r1 (lhs) and r0 (rhs), result in r0
        e = self.e
        if op == '+':
            if is_ptr(lt):
                # r0 = r1 + r0*elem_size  (r1 is the pointer)
                self.emit_scale_add(base_size(lt[1]))
            elif is_ptr(rt):
                # r0 = r0 + r1*elem_size  (r0 is the pointer)
                sz = base_size(rt[1])
                if sz == 1:
                    e.emit(dp_reg(4, 0, 0, 1))   # add r0, r0, r1
                elif sz & (sz - 1) == 0:
                    n = 0
                    t = sz
                    while t > 1:
                        t >>= 1
                        n += 1
                    e.emit(dp_shift_imm(4, 0, 0, 1, 0, n))  # add r0, r0, r1, lsl #n
                else:
                    mov_imm(e, 2, sz)
                    e.emit(0xE0010291)            # mul r1, r1, r2
                    e.emit(dp_reg(4, 0, 0, 1))    # add r0, r0, r1
            else:
                e.emit(dp_reg(4, 1, 0, 0))   # add r0, r1, r0
            return
        if op == '-':
            if is_ptr(lt) and is_ptr(rt):
                e.emit(dp_reg(2, 1, 0, 0))   # sub r0, r1, r0
                sz = base_size(lt[1])
                if sz == 1:
                    pass
                elif sz & (sz - 1) == 0:
                    n = 0
                    t = sz
                    while t > 1:
                        t >>= 1
                        n += 1
                    mov_lsr(e, 0, 0, n)      # element count
                else:
                    raise CompileError('pointer subtraction only for power-of-two element sizes')
            elif is_ptr(lt):
                # r0 = r1 - r0*elem_size
                sz = base_size(lt[1])
                if sz == 1:
                    e.emit(dp_reg(2, 1, 0, 0))
                elif sz & (sz - 1) == 0:
                    n = 0
                    t = sz
                    while t > 1:
                        t >>= 1
                        n += 1
                    e.emit(dp_shift_imm(2, 1, 0, 0, 0, n))  # sub r0, r1, r0, lsl #n
                else:
                    mov_imm(e, 2, sz)
                    e.emit(0xE0000092)            # mul r0, r0, r2
                    e.emit(dp_reg(2, 1, 0, 0))    # sub r0, r1, r0
            else:
                e.emit(dp_reg(2, 1, 0, 0))   # sub r0, r1, r0
            return
        if op == '*':
            e.emit(0xE0000091)               # mul r0, r1, r0
            return
        if op in ('/', '%'):
            e.emit(dp_reg(13, 0, 2, 1))      # mov r2, r1
            e.emit(dp_reg(13, 0, 1, 0))      # mov r1, r0
            e.emit(dp_reg(13, 0, 0, 2))      # mov r0, r2
            e.branch(14, '__aeabi_idivmod' if op == '%' else '__aeabi_idiv', True)
            return
        if op == '<<':
            e.emit(0xE1A00011)               # mov r0, r1, lsl r0
            return
        if op == '>>':
            e.emit(0xE1A00051)               # mov r0, r1, asr r0
            return
        if op == '&':
            e.emit(dp_reg(0, 1, 0, 0))       # and r0, r1, r0
            return
        if op == '^':
            e.emit(dp_reg(1, 1, 0, 0))       # eor r0, r1, r0
            return
        if op == '|':
            e.emit(dp_reg(12, 1, 0, 0))      # orr r0, r1, r0
            return
        if op in ('==', '!=', '<', '>', '<=', '>='):
            e.emit(enc_cmp_reg(1, 0))        # cmp r1, r0
            cond = {'==': 0, '!=': 1, '<': 11, '>': 12, '<=': 13, '>=': 10}[op]
            l1 = self.new('ct')
            le = self.new('ce')
            e.branch(cond, l1)
            mov_imm(e, 0, 0)
            e.branch(14, le)
            e.label(l1)
            mov_imm(e, 0, 1)
            e.label(le)
            return
        raise CompileError('unsupported operator ' + op)

    def gen_struct_copy(self, dst, src, st):
        # copy sizeof(struct) bytes from src lvalue to dst lvalue
        e = self.e
        self.gen_addr(dst)           # r0 = dst
        e.emit(push(1 << 0))
        self.gen_addr(src)           # r0 = src
        e.emit(pop(1 << 1))          # r1 = dst
        sz = struct_size(st)
        if sz % 4 == 0:
            for i in range(0, sz, 4):
                e.emit(ldr_str(True, 0, 2, i))    # ldr r2, [r0, #i]
                e.emit(ldr_str(False, 1, 2, i))   # str r2, [r1, #i]
        else:
            for i in range(sz):
                e.emit(ldrb_str(True, 0, 2, i))   # ldrb r2, [r0, #i]
                e.emit(ldrb_str(False, 1, 2, i))  # strb r2, [r1, #i]

    def gen_assign(self, x):
        # ('assign', op, lhs, rhs)
        e = self.e
        op = x[1]
        lhs = x[2]
        rhs = x[3]
        if op == '=':
            t = self.typeof(lhs)
            if is_struct(t):
                # struct assignment: copy sizeof(struct) bytes
                self.gen_struct_copy(lhs, rhs, t)
                return
            self.gen_expr(rhs)               # r0 = value
            if lhs[0] == 'var':
                self.store_var(lhs[1])
            else:
                e.emit(push(1 << 0))
                self.gen_addr(lhs)           # r0 = address
                e.emit(pop(1 << 1))          # r1 = value
                if t == T_CHAR:
                    e.emit(0xE5C01000)       # strb r1, [r0]
                else:
                    e.emit(ldr_str(False, 0, 1, 0))  # str r1, [r0]
                e.emit(dp_reg(13, 0, 0, 1))  # mov r0, r1 (assignment value)
            return
        # compound assignment
        t = self.typeof(lhs)
        if is_struct(t):
            raise CompileError('compound assignment on a struct is not supported')
        self.gen_addr(lhs)
        e.emit(push(1 << 0))                 # [sp] = addr
        if t == T_CHAR:
            e.emit(0xE5D00000)               # ldrb r0, [r0]
        else:
            e.emit(ldr_str(True, 0, 0, 0))
        e.emit(push(1 << 0))                 # [sp] = old, [sp+4] = addr
        self.gen_expr(rhs)
        e.emit(pop(1 << 1))                  # r1 = old
        bop = op[0]                          # '+','-','*','/','%','<','>','&','|','^'
        lt = t
        rt = T_INT
        if bop == '<':
            bop = '<<'
        elif bop == '>':
            bop = '>>'
        self.emit_bin(bop, lt, rt)           # r0 = new
        e.emit(ldr_str(True, 13, 1, 0))      # ldr r1, [sp]  (addr)
        if t == T_CHAR:
            e.emit(0xE5C10000)               # strb r0, [r1]
        else:
            e.emit(ldr_str(False, 1, 0, 0))  # str r0, [r1]
        e.emit(dp_imm(4, 13, 13, 4))         # add sp, sp, #4

    def gen_call(self, x):
        e = self.e
        name = x[1]
        args = x[2]
        if name == '__svc':
            if not args or args[0][0] != 'num':
                raise CompileError('__svc first argument must be a constant')
            num = args[0][1]
            if num < 0 or num > 0xFFFFFF:
                raise CompileError('__svc immediate out of range')
            m = len(args) - 1
            if m > 4:
                raise CompileError('__svc takes at most 4 value arguments')
            for a in reversed(args[1:]):
                self.gen_expr(a)
                e.emit(push(1 << 0))
            for i in range(m):
                e.emit(pop(1 << i))
            # The firmware SVC convention (HP Prime G1): the handler reads
            # the result into r0 and RETURNS VIA THE LR PUSHED ONTO THE
            # STACK, so every syscall goes through a tiny wrapper that does
            # "push {r0}; push {lr}; svc" - the same shape as the DOOM
            # port's sys_* wrappers. A plain svc would pop a garbage LR.
            e.branch(14, self.svc_wrapper(num), True)
            return
        if name == '__sleep':
            if len(args) != 1:
                raise CompileError('__sleep takes 1 argument')
            self.gen_expr(args[0])
            e.branch(14, self.svc_wrapper(0x10008), True)
            return
        if name == '__va_start':
            # address of the first variadic (stack-passed) argument.
            # Prologue is push {r4,fp,lr}; mov fp,sp -> extras at fp+12.
            if len(args) != 0:
                raise CompileError('__va_start takes no arguments')
            c = dp_imm(4, 11, 0, 12)      # add r0, fp, #12
            if c is None:
                raise CompileError('internal: va offset')
            e.emit(c)
            return
        if name not in self.functions:
            raise CompileError('unknown function ' + name)
        fn = self.functions[name]
        variadic = len(fn) > 5 and fn[5]
        fixed = len(fn[3])
        if variadic:
            if len(args) < fixed:
                raise CompileError('function %s expects at least %d arguments, got %d' %
                                   (name, fixed, len(args)))
        else:
            if len(args) != fixed:
                raise CompileError('function %s expects %d arguments, got %d' %
                                   (name, fixed, len(args)))
            if len(args) > 4:
                raise CompileError('maximum 4 arguments')
        # argument type checking on the fixed parameters only (variadic
        # arguments are untyped, like in C)
        for i in range(min(len(args), fixed)):
            at = self.typeof(args[i])
            pt = fn[3][i][1]
            if is_ptr(pt):
                if not is_ptr(at):
                    raise CompileError('argument %d of %s expects a pointer, got an int' %
                                       (i + 1, name))
            elif is_ptr(at):
                raise CompileError('argument %d of %s expects an int, got a pointer' %
                                   (i + 1, name))
        # push ALL arguments right-to-left, then pop the fixed ones into
        # r0..r3; the remaining (variadic) arguments stay on the stack and
        # the caller removes them after the call. __va_start() == fp+12.
        for a in reversed(args):
            self.gen_expr(a)
            e.emit(push(1 << 0))
        for i in range(fixed if variadic else len(args)):
            e.emit(pop(1 << i))
        e.branch(14, name, True)
        if variadic and len(args) > fixed:
            extra = (len(args) - fixed) * 4
            c = dp_imm(4, 13, 13, extra)   # add sp, sp, #extra
            if c is None:
                raise CompileError('variadic cleanup offset too large')
            e.emit(c)


# ---------- ELF writer ----------
def align(x, a):
    return (x + a - 1) & ~(a - 1)


def make_elf(words, main_idx, pool_entries, globals_, strings):
    # Image offsets are vaddr-relative (vaddr base is 0); the file layout
    # is shifted by FILE_OFF so the loader can map the image at its base.
    FILE_OFF = 0x1000
    text_len = len(words) * 4
    ro_off = align(text_len, 4)          # image offsets from here on
    # rodata: string literals (NUL-terminated, 4-byte aligned)
    rodata = bytearray()
    s_off = []
    for s in strings:
        s_off.append(ro_off + len(rodata))
        rodata.extend(s)
        rodata.append(0)          # NUL terminator
        while len(rodata) % 4:
            rodata.append(0)
    da_off = align(ro_off + len(rodata), 4)
    # data: globals
    data = bytearray()
    relocs = []
    g_off = {}

    def d_align(a):
        while len(data) % a:
            data.append(0)

    for (name, t, init) in globals_:
        # unwrap the generic expression wrapper; only constant forms allowed
        if init is not None and init[0] == 'e':
            init = init[1]
        d_align(4 if (t == T_INT or is_ptr(t)) else 1)
        g_off[name] = da_off + len(data)
        if is_arr(t):
            elem = t[1]
            n = t[2]
            sz = base_size(elem)
            if n is None:
                # size inferred from initializer
                if init is not None and init[0] == 'str':
                    n = len(strings[init[1]]) + 1
                elif init is not None and init[0] == 'arr_init':
                    n = len(init[1])
                else:
                    raise CompileError('array %s needs a size' % name)
            if init is None:
                data.extend(b'\0' * (n * sz))
            elif init[0] == 'str':
                if elem != T_CHAR:
                    raise CompileError('only char arrays can be string-initialized')
                b = strings[init[1]]
                if len(b) + 1 > n * sz:
                    raise CompileError('string initializer too long for %s' % name)
                data.extend(b)
                data.extend(b'\0' * (n * sz - len(b)))
            elif init[0] == 'arr_init':
                vals = init[1]
                # flat initializer fills the whole array: total elements =
                # array size / innermost element size (handles m[2][2] = {...})
                total = n
                t2 = t
                while is_arr(t2):
                    t2 = t2[1]
                esz = 1 if t2 == T_CHAR else 4
                total = (storage_size(t) // esz) if is_arr(t) else n
                if len(vals) > total:
                    raise CompileError('too many initializers for %s' % name)
                for v in vals:
                    if sz == 1:
                        data.append(v & 0xFF)
                    else:
                        data.extend(struct.pack('<I', v & 0xffffffff))
                data.extend(b'\0' * ((total - len(vals)) * sz))
            else:
                raise CompileError('bad initializer for array %s' % name)
        else:
            if init is None:
                data.extend(b'\0' * storage_size(t))
            elif init[0] == 'num':
                v = init[1]
                if t == T_CHAR:
                    data.append(v & 0xFF)
                else:
                    data.extend(struct.pack('<I', v & 0xffffffff))
            elif init[0] == 'str' and is_ptr(t):
                # char* p = "str": word holds string offset, relocated
                soff = s_off[init[1]]
                data.extend(struct.pack('<I', soff))
                relocs.append(g_off[name])
            else:
                raise CompileError('bad initializer for %s' % name)
    # patch function literal pools (addresses of globals / strings)
    for (w_idx, kind, key) in pool_entries:
        if kind == 's':
            words[w_idx] = s_off[key]
        elif kind == 'g':
            words[w_idx] = g_off[key]
        else:
            continue
        relocs.append(w_idx * 4)
    # relocation table
    rel_off = align(da_off + len(data), 4)
    rel_bytes = b''.join(struct.pack('<II', o, R_ARM_RELATIVE) for o in relocs)
    dyn_off = align(rel_off + len(rel_bytes), 4)
    dyn_entries = ((DT_REL, rel_off), (DT_RELSZ, len(rel_bytes)),
                   (DT_RELENT, 8), (DT_RELCOUNT, len(relocs)), (DT_NULL, 0))
    dyn_bytes = b''.join(struct.pack('<II', t, v) for t, v in dyn_entries)
    filesz = dyn_off + len(dyn_bytes)      # image size
    # assemble the image, padding so each section lands at its computed offset
    image = bytearray()
    image.extend(b''.join(struct.pack('<I', x) for x in words))
    while len(image) < ro_off:
        image.append(0)
    image.extend(rodata)
    while len(image) < da_off:
        image.append(0)
    image.extend(data)
    while len(image) < rel_off:
        image.append(0)
    image.extend(rel_bytes)
    while len(image) < dyn_off:
        image.append(0)
    image.extend(dyn_bytes)
    hdr = bytearray(52)
    hdr[0:4] = b'\x7fELF'
    hdr[4] = 1
    hdr[5] = 1
    hdr[6] = 1
    struct.pack_into('<HHIIIIIHHHHHH', hdr, 16, 3, 40, 1, main_idx, 52, 0, 0,
                     52, 32, 2, 40, 1, 0)
    ph0 = struct.pack('<IIIIIIII', PT_LOAD, FILE_OFF, 0, 0, filesz,
                      filesz, 7, 0x1000)
    ph1 = struct.pack('<IIIIIIII', PT_DYNAMIC, FILE_OFF + dyn_off, dyn_off,
                      dyn_off, len(dyn_bytes), len(dyn_bytes), 6, 4)
    pad = b'\0' * (FILE_OFF - 52 - 64)
    return bytes(hdr) + ph0 + ph1 + pad + image


# Builtin small library: compiled from C source with the compiler itself.
# User-defined functions override these (user definitions win).
BUILTIN_LIB_SRC = (
    "int strlen(char* s) { int i = 0; while (s[i]) i++; return i; }\n"
    "int strcmp(char* a, char* b) { int i = 0; while (a[i] && a[i] == b[i]) i++; "
    "return a[i] - b[i]; }\n"
    "void strcpy(char* d, char* s) { int i = 0; while ((d[i] = s[i])) i++; }\n"
    "void memcpy(char* d, char* s, int n) { int i; for (i = 0; i < n; i++) d[i] = s[i]; }\n"
    "void memset(char* d, int c, int n) { int i; for (i = 0; i < n; i++) d[i] = c; }\n"
    # ---- variadic formatting (printf / sprintf) ----
    "int __u10div(int v) {\n"
    "    int q = 0, r = 0, i;\n"
    "    for (i = 31; i >= 0; i--) {\n"
    "        r = (r << 1) | ((v >> i) & 1);\n"
    "        if (r >= 10) { r -= 10; q = q | (1 << i); }\n"
    "    }\n"
    "    return q;\n"
    "}\n"
    "char* __fmt_u(char* out, int v) {\n"
    "    char tmp[12];\n"
    "    int n = 0;\n"
    "    if (v == 0) { out[0] = '0'; out[1] = 0; return out + 1; }\n"
    "    while (v != 0) {\n"
    "        int d = v - __u10div(v) * 10;\n"
    "        tmp[n] = '0' + d; n++;\n"
    "        v = __u10div(v);\n"
    "    }\n"
    "    while (n > 0) { n--; out[0] = tmp[n]; out++; }\n"
    "    out[0] = 0;\n"
    "    return out;\n"
    "}\n"
    "int vsformat(char* out, char* fmt, int* va) {\n"
    "    char* p = fmt;\n"
    "    char* o = out;\n"
    "    int vi = 0;\n"
    "    while (p[0] != 0) {\n"
    "        if (p[0] != '%') { o[0] = p[0]; o++; p++; continue; }\n"
    "        p++;\n"
    "        int left = 0, zero = 0, width = 0;\n"
    "        if (p[0] == '-') { left = 1; p++; }\n"
    "        if (p[0] == '0') { zero = 1; p++; }\n"
    "        while (p[0] >= '0' && p[0] <= '9') { width = width * 10 + p[0] - '0'; p++; }\n"
    "        if (p[0] == 0) break;\n"
    "        char conv = p[0];\n"
    "        p++;\n"
    "        if (conv == '%') { o[0] = '%'; o++; continue; }\n"
    "        char tmp[256];\n"
    "        char* t = tmp;\n"
    "        int is_neg = 0;\n"
    "        if (conv == 'd' || conv == 'i') {\n"
    "            int v = va[vi]; vi++;\n"
    "            if (v < 0) { is_neg = 1; v = -v; }\n"
    "            t = __fmt_u(t, v);\n"
    "        } else if (conv == 'u') {\n"
    "            t = __fmt_u(t, va[vi]); vi++;\n"
    "        } else if (conv == 'x' || conv == 'X') {\n"
    "            int v = va[vi]; vi++;\n"
    "            char hex[9];\n"
    "            int hn = 0, i2;\n"
    "            for (i2 = 0; i2 < 8; i2++) {\n"
    "                int nib = v & 15;\n"
    "                hex[hn] = nib < 10 ? '0' + nib : (conv == 'X' ? 'A' : 'a') + nib - 10;\n"
    "                hn++;\n"
    "                v = v >> 4;\n"
    "            }\n"
    "            while (hn > 1 && hex[hn - 1] == '0') hn--;\n"
    "            while (hn > 0) { hn--; t[0] = hex[hn]; t++; }\n"
    "            t[0] = 0;\n"
    "        } else if (conv == 'p') {\n"
    "            int v = va[vi]; vi++;\n"
    "            t[0] = '0'; t[1] = 'x'; t += 2;\n"
    "            char hex[9];\n"
    "            int hn = 0, i2;\n"
    "            for (i2 = 0; i2 < 8; i2++) {\n"
    "                int nib = v & 15;\n"
    "                hex[hn] = nib < 10 ? '0' + nib : 'a' + nib - 10;\n"
    "                hn++;\n"
    "                v = v >> 4;\n"
    "            }\n"
    "            while (hn > 1 && hex[hn - 1] == '0') hn--;\n"
    "            while (hn > 0) { hn--; t[0] = hex[hn]; t++; }\n"
    "            t[0] = 0;\n"
    "        } else if (conv == 'c') {\n"
    "            t[0] = va[vi] & 255; vi++;\n"
    "            t[1] = 0; t++;\n"
    "        } else if (conv == 's') {\n"
    "            char* s = (char*)va[vi]; vi++;\n"
    "            while (s[0] != 0) { t[0] = s[0]; t++; s++; }\n"
    "            t[0] = 0;\n"
    "        } else {\n"
    "            o[0] = '%'; o++;\n"
    "            o[0] = conv; o++;\n"
    "            continue;\n"
    "        }\n"
    "        int dlen = strlen(tmp);\n"
    "        int pad = width - dlen - (is_neg ? 1 : 0);\n"
    "        if (pad < 0) pad = 0;\n"
    "        if (is_neg) { o[0] = '-'; o++; }\n"
    "        if (!left) { while (pad > 0) { o[0] = zero ? '0' : ' '; o++; pad--; } }\n"
    "        { char* q = tmp; while (q[0] != 0) { o[0] = q[0]; o++; q++; } }\n"
    "        if (left) { while (pad > 0) { o[0] = ' '; o++; pad--; } }\n"
    "    }\n"
    "    o[0] = 0;\n"
    "    return o - out;\n"
    "}\n"
    "int sprintf(char* buf, char* fmt, ...) {\n"
    "    int* va = (int*)__va_start();\n"
    "    return vsformat(buf, fmt, va);\n"
    "}\n"
    # ---- printf output ring: magic(8) + count(4) + data(4096) ----
    "char __log_magic[8] = {'P','R','I','M','E','L','O','G'};\n"
    "int __log_count = 0;\n"
    "char __log_data[4096];\n"
    "int printf(char* fmt, ...) {\n"
    "    int* va = (int*)__va_start();\n"
    "    char tmp[512];\n"
    "    int n = vsformat(tmp, fmt, va);\n"
    "    int i;\n"
    "    for (i = 0; i < n; i++) {\n"
    "        if (__log_count < 4096) {\n"
    "            __log_data[__log_count] = tmp[i];\n"
    "            __log_count++;\n"
    "        }\n"
    "    }\n"
    "    return n;\n"
    "}\n"
)


# ---------- minimal preprocessor (#define constants only) ----------
def preprocess(text):
    """Handle '#' lines: #define NAME replacement (object-like macros).
    Returns a token list with macros expanded (recursion depth-capped)."""
    lines = text.split('\n')
    kept = []
    macros = {}
    for line in lines:
        s = line.strip()
        if s.startswith('#'):
            body = s[1:].strip()
            if body.startswith('define'):
                rest = body[len('define'):].strip()
                i = 0
                while i < len(rest) and (rest[i].isalpha() or rest[i] == '_'):
                    i += 1
                name = rest[:i]
                if not name:
                    raise CompileError('bad #define')
                if i < len(rest) and rest[i] == '(':
                    raise CompileError('function-like macros are not supported')
                while i < len(rest) and rest[i].isspace():
                    i += 1
                macros[name] = rest[i:]
            elif body.startswith('include'):
                raise CompileError('#include is not supported')
            else:
                raise CompileError('unsupported preprocessor directive')
            continue
        kept.append(line)
    toks = Lexer('\n'.join(kept)).lex()

    def expand(name, depth):
        if name not in macros or depth > 8:
            return None
        rtoks = Lexer(macros[name]).lex()
        res = []
        for t in rtoks:
            if t.k == 'EOF':
                break
            if t.k == 'ID':
                sub = expand(t.v, depth + 1)
                if sub is not None:
                    res.extend(sub)
                else:
                    res.append(t)
            else:
                res.append(t)
        return res

    out = []
    for t in toks:
        if t.k == 'EOF':
            break
        if t.k == 'ID' and t.v in macros:
            out.extend(expand(t.v, 0))
        else:
            out.append(t)
    out.append(Tok('EOF', '', 0))
    return out


def compile_c(source):
    global STRUCT_MEMBERS, STRUCT_SIZES
    STRUCT_MEMBERS = {}
    STRUCT_SIZES = {}
    functions, globals_, strings = Parser(preprocess(source)).parse()
    if not functions:
        raise CompileError('no functions')
    # merge builtin library functions and globals (user definitions win)
    lib_fns, lib_globals, lib_strings = Parser(Lexer(BUILTIN_LIB_SRC).lex()).parse()
    have = set()
    for f in functions:
        have.add(f[1])
    for f in lib_fns:
        if f[1] not in have:
            functions.append(f)
    haveg = set()
    for g in globals_:
        haveg.add(g[0])
    for g in lib_globals:
        if g[0] not in haveg:
            globals_.append(g)
    cg = CodeGen(functions, globals_, strings)
    words, main_idx, pool_entries = cg.compile()
    # cg.globals includes static locals registered during codegen
    return make_elf(words, main_idx, pool_entries, list(cg.globals.values()), strings)
