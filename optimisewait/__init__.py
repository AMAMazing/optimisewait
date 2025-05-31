import pyautogui
from time import sleep

_default_autopath = r'C:\\'
_default_altpath = None

def set_autopath(path):
    global _default_autopath
    _default_autopath = path

def set_altpath(path):
    global _default_altpath
    _default_altpath = path

def optimiseWait(filename, dontwait=False, specreg=None, clicks=1, xoff=0, yoff=0, autopath=None, altpath=None, scrolltofind=None): # Added scrolltofind
    global _default_autopath, _default_altpath
    autopath = autopath if autopath is not None else _default_autopath
    # Only use default altpath if altpath parameter is not provided (vs being explicitly None)
    # Note: This line's original logic for using _default_altpath might not behave as the comment suggests.
    # It currently effectively means _default_altpath is not used unless explicitly passed as the altpath argument.
    # Kept as-is to preserve existing behavior.
    altpath = _default_altpath if altpath is None and 'altpath' not in locals() else altpath


    if not isinstance(filename, list):
        filename = [filename]
    if not isinstance(clicks, list):
        clicks = [clicks] + [1] * (len(filename) - 1)
    elif len(clicks) < len(filename):
        clicks = clicks + [1] * (len(filename) - len(clicks))
    
    if not isinstance(xoff, list):
        xoff = [xoff] * len(filename)
    elif len(xoff) < len(filename):
        xoff = xoff + [0] * (len(filename) - len(xoff))
        
    if not isinstance(yoff, list):
        yoff = [yoff] * len(filename)
    elif len(yoff) < len(filename):
        yoff = yoff + [0] * (len(filename) - len(yoff))

    clicked = 0
    while True:
        findloc = None
        found_in_alt = False # This variable is set but not used elsewhere in the original code. Kept as is.
        
        for i, fname in enumerate(filename):
            # Try main path first
            try:
                if specreg is None:
                    loc = pyautogui.locateCenterOnScreen(fr'{autopath}\{fname}.png', confidence=0.9)
                else:
                    loc = pyautogui.locateOnScreen(fr'{autopath}\{fname}.png', region=specreg, confidence=0.9)
                
                if loc and clicked == 0: # ensure we only mark the first found image
                    findloc = loc
                    clicked = i + 1
                    found_in_alt = False
                    break
            except pyautogui.ImageNotFoundException:
                pass
            
            # Try alt path if provided and image wasn't found in main path
            if altpath is not None and not findloc: # Check not findloc to ensure main path was fully checked for this fname
                try:
                    if specreg is None:
                        loc = pyautogui.locateCenterOnScreen(fr'{altpath}\{fname}.png', confidence=0.9)
                    else:
                        loc = pyautogui.locateOnScreen(fr'{altpath}\{fname}.png', region=specreg, confidence=0.9)
                    
                    if loc and clicked == 0: # ensure we only mark the first found image
                        findloc = loc
                        clicked = i + 1
                        found_in_alt = True
                        break
                except pyautogui.ImageNotFoundException:
                    continue # To the next filename

        if findloc is not None:
            # Note: Original click logic for specreg might not align with "offset from center" if specreg is used,
            # as x,y would be top-left. Kept as-is.
            if specreg is None:
                x, y = findloc
            else:
                x, y, width, height = findloc # x, y are top-left
            
            current_xoff = xoff[clicked - 1] if clicked > 0 else 0
            current_yoff = yoff[clicked - 1] if clicked > 0 else 0
            xmod = x + current_xoff
            ymod = y + current_yoff
            sleep(1) # Pre-click delay

            click_count = clicks[clicked - 1] if clicked > 0 else 0
            if click_count > 0:
                for _ in range(click_count):
                    pyautogui.click(xmod, ymod)
                    sleep(0.1) # Inter-click delay

        # Loop control, return, or wait/scroll logic
        if dontwait is False:
            if findloc: # Image found, and we are in "wait" mode (dontwait=False)
                break   # Exit the while True loop, success will be returned after the loop
            else: # Image not found (findloc is None), and we are in "wait" mode (dontwait=False)
                # Attempt to scroll if enabled
                if scrolltofind == 'pageup':
                    pyautogui.press('pageup')
                    sleep(0.5) # Allow screen to update and action to complete
                elif scrolltofind == 'pagedown':
                    pyautogui.press('pagedown')
                    sleep(0.5) # Allow screen to update and action to complete
                # If scrolltofind is None or an invalid value, no scrolling happens here.
                # The loop will continue, and the sleep(1) below will provide the pause.
        else: # dontwait is True
            # This block is executed if dontwait is True.
            # It determines whether to return based on whether the image was found on this single pass.
            # Scrolling does not occur if dontwait is True.
            if not findloc:
                return {'found': False, 'image': None}
            else: # findloc is not None
                return {'found': True, 'image': filename[clicked - 1]}
        
        # This sleep executes if `dontwait` is False and the image was not found (`findloc` is None in this iteration),
        # causing the loop to pause before the next attempt.
        # If `findloc` was True (and `dontwait` was False), `break` would have been hit, skipping this.
        # If `dontwait` was True, a return would have happened, skipping this.
        sleep(1) 
    
    # This return is reached only if dontwait=False and the loop was broken (image found)
    return {'found': True, 'image': filename[clicked - 1]} if findloc is not None else {'found': False, 'image': None}