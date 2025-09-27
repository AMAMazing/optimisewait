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

def optimiseWait(filename, dontwait=False, specreg=None, clicks=1, xoff=0, yoff=0, autopath=None, altpath=None, scrolltofind=None, clickdelay=0.1):
    global _default_autopath, _default_altpath
    autopath = autopath if autopath is not None else _default_autopath
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

    while True:
        images_found = []  # Track all found images this iteration
        
        for i, fname in enumerate(filename):
            findloc = None
            found_in_alt = False
            
            # Try main path first
            try:
                # Check if file exists before trying to locate it
                import os
                main_path = fr'{autopath}\{fname}.png'
                if os.path.exists(main_path):
                    if specreg is None:
                        loc = pyautogui.locateCenterOnScreen(main_path, confidence=0.9)
                    else:
                        loc = pyautogui.locateOnScreen(main_path, region=specreg, confidence=0.9)
                    
                    if loc:
                        findloc = loc
                        found_in_alt = False
            except (pyautogui.ImageNotFoundException, FileNotFoundError):
                pass
            
            # Try alt path if provided and image wasn't found in main path
            if altpath is not None and not findloc:
                try:
                    alt_path = fr'{altpath}\{fname}.png'
                    if os.path.exists(alt_path):
                        if specreg is None:
                            loc = pyautogui.locateCenterOnScreen(alt_path, confidence=0.9)
                        else:
                            loc = pyautogui.locateOnScreen(alt_path, region=specreg, confidence=0.9)
                        
                        if loc:
                            findloc = loc
                            found_in_alt = True
                except (pyautogui.ImageNotFoundException, FileNotFoundError):
                    continue

            # If we found this image, add it to our found list
            if findloc is not None:
                images_found.append({
                    'index': i,
                    'filename': fname,
                    'location': findloc,
                    'found_in_alt': found_in_alt
                })

        # If we found at least one image, click on the first one found
        if images_found:
            # Use the first found image
            first_found = images_found[0]
            findloc = first_found['location']
            clicked_index = first_found['index']
            
            # Click logic
            if specreg is None:
                x, y = findloc
            else:
                x, y, width, height = findloc
            
            current_xoff = xoff[clicked_index]
            current_yoff = yoff[clicked_index]
            xmod = x + current_xoff
            ymod = y + current_yoff
            sleep(1)  # Pre-click delay

            click_count = clicks[clicked_index]
            if click_count > 0:
                for _ in range(click_count):
                    sleep(clickdelay)  # Inter-click delay
                    pyautogui.click(xmod, ymod)

        # Loop control logic
        if dontwait is False:
            if images_found:  # At least one image found, exit the loop
                break
            else:  # No images found, continue searching
                # Attempt to scroll if enabled
                if scrolltofind == 'pageup':
                    pyautogui.press('pageup')
                    sleep(0.5)
                elif scrolltofind == 'pagedown':
                    pyautogui.press('pagedown')
                    sleep(0.5)
                sleep(1)  # Wait before next attempt
        else:  # dontwait is True
            if not images_found:
                return {'found': False, 'image': None}
            else:
                return {'found': True, 'image': images_found[0]['filename']}
    
    # This return is reached only if dontwait=False and at least one image was found
    return {'found': True, 'image': images_found[0]['filename']} if images_found else {'found': False, 'image': None}
