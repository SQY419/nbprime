py_eval = eval
match = []
search = []

from hpprime import *
from math import sin
from load import *
from keys import *
from coloring import *


def getSize():
    siz = 0
    for d in range(len(s)):
        siz += len(s[d]) * 2
    return siz


def title_bar(grob):
    cc = rgb(40, 80, 200) if theme == 0 else rgb(120, 160, 255)
    fillrect(grob, 0, 0, 320, 24, cc, cc)


def getOriginSaveFile(j):
    t = ""
    for i in range(1, j):
        t += s[i] + "\n"
    return t[:len(t) - 1]


def Ssave(fn, draw_menu, titl, drs):
    global indent, ColT
    tmp = len(s)
    indent, ColT = [], []
    index = 0
    eval('Programs("' + fn + '"):=" "')
    while index < tmp - 1:
        try:
            tmp_str, j = "", 0
            while j < 32 and index < tmp - 1:
                tmp_str += s[index].replace('"', '""').replace('\\' + 'n', '\\' * 2 + 'n') + chr(10)
                index += 1
                j += 1
            eval('Programs("' + fn + '"):=' + 'Programs("' + fn + '")+"' + tmp_str + '"')
        except KeyboardInterrupt:
            continue
        try:
            blit(3, 0, 0, 2)
            tit(tmp, titl, draw_menu, drs)
            fillrect(3, 42, 105, 240, 30, rgb(80, 100, 180), rgb(80, 100, 180))
            fillrect(3, 40, 103, 240, 30, forec, forec)
            SAPrint("Saving... " + str(index + 1) + "/" + str(tmp), 50, 110, 3, fontc)
            blit(0, 0, 0, 3)
        except KeyboardInterrupt:
            continue
    eval('Programs("' + fn + '"):=' + 'Programs("' + fn + '")+"' + s[index].replace('"', '""').replace('\\' + 'n',
                                                                                                       '\\' * 2 + 'n') + '"')
    eval('Programs("' + fn + '"):=' + 'MID(Programs("' + fn + '"),3)')
    ColT, indent = resetTemp(tmp)


def dSetting():
    global lang, indn, hl, theme, showColor, maxTokenLen, font
    lang = "PPL"
    indn = 4
    hl = True
    theme = 0
    showColor = True
    maxTokenLen = 10000
    Aindent = 1
    font = "Cascadia Code"


def readSetting(sett):
    global fontc, forec, qc, bg, lang, hl, indn, showColor, Aindent
    try:
        exec('parse_setting=' + sett)
        for i in range(len(KeyToValue[0])):
            tryToChangeSetting(KeyToValue[1][i], KeyToValue[0][i])
        if theme == 0:
            fontc, qc, bg = 1, 16777215, 0
            forec = rgb(0, 20, 140)
        else:
            fontc, qc, bg = 0, 0, 16777215
            forec = rgb(150, 180, 240)
        loadFont(font)
    except (KeyError, NameError, SyntaxError):
        dSetting()


def getSaveFile():
    t = ""
    for i in range(1, len(indent)):
        t += (s[i]).replace('"', '""').replace('\\' + 'n', '\\' * 2 + 'n') + chr(10)
    if len(t) == 1:
        return " "
    return t[:len(t) - 1]


def makesetting():
    global setting
    if "pc_setting" not in eval('AFiles'):
        eval('AFiles("pc_setting"):="{\n""language"" : ""PPL"",\n""indent"" : 4,\n""highLight"" : True,\n""theme"" : 1,\n""showColor"" : True,\n""maxTokenLen"" : 1000,\n""Aindent"":1\n""font"" : ""Cascadia Code""\n}"')
    setting = eval('AFiles("pc_setting")')


def APrint(txt, x, y, sgb, dat=""):
    global gbx, gby1
    s_p, l, l_t = [], len(dat), len(txt)
    k = 0
    while k < l_t and x <= 320:
        s_p.append(x)
        if k < l:
            col = int(dat[k])
        else:
            col = fontc
        if sgb == 1 and (j, k) in search:
            cc = rgb(40, 40, 190)
            fillrect(2, x - 1, y, search_w, 18, cc, cc)
        if j == gbl and gb == k and sgb == 1:
            gbx, gby1 = x - 1, y
        if txt[k] != " ":
            if txt[k] == "_":
                line(2, x, y + 14, x + 8, y + 14, color2rgb[col])
                x += 10
            else:
                x += DrawC(2, txt[k], x, y, col)
        else:
            x += 10
        if txt[k] == "#" and showColor:
            try:
                if txt[k + 7] == "h":
                    rect(2, x - 10, y, 10 * 8, 16, int('0x' + txt[k + 1:k + 7]))
            except IndexError:
                pass
        k += 1
    if j == gbl and gb == k and sgb == 1:
        gbx, gby1 = x - 1, y
    s_p.append(x)
    return s_p


