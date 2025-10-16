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

def _locate_image(fname, autopath, altpath, specreg=None):
    """Internal helper to find an image, checking both primary and alt paths."""
    # Try main path first
    try:
        main_path = os.path.join(autopath, f'{fname}.png')
        if os.path.exists(main_path):
            if specreg is None:
                # Returns a Point(x, y) or None
                return pyautogui.locateCenterOnScreen(main_path, confidence=0.9)
            else:
                # Returns a Box(left, top, width, height) or None
                return pyautogui.locateOnScreen(main_path, region=specreg, confidence=0.9)
    except (pyautogui.ImageNotFoundException, FileNotFoundError):
        pass

    # Try alt path if not found in main and altpath is provided
    if altpath is not None:
        try:
            alt_path = os.path.join(altpath, f'{fname}.png')
            if os.path.exists(alt_path):
                if specreg is None:
                    return pyautogui.locateCenterOnScreen(alt_path, confidence=0.9)
                else:
                    return pyautogui.locateOnScreen(alt_path, region=specreg, confidence=0.9)
        except (pyautogui.ImageNotFoundException, FileNotFoundError):
            pass
            
    return None

def optimiseWait(filename, dontwait=False, specreg=None, clicks=1, xoff=0, yoff=0, autopath=None, altpath=None, scrolltofind=None, clickdelay=0.1, interrupter=None):
    """
    Waits for one of several possible images to appear on screen and optionally clicks it.
    Can also handle and click 'interrupter' images that appear while waiting.

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
            
        interrupter (str or list[str], optional): An image or list of images
            to search for and click if the primary `filename` is not found
            in a given loop. After clicking an interrupter, the function
            continues to wait for the primary image instead of returning.
            This is useful for handling unexpected pop-ups. Defaults to None.

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
    filenames = filename if isinstance(filename, list) else [filename]
    
    if not isinstance(clicks, list):
        clicks = [clicks] * len(filenames)
    elif len(clicks) < len(filenames):
        clicks.extend([1] * (len(filenames) - len(clicks)))
    
    if not isinstance(xoff, list):
        xoff = [xoff] * len(filenames)
    elif len(xoff) < len(filenames):
        xoff.extend([0] * (len(filenames) - len(xoff)))
        
    if not isinstance(yoff, list):
        yoff = [yoff] * len(filenames)
    elif len(yoff) < len(filenames):
        yoff.extend([0] * (len(filenames) - len(yoff)))

    # --- Main Loop ---
    while True:
        first_found_image = None
        
        # 1. Search for the primary target images
        for i, fname in enumerate(filenames):
            findloc = _locate_image(fname, autopath, altpath, specreg)
            
            if findloc is not None:
                first_found_image = {
                    'index': i,
                    'filename': fname,
                    'location': findloc,
                }
                break # Prioritize first image in the list

        # 2. If a primary image was found, process and return
        if first_found_image:
            loc = first_found_image['location']
            found_index = first_found_image['index']
            
            # Determine center coordinates for clicking
            # PyAutoGUI's center() works on both Point and Box objects
            center_loc = pyautogui.center(loc)
            
            # Apply offsets
            xmod = center_loc.x + xoff[found_index]
            ymod = center_loc.y + yoff[found_index]

            # Perform clicks if count > 0
            click_count = clicks[found_index]
            pyautogui.moveTo(xmod, ymod)
            if click_count > 0:
                for _ in range(click_count):
                    pyautogui.click()
                    if click_count > 1:
                        sleep(clickdelay)
            
            return {'found': True, 'image': first_found_image['filename'], 'location': loc}

        # 3. If NO primary image found, check for interrupters before waiting
        if interrupter:
            interrupter_list = interrupter if isinstance(interrupter, list) else [interrupter]
            for inter_fname in interrupter_list:
                inter_loc = _locate_image(inter_fname, autopath, altpath, specreg)
                if inter_loc:
                    pyautogui.click(inter_loc)
                    sleep(0.3) # Brief pause after clicking the interrupter
                    break # Handle one interrupter per cycle, then re-scan for primary

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