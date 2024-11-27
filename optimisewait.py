import pyautogui
from time import sleep

def optimiseWait(filename, dontwait=False, specreg=None, clicks=1, xoff=0, yoff=0, autopath=r'D:\BobaDays\Auto', orfiles=None, orclicks=None):
    if not isinstance(filename, list):
        filename = [filename]
    if orfiles and not isinstance(orfiles, list):
        orfiles = [orfiles]
    if orclicks and not isinstance(orclicks, list):
        orclicks = [orclicks]
    if orfiles and not orclicks:
        orclicks = [1] * len(orfiles)

    clicked = 0
    while True:
        findloc = None
        for i, fname in enumerate([*filename, *(orfiles or [])]):
            try:
                if specreg is None:
                    loc = pyautogui.locateCenterOnScreen(fr'{autopath}\{fname}.png', confidence=0.9)
                    if loc and clicked == 0:
                        findloc = loc
                        clicked = i + 1
                else:
                    loc = pyautogui.locateOnScreen(fr'{autopath}\{fname}.png', region=specreg, confidence=0.9)
                    if loc:
                        findloc = loc
                        clicked = i + 1
            except pyautogui.ImageNotFoundException:
                continue

        if dontwait is False:
            if findloc:
                break
        else:
            if not findloc:
                print('dontwait: image not found')
                break
            else:
                print('dontwait: image found')
                break
        sleep(1)

    if findloc is not None:
        if specreg is None:
            x, y = findloc
        else:
            x, y, width, height = findloc
        xmod = x + xoff
        ymod = y + yoff
        sleep(1)

        click_count = clicks if clicked == 1 else orclicks[clicked-2] if clicked > 1 else 0
        if click_count > 0:
            for _ in range(click_count):
                pyautogui.click(xmod, ymod)
                sleep(0.1)
            print('clicked')