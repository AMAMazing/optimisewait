import pyautogui
import time
from time import sleep
import os
import random
import math
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
import numpy as np
from PIL import Image

# --- Global Default Paths ---
_default_autopath = os.getcwd()
_default_altpath = None

# --- Multi-Scale Caching, Smart Memory & Thread Safety ---
_template_cache = {}          # Caches loaded/resized templates in RAM
_image_scale_memory = {}      # Remembers the exact scale per image file
_recent_scales = [1.0]        # Remembers the last 4 active scales (e.g. OS scale + Chrome zoom scale)

_cache_lock = threading.Lock()
_memory_lock = threading.Lock()

# Persistent worker pool so threads aren't recreated on every scan pass
_MAX_WORKERS = min(16, max(4, (os.cpu_count() or 4) * 2))
_SCAN_EXECUTOR = ThreadPoolExecutor(max_workers=_MAX_WORKERS)

# Generate exact compound scales (OS DPI x Chrome Zoom presets) + uniform coarse coverage (0.40x to 2.50x)
_OS_SCALES = [1.0, 1.25, 0.80, 1.50, 0.6667, 1.75, 2.0, 0.50]


def _build_coarse_scales():
    """Builds a deduplicated list of compound OS x Chrome scales from 0.40x to 2.50x."""
    raw = []
    for os_s in _OS_SCALES:
        for cz in [1.0, 0.90, 1.10, 0.80, 1.25, 0.75, 1.50, 0.67, 1.75, 0.50, 2.0]:
            val = round(os_s * cz, 4)
            if 0.40 <= val <= 2.50:
                raw.append(val)

    for s in np.arange(0.40, 2.52, 0.04):
        raw.append(round(float(s), 4))

    deduped = []
    for s in raw:
        if not any(abs(s - existing) < 0.015 for existing in deduped):
            deduped.append(s)
    return deduped


_COARSE_SCALES = _build_coarse_scales()


def set_autopath(path):
    """Sets the global default primary path for image assets."""
    global _default_autopath
    _default_autopath = path


def set_altpath(path):
    """Sets the global default alternative/fallback path for image assets."""
    global _default_altpath
    _default_altpath = path


def _remember_scale(image_path, scale):
    """Thread-safely stores the matched scale for the specific image and updates recent scales."""
    global _recent_scales
    scale = round(float(scale), 4)
    with _memory_lock:
        _image_scale_memory[image_path] = scale
        _recent_scales = [s for s in _recent_scales if abs(s - scale) > 0.008]
        _recent_scales.insert(0, scale)
        if len(_recent_scales) > 4:
            _recent_scales.pop()


def _get_fast_scales(image_path):
    """Thread-safely retrieves the known scale for an image plus recent active scales."""
    with _memory_lock:
        fast_scales = []
        if image_path in _image_scale_memory:
            fast_scales.append(_image_scale_memory[image_path])
        for s in _recent_scales:
            if all(abs(s - existing) > 0.008 for existing in fast_scales):
                fast_scales.append(s)
        return fast_scales


def _get_cached_template(image_path, scale=1.0, grayscale=False):
    """
    Thread-safely loads and resizes a template image, caching it in RAM.
    Uses INTER_AREA for shrinking (zoomed out) and INTER_LANCZOS4 for enlarging (zoomed in).
    """
    try:
        mtime = os.path.getmtime(image_path)
    except OSError:
        return None

    base_key = (image_path, mtime)
    scale_key = (round(scale, 4), grayscale)

    with _cache_lock:
        entry = _template_cache.get(base_key)
        if entry is not None and scale_key in entry['scaled']:
            return entry['scaled'][scale_key]

    if entry is None:
        try:
            with Image.open(image_path) as pil_img:
                rgb = np.array(pil_img.convert('RGB'))
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        except Exception:
            return None

        with _cache_lock:
            entry = _template_cache.setdefault(base_key, {'bgr': bgr, 'gray': gray, 'scaled': {}})
            if scale_key in entry['scaled']:
                return entry['scaled'][scale_key]

    src = entry['gray'] if grayscale else entry['bgr']
    if abs(scale - 1.0) < 1e-4:
        resized = src
    else:
        h, w = src.shape[:2]
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LANCZOS4
        resized = cv2.resize(src, (new_w, new_h), interpolation=interp)

    with _cache_lock:
        if len(entry['scaled']) > 90:
            entry['scaled'].clear()
        entry['scaled'][scale_key] = resized
        return resized


