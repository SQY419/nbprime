from hpprime import *

ver="0.9.1c"  #PrimeCode version
lang="ppl" #highlight language
indn=4     #indent length (1, 2, 4)
j=0
mode=1
Name=""
menu, menux = 0, 320
saved, savet = 0, "?" #file saved? , save time
yr, y0, y, dx, ddx = 20, 20, 20, 0, 0
showgb, gbx, gby1, gbl, gb = True, 0, 0, 1, 0
slider_y, l_s_x, l_s_y, ref = 0, 0, 0, 0
str_pos, s_p = [], []
mouse_status, mouse_ansp, start_pos = 0, [0,0,0,0,-1], [0,0]
KeyToValue = ['"showColor"', '"theme"', '"indent"', '"Aindent"', '"highLight"', '"maxTokenLen"', '"language"', '"font"'], ['showColor', 'theme', 'indn', 'Aindent', 'hl', 'maxTokenLen', 'lang', 'font']
fonts = {"cascadia code" : "", "fira code" : "_fira", "consolas" : "_consolas"} 


def loadfile(fileName):
    global s, ColT, indent
    file=eval('Programs("'+fileName+'")')
    s=file.split(chr(10))
    s.insert(0,"")
    return s 
    
    
def resetTemp(ind): 
    ColT,indent=[],[]
    for i in range(ind):
        ColT.append("")
        indent.append(0)
    return ColT, indent 


def loadFont(name):
    eval('G1:=AFiles("font'+fonts[name.lower()]+'.png")')


"""-----------------------------------"""
 
def tryToChangeSetting(name,keyName):
    try:
        exec(name+"=py_eval('parse_setting["+keyName+"]')")
    except KeyError:
        exec(name+"=py_eval('parse_setting["+defaultSetting[name]+"]')") 


def checkJSON(sett):
    try:
        exec('parse_setting='+sett) 
        return 0
    except KeyError:
        return 1
    except NameError:
        return 1
    except SyntaxError:
        return 1 
    

def getTicks():
    return eval('ticks()')