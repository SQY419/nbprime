/* PRIME-C-CODE-BEGIN */

/* PrimeC v0.4 demo: casts, structs, switch, sizeof, builtin string lib,
   multi-dim arrays, static locals and #define.
   Edit this file on the calculator, then run main.py. */

#define SIZE 4
#define GOLD 1000

struct Player {
    char name[8];
    int score;
    int level;
};

/* builtin library: strlen / strcmp / strcpy / memcpy / memset */

int strlen_ok(void) { return strlen("hello"); }

int switch_demo(int x) {
    int r = 0;
    switch (x) {
        case 1: r = 10; break;
        case 2: r = 20; break;
        case 3: r = 30; break;
        default: r = 99;
    }
    return r;
}

int table_sum(void) {
    int m[SIZE][SIZE];
    int i, j, s = 0;
    for (i = 0; i < SIZE; i++)
        for (j = 0; j < SIZE; j++)
            m[i][j] = i * SIZE + j;
    for (i = 0; i < SIZE; i++)
        for (j = 0; j < SIZE; j++)
            s += m[i][j];
    return s;
}

int next_id(void) {
    static int id = 0;
    return ++id;
}

int main() {
    int checks = 0;
    char buf[64];

    /* printf() output is captured and shown by main.py after the run */
    printf("PrimeC v0.5 demo\n");

    /* 1. cast: truncate to char and back */
    if ((char)300 == 44 && (int)(char)300 == 44) checks = checks * 10 + 1;

    /* 2. struct with . and -> */
    {
        struct Player p;
        struct Player* q = &p;
        strcpy(p.name, "doom");
        q->score = 100;
        p.level = 5;
        if (p.level == 5 && q->score == 100 && p.name[0] == 'd')
            checks = checks * 10 + 2;
        sprintf(buf, "player %s level=%d score=%d", p.name, p.level, q->score);
        printf("%s\n", buf);
    }

    /* 3. switch with fallthrough */
    if (switch_demo(2) == 20 && switch_demo(9) == 99) checks = checks * 10 + 3;

    /* 4. sizeof */
    if (sizeof(struct Player) == 16 && sizeof(int) == 4 && sizeof(char) == 1)
        checks = checks * 10 + 4;

    /* 5. builtin library */
    if (strlen("primec") == 6 && strcmp("abc", "abd") < 0)
        checks = checks * 10 + 5;

    /* 6. multi-dim arrays */
    if (table_sum() == 120) checks = checks * 10 + 6;

    /* 7. static locals persist across calls */
    next_id(); next_id();
    if (next_id() == 3) checks = checks * 10 + 7;

    /* 8. #define constants */
    if (SIZE == 4 && GOLD == 1000) checks = checks * 10 + 8;

    /* 9. struct copy */
    {
        struct Player a, b;
        a.score = 7;
        b = a;
        if (b.score == 7) checks = checks * 10 + 9;
    }

    /* 10. memcpy/memset */
    {
        char cbuf[8];
        memset(cbuf, 65, 4);
        cbuf[4] = 0;
        if (cbuf[0] == 65 && cbuf[3] == 65) checks = checks * 10 + 0;
    }

    /* printf with all conversions */
    sprintf(buf, "%d %u %x %X %c %s %5d %05d %p", -42, 0xFFFFFFFF, 255, 255,
            65, "str", 7, 7, (void*)0x1234);
    printf("formats: %s\n", buf);

    /* checks should be 1234567890 */
    printf("checks = %d\n", checks);
    return checks;
}

/* PRIME-C-CODE-END */
