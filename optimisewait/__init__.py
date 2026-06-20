import pyautogui
import time
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

def optimiseWait(filename, dontwait=False, specreg=None, clicks=1, xoff=0, yoff=0, autopath=None, altpath=None, scrolltofind=None, clickdelay=0.1, interrupter=None, interrupterclicks=1, interrupter_once=True, humanize=False, circles=False, max_circle_time=5.0):
    """
    Waits for one of several possible images to appear on screen and optionally clicks it.

    Args:
        filename (str or list[str]): The name(s) of the image file(s) to find.
        dontwait (bool): If True, performs a single search and returns immediately.
        specreg (tuple): A specific region on the screen to search within.
        clicks (int or list[int]): The number of times to click the found image.
        xoff (int or list[int]): Horizontal offset in pixels for the click.
        yoff (int or list[int]): Vertical offset in pixels for the click.
        autopath (str): The primary directory path to search for the image files.
        altpath (str): A secondary, fallback directory path.
        scrolltofind (str): 'pageup' or 'pagedown' to scroll if not found.
        clickdelay (float): The delay in seconds between multiple clicks.
        interrupter (str or list[str]): Image(s) to click if they interrupt the wait.
        interrupterclicks (int or list[int]): Number of times to click interrupters.
        interrupter_once (bool): Whether to click interrupters only once.
        humanize (bool): If True, applies random offsets and WindMouse trajectories.
        circles (bool): If True, idly moves mouse in a wobbly human circle while waiting.
        max_circle_time (float): Maximum seconds to circle before going totally idle.
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
        circle_start_time = time.time()
        try:
            start_x, start_y = pyautogui.position()
        except:
            start_x, start_y = 500, 500
            
        # Define the human circle characteristics
        circle_revolutions = random.uniform(1.5, 3.5)
        circle_base_rx = random.randint(50, 180)
        circle_base_ry = random.randint(50, 180)
        circle_start_angle = random.uniform(0, 2 * math.pi)
        
        # Shift the center so the mouse doesn't jerk to start the circle
        circle_center_x = start_x - circle_base_rx * math.cos(circle_start_angle)
        circle_center_y = start_y - circle_base_ry * math.sin(circle_start_angle)
        
        try:
            screen_w, screen_h = pyautogui.size()
        except:
            screen_w, screen_h = 1920, 1080

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
                        current_x, current_y = pyautogui.position()
                        
                        # Use WindMouse for natural, curved traversal
                        wind_mouse(current_x, current_y, hx, hy)
                        
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
                current_x, current_y = pyautogui.position()
                
                # Use WindMouse for natural, curved traversal
                wind_mouse(current_x, current_y, hxmod, hymod)
                
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

        # --- Loop Control & Idle Wait ---
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
                elapsed_time = time.time() - circle_start_time
                
                if elapsed_time < max_circle_time:
                    # Calculate progress of the circle from 0.0 to 1.0
                    t = elapsed_time / max_circle_time
                    
                    # Ease-in/ease-out timing for realistic acceleration
                    human_t = t + (math.sin(t * math.pi * 2) * 0.05)
                    angle = circle_start_angle + (human_t * circle_revolutions * 2 * math.pi)
                    
                    # Convert elapsed time into a pseudo-frame counter to create wobble noise
                    i_equiv = elapsed_time * 60 
                    noise_x = math.sin(i_equiv * 0.2) * 8 + random.uniform(-2, 2)
                    noise_y = math.cos(i_equiv * 0.2) * 8 + random.uniform(-2, 2)
                    
                    # Determine next coordinates
                    dest_x = circle_center_x + (circle_base_rx + noise_x) * math.cos(angle)
                    dest_y = circle_center_y + (circle_base_ry + noise_y) * math.sin(angle)
                    
                    # Ensure mouse doesn't crash into monitor bounds
                    dest_x = max(10, min(screen_w - 10, dest_x))
                    dest_y = max(10, min(screen_h - 10, dest_y))
                    
                    try:
                        # Move smoothly to the new calculated point
                        pyautogui.moveTo(dest_x, dest_y, duration=0.05)
                    except pyautogui.FailSafeException:
                        pass
                else:
                    # Max circle time exceeded; drop to a fully idle state
                    sleep(0.25)
            else:
                sleep(random.uniform(0.8, 1.2) if humanize else 1)