def show(x, it, y0):
    global indn, str_pos, str_i, gbx, gby1, j
    fillrect(2, 0, 0, 320, 240, bg, bg)
    gbx, gby1, y, j, len_s = -999, -999, y0, it, len(s)
    str_pos, str_i = [], []
    while j < len_s and y < 240:
        if j == gbl:
            c = rgb(0, 0, 255, 160) if theme == 0 else rgb(0, 0, 255, 235)
            fillrect(2, 0, y - 1, 320, 18, c, c)
        if ColT[j] == "":
            sp = SplitText(s[j], maxTokenLen, hl)
            c = Coloring(sp, fontc, hl)
            ColT[j] = c
            ind_ = 0
            while sp[ind_] == " " and ind_ < len(sp) - 1:
                ind_ += 1
            indent[j] = ind_
        else:
            c = ColT[j]
            ind_ = indent[j]
        if indn == 0:
            indn = 4
        for m in range(int(ind_ / indn)):
            c0 = rgb(50, 50, 150, 50) if theme == 0 else rgb(200, 200, 255, 100)
            line(2, x + m * indn * 10, y, x + m * indn * 10, y + 20, c0)
        str_pos.append(APrint(s[j], x, y, showgb, c))
        str_i.append(j)
        y += 20
        j += 1
    cc = rgb(5, 5, 55) if theme == 0 else rgb(200, 200, 255)
    fillrect(2, 0, 0, 50, 240, cc, cc)
    y, j, c = y0, it, rgb(255, 200, 0)
    while j < len(s) and y < 240:
        APrint(str(j), 5, y, 0)
        if len(s[j]) > maxTokenLen:
            rect(2, 3, y, 46, 16, c)
        y += 20
        j += 1


def load_gui():
    fillrect(2, 0, 0, 320, 240, bg, bg)
    title_bar(2)
    APrint("PrimeCode " + ver + " - " + Name + "*", 5, 3, 0)
    APrint("Loading...", 120, 110, 0)
    blit(0, 0, 0, 2)


def tit(len_s, pr, draw_menu=0, ds=1):
    global k_alp, k_shi
    if ds:
        drawSlider(3, len_s, yr, theme)
    title_bar(3)
    if draw_menu == 1:
        line(3, 305, 5, 315, 5, qc)
        line(3, 305, 10, 315, 10, qc)
        line(3, 305, 15, 315, 15, qc)
    if menux < 319 and draw_menu == 1:
        fillrect(3, menux, 25, 120, 85, forec, forec)
        SAPrint("Save", menux + 5, 28, 3, fontc)
        SAPrint("Save as", menux + 5, 48, 3, fontc)
        SAPrint("Go to", menux + 5, 68, 3, fontc)
        SAPrint("Info", menux + 5, 88, 3, fontc)
    if k_alp != 0:
        SAPrint("a", 290, 3, 3, fontc, "22")
        if k_alp == 2 or k_alp == 4:
            SAPrint("↑", 280, 3, 3, fontc, "22")
    if k_shi != 0:
        SAPrint("S", 260, 3, 3, fontc, "1")
    SAPrint(pr, 5, 3, 3, fontc)


