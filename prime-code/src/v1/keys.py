from hpprime import *


def getMouse():
    a=eval('get(mouse(),1)')
    if len(a)==0:
        return [0,0,0,0,-1]
    else:
        try:
            a[0]=mouse()[0][0]
            a[1]=mouse()[0][1]
        except IndexError:
            return [0,0,0,0,-1] 
        if a[0]>320:
            return [0,0,0,0,-1] 
        return a
        

k_alp=0
k_shi=0

Kt=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
Keyb = [
14,15,16,17,18,
20,21,22,23,24,25,
26,27,28,29,
31,32,33,34,35,
   37,38,39,40,
   42,43,44,45,
   47,48,49,50
]

alp = [
"a","b","c","d","e",
"f","g","h","i","j","k",
"l","m","n","o",
"p","q","r","s","t",
    "u","v","w","x",
    "y","z","#",":",
    '""',"."," ",";"
]


sha = [
"A","B","C","D","E",
"F","G","H","I","J","K",
"L","M","N","O",
"P","Q","R","S","T",
    "U","V","W","X",
    "Y","Z","#",":",
    '""',"."," ",";"
]


shi = [
"","","","","°′″",
" NTHROOT ","asin()","acos()","atan()","exp()","alog()",
"sqrt()","abs()","''","eval()",
":="," ","{}","!","1/",
    " ","[]","__sym__"," ",
    " ","i","pi","0x",
    " ","=","_","Ans"
]


norm = [
"","","","x","/",
"^","sin()","cos()","tan()","ln()","log()",
"^2","-","()",",",
"*10^","7","8","9","/",
    "4","5","6","*",
    "1","2","3","-",
    "0","."," ","+"
]

  
def press_key_simple(Kt, txt, gb, k_shi, k_alp):
    global search, match, saved, ref, y0,yr,y, dx,ddx, gby, showgb, mouse_status, mouse_ansp, mse, eps, start_pos, mse_time, s, ColT, indent
    if keyboard() & (1<<36):
        if Kt[36]==0:
            if k_alp>2:k_alp-=2
            k_alp=(k_alp+1)%3
            if k_shi==1:
                if k_alp == 2:k_shi=0
                k_alp+=2 
        Kt[36]+=1
    else:Kt[36]=0
    if keyboard() & (1<<41):
        if Kt[41]==0:
            k_shi=(k_shi+1)%2
        Kt[41]+=1
    else:Kt[41]=0
    if keyboard() & (1<<7):
        if Kt[7]==0 or Kt[7]>=25:
            if k_shi==1:
                gb=0
                k_shi=0
            elif gb>0:
                gb-=1 
        Kt[7]+=1
    else:Kt[7]=0
    if keyboard() & (1<<8):
        if Kt[8]==0 or Kt[8]>=25: 
            if k_shi==1:
                gb=len(txt)
                k_shi=0
            elif gb<len(txt):
                gb+=1
        Kt[8]+=1
    else:Kt[8]=0
    if keyboard() & (1<<19):
        if Kt[19]==0 or Kt[19]>=25:
            if k_shi==1:
                if gb<len(s[gbl]):
                    txt = txt[:gb]+txt[gb+1:] 
                    ColT[gbl] = ""
                k_shi=0
            elif gb>0:
                txt = txt[:gb-1]+txt[gb:]
                gb-=1
        Kt[19]+=1
    else:Kt[19]=0
    for d in range(len(Keyb)):
        if keyboard() & (1<<Keyb[d]):
            if Kt[Keyb[d]]==0 or Kt[Keyb[d]]>=20: 
                if k_alp==0 and k_shi==0:
                    adde=norm[d] 
                elif k_alp==3 and k_shi==1:
                    adde=sha[d] 
                elif k_alp!=0 and k_shi==0:
                    if k_alp==4:
                        adde=sha[d]
                    else:
                        adde=alp[d] 
                elif k_alp==0 and k_shi==1:
                    adde=shi[d]
                else:
                    if not((k_alp==4 and k_shi==1) or (k_alp==3 and k_shi==1)) or (k_alp<=2 and k_shi==1):
                        adde=sha[d]
                    else:
                        adde=alp[d] 
                if k_alp==1 or k_alp==3:
                    k_alp=0  
                if k_shi==1:
                    k_shi=0
                if adde=="__sym__":
                    adde = symPad(len(indent)) 
                txt=txt[:gb]+adde+txt[gb:]
                gb+=len(adde) 
                if len(adde)>=1:
                    if adde[-1] in ')]}"':
                        gb-=1
            Kt[Keyb[d]]+=1
        else:Kt[Keyb[d]]=0
    return Kt, txt, gb, k_shi, k_alp
    
    