def _capture_screen(specreg=None):
    """
    Captures the screen (or specific region) once and precomputes BGR, Grayscale,
    and a 0.5x Half-Resolution Pyramid Grayscale image for ultra-fast coarse sweeps.
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
    # 0.5x pyramid image makes broad multi-scale sweeps ~8x faster
    gray_half = cv2.resize(gray, (max(1, gray.shape[1] // 2), max(1, gray.shape[0] // 2)), interpolation=cv2.INTER_AREA)
    return bgr, gray, gray_half, offset_x, offset_y


def _effective_threshold(base_confidence, scale):
    """Adjusts confidence threshold slightly for extreme zoom-in / zoom-out interpolation."""
    if abs(scale - 1.0) < 1e-3:
        return max(base_confidence, 0.88)
    elif scale < 0.70 or scale > 1.65:
        return max(0.78, base_confidence - 0.03)
    return base_confidence


def _verify_edge_structure(screen_gray, image_path, scale, box):
    """
    Sobel Edge-Structure Verification:
    Rescues borderline matches (e.g. when monitor gamma, Night Light, or font smoothing differs)
    by verifying that the geometric outlines/text edges inside the candidate box match the template.
    """
    mx, my, tw, th = box
    sh, sw = screen_gray.shape[:2]
    if my < 0 or mx < 0 or my + th > sh or mx + tw > sw or tw < 8 or th < 8:
        return 0.0

    tmpl_gray = _get_cached_template(image_path, scale=scale, grayscale=True)
    if tmpl_gray is None or tmpl_gray.shape[:2] != (th, tw):
        return 0.0

    patch_gray = screen_gray[my:my + th, mx:mx + tw]

    gx_t = cv2.Sobel(tmpl_gray, cv2.CV_32F, 1, 0, ksize=3)
    gy_t = cv2.Sobel(tmpl_gray, cv2.CV_32F, 0, 1, ksize=3)
    mag_t = cv2.magnitude(gx_t, gy_t)

    gx_p = cv2.Sobel(patch_gray, cv2.CV_32F, 1, 0, ksize=3)
    gy_p = cv2.Sobel(patch_gray, cv2.CV_32F, 0, 1, ksize=3)
    mag_p = cv2.magnitude(gx_p, gy_p)

    if np.std(mag_t) < 1e-3 or np.std(mag_p) < 1e-3:
        return 0.0

    res = cv2.matchTemplate(mag_p, mag_t, cv2.TM_CCOEFF_NORMED)
    return float(res[0, 0])


def _match_single_scale(screen_img, image_path, scale, grayscale):
    """Runs OpenCV template matching for a single scale and returns (score, (x, y, w, h))."""
    sh, sw = screen_img.shape[:2]
    tmpl = _get_cached_template(image_path, scale=scale, grayscale=grayscale)
    if tmpl is None:
        return -1.0, None

    th, tw = tmpl.shape[:2]
    if th < 4 or tw < 4 or th > sh or tw > sw:
        return -1.0, None

    # Reject completely flat/blank templates to prevent false positives
    if np.std(tmpl) < 1.5:
        return -1.0, None

    res = cv2.matchTemplate(screen_img, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if math.isnan(max_val) or math.isinf(max_val):
        return -1.0, None
    return float(max_val), (max_loc[0], max_loc[1], tw, th)


def _format_location(offset_x, offset_y, box, specreg):
    """Formats the matched bounding box into a Point or Box while preserving center accuracy."""
    mx, my, tw, th = box
    left = offset_x + mx
    top = offset_y + my
    if specreg is None:
        return pyautogui.Point(int(round(left + tw / 2.0)), int(round(top + th / 2.0)))
    return pyautogui.Box(int(left), int(top), int(tw), int(th))


def locate_multiscale(
    image_path,
    screen_data=None,
    specreg=None,
    confidence=0.84,
    multiscale=True,
    grayscale=False,
    fast_only=False,
    cancel_event=None
):
    """
    High-Speed Pyramid + ROI Multi-Scale Matcher with Sobel Edge Rescue.
    Supports `cancel_event` so parallel scans abort immediately when another thread finds a match.
    Returns (location, matched_scale, matched_confidence, matched_box).
    """
    if cancel_event is not None and cancel_event.is_set():
        return None, None, 0.0, None

    if not os.path.exists(image_path):
        return None, None, 0.0, None

    if screen_data is None:
        screen_bgr, screen_gray, screen_gray_half, offset_x, offset_y = _capture_screen(specreg)
    else:
        screen_bgr, screen_gray, screen_gray_half, offset_x, offset_y = screen_data

    target_screen = screen_gray if grayscale else screen_bgr
    sh, sw = target_screen.shape[:2]

    if not multiscale:
        score, box = _match_single_scale(target_screen, image_path, 1.0, grayscale)
        thresh = _effective_threshold(confidence, 1.0)
        if box is not None and score >= thresh:
            return _format_location(offset_x, offset_y, box, specreg), 1.0, score, box
        return None, None, 0.0, None

    # --- STAGE 1: Fast-Path (Per-Image Memory + Recent Active Scales) ---
    fast_scales = _get_fast_scales(image_path)

    best_score = -1.0
    best_match = None
    best_scale = None

    for s in fast_scales:
        if cancel_event is not None and cancel_event.is_set():
            return None, None, 0.0, None

        score, box = _match_single_scale(target_screen, image_path, s, grayscale)
        thresh = _effective_threshold(confidence, s)
        if box is not None and score >= thresh and score > best_score:
            best_score, best_match, best_scale = score, box, s
            if score >= max(thresh + 0.04, 0.90):
                break

    if best_match is not None:
        # Refine +-1% inside a local ROI around the match for pinpoint box dimensions
        if best_score < 0.94:
            mx, my, tw, th = best_match
            pad = max(tw, th, 48)
            rx1, ry1 = max(0, mx - pad), max(0, my - pad)
            rx2, ry2 = min(sw, mx + tw + pad), min(sh, my + th + pad)
            roi_screen = target_screen[ry1:ry2, rx1:rx2]

            for micro_s in (round(best_scale - 0.01, 4), round(best_scale + 0.01, 4)):
                if 0.40 <= micro_s <= 2.50:
                    m_score, m_box = _match_single_scale(roi_screen, image_path, micro_s, grayscale)
                    if m_box is not None and m_score > best_score:
                        best_score = m_score
                        best_scale = micro_s
                        best_match = (rx1 + m_box[0], ry1 + m_box[1], m_box[2], m_box[3])

        _remember_scale(image_path, best_scale)
        loc = _format_location(offset_x, offset_y, best_match, specreg)
        return loc, best_scale, best_score, best_match

    if fast_only or (cancel_event is not None and cancel_event.is_set()):
        return None, None, 0.0, None

    # --- STAGE 2: Ultra-Fast 0.5x Pyramid Coarse Sweep (0.40x to 2.50x) ---
    base_tmpl = _get_cached_template(image_path, scale=1.0, grayscale=True)
    if base_tmpl is None:
        return None, None, 0.0, None
    base_h, base_w = base_tmpl.shape[:2]

    coarse_candidates = []
    for s in _COARSE_SCALES:
        if cancel_event is not None and cancel_event.is_set():
            return None, None, 0.0, None

        if any(abs(s - fs) < 0.008 for fs in fast_scales):
            continue

        # Use 0.5x pyramid when the scaled template is large enough (>= 24px), otherwise full-res
        if (base_w * s >= 24) and (base_h * s >= 24) and screen_gray_half.shape[0] >= 20:
            g_score, g_box = _match_single_scale(screen_gray_half, image_path, s * 0.5, grayscale=True)
            if g_box is not None and g_score > 0.0:
                coarse_candidates.append((g_score, s, g_box[0] * 2, g_box[1] * 2))
        else:
            g_score, g_box = _match_single_scale(screen_gray, image_path, s, grayscale=True)
            if g_box is not None and g_score > 0.0:
                coarse_candidates.append((g_score, s, g_box[0], g_box[1]))

    if not coarse_candidates:
        return None, None, 0.0, None

    coarse_candidates.sort(key=lambda x: x[0], reverse=True)
    top_peaks = coarse_candidates[:2]

    if top_peaks[0][0] < (confidence - 0.18):
        return None, None, 0.0, None

    # --- STAGE 3: ROI-Cropped 1% Micro-Sweep + Sobel Edge Rescue ---
    borderline_candidate = None
    tested_fine = set()

    for _, peak_s, px, py in top_peaks:
        if cancel_event is not None and cancel_event.is_set():
            return None, None, 0.0, None

        est_w, est_h = int(base_w * peak_s), int(base_h * peak_s)
        pad = max(est_w, est_h, 64)
        rx1, ry1 = max(0, px - pad), max(0, py - pad)
        rx2, ry2 = min(sw, px + est_w + pad), min(sh, py + est_h + pad)
        roi_screen = target_screen[ry1:ry2, rx1:rx2]

        for delta in (0.0, -0.01, 0.01, -0.02, 0.02, -0.03, 0.03):
            if cancel_event is not None and cancel_event.is_set():
                return None, None, 0.0, None

            fine_s = round(peak_s + delta, 4)
            if not (0.40 <= fine_s <= 2.50) or fine_s in tested_fine:
                continue
            tested_fine.add(fine_s)

            score, local_box = _match_single_scale(roi_screen, image_path, fine_s, grayscale)
            if local_box is None:
                score, global_box = _match_single_scale(target_screen, image_path, fine_s, grayscale)
            else:
                global_box = (rx1 + local_box[0], ry1 + local_box[1], local_box[2], local_box[3])

            thresh = _effective_threshold(confidence, fine_s)
            if global_box is not None:
                if score >= thresh and score > best_score:
                    best_score = score
                    best_match = global_box
                    best_scale = fine_s
                elif score >= (thresh - 0.06) and (borderline_candidate is None or score > borderline_candidate[0]):
                    borderline_candidate = (score, fine_s, global_box, thresh)

    # Sobel Edge Rescue: if color confidence was borderline (within 6% of threshold due to display differences),
    # verify whether the geometric edges/text outlines match strongly.
    if best_match is None and borderline_candidate is not None:
        if cancel_event is None or not cancel_event.is_set():
            b_score, b_scale, b_box, b_thresh = borderline_candidate
            edge_score = _verify_edge_structure(screen_gray, image_path, b_scale, b_box)
            if edge_score >= 0.72:
                best_score = b_score
                best_scale = b_scale
                best_match = b_box

    if best_match is not None:
        _remember_scale(image_path, best_scale)
        loc = _format_location(offset_x, offset_y, best_match, specreg)
        return loc, best_scale, best_score, best_match

    return None, None, 0.0, None


def _scan_single_candidate(
    index,
    fname,
    autopath,
    altpath,
    screen_data,
    specreg,
    confidence,
    multiscale,
    grayscale,
    cancel_event
):
    """Worker function that scans a single image name across autopath/altpath."""
    for folder in (autopath, altpath):
        if folder is None:
            continue
        if cancel_event is not None and cancel_event.is_set():
            return None

        cand_path = os.path.join(folder, f"{fname}.png")
        if not os.path.exists(cand_path):
            continue

        loc, matched_scale, matched_conf, m_box = locate_multiscale(
            cand_path,
            screen_data=screen_data,
            specreg=specreg,
            confidence=confidence,
            multiscale=multiscale,
            grayscale=grayscale,
            cancel_event=cancel_event
        )
        if loc is not None:
            if cancel_event is not None:
                cancel_event.set()
            return {
                'index': index,
                'filename': fname,
                'location': loc,
                'scale': matched_scale,
                'confidence': matched_conf,
                'box': m_box
            }
    return None


def _scan_candidates_simultaneously(
    candidates,
    autopath,
    altpath,
    screen_data,
    specreg,
    confidence,
    multiscale,
    grayscale
):
    """
    Scans all candidate (index, filename) pairs simultaneously across worker threads.
    As soon as a match is found, cancels remaining in-flight scans and returns the winner.
    """
    if not candidates:
        return None

    # Fast direct call when there is only 1 image to check (avoids thread dispatch overhead)
    if len(candidates) == 1:
        idx, fname = candidates[0]
        return _scan_single_candidate(
            idx, fname, autopath, altpath, screen_data, specreg,
            confidence, multiscale, grayscale, cancel_event=None
        )

    cancel_event = threading.Event()
    futures = [
        _SCAN_EXECUTOR.submit(
            _scan_single_candidate,
            idx,
            fname,
            autopath,
            altpath,
            screen_data,
            specreg,
            confidence,
            multiscale,
            grayscale,
            cancel_event
        )
        for idx, fname in candidates
    ]

    matches = []
    for fut in as_completed(futures):
        res = fut.result()
        if res is not None:
            matches.append(res)

    if not matches:
        return None

    # If two threads matched at the exact same millisecond, prefer the earlier item in the list
    matches.sort(key=lambda m: m['index'])
    return matches[0]


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

            if random.randint(1, 100) < 50:
                wind_x = wind_x / math.sqrt(3) + (random.random() * (wind * 2 + 1) - wind) / math.sqrt(5)
                wind_y = wind_y / math.sqrt(3) + (random.random() * (wind * 2 + 1) - wind) / math.sqrt(5)

            grav_x = (dest_x - current_x) * (gravity / max(dist, 1))
            grav_y = (dest_y - current_y) * (gravity / max(dist, 1))

            velo_x += grav_x + wind_x
            velo_y += grav_y + wind_y

            velo_mag = math.hypot(velo_x, velo_y)
            if velo_mag > max_step:
                random_step = (max_step / 2) + random.random() * (max_step / 2)
                velo_x = (velo_x / velo_mag) * random_step
                velo_y = (velo_y / velo_mag) * random_step

            old_x, old_y = current_x, current_y
            current_x += velo_x
            current_y += velo_y

            new_px, new_py = int(round(current_x)), int(round(current_y))

            if new_px != int(round(old_x)) or new_py != int(round(old_y)):
                pyautogui.moveTo(new_px, new_py)
                sleep(random.uniform(min_wait, max_wait))

            if dist < target_area:
                wind_x, wind_y = 0, 0
                max_step = max_step * 0.6

        pyautogui.moveTo(int(round(dest_x)), int(round(dest_y)))

    finally:
        pyautogui.PAUSE = original_pause


def humancircles(duration=5.0, start_x=None, start_y=None, base_speed=16.5):
    """
    Simulates human-like fast trackpad oval swirling with dynamic breathing,
    continuous center drift, biomechanical 2/3-power-law cadence, and Brownian motor tremor.
    """
    if duration <= 0:
        return

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
    base_tilt = math.radians(-15)

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
    start_time = time.perf_counter()
    last_time = start_time

    try:
        while True:
            now = time.perf_counter()
            elapsed = now - start_time
            if elapsed >= duration:
                break

            dt = now - last_time
            last_time = now

            center_drift_x = (center_drift_x + random.uniform(-1.8, 1.8)) * 0.985
            center_drift_y = (center_drift_y + random.uniform(-1.2, 1.2)) * 0.985
            curr_cx = base_center_x + center_drift_x
            curr_cy = base_center_y + center_drift_y

            rx = base_rx + math.sin(elapsed * 2.1) * 35 + math.sin(elapsed * 0.7) * 20
            ry = base_ry + math.cos(elapsed * 2.8) * 18 + math.cos(elapsed * 0.5) * 10
            tilt = base_tilt + math.radians(math.sin(elapsed * 1.5) * 8)

            curvature_factor = 1.0 - 0.22 * math.cos(2 * angle)
            angle += (base_speed * curvature_factor) * dt

            raw_x = rx * math.cos(angle)
            raw_y = ry * math.sin(angle)
            rot_x = raw_x * math.cos(tilt) - raw_y * math.sin(tilt)
            rot_y = raw_x * math.sin(tilt) + raw_y * math.cos(tilt)

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


def _safe_jitter(scale, box):
    """
    Calculates humanize click jitter that scales with the display but never exceeds
    25% of the matched button's width/height, guaranteeing every click lands inside the target.
    """
    base_j = max(1, int(round(4 * scale)))
    if box is None:
        return base_j, base_j
    _, _, tw, th = box
    jx = max(1, min(base_j, tw // 4))
    jy = max(1, min(base_j, th // 4))
    return jx, jy


def _wait_until(deadline):
    """
    Waits only for the remaining time until `deadline` (using time.perf_counter()).
    If `deadline` has already passed because image scanning took longer, returns immediately.
    """
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        time.sleep(min(0.015, remaining))


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
    scale_offsets=True,
    poll_interval=1.0
):
    """
    Waits for one of several possible images to appear on screen and optionally clicks it.
    Scans all candidate images simultaneously in parallel threads against each captured frame.
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
        circle_start_time = time.perf_counter()

    main_candidates = list(enumerate(filename))

    # --- Main Loop ---
    while True:
        loop_start = time.perf_counter()

        screen_data = _capture_screen(specreg)
        _, _, _, offset_x, offset_y = screen_data

        # --- Check for Interrupter Images Simultaneously ---
        if interrupter_list is not None:
            active_interrupters = [
                (i, int_fname)
                for i, int_fname in enumerate(interrupter_list)
                if not (interrupter_once and i in clicked_interrupters)
            ]

            int_match = _scan_candidates_simultaneously(
                active_interrupters,
                autopath,
                altpath,
                screen_data,
                specreg,
                confidence,
                multiscale,
                grayscale
            )

            if int_match is not None:
                i = int_match['index']
                int_findloc = int_match['location']
                int_scale = int_match['scale']
                int_box = int_match['box']

                if int_box is not None:
                    x = offset_x + int_box[0] + (int_box[2] / 2.0)
                    y = offset_y + int_box[1] + (int_box[3] / 2.0)
                elif specreg is None:
                    x, y = int_findloc
                else:
                    x = int_findloc.left + int_findloc.width / 2.0
                    y = int_findloc.top + int_findloc.height / 2.0

                int_click_count = interrupterclicks_list[i]

                if humanize:
                    jx, jy = _safe_jitter(int_scale, int_box)
                    hx = x + random.randint(-jx, jx)
                    hy = y + random.randint(-jy, jy)
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

                screen_data = _capture_screen(specreg)
                _, _, _, offset_x, offset_y = screen_data

        # --- Check All Main Images Simultaneously ---
        first_found_image = _scan_candidates_simultaneously(
            main_candidates,
            autopath,
            altpath,
            screen_data,
            specreg,
            confidence,
            multiscale,
            grayscale
        )

        # --- Action Phase (Immediate execution on match, ignores any remaining cycle wait) ---
        if first_found_image:
            loc = first_found_image['location']
            found_index = first_found_image['index']
            matched_scale = first_found_image['scale']
            m_box = first_found_image['box']

            if m_box is not None:
                x = offset_x + m_box[0] + (m_box[2] / 2.0)
                y = offset_y + m_box[1] + (m_box[3] / 2.0)
            elif specreg is None:
                x, y = loc
            else:
                x = loc.left + loc.width / 2.0
                y = loc.top + loc.height / 2.0

            offset_mult = matched_scale if scale_offsets else 1.0
            xmod = x + (xoff[found_index] * offset_mult)
            ymod = y + (yoff[found_index] * offset_mult)

            click_count = clicks[found_index]

            if humanize:
                jx, jy = _safe_jitter(matched_scale, m_box)
                hxmod = xmod + random.randint(-jx, jx)
                hymod = ymod + random.randint(-jy, jy)
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

        # --- Loop Control & Elapsed-Time Cycle Pacing (Skips wait if scan was already slower) ---
        if dontwait:
            return {'found': False, 'image': None, 'location': None, 'scale': None, 'confidence': 0.0}

        if scrolltofind in ('pageup', 'pagedown'):
            pyautogui.press(scrolltofind)
            scroll_target = random.uniform(0.4, 0.7) if humanize else 0.5
        else:
            scroll_target = 0.0

        if circles:
            circle_elapsed = time.perf_counter() - circle_start_time
            target_cycle = max(scroll_target, 0.3 if circle_elapsed < max_circle_time else 0.25)
            deadline = loop_start + target_cycle
            remaining = deadline - time.perf_counter()

            if remaining > 0:
                if circle_elapsed < max_circle_time:
                    humancircles(duration=min(remaining, max_circle_time - circle_elapsed))
                else:
                    _wait_until(deadline)
        else:
            base_wait = poll_interval * random.uniform(0.8, 1.2) if humanize else poll_interval
            target_cycle = max(scroll_target, base_wait)
            _wait_until(loop_start + target_cycle)


if __name__ == "__main__":
    set_autopath(r'D:\optimisewait\optimisewait')
    target_image = 'image'

    result = optimiseWait(target_image)
    print(f"Match found: {result['image']} at {result['scale']}x (Confidence: {result['confidence']:.2f})")