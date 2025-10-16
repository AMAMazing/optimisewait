import pyautogui
from time import sleep
import os

# --- Global Default Paths ---
_default_autopath = r'C:\\'
_default_altpath = None

def set_autopath(path):
    """Sets the global default primary path for image assets."""
    global _default_autopath
    _default_autopath = path

def set_altpath(path):
    """Sets the global default alternative/fallback path for image assets."""
    global _default_altpath
    _default_altpath = path

def optimiseWait(filename, dontwait=False, specreg=None, clicks=1, xoff=0, yoff=0, autopath=None, altpath=None, scrolltofind=None, clickdelay=0.1, interrupter=None, interrupterclicks=1, interrupter_once=True):
    """
    Waits for one of several possible images to appear on screen and optionally clicks it.

    This function repeatedly scans the screen for a list of images. It will act
    on the first image it finds in the list's order. It is highly configurable,
    allowing for different click counts, click offsets, and search paths for each
    image, as well as fallback behaviors like scrolling.

    Args:
        filename (str or list[str]): The name(s) of the image file(s) to find,
            without the '.png' extension. If a list is provided, images are
            searched for in that order. The first one found is used.

        dontwait (bool, optional): Controls the waiting behavior.
            - False (default): The function will loop indefinitely until an image
              is found.
            - True: The function will perform a single search and return
              immediately, whether an image was found or not.

        specreg (tuple, optional): A specific region on the screen to search within,
            defined as a tuple (left, top, width, height). If None (default),
            the entire screen is searched. Searching a smaller region is
            significantly faster.

        clicks (int or list[int], optional): The number of times to click the
            found image. Defaults to 1.
            - int: The specified number of clicks is applied to whichever image
              is found (e.g., `clicks=0` finds but doesn't click; `clicks=3`
              clicks the found image 3 times).
            - list[int]: Assigns a specific click count to each image in
              `filename` by index. If the list is shorter than `filename`, the
              remaining images will default to 1 click (e.g., for 3 filenames,
              `clicks=[2, 0]` means the first gets 2 clicks, the second gets 0,
              and the third defaults to 1).

        xoff (int or list[int], optional): Horizontal offset in pixels to apply
            to the click coordinate, relative to the center of the found image.
            A positive value moves the click right, negative moves it left.
            Accepts a single integer to apply to all images or a list to
            specify an offset for each. Defaults to 0.

        yoff (int or list[int], optional): Vertical offset in pixels to apply to
            the click coordinate. A positive value moves the click down,
            negative moves it up. Accepts a single integer or a list.
            Defaults to 0.

        autopath (str, optional): The primary directory path to search for the
            image files. If None (default), uses the global `_default_autopath`.

        altpath (str, optional): A secondary, fallback directory path. If an
            image is not found in `autopath`, this directory will be checked.
            If None (default), uses the global `_default_altpath`.

        scrolltofind (str, optional): If no images are found in a search loop,
            this action can be performed to reveal more of the screen.
            Accepts 'pageup' or 'pagedown'. If None (default), no scrolling occurs.
            This only has an effect when `dontwait=False`.

        clickdelay (float, optional): The delay in seconds between multiple
            clicks when `clicks` is greater than 1. Defaults to 0.1.

        interrupter (str or list[str], optional): The name(s) of image file(s)
            to check for while waiting for the main `filename` images. If any
            interrupter image appears, it will be clicked according to
            `interrupterclicks`, but the function will continue waiting for the
            main images. If None (default), no interrupter checking occurs.

        interrupterclicks (int or list[int], optional): The number of times to
            click an interrupter image if found. Defaults to 1.
            - int: Applied to all interrupter images.
            - list[int]: Assigns a specific click count to each interrupter
              image by index, with remaining images defaulting to 1 click.

        interrupter_once (bool, optional): Controls whether interrupter images
            are clicked only once or repeatedly. Defaults to True.
            - True (default): Each interrupter image is clicked only the first
              time it appears, then ignored for the remainder of the wait.
            - False: Interrupter images are clicked every time they are detected
              during the waiting loop.

    Returns:
        dict: A dictionary containing the results of the search.
            - 'found' (bool): True if an image was found, otherwise False.
            - 'image' (str or None): The filename of the found image.
            - 'location' (pyautogui.Point or pyautogui.Box or None): The location
              of the found image on the screen.
    """
    global _default_autopath, _default_altpath
    autopath = autopath if autopath is not None else _default_autopath
    altpath = altpath if altpath is not None else _default_altpath

    # --- Parameter Normalization ---
    if not isinstance(filename, list):
        filename = [filename]

    if not isinstance(clicks, list):
        clicks = [clicks] * len(filename)
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

    # --- Interrupter Parameter Normalization ---
    interrupter_list = None
    interrupterclicks_list = None
    clicked_interrupters = set()  # Track which interrupters have been clicked
    
    if interrupter is not None:
        if not isinstance(interrupter, list):
            interrupter_list = [interrupter]
        else:
            interrupter_list = interrupter
        
        if not isinstance(interrupterclicks, list):
            interrupterclicks_list = [interrupterclicks] * len(interrupter_list)
        elif len(interrupterclicks) < len(interrupter_list):
            interrupterclicks_list = interrupterclicks + [1] * (len(interrupter_list) - len(interrupterclicks))
        else:
            interrupterclicks_list = interrupterclicks

    # --- Main Loop ---
    while True:
        # --- Check for Interrupter Images ---
        if interrupter_list is not None:
            for i, int_fname in enumerate(interrupter_list):
                # Skip if already clicked and interrupter_once is True
                if interrupter_once and i in clicked_interrupters:
                    continue
                
                int_findloc = None
                
                # Try main path first
                try:
                    main_path = fr'{autopath}\{int_fname}.png'
                    if os.path.exists(main_path):
                        if specreg is None:
                            loc = pyautogui.locateCenterOnScreen(main_path, confidence=0.9)
                        else:
                            loc = pyautogui.locateOnScreen(main_path, region=specreg, confidence=0.9)
                        if loc: int_findloc = loc
                except (pyautogui.ImageNotFoundException, FileNotFoundError):
                    pass
                
                # Try alt path if not found in main
                if int_findloc is None and altpath is not None:
                    try:
                        alt_path = fr'{altpath}\{int_fname}.png'
                        if os.path.exists(alt_path):
                            if specreg is None:
                                loc = pyautogui.locateCenterOnScreen(alt_path, confidence=0.9)
                            else:
                                loc = pyautogui.locateOnScreen(alt_path, region=specreg, confidence=0.9)
                            if loc: int_findloc = loc
                    except (pyautogui.ImageNotFoundException, FileNotFoundError):
                        pass
                
                # If interrupter found, click it and continue waiting
                if int_findloc is not None:
                    # Determine center coordinates for clicking
                    if specreg is None:
                        x, y = int_findloc
                    else:
                        x = int_findloc.left + int_findloc.width / 2
                        y = int_findloc.top + int_findloc.height / 2
                    
                    # Perform clicks
                    int_click_count = interrupterclicks_list[i]
                    pyautogui.moveTo(x, y)
                    if int_click_count > 0:
                        for _ in range(int_click_count):
                            pyautogui.click()
                            sleep(clickdelay)
                    
                    # Mark this interrupter as clicked
                    if interrupter_once:
                        clicked_interrupters.add(i)
                    
                    # Don't return, continue to check for main images
                    break  # Exit interrupter loop to continue main flow

        # --- Check for Main Images ---
        first_found_image = None
        
        for i, fname in enumerate(filename):
            findloc = None
            
            # Try main path first
            try:
                main_path = fr'{autopath}\{fname}.png'
                if os.path.exists(main_path):
                    if specreg is None:
                        loc = pyautogui.locateCenterOnScreen(main_path, confidence=0.9)
                    else:
                        loc = pyautogui.locateOnScreen(main_path, region=specreg, confidence=0.9)
                    if loc: findloc = loc
            except (pyautogui.ImageNotFoundException, FileNotFoundError):
                pass
            
            # Try alt path if not found in main
            if findloc is None and altpath is not None:
                try:
                    alt_path = fr'{altpath}\{fname}.png'
                    if os.path.exists(alt_path):
                        if specreg is None:
                            loc = pyautogui.locateCenterOnScreen(alt_path, confidence=0.9)
                        else:
                            loc = pyautogui.locateOnScreen(alt_path, region=specreg, confidence=0.9)
                        if loc: findloc = loc
                except (pyautogui.ImageNotFoundException, FileNotFoundError):
                    pass

            # If found, store it and break the inner loop to prioritize this image
            if findloc is not None:
                first_found_image = {
                    'index': i,
                    'filename': fname,
                    'location': findloc,
                }
                break # Exit the for loop over filenames

        # --- Action Phase ---
        if first_found_image:
            loc = first_found_image['location']
            found_index = first_found_image['index']
            
            # Determine center coordinates for clicking
            if specreg is None:
                x, y = loc # locateCenterOnScreen returns a Point(x, y)
            else:
                # locateOnScreen returns a Box(left, top, width, height)
                x = loc.left + loc.width / 2
                y = loc.top + loc.height / 2
            
            # Apply offsets
            xmod = x + xoff[found_index]
            ymod = y + yoff[found_index]

            # Perform clicks if count > 0
            click_count = clicks[found_index]
            pyautogui.moveTo(xmod, ymod)
            if click_count > 0:
                for _ in range(click_count):
                    pyautogui.click()
                    sleep(clickdelay)
            
            # Since we found and processed an image, return success
            return {'found': True, 'image': first_found_image['filename'], 'location': loc}

        # --- Loop Control ---
        if dontwait:
            return {'found': False, 'image': None, 'location': None}
        else:
            # If nothing was found, scroll if configured, then wait and retry
            if scrolltofind == 'pageup':
                pyautogui.press('pageup')
                sleep(0.5)
            elif scrolltofind == 'pagedown':
                pyautogui.press('pagedown')
                sleep(0.5)
            sleep(1)