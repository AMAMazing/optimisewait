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
        pyautogui.PAUSE = original_pause

def organic_trackpad_swirl(duration=5.0, start_x=None, start_y=None, base_speed=16.5):
    """
    Simulates human-like fast oval swirling on a trackpad with dynamic breathing,
    continuous center drift, biomechanical 2/3-power-law cadence, and Brownian motor tremor.
    Can be called standalone or imported into other scripts.
    """
    try:
        screen_w, screen_h = pyautogui.size()
    except Exception:
        screen_w, screen_h = 1920, 1080

    if start_x is None or start_y is None:
        try:
            start_x, start_y = pyautogui.position()
        except Exception:
            start_x, start_y = screen_w // 2, screen_h // 2

    base_rx = 180.0
    base_ry = 75.0
    base_tilt = math.radians(-15)  # Natural right-handed trackpad wrist slant

    # Offset center relative to start position so there is no initial jump/teleport
    init_rot_x = base_rx * math.cos(base_tilt)
    init_rot_y = base_rx * math.sin(base_tilt)
    base_center_x = max(base_rx + 20, min(screen_w - base_rx - 20, start_x - init_rot_x))
    base_center_y = max(base_ry + 20, min(screen_h - base_ry - 20, start_y - init_rot_y))

    center_drift_x = 0.0
    center_drift_y = 0.0
    angle = 0.0
    tremor_x = 0.0
    tremor_y = 0.0

    original_pause = pyautogui.PAUSE
    pyautogui.PAUSE = 0
    start_time = time.time()
    last_time = start_time

    try:
        while True:
            now = time.time()
            elapsed = now - start_time
            if elapsed >= duration:
                break

            dt = now - last_time
            last_time = now

            # 1. Continuous center wandering
            center_drift_x = (center_drift_x + random.uniform(-1.8, 1.8)) * 0.985
            center_drift_y = (center_drift_y + random.uniform(-1.2, 1.2)) * 0.985
            curr_cx = base_center_x + center_drift_x
            curr_cy = base_center_y + center_drift_y

            # 2. Dynamic oval breathing (morphs size and tilt continuously)
            rx = base_rx + math.sin(elapsed * 2.1) * 35 + math.sin(elapsed * 0.7) * 20
            ry = base_ry + math.cos(elapsed * 2.8) * 18 + math.cos(elapsed * 0.5) * 10
            tilt = base_tilt + math.radians(math.sin(elapsed * 1.5) * 8)

            # 3. Biomechanical 2/3-power-law speed variation
            curvature_factor = 1.0 - 0.22 * math.cos(2 * angle)
            angle += (base_speed * curvature_factor) * dt

            # 4. Geometry calculation and rotation
            raw_x = rx * math.cos(angle)
            raw_y = ry * math.sin(angle)
            rot_x = raw_x * math.cos(tilt) - raw_y * math.sin(tilt)
            rot_y = raw_x * math.sin(tilt) + raw_y * math.cos(tilt)

            # 5. Biological Brownian motor tremor
            tremor_x = (tremor_x * 0.7) + random.uniform(-2.5, 2.5)
            tremor_y = (tremor_y * 0.7) + random.uniform(-2.5, 2.5)

            dest_x = int(round(curr_cx + rot_x + tremor_x))
            dest_y = int(round(curr_cy + rot_y + tremor_y))

            dest_x = max(10, min(screen_w - 10, dest_x))
            dest_y = max(10, min(screen_h - 10, dest_y))

            pyautogui.moveTo(dest_x, dest_y, duration=0)
            time.sleep(random.uniform(0.002, 0.006))
    finally:
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
        circles (bool): If True, idly swirls mouse in natural, non-repeating trackpad ovals while waiting.
        max_circle_time (float): Maximum seconds to swirl before dropping to static idle.
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
    clicked_interrupters = set()
    
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
                        
                        wind_mouse(current_x, current_y, hx, hy)
                        
                        if int_click_count > 0:
                            sleep(random.uniform(0.1, 0.3))
                    else:
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
                    
                    break

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
                
                wind_mouse(current_x, current_y, hxmod, hymod)
                
                if click_count > 0:
                    sleep(random.uniform(0.1, 0.3))
            else:
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
                    # Swirl in responsive 0.3s bursts so image detection stays fast
                    burst = min(0.3, max_circle_time - elapsed_time)
                    organic_trackpad_swirl(duration=burst)
                else:
                    # Max circle time exceeded; drop to a fully idle state
                    sleep(0.25)
            else:
                sleep(random.uniform(0.8, 1.2) if humanize else 1)

if __name__ == "__main__":
    print('Script Started')
    set_autopath(r'D:\optimisewait\optimisewait')
    optimiseWait('image')