def menuOperation(yi):
    global saved, savet, ref, y0, yr, y, dx, ddx, gby, gbl, gb
    global menu, menux, mouse_ansp, mse, start_pos, gbx, gby1, ColT, indent
    menu = 0
    if 25 < yi <= 45:
        # save file
        saved = 1
        if Name == "setting.json":
            setting = getSaveFile()
            eval('AFiles("pc_setting"):="' + setting + '"')
            readSetting(getOriginSaveFile(len(indent)))
            ColT, indent = resetTemp(len(s))
        else:
            if len(s) < 200:
                eval('Programs("' + Name + '"):="' + getSaveFile() + '"')
            else:
                # too large... using split save
                Ssave(Name, 1, Name, 1)
                savet = eval('string(Time)')
    elif 45 < yi <= 65:
        if Name == "setting.json":
            t = ""
        else:
            gb_t, gbl_t = gb, gbl
            t = textBox(Name, "Save as...", "Name:")
            gb, gbl = gb_t, gbl_t
            if len(t) > 0 and t not in eval('Programs'):
                if len(s) < 200:
                    eval('Programs("' + t + '"):="' + getSaveFile() + '"')
                else:
                    Ssave(t, 0, "Save as...", 0)
            elif t in eval('Programs'):
                msgbox("Save as...", "Name error.", len(indent))
    elif 65 < yi <= 85:
        gb_t, gbl_t = gb, gbl
        t = textBox("", "Go to line #...", "line #:")
        gb, gbl = gb_t, gbl_t
        try:
            gbl = int(t)
            gby = yr + 20 * gbl
            y_mov()
        except ValueError:
            pass
    elif 85 < yi <= 105:
        blit(3, 0, 0, 2)
        tit(len(indent), Name if saved else Name + "*", 1)
        fillrect(3, 42, 52, 240, 140, rgb(80, 100, 180), rgb(80, 100, 180))
        fillrect(3, 40, 50, 240, 140, forec, forec)
        SAPrint("info", 50, 60, 3, fontc)
        SAPrint("name: " + Name, 55, 80, 3, fontc)
        SAPrint("size: ~" + str(int(getSize() / 1024 * 10) / 10) + " KB", 55, 100, 3, fontc)
        SAPrint("save time: " + savet.replace("°", ":").replace("′", ":").replace("″", ""), 55, 120, 3, fontc)
        blit(0, 0, 0, 3)
        while getMouse()[4] == -1 and not (keyboard() & (1 << 4)):
            pass
        while getMouse()[4] != -1 or (keyboard() & (1 << 4)):
            pass
    ref = 1


def uni():
    global match, saved, savet, Kt, ref, l_s_x, l_s_y, k_alp, slider_y, indn, y0, yr, y, dx, ddx, gby, gbl, gb
    global menu, menux, showgb, mouse_status, mouse_ansp, mse, eps, start_pos, mse_time, gbx, gby1, ColT, indent
    yr += (y0 - yr) * .4
    menux += (320 - 120 * menu - menux) * 0.4
    ddx += (dx - ddx) * .4
    j = int(max(-yr / 20, 1))
    y = yr + j * 20 - 12
    gby = yr + 20 * gbl
    if ref or abs(60 - ddx - l_s_x) > 0.05 or abs(y - l_s_y) > 0.05:
        show(60 - ddx, j, y)
        l_s_x, l_s_y = 60 - ddx, y
        ref = 0
    blit(3, 0, 0, 2)
    if 0 < gby < 240 or keyboard() != 0:
        if gbx >= 50:
            if keyboard() != 0:
                c = rgb(200, 200, 255) if theme == 0 else rgb(0, 0, 55)
            else:
                c = (rgb(200, 200, 255, int(255 * 0.5 * (1 + sin(getTicks() / 200))))
                     if theme == 0 else
                     rgb(0, 0, 55, int(255 * 0.5 * (1 + sin(getTicks() / 200)))))
            line(3, gbx, max(24, gby1), gbx, max(gby1 + 16, 24), c)
            if len(match) > 0:
                Trem()
    if len(search) > 0:
        fillrect(3, 105, 31, 200, 22, rgb(80, 100, 180), rgb(80, 100, 180))
        fillrect(3, 103, 29, 200, 22, forec, forec)
        SAPrint("Nothing found." if search[0] == (-1, -1) else str(len(search)) + " '" + search_t + "' found.",
                110, 33, 3, fontc)
    tit(len(s), Name if saved else Name + "*", 1)
    blit(0, 0, 0, 3)
    if getMouse()[4] != -1:
        if mouse_status == 0 or getMouse()[2] != start_pos[0] or getMouse()[3] != start_pos[1]:
            mouse_ansp = getMouse()
            start_pos[0], start_pos[1] = getMouse()[2], getMouse()[3]
            if len(s) > 8:
                slider_y = mouse_ansp[1] - (24 - (240 - 24 - (10 + 1500 / len(s))) * (yr - 20) / (20 * len(s) - 100))
        else:
            try:
                if mouse_ansp[4] == 0 and mouse_ansp[0] >= 300 and mouse_ansp[1] <= 24:
                    menu = 1 - menu
                    while mouse_ansp[4] == 0:
                        mouse_ansp = getMouse()
                elif mouse_ansp[0] >= 310 and len(s) > 7:
                    y0 = (20 * len(s) - 100) * (mouse_ansp[1] - slider_y - 24) / (-206 + 1500 / len(s)) + 20
                    menu = 0
                elif mouse_ansp[4] == 2:
                    menu = 0
                    if 0 < getMouse()[0] < 320 and 0 < mouse_ansp[0] < 320:
                        dx -= getMouse()[0] - mouse_ansp[0]
                    y0 += getMouse()[1] - mouse_ansp[1]
                if len(getMouse()) != 0:
                    mouse_ansp = getMouse()
            except IndexError:
                pass
            match = []
        mouse_status += 1
    else:
        mouse_status = 0
        if mouse_ansp[4] == 0:
            if mouse_ansp[0] >= 300 and mouse_ansp[1] <= 24:
                pass
            elif menu and mouse_ansp[0] >= 200 and mouse_ansp[1] <= 110:
                menuOperation(mouse_ansp[1])
            else:
                gbl = 1 + int((mouse_ansp[1] - yr) / 20 - .5)
                gbl = max(1, min(gbl, len(indent) - 1))
                gb = (b_find(str_pos[str_i.index(gbl)], mouse_ansp[0]))
                menu, ref = 0, 1
        mouse_ansp = [0, 0, 0, 0, -1]
    if keyboard() != 0:
        press_key()
        ref = 1
    else:
        Kt = [0] * 52
    gbl = max(1, min(gbl, len(s) - 1))
    y0 = min(20, max(y0, 120 - 20 * len(s)))
    gb = min(max(0, gb), len(s[gbl]))
    dx = max(0, dx)


