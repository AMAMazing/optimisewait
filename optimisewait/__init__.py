import pyautogui
import time
from time import sleep
import os
import random
import math
import cv2
import numpy as np
from PIL import Image

# --- Global Default Paths ---
_default_autopath = r'C:\\'
_default_altpath = None

# --- Multi-Scale Caching & State ---
_template_cache = {}          # Caches loaded/resized templates in RAM
_last_matched_scale = 1.0     # Remembers the working scale of the current monitor

# Priority DPI/Resolution ratios (100%<->125%, 100%<->150%, 125%<->150%, 1080p<->1440p, 200%, etc.)
_PRIORITY_SCALES = [
    1.0, 1.25, 0.80, 1.50, 0.6667, 1.20, 0.8333,
    1.3333, 0.75, 1.75, 0.5714, 2.0, 0.50
]
# Fallback sweep from 0.55x to 1.95x in 5% increments for custom/unusual scaling
_FALLBACK_SCALES = [
    round(s, 2) for s in np.arange(0.55, 2.00, 0.05)
    if not any(abs(s - p) < 0.02 for p in _PRIORITY_SCALES)
]


def set_autopath(path):
    """Sets the global default primary path for image assets."""
    global _default_autopath
    _default_autopath = path


def set_altpath(path):
    """Sets the global default alternative/fallback path for image assets."""
    global _default_altpath
    _default_altpath = path


def _get_cached_template(image_path, scale=1.0, grayscale=False):
    """
    Loads and resizes a template image, caching it in RAM so disk I/O
    and resizing only happen once per image/scale combination.
    """
    try:
        mtime = os.path.getmtime(image_path)
    except OSError:
        return None

    base_key = (image_path, mtime)
    if base_key not in _template_cache:
        try:
            with Image.open(image_path) as pil_img:
                rgb = np.array(pil_img.convert('RGB'))
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                _template_cache[base_key] = {'bgr': bgr, 'gray': gray, 'scaled': {}}
        except Exception:
            return None

    entry = _template_cache[base_key]
    scale_key = (round(scale, 4), grayscale)

    if scale_key not in entry['scaled']:
        src = entry['gray'] if grayscale else entry['bgr']
        if abs(scale - 1.0) < 1e-4:
            entry['scaled'][scale_key] = src
        else:
            h, w = src.shape[:2]
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
            entry['scaled'][scale_key] = cv2.resize(src, (new_w, new_h), interpolation=interp)

    return entry['scaled'][scale_key]


def _capture_screen(specreg=None):
    """
    Captures the screen (or specific region) once and returns both BGR and Grayscale arrays,
    plus the (offset_x, offset_y) of the region.
    """
    if specreg is not None:
        screen_w, screen_h = pyautogui.size()
        left = max(0, min(screen_w - 1, int(specreg[0])))
        top = max(0, min(screen_h - 1, int(specreg[1])))
        width = max(1, min(screen_w - left, int(specreg[2])))
        height = max(1, min(screen_h - top, int(specreg[3])))
        pil_shot = pyautogui.screenshot(region=(left, top, width, height))
        offset_x, offset_y = left, top
    else:
        pil_shot = pyautogui.screenshot()
        offset_x, offset_y = 0, 0

    rgb = np.array(pil_shot)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return bgr, gray, offset_x, offset_y


