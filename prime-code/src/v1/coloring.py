"""
          ★ PrimeCode ★
          
           ♡ by SQY ♡
           
    powerful code editor on HP Prime
    tested on HP Prime v2 (Hardware C)
       software v0.050.640 (2025 09 15)
   
    Features:
       1. the font width is the same.
          ww(2 chinese chars) 
            == ww(3 ASCII chars)
       2. highlight your code.
       3. use 'setting.json' to change config. 
       4. 'smooth' operation.
       5. two themes to switch:
           dark / light
       6. can open big file (> 50 KB)
       7. search something and mark them.
           press [Symb] to enable search.
       8. search something and replace them with another string.
           press [Plot] to enable replace.
       9. a slider that can move codes quickly.
       
    Problems:
       1. Can't edit a program with more than 1 file.
           (Programs(Name) := {{"", "Name", 0}} is invalid.)
       2. !!! if you quit the program while saving a lot of codes, 
           the codes may be missing. !!!
           (Use 'except KeyboardInterrupt:' may cause problems.)

    2025 SQY all rights reserved.
     
"""

from hpprime import *

def ifte(a,b,c):
    if a:
        return b
    else:
        return c


def rgb(r,g,b,a=0):
    return a*256**3+65536*r+256*g+b


symlist = ["<", "≤", ">", "≥", "==", "≠"]
color2rgb = [0,16777215,rgb(255,180,0),rgb(255,255,0),rgb(0,255,0),rgb(90,90,255),rgb(255,0,255),rgb(255,0,0)]
defaultSetting = {"language" : "PPL", "indent" : 4, "highLight" : True, "theme" : 0, "showColor" : True, "maxTokenLen" : 10000, "Aindent" : 1, "font" : "Cascadia Code"}


def initPPLKeyw():
    global UpperLowerKey, Key1, Key2, Key3, Key4 
    Key1=["LOCAL","EXPORT","CONST","ICON","PROGRAMS","NOTES","AFILES"]
    Key2=["KEY","DEBUG","DEFAULT","FOR","FROM","TO","DO","THEN","UNTIL","IFERR","END","REPEAT","WHILE","IF","ELSE","CASE","BREAK","CONTINUE","BEGIN","RETURN"]
    Key3=["PRINT","WAIT","FREEZE","BLIT","DIMGROB","LINE","ARC","TEXTOUT","RECT","PIXON","FILLPOLY","RGB","GETPIX","GROBW","GROBH","INVERT","TRIANGLE","SUBGROB"]
    Key4=['SQRT','EVAL','LOG','LOGB','EXP','APPROX','ABS',"MOD",'TYPE','CHOOSE','ISKEYDOWN','GET','TEXTSIZE','IFTE','when',"ASC","LOWER","STRINGFROMID","ROTATE","MID","UPPER","RIGHT","INSTRING","STRING","EXPR","DIM","CHAR","LEFT",
    'ADDCOL','SUB','SCALEADD','SCALE','SWAPCOL','REPLACE','EDITMAT','DELROW','DELCOL','ADDROW','REDIM','SWAPROW','MAKEMAT',
    'MAKELIST','SORT','REVERSE','CONCAT','SUPPRESS','INSERT','POS','ΔLIST','SIZE','ΣLIST','ΠLIST','UNION','DIFFERENCE','INTERSECT','EQ',
    'CEILING','FLOOR','IP','FP','MAX','MIN','ARG','CONJ','RE','IM','SIGN','SIN','COS','TAN','CSC','SEC','COT','ASIN','ACOS','ATAN','ACSC','ASEC','ACOT','SINH','ASINH','COSH','ACOSH','TANH','ATANH','COMB','PERM','RANDOM','RANDINT','RANDSEED']
    UpperLowerKey = 1


def initPythonKeyw():
    global UpperLowerKey, Key1, Key2, Key3, Key4 
    Key1 = ["global", "const", 'def', 'class', 'import', 'from', 'as', 'tuple', 'list', 'array']
    Key2 = ['for', 'while', 'if', 'else', 'elif', 'try', 'except', 'finally', 'return', 'raise', 'break', 'continue']
    Key3 = ["print", 'input']
    Key4 = ['in', 'len', 'range', 'float', 'int', 'open', 'str', 'eval', ]
    UpperLowerKey = 0


def SplitText(t,maxTokenLen,hl=1):
    if len(t)>maxTokenLen or hl==0:
        return [t]
    elif t=="":
        return [""];
    text=[]
    temp1=""
    yh, yh2 = 0, 0
    for i in range(len(t)):
        if t[i]=='"' and yh2 == 0:
            yh=1-yh
        if t[i]=="'" and yh == 0:
            yh2=1-yh2
        if t[i] in "+-*/(,^);:= ▶{[]}<>≤≥≠#.%&" and yh==0 and yh2==0:
            if temp1!="":
                text.append(temp1) 
            text.append(t[i])
            temp1=""
        else:
            temp1+=t[i]
    if temp1 != "":
        text.append(temp1)
    return text