def msgbox(titl, showtext, l):
    global menu, menux
    menu, menux = 0, 320
    blit(3, 0, 0, 2)
    tit(l, titl, 0, 0)
    fillrect(3, 42, 105, 240, 30, rgb(80, 100, 180), rgb(80, 100, 180))
    fillrect(3, 40, 103, 240, 30, forec, forec)
    SAPrint(showtext, 50, 110, 3, fontc)
    blit(0, 0, 0, 3)
    while getMouse()[4] == -1 and not (keyboard() & (1 << 4)):
        pass
    while getMouse()[4] != -1 or keyboard() & (1 << 4):
        pass


def Trem():
    yn = min(gby, 240 - 20 * len(match))
    fillrect(3, gbx + 2, yn + 2, 150, 20 * len(match) + 2, rgb(80, 100, 180), rgb(80, 100, 180))
    fillrect(3, gbx, yn, 150, 20 * len(match) + 2, forec, forec)
    for d in range(len(match)):
        cc = Coloring([match[d]], fontc)
        SAPrint(match[d], gbx + 5, yn + d * 20 + 2, 3, fontc, cc)


def iexit(j):
    global mode, saved
    c = 0
    while True:
        fillrect(3, 42, 52, 240, 140, rgb(80, 100, 180), rgb(80, 100, 180))
        fillrect(3, 40, 50, 240, 140, forec, forec)
        SAPrint("Warning!" if j == 3 else "Exit?", 50, 60, 3, fontc)
        if j == 0:
            SAPrint("quit editing?" if saved else "'*' file will lost.", 55, 80, 3, fontc)
        elif j == 1:
            SAPrint("leave PrimeCode?", 55, 80, 3, fontc)
        elif j == 2:
            SAPrint("quit setting?", 55, 80, 3, fontc)
        elif j == 3:
            SAPrint("json syntax error.", 55, 80, 3, fontc)
            SAPrint("use default data...", 55, 100, 3, fontc)
        SAPrint("[Cancel]", 50, 162, 3, fontc, 8 * str((1 if theme == 0 else 0) + (1 if theme == 0 else 2) * (c == 0)))
        SAPrint("[Confirm]", 180, 162, 3, fontc, 9 * str((1 if theme == 0 else 0) + (1 if theme == 0 else 2) * (c == 1)))
        if keyboard() & (1 << 7):
            c = (c - 1) % 2
            while keyboard() & (1 << 7):
                pass
        if keyboard() & (1 << 8):
            c = (c + 1) % 2
            while keyboard() & (1 << 8):
                pass
        blit(0, 0, 0, 3)
        if keyboard() & (1 << 30):
            while keyboard() & (1 << 30):
                pass
            if c == 1:
                if j == 0 or j == 3:
                    mode = 0
                else:
                    mode = -1
            break


