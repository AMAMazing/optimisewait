# OptimiseWait

A Python utility function for automated image detection and clicking using PyAutoGUI.

## Installation

Requires PyAutoGUI:
```bash
pip install pyautogui
```

## Usage

```python
from optimisewait import optimiseWait

# Basic usage - wait for image and click
optimiseWait('button')  # Looks for button.png

# Don't wait for image (check if image exists)
optimiseWait('button', dontwait=True)

# Multiple click options
optimiseWait('button', clicks=2)  # Double click
optimiseWait('button', clicks=3)  # Triple click
optimiseWait('button', clicks=0)  # No click, just wait for image

# Offset clicking
optimiseWait('button', xoff=10, yoff=20)  # Click 10px right, 20px down from center

# Custom image path
optimiseWait('button', autopath=r'D:\Images')  # Look in D:\Images for button.png

# Multiple images to search for
optimiseWait(['button1', 'button2'])  # Will click first image found
optimiseWait('main_button', orfiles=['alt_button1', 'alt_button2'])  # Try main, then alternatives

# Different click counts for different images
optimiseWait('main_button', orfiles=['alt_button1', 'alt_button2'], orclicks=[2, 3])
```

## Parameters

- `filename`: String or list of strings. Image filename(s) without .png extension
- `dontwait`: Boolean (default False). If True, don't wait for image to appear
- `specreg`: Tuple (default None). Specific region to search in (x, y, width, height)
- `clicks`: Integer (default 1). Number of clicks (0 = no click, 1 = single, 2 = double, 3 = triple)
- `xoff`: Integer (default 0). X offset from center for clicking
- `yoff`: Integer (default 0). Y offset from center for clicking
- `autopath`: String (default 'D:\BobaDays\Auto'). Directory containing image files
- `orfiles`: String or list (default None). Alternative image(s) to search for
- `orclicks`: Integer or list (default None). Click counts for alternative images

## Notes

- All image files should be PNG format
- Images are searched with 90% confidence level
- Function will wait indefinitely until image is found (unless dontwait=True)
- When using multiple images (orfiles), it will try each in order until one is found
- Click offsets are calculated from the center of the found image
