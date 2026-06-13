import pyautogui
from time import sleep
import os
import random
import math

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

def wind_mouse(start_x, start_y, dest_x, dest_y, gravity=9, wind=3, min_wait=0.004, max_wait=0.009, max_step=8, target_area=10):
    """
    Simulates human-like mouse movement using the WindMouse algorithm.
    Tuned for a slower, more deliberate movement speed.
    """
    # Temporarily disable pyautogui's default pause to prevent the movement from stuttering heavily
    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = 0
    
    current_x, current_y = start_x, start_y
    velo_x, velo_y = 0, 0
    wind_x, wind_y = 0, 0
    
    try:
        while True:
            dist = math.hypot(dest_x - current_x, dest_y - current_y)
            if dist < 1:
                break
                
            # Randomly adjust wind to create wobble
            if random.randint(1, 100) < 50:
                wind_x = wind_x / math.sqrt(3) + (random.random() * (wind * 2 + 1) - wind) / math.sqrt(5)
                wind_y = wind_y / math.sqrt(3) + (random.random() * (wind * 2 + 1) - wind) / math.sqrt(5)
            
            # Gravity pulls the mouse towards the destination
            grav_x = (dest_x - current_x) * (gravity / max(dist, 1))
            grav_y = (dest_y - current_y) * (gravity / max(dist, 1))
            
            # Apply forces to velocity
            velo_x += grav_x + wind_x
            velo_y += grav_y + wind_y
            
            # Limit the maximum step size (velocity magnitude)
            velo_mag = math.hypot(velo_x, velo_y)
            if velo_mag > max_step:
                # Randomize the step slightly so speed isn't perfectly uniform
                random_step = (max_step / 2) + random.random() * (max_step / 2)
                velo_x = (velo_x / velo_mag) * random_step
                velo_y = (velo_y / velo_mag) * random_step
            
            old_x, old_y = current_x, current_y
            current_x += velo_x
            current_y += velo_y
            
            new_px, new_py = int(round(current_x)), int(round(current_y))
            
            # Only issue a move command if the pixel coordinate actually changed
            if new_px != int(round(old_x)) or new_py != int(round(old_y)):
                pyautogui.moveTo(new_px, new_py)
                sleep(random.uniform(min_wait, max_wait))
            
            # Slow down as the mouse approaches the target
            if dist < target_area:
                wind_x, wind_y = 0, 0
                max_step = max_step * 0.6  # Apply brakes
                
        # Final exact snap to ensure it reaches the destination
        pyautogui.moveTo(dest_x, dest_y)
        
    finally:
        # Always restore original pause setting
        pyautogui.PAUSE = original_pause

def optimiseWait(filename, dontwait=False, specreg=None, clicks=1, xoff=0, yoff=0, autopath=None, altpath=None, scrolltofind=None, clickdelay=0.1, interrupter=None, interrupterclicks=1, interrupter_once=True, humanize=False, circles=False):
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
              
        humanize (bool, optional): If True, applies random offsets, randomized 
            mouse movement durations, ease-in/ease-out curves, and jittered 
            delays to simulate a human user. Defaults to False.
            
        circles (bool, optional): If True, moves the mouse in a slow circular motion
            using windmouse while waiting for the image to appear. Defaults to False.

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

    # --- Circle Parameter Initialization ---
    if circles:
        circle_angle = 0
        circle_radius = 100
        try:
            circle_center_x, circle_center_y = pyautogui.position()
        except:
            circle_center_x, circle_center_y = 500, 500

    # --- Main Loop ---
    while True:
        # --- Check for Interrupter Images ---
        if interrupter_list is not None:
            for i, int_fname in enumerate(interrupter_list):
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
                    if specreg is None:
                        x, y = int_findloc
                    else:
                        x = int_findloc.left + int_findloc.width / 2
                        y = int_findloc.top + int_findloc.height / 2
                    
                    int_click_count = interrupterclicks_list[i]
                    
                    if humanize:
                        hx = x + random.randint(-4, 4)
                        hy = y + random.randint(-4, 4)
                        start_x, start_y = pyautogui.position()
                        
                        # Use WindMouse for natural, curved traversal
                        wind_mouse(start_x, start_y, hx, hy)
                        
                        if int_click_count > 0:
                            sleep(random.uniform(0.1, 0.3))
                    else:
                        # Original fast robotic movement
                        pyautogui.moveTo(x, y)
                        
                    if int_click_count > 0:
                        for _ in range(int_click_count):
                            pyautogui.click()
                            if humanize:
                                sleep(max(0, clickdelay + random.uniform(-0.03, 0.08)))
                            else:
                                sleep(clickdelay)
                    
                    if interrupter_once:
                        clicked_interrupters.add(i)
                    
                    break  # Exit interrupter loop to continue main flow

        # --- Check for Main Images ---
        first_found_image = None
        
        for i, fname in enumerate(filename):
            findloc = None
            
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

            if findloc is not None:
                first_found_image = {
                    'index': i,
                    'filename': fname,
                    'location': findloc,
                }
                break

        # --- Action Phase ---
        if first_found_image:
            loc = first_found_image['location']
            found_index = first_found_image['index']
            
            if specreg is None:
                x, y = loc 
            else:
                x = loc.left + loc.width / 2
                y = loc.top + loc.height / 2
            
            xmod = x + xoff[found_index]
            ymod = y + yoff[found_index]

            click_count = clicks[found_index]
            
            if humanize:
                hxmod = xmod + random.randint(-4, 4)
                hymod = ymod + random.randint(-4, 4)
                start_x, start_y = pyautogui.position()
                
                # Use WindMouse for natural, curved traversal
                wind_mouse(start_x, start_y, hxmod, hymod)
                
                if click_count > 0:
                    sleep(random.uniform(0.1, 0.3))
            else:
                # Original fast robotic movement
                pyautogui.moveTo(xmod, ymod)
                
            if click_count > 0:
                for _ in range(click_count):
                    pyautogui.click()
                    if humanize:
                        sleep(max(0, clickdelay + random.uniform(-0.03, 0.08)))
                    else:
                        sleep(clickdelay)
            
            return {'found': True, 'image': first_found_image['filename'], 'location': loc}

        # --- Loop Control ---
        if dontwait:
            return {'found': False, 'image': None, 'location': None}
        else:
            if scrolltofind == 'pageup':
                pyautogui.press('pageup')
                sleep(random.uniform(0.4, 0.7) if humanize else 0.5)
            elif scrolltofind == 'pagedown':
                pyautogui.press('pagedown')
                sleep(random.uniform(0.4, 0.7) if humanize else 0.5)
                
            if circles:
                circle_angle += math.pi / 4  # Move 45 degrees around the circle
                dest_x = circle_center_x + math.cos(circle_angle) * circle_radius
                dest_y = circle_center_y + math.sin(circle_angle) * circle_radius
                
                try:
                    screen_width, screen_height = pyautogui.size()
                    dest_x = max(10, min(screen_width - 10, dest_x))
                    dest_y = max(10, min(screen_height - 10, dest_y))
                except:
                    pass
                
                try:
                    start_x, start_y = pyautogui.position()
                    wind_mouse(start_x, start_y, dest_x, dest_y)
                except pyautogui.FailSafeException:
                    pass
                    
                # Small pause since wind_mouse itself contains small delays
                sleep(random.uniform(0.1, 0.3) if humanize else 0.2)
            else:
                sleep(random.uniform(0.8, 1.2) if humanize else 1)