def press_key():
    global search, match, saved, adde, gbl, gb, Kt, ref, l_s_x, l_s_y, k_alp, k_shi, slider_y, indn, y0, yr, y, dx, ddx, gby, menu, menux, showgb, mouse_status, mouse_ansp, mse, eps, start_pos, mse_time, s, ColT, indent
    if keyboard() & (1 << 36):
        if Kt[36] == 0:
            if k_alp > 2:
                k_alp -= 2
            k_alp = (k_alp + 1) % 3
            if k_shi == 1:
                if k_alp == 2:
                    k_shi = 0
                k_alp += 2
        Kt[36] += 1
    else:
        Kt[36] = 0
    if keyboard() & (1 << 41):
        if Kt[41] == 0:
            k_shi = (k_shi + 1) % 2
        Kt[41] += 1
    else:
        Kt[41] = 0
    if keyboard() & (1 << 12):
        if k_shi == 1:
            gbl = len(s)
            gby = yr + 20 * gbl
            k_shi = 0
        elif Kt[12] == 0 or Kt[12] >= 15:
            gbl += 1
        match = []
        y_mov()
        Kt[12] += 1
    else:
        Kt[12] = 0
    if keyboard() & (1 << 2):
        if k_shi == 1:
            gbl = 1
            gby = yr + 20 * gbl
            k_shi = 0
        elif Kt[2] == 0 or Kt[2] >= 15:
            gbl -= 1
        match = []
        y_mov()
        Kt[2] += 1
    else:
        Kt[2] = 0
    if keyboard() & (1 << 7):
        if Kt[7] == 0 or Kt[7] >= 25:
            if k_shi == 1:
                gb = 0
                k_shi = 0
            elif gb == 0 and gbl > 1:
                gbl -= 1
                gb = len(s[gbl])
            else:
                gb -= 1
            match = []
        Kt[7] += 1
    else:
        Kt[7] = 0
    if keyboard() & (1 << 8):
        if Kt[8] == 0 or Kt[8] >= 25:
            if k_shi == 1:
                gb = len(s[gbl])
                k_shi = 0
            elif gb == len(s[gbl]) and gbl < len(s) - 1:
                gbl += 1
                gb = 0
            else:
                gb += 1
            match = []
        Kt[8] += 1
    else:
        Kt[8] = 0
    if keyboard() & (1 << 19):
        if Kt[19] == 0 or Kt[19] >= 25:
            if k_shi == 1:
                if gb < len(s[gbl]):
                    s[gbl] = s[gbl][:gb] + s[gbl][gb + 1:]
                    ColT[gbl] = ""
                    saved = 0
                k_shi = 0
            elif gb > 0:
                s[gbl] = s[gbl][:gb - 1] + s[gbl][gb:]
                ColT[gbl] = ""
                gb -= 1
                saved = 0
            elif gbl > 1:
                gb = len(s[gbl - 1])
                s[gbl - 1] = s[gbl - 1] + s[gbl]
                s.pop(gbl)
                ColT[gbl - 1] = ""
                ColT.pop(gbl)
                indent.pop(gbl)
                gbl -= 1
                saved = 0
            search = AFind(search_t)
            match = []
        Kt[19] += 1
    else:
        Kt[19] = 0
    if keyboard() & (1 << 30):
        if Kt[30] == 0 or Kt[30] >= 20:
            if k_shi == 1:
                s[gbl] = s[gbl][:gb] + 'approx()' + s[gbl][gb:]
                ColT[gbl] = ""
                gb += 7
            elif gb > -1:
                t = s[gbl][gb:]
                if gbl > 1 and Aindent:
                    # auto indent
                    ind_t = 0
                    if len(s[gbl]) > 0:
                        while s[gbl][ind_t] == " " and ind_t < len(s[gbl]) - 1:
                            ind_t += 1
                        if ind_t == len(s[gbl]) - 1:
                            ind_t += 1
                    t = (ind_t) * " " + t
                    gbt = ind_t
                else:
                    gbt = 0
                s[gbl] = s[gbl][:gb]
                s.insert(gbl + 1, t)
                ColT[gbl] = ""
                ColT.insert(gbl + 1, "")
                indent.insert(gbl + 1, 0)
                gb = gbt
                gbl += 1
            saved = 0
            search = AFind(search_t)
            match = []
        Kt[30] += 1
    else:
        Kt[30] = 0
    for d in range(len(Keyb)):
        if keyboard() & (1 << Keyb[d]):
            if Kt[Keyb[d]] == 0 or Kt[Keyb[d]] >= 20:
                if k_alp == 0 and k_shi == 0:
                    if d == 0:
                        adde = indn * " "
                    elif d == 1:
                        adde = ""
                        if gb >= indn and s[gbl][gb - 1] == " ":
                            s[gbl] = s[gbl][:gb - indn] + s[gbl][gb:]
                            gb -= indn
                    else:
                        adde = norm[d]
                elif k_alp == 3 and k_shi == 1:
                    adde = sha[d]
                elif k_alp != 0 and k_shi == 0:
                    if k_alp == 4:
                        adde = sha[d]
                    else:
                        adde = alp[d]
                elif k_alp == 0 and k_shi == 1:
                    adde = shi[d]
                else:
                    if not ((k_alp == 4 and k_shi == 1) or (k_alp == 3 and k_shi == 1)) or (k_alp <= 2 and k_shi == 1):
                        adde = sha[d]
                    else:
                        adde = alp[d]
                if k_alp == 1 or k_alp == 3:
                    k_alp = 0
                if k_shi == 1:
                    k_shi = 0
                if adde == "__sym__":
                    adde = symPad(len(indent))
                s[gbl] = s[gbl][:gb] + adde + s[gbl][gb:]
                ColT[gbl] = ""
                gb += len(adde)

                match_i = Afetch(s[gbl], gb)
                match = Amatch(s[gbl][match_i:gb])

                if len(adde) >= 1:
                    if adde[-1] in ')]}"':
                        gb -= 1
                saved = 0
                search = AFind(search_t)
            Kt[Keyb[d]] += 1
        else:
            Kt[Keyb[d]] = 0