def locate_multiscale(image_path, screen_data=None, specreg=None, confidence=0.84, multiscale=True, grayscale=False):
    """
    Finds an image on screen across multiple DPI/resolution scales.
    Returns (location, matched_scale, matched_confidence) or (None, None, 0.0).
    """
    global _last_matched_scale

    if not os.path.exists(image_path):
        return None, None, 0.0

    if screen_data is None:
        screen_bgr, screen_gray, offset_x, offset_y = _capture_screen(specreg)
    else:
        screen_bgr, screen_gray, offset_x, offset_y = screen_data

    screen_img = screen_gray if grayscale else screen_bgr
    sh, sw = screen_img.shape[:2]

    if not multiscale:
        scales_to_test = [1.0]
    else:
        # Check the last known working scale and 1.0x first
        fast_scales = []
        for s in [_last_matched_scale, 1.0]:
            if s not in fast_scales:
                fast_scales.append(s)

        remaining_priority = [s for s in _PRIORITY_SCALES if s not in fast_scales]
        scales_to_test = fast_scales + remaining_priority + _FALLBACK_SCALES

    best_score = -1.0
    best_match = None
    best_scale = None

    for idx, scale in enumerate(scales_to_test):
        tmpl = _get_cached_template(image_path, scale=scale, grayscale=grayscale)
        if tmpl is None:
            continue

        th, tw = tmpl.shape[:2]
        # Skip if scaled template is too small or larger than the screenshot region
        if th < 4 or tw < 4 or th > sh or tw > sw:
            continue

        res = cv2.matchTemplate(screen_img, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        # Require slightly higher confidence at native 1.0x, slightly more forgiving when interpolated
        effective_thresh = confidence if abs(scale - 1.0) > 1e-3 else max(confidence, 0.88)

        if max_val >= effective_thresh and max_val > best_score:
            best_score = max_val
            best_scale = scale
            best_match = (max_loc[0], max_loc[1], tw, th)

            # Fast-path early exit: if our known working scale hits a strong match, return immediately
            if max_val >= max(effective_thresh + 0.05, 0.90):
                break

        # If we found a valid match within the priority DPI scales, no need to check fallback scales
        if best_match is not None and idx == len(fast_scales) + len(remaining_priority) - 1:
            break

    if best_match is not None:
        _last_matched_scale = best_scale
        mx, my, tw, th = best_match
        left = offset_x + mx
        top = offset_y + my

        if specreg is None:
            loc = pyautogui.Point(int(round(left + tw / 2)), int(round(top + th / 2)))
        else:
            loc = pyautogui.Box(int(left), int(top), int(tw), int(th))

        return loc, best_scale, float(best_score)

    return None, None, 0.0


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
        pyautogui.moveTo(int(round(dest_x)), int(round(dest_y)))

    finally:
        pyautogui.PAUSE = original_pause


def humancircles(duration=5.0, start_x=None, start_y=None, base_speed=16.5):
    """
    Simulates human-like fast trackpad oval swirling with dynamic breathing,
    continuous center drift, biomechanical 2/3-power-law cadence, and Brownian motor tremor.
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

    # Offset center relative to starting position so cursor never jumps on start
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

            # 2. Dynamic oval breathing (non-repeating ovals)
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


# Backwards compatibility alias
organic_trackpad_swirl = humancircles


def optimiseWait(
    filename,
    dontwait=False,
    specreg=None,
    clicks=1,
    xoff=0,
    yoff=0,
    autopath=None,
    altpath=None,
    scrolltofind=None,
    clickdelay=0.1,
    interrupter=None,
    interrupterclicks=1,
    interrupter_once=True,
    humanize=False,
    circles=False,
    max_circle_time=5.0,
    confidence=0.84,
    multiscale=True,
    grayscale=False,
    scale_offsets=True
):
    """
    Waits for one of several possible images to appear on screen and optionally clicks it.
    Supports automatic multi-scale matching across different resolutions and Windows DPI scales.
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
        # Take ONE screenshot per loop pass for fast multi-scale matching
        screen_data = _capture_screen(specreg)

        # --- Check for Interrupter Images ---
        if interrupter_list is not None:
            for i, int_fname in enumerate(interrupter_list):
                if interrupter_once and i in clicked_interrupters:
                    continue

                int_findloc = None
                int_scale = 1.0

                # Try main path first
                main_path = os.path.join(autopath, f"{int_fname}.png")
                loc, matched_scale, _ = locate_multiscale(
                    main_path, screen_data=screen_data, specreg=specreg,
                    confidence=confidence, multiscale=multiscale, grayscale=grayscale
                )
                if loc is not None:
                    int_findloc = loc
                    int_scale = matched_scale

                # Try alt path if not found in main
                if int_findloc is None and altpath is not None:
                    alt_path = os.path.join(altpath, f"{int_fname}.png")
                    loc, matched_scale, _ = locate_multiscale(
                        alt_path, screen_data=screen_data, specreg=specreg,
                        confidence=confidence, multiscale=multiscale, grayscale=grayscale
                    )
                    if loc is not None:
                        int_findloc = loc
                        int_scale = matched_scale

                # If interrupter found, click it and refresh screenshot
                if int_findloc is not None:
                    if specreg is None:
                        x, y = int_findloc
                    else:
                        x = int_findloc.left + int_findloc.width / 2
                        y = int_findloc.top + int_findloc.height / 2

                    int_click_count = interrupterclicks_list[i]

                    if humanize:
                        jitter = max(2, int(round(4 * int_scale)))
                        hx = x + random.randint(-jitter, jitter)
                        hy = y + random.randint(-jitter, jitter)
                        current_x, current_y = pyautogui.position()

                        wind_mouse(current_x, current_y, hx, hy)

                        if int_click_count > 0:
                            sleep(random.uniform(0.1, 0.3))
                    else:
                        pyautogui.moveTo(int(round(x)), int(round(y)))

                    if int_click_count > 0:
                        for _ in range(int_click_count):
                            pyautogui.click()
                            if humanize:
                                sleep(max(0, clickdelay + random.uniform(-0.03, 0.08)))
                            else:
                                sleep(clickdelay)

                    if interrupter_once:
                        clicked_interrupters.add(i)

                    # Re-capture screen since clicking the interrupter likely changed the UI
                    screen_data = _capture_screen(specreg)
                    break

        # --- Check for Main Images ---
        first_found_image = None

        for i, fname in enumerate(filename):
            findloc = None
            found_scale = 1.0
            found_conf = 0.0

            main_path = os.path.join(autopath, f"{fname}.png")
            loc, matched_scale, matched_conf = locate_multiscale(
                main_path, screen_data=screen_data, specreg=specreg,
                confidence=confidence, multiscale=multiscale, grayscale=grayscale
            )
            if loc is not None:
                findloc = loc
                found_scale = matched_scale
                found_conf = matched_conf

            if findloc is None and altpath is not None:
                alt_path = os.path.join(altpath, f"{fname}.png")
                loc, matched_scale, matched_conf = locate_multiscale(
                    alt_path, screen_data=screen_data, specreg=specreg,
                    confidence=confidence, multiscale=multiscale, grayscale=grayscale
                )
                if loc is not None:
                    findloc = loc
                    found_scale = matched_scale
                    found_conf = matched_conf

            if findloc is not None:
                first_found_image = {
                    'index': i,
                    'filename': fname,
                    'location': findloc,
                    'scale': found_scale,
                    'confidence': found_conf
                }
                break

        # --- Action Phase ---
        if first_found_image:
            loc = first_found_image['location']
            found_index = first_found_image['index']
            matched_scale = first_found_image['scale']

            if specreg is None:
                x, y = loc
            else:
                x = loc.left + loc.width / 2
                y = loc.top + loc.height / 2

            # Scale xoff and yoff proportionally so offset clicks land accurately on scaled screens
            offset_mult = matched_scale if scale_offsets else 1.0
            xmod = x + (xoff[found_index] * offset_mult)
            ymod = y + (yoff[found_index] * offset_mult)

            click_count = clicks[found_index]

            if humanize:
                jitter = max(2, int(round(4 * matched_scale)))
                hxmod = xmod + random.randint(-jitter, jitter)
                hymod = ymod + random.randint(-jitter, jitter)
                current_x, current_y = pyautogui.position()

                wind_mouse(current_x, current_y, hxmod, hymod)

                if click_count > 0:
                    sleep(random.uniform(0.1, 0.3))
            else:
                pyautogui.moveTo(int(round(xmod)), int(round(ymod)))

            if click_count > 0:
                for _ in range(click_count):
                    pyautogui.click()
                    if humanize:
                        sleep(max(0, clickdelay + random.uniform(-0.03, 0.08)))
                    else:
                        sleep(clickdelay)

            return {
                'found': True,
                'image': first_found_image['filename'],
                'location': loc,
                'scale': matched_scale,
                'confidence': first_found_image['confidence']
            }

        # --- Loop Control & Idle Wait ---
        if dontwait:
            return {'found': False, 'image': None, 'location': None, 'scale': None, 'confidence': 0.0}
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
                    humancircles(duration=burst)
                else:
                    # Max circle time exceeded; drop to a fully idle state
                    sleep(0.25)
            else:
                sleep(random.uniform(0.8, 1.2) if humanize else 1)


if __name__ == "__main__":
    print('Script Started')
    set_autopath(r'D:\optimisewait\optimisewait')
    result = optimiseWait('image')
    print(f"Matched at scale: {result['scale']}x (Confidence: {result['confidence']:.2f})")