def Coloring(textl,fc,hl=1):
    j, Ccol = 0, ""
    Notei=0
    if hl==0:
        for i in range(len(textl)):
            Ccol+=len(textl[i])*str(fc)
        return Ccol
    if textl==[""]:
        return "1" 
    if textl[0]=="#":
        for i in range(len(textl)):
            Ccol+=len(textl[i])*"4"
        return Ccol 
    while j<len(textl):
        st = ifte(UpperLowerKey == 1, textl[j].upper(), textl[j])
        if st == "/" and j<len(textl)-1:
            if textl[j+1]=="/" or Notei==1:
                Ccol+="4"
                Notei=1
            else:
                Ccol+="5"
        else:
            if Notei==0:
                if textl[j][0]=='"' or textl[j][0]=="'":
                    Ccol+=len(textl[j])*"4" 
                elif st in "+-*/(!^),;:={[]}<>≤≥≠▶%&" or st in ["AND","OR","NOT"]:
                    Ccol+=len(st)*"5" 
                elif st in Key1:
                    Ccol+=len(st)*"6"
                elif st in Key2:
                    Ccol+=len(st)*"2"
                elif st in Key4 or textl[j] in ["True","False"]:
                    Ccol+=len(st)*"3"
                elif st in Key3 or (st[:len(st)-2] in Key3 and "_P" in st):
                    Ccol+=len(st)*"6"
                else:
                    Ccol+=len(st)*str(fc)
            else:
                Ccol+=len(st)*"4"
        j+=1 
    return Ccol


def b_find(poslist,x):
    if x >= poslist[-1]:
        return len(poslist)-1
    i_min, i_max = 0, len(poslist)-1 
    while abs(i_max-i_min)>1:
        if poslist[(i_min + i_max) // 2] <= x:
            i_min = (i_min+i_max)//2
        else:
            i_max = (i_min+i_max)//2
    return i_min


def textW(c):
    ww=0
    for e in range(len(c)):
        j = ord(c[e])-33
        if j+33>127:
            ww += ifte(c in "≤≥≠▶αβ→∞°′″Σ−",10,15)
        else:
            ww += 10
    return ww 
         

def DrawC(grob,c,x,y,color):
    try:
        j = ord(c) - 33
    except TypeError:
        j = 65536
    if j+33>127:
        textout(grob, x, y, c, color2rgb[color])
        return ifte(c in "≤≥≠▶αβ→∞°′″Σ−",10,15)
    else:
        if x>0:
            strblit2(grob,x,y,10,18,1,j*10,color*24,10,20)
        return 10
 
         
def SAPrint(txt,x,y,grob,default_color,dat=""):
    k=0
    while k<len(txt) and x<=320:
        if k<len(dat):
            col = int(dat[k])
        else:
            col = default_color
        if txt[k] != " ":
            if txt[k]=="_":
                line(grob,x,y+14,x+8,y+14,color2rgb[col])
                x+=10
            else: 
                x+=DrawC(grob,txt[k],x,y,col); 
        else:
            x+=10
        k+=1


def drawSlider(g,l,y,t):
    if l>8:
        fillrect(g,310,0,10,320,rgb(160,160,200,180),rgb(160,160,200,180))
        c=ifte(t == 0, rgb(200,200,200,150), rgb(100,100,100,150))
        fillrect(g,310,24-(240-24-(10+1500/l))*(y-20)/(20*l-100),10,10+1500/l,c,c) 


def symPadGui(th):
    line(3,130,60,130,179,rgb(200,200,200))
    line(3,190,60,190,179,rgb(200,200,200))
    line(3,70,120,249,120,rgb(200,200,200))
    textout(3,96,82,"<",ifte(th==0,16777215,0))
    textout(3,156,82,"≤",ifte(th==0,16777215,0))
    textout(3,216,82,">",ifte(th==0,16777215,0))
    textout(3,96,142,"≥",ifte(th==0,16777215,0))
    textout(3,152,142,"==",ifte(th==0,16777215,0))
    textout(3,216,142,"≠",ifte(th==0,16777215,0))
 

def ATryFind(txt,list):
    res = []
    for i in range(len(list)):
        if txt.upper() in list[i]:
            res.append(list[i].lower())
    return res


def Amatch(txt):
    if len(txt) < 3:
        return []
    r = []
    r += ATryFind(txt,Key1)
    r += ATryFind(txt,Key2)
    r += ATryFind(txt,Key3)
    r += ATryFind(txt,Key4)
    return r 
    
     
def Afetch(txt,i):
    itemp = i-1
    while itemp >= 0:
        if itemp >= 0:
            if txt[itemp] in "+-*/(,^);:= ▶{[]}<>≤≥≠#":
                return itemp+1
        itemp -= 1
    return itemp+1
 