def mouseEvent(file_list):
    global mode, Name, y, y0, yr, s, ColT, indent, gbl, mouse_status, mouse_ansp, slider_y
    if getMouse()[4] != -1:
        if mouse_status == 0:
            mouse_ansp = getMouse()
            if len(file_list) > 8:
                slider_y = mouse_ansp[1] - (24 - (240 - 24 - (10 + 1500 / len(file_list))) * (yr - 20) / (
                            20 * len(file_list) - 100))
        else:
            try:
                if mouse_ansp[0] >= 310 and len(file_list) > 7:
                    y0 = (20 * len(file_list) - 100) * (mouse_ansp[1] - slider_y - 24) / (-206 + 1500 / len(
                        file_list)) + 20
                    if len(getMouse()) != 0:
                        mouse_ansp = getMouse()
                elif mouse_ansp[4] == 2:
                    y0 += getMouse()[1] - mouse_ansp[1]
            except IndexError:
                pass
            mouse_ansp = getMouse()
        mouse_status += 1
    else:
        mouse_status = 0
        if mouse_ansp[4] == 0:
            # Click
            gbl = 1 + int((mouse_ansp[1] - yr) / 20 - .5)
            gbl = max(1, min(gbl, len(file_list) - 1))
            mouse_ansp = getMouse()


def choose(m, n, u, title, draw_menu=0):
    file_list = m
    global gb, gbl, gby, mode, Name, y, y0, yr, s, ColT, indent, gbl, mouse_status, mouse_ansp, slider_y
    yr, y, y0 = 20, 20, 20
    while True:
        gby = yr + 20 * gbl
        yr += (y0 - yr) * .4
        j = int(max(-(yr) / 20, 1))
        y = yr + j * 20 - 12
        fillrect(2, 0, 0, 320, 240, bg, bg)
        while j < len(file_list):
            if j == gbl:
                c = rgb(0, 0, 255, 160) if theme == 0 else rgb(0, 0, 255, 235)
                fillrect(2, 0, y - 1, 320, 18, c, c)
                APrint(file_list[j], 5, y, 0, "2" * len(file_list[j]))
            else:
                APrint(file_list[j], 5, y, 0)
            j += 1
            y += 20
        mouseEvent(file_list)
        drawSlider(2, len(file_list), yr, theme)
        if keyboard() & (1 << 30):
            while keyboard() & (1 << 30):
                pass
            Name = file_list[gbl]
            if Name == "setting.json":
                s = setting.split("\n")
                s.insert(0, "")
                suc = 1
            elif Name == "#New program":
                gb_t, gbl_t = gb, gbl
                Name = textBox("", "New program", "name:")
                gb, gbl = gb_t, gbl_t
                if len(Name) > 0 and Name not in eval('Programs'):
                    resetPrgm = ' '

                    if Name[-3:] == '.py':
                        resetPrgm = '//using <python> function. \n#PYTHON myPy()\n#python here...\n\n#end\n\n\nexport init()\nbegin\n    myPy();\nend;'
                        Name = Name[:-3]
                        s = resetPrgm.split("\n")
                        s.insert(0, "")
                    else:
                        s = ["", ""]
                    eval('Programs("' + Name + '"):=' + '"' + resetPrgm + '"')
                    suc = Name in eval('Programs')
                    title_, nr = "New program", "Invalid name."
                else:
                    suc = 0
                    title_, nr = "New program", ""
            else:
                try:
                    s = loadfile(Name)
                    suc = 1
                except AttributeError:
                    suc = 0
                    title_, nr = "PrimeCode " + ver, "Bad file type."
            if suc:
                ColT, indent = resetTemp(len(s))
                break
            else:
                if nr != "":
                    msgbox(title_, nr, len(file_list))

        if keyboard() & (1 << 4):
            blit(3, 0, 0, 2)
            tit(len(file_list), title, draw_menu, 0)
            iexit(u)
            if mode == -1:
                mode = n
                break
            else:
                mode = 1
        if keyboard() & (1 << 12):
            if Kt[12] == 0 or Kt[12] >= 15:
                gbl += 1
                y_mov()
            Kt[12] += 1
        else:
            Kt[12] = 0
        if keyboard() & (1 << 2):
            if Kt[2] == 0 or Kt[2] >= 15:
                gbl -= 1
                y_mov()
            Kt[2] += 1
        else:
            Kt[2] = 0
        gbl = max(1, min(gbl, len(file_list) - 1))
        y0 = min(20, max(y0, 120 - 20 * len(file_list)))
        title_bar(2)
        APrint(title, 5, 3, 0)
        blit(0, 0, 0, 2)


def y_mov():
    global y0, gby
    if gby > 200:
        y0 -= gby - 200
    if gby < 70:
        y0 -= gby - 70


def symPad(fl):
    blit(3, 0, 0, 2)
    tit(fl, Name if saved else Name + "*", 1, 1)
    fillrect(3, 72, 62, 180, 120, rgb(80, 100, 180), rgb(80, 100, 180))
    fillrect(3, 70, 60, 180, 120, forec, forec)
    symPadGui(theme)
    SAPrint("", 50, 110, 3, fontc)
    blit(0, 0, 0, 3)
    while getMouse()[4] == -1 and not (keyboard() & (1 << 4)):
        pass
    t = (getMouse()[0], getMouse()[1])
    while getMouse()[4] != -1 or keyboard() & (1 << 4):
        pass
    xi = int((t[0] - 70) / 60)
    yi = int((t[1] - 60) / 60)
    if 0 <= xi <= 2 and 0 <= yi <= 1:
        return symlist[yi * 3 + xi]
    return ""


def main():
    global j, gbx, gby1, Kt, txt, gb, k_shi, k_alp, dx, ddx, y0, yr, y, mode, gbl, saved, s, ColT, indent, search, search_t, search_w
    makesetting()
    readSetting(setting)
    initPPLKeyw()
    loadFont(font)
    dimgrob(2, 320, 240, rgb(255, 255, 255, 255))
    dimgrob(3, 320, 240, 0)
    fillrect(2, 42, 52, 240, 140, rgb(80, 100, 180), rgb(80, 100, 180))
    fillrect(2, 40, 50, 240, 140, forec, forec)
    APrint("PrimeCode " + ver, 50, 60, 0)
    APrint("initializing...", 160 - 16 * 10 / 2, 88, 0)
    APrint("by SQY", 50, 166, 0, "222222")
    blit(0, 0, 0, 2)
    eval('wait(0.6)')
    fillrect(2, 0, 0, 320, 240, bg, bg)
    title_bar(2)
    APrint("PrimeCode " + ver, 5, 3, 0)
    APrint("Welcome.", 160 - 8 * 10 / 2, 110, 0)
    blit(0, 0, 0, 2)
    eval('wait(0.5)')
    while mode >= 0:
        gb, gbl = 0, 1
        file_l = eval('Programs')
        file_l.insert(0, "#New program")
        file_l.insert(0, "setting.json")
        file_l.insert(0, "")
        makesetting()
        readSetting(setting)
        s, indent, ColT = [], [], []
        choose(file_l, -1, 1, "PrimeCode " + ver)
        if mode == -1:
            break
        else:
            mode = 1
        load_gui()
        gbl = 1
        yr, y0, y, dx, ddx = 20, 20, 20, 0, 0
        menu = 0
        saved, savet = 1, "?"
        clearSearch()
        k_alp = 0
        while mode == 1:
            uni()
            if keyboard() & (1 << 1) or keyboard() & (1 << 6):
                keyp = keyboard() & (1 << 1)
                gb_t, gbl_t = gb, gbl
                if keyboard() & (1 << 6):
                    search = []
                    t = textBox(search_t, "Replace", "search:", "", "replace:")
                else:
                    t = textBox(search_t, "Search", "search:")
                gb, gbl = gb_t, gbl_t
                if keyp:
                    Asearch(t)
                else:
                    if isinstance(t, tuple):
                        Areplace(t[0], t[1])

            if keyboard() & (1 << 4):
                if len(search) != 0:
                    clearSearch()
                    while keyboard() & (1 << 4):
                        pass
                else:
                    blit(3, 0, 0, 2)
                    tit(len(s), Name if saved else Name + "*", 1)
                    blit(0, 0, 0, 3)
                    iexit(3 if Name == "setting.json" and checkJSON(getOriginSaveFile(len(indent))) == 1 else 0)


def textBox(tt, title, remt, tt2="", remt2=""):
    global j, gbx, gby1, Kt, txt, gb, gbl, k_shi, k_alp, dx, ddx, y0, yr, y, mode, saved, s, ColT, indent, search, search_t, search_w
    txt = tt
    txt2 = tt2
    k_alp = 2
    gb = len(tt)
    gbl = j = 1
    gbx = 5 + len(remt) * 10
    while True:
        if getMouse()[4] == 0:
            mx, my = getMouse()[0], getMouse()[1]
            if 25 <= my <= 48:
                gbl = 1
            elif 48 < my <= 73:
                gbl = 2
            gb = b_find(u, getMouse()[0])
        fillrect(2, 0, 0, 320, 240, bg, bg)
        j = 1
        if gbl == j:
            u = APrint(txt, 5 + len(remt) * 10, 28, 1)
        else:
            APrint(txt, 5 + len(remt) * 10, 28, 1)
        APrint(remt, 5, 28, 3)
        line(2, 5 + len(remt) * 10, 48, 315, 48, rgb(200, 200, 200))
        if remt2 != "":
            j = 2
            if gbl == j:
                u = APrint(txt2, 5 + len(remt2) * 10, 53, 1)
            else:
                APrint(txt2, 5 + len(remt2) * 10, 53, 1)
            APrint(remt2, 5, 53, 3)
            line(2, 5 + len(remt2) * 10, 73, 315, 73, rgb(200, 200, 200))
        blit(3, 0, 0, 2)
        tit(0, title, 0, 0)
        if keyboard() != 0:
            c = rgb(200, 200, 255) if theme == 0 else rgb(0, 0, 55)
        else:
            c = (rgb(200, 200, 255, int(255 * 0.5 * (1 + sin(getTicks() / 200))))
                 if theme == 0 else
                 rgb(0, 0, 55, int(255 * 0.5 * (1 + sin(getTicks() / 200)))))
        line(3, gbx, 3 + gbl * 25, gbx, 19 + gbl * 25, c)
        if keyboard() != 0:
            if gbl == 1:
                Kt, txt, gb, k_shi, k_alp = press_key_simple(Kt, txt, gb, k_shi, k_alp)
            else:
                Kt, txt2, gb, k_shi, k_alp = press_key_simple(Kt, txt2, gb, k_shi, k_alp)
        else:
            Kt = [0] * 52
        blit(0, 0, 0, 3)
        if keyboard() & (1 << 12):
            while keyboard() & (1 << 12):
                pass
            gbl = min(2, gbl + 1)
        if keyboard() & (1 << 2):
            while keyboard() & (1 << 2):
                pass
            gbl = max(1, gbl - 1)
        if keyboard() & (1 << 30):
            while keyboard() & (1 << 30):
                pass
            return (txt, txt2) if remt2 != "" else txt
        if keyboard() & (1 << 4):
            while keyboard() & (1 << 4):
                pass
            return ""
        if gbl == 1:
            gb = min(gb, len(txt))
        else:
            gb = min(gb, len(txt2))


def clearSearch():
    global search, search_t, search_w
    search_t = ""
    search_w = 0
    search = []


def Asearch(txt):
    global search, search_t, search_w
    search_t = txt
    search_w = textW(search_t)
    search = AFind(search_t)


def Areplace(txt, rep):
    global indent, ColT, saved
    tmp = len(s)
    indent, ColT = [], []
    ColT, indent = resetTemp(tmp)
    saved = 0
    for e in range(len(indent)):
        s[e] = s[e].replace(txt, rep)


def AFind(txt):
    if len(txt) == 0:
        return []
    res = []
    for e in range(len(indent)):
        u = s[e]
        t = 0
        while u.find(txt) != -1:
            t += u.find(txt)
            res.append((e, t))
            u = u[u.find(txt) + 1:]
            t += 1
    if res == []:
        return [(-1, -1)]
    return res


main()
