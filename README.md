# OptimiseWait

A Python utility function for automated image detection and clicking using PyAutoGUI.

## Installation

```bash
# Install from PyPI
pip install optimisewait

# Or install from source
git clone https://github.com/AMAMazing/optimisewait.git
cd optimisewait
pip install .
```

## Quick Start

```python
from optimisewait import optimiseWait, set_autopath, set_altpath

# Set default path for all subsequent optimiseWait calls
set_autopath(r'D:\Images')

# Optional: Set an alternative path for fallback image search
set_altpath(r'D:\Images\Alt')

# Basic usage - wait for image and click
result = optimiseWait('button')  # Looks for button.png in D:\Images, then D:\Images\Alt if not found
# Returns {'found': True, 'image': 'button'} if found
```

## Usage Examples

```python
# Override default path for specific call
result = optimiseWait('button', autopath=r'D:\OtherImages')

# Specify both main and alternative paths for specific call
result = optimiseWait('button', autopath=r'D:\Images', altpath=r'D:\Images\Alt')

# Don't wait for image (check if image exists)
result = optimiseWait('button', dontwait=True)
# Returns {'found': False, 'image': None} if not found

# Multiple click options
optimiseWait('button', clicks=2)  # Double click
optimiseWait('button', clicks=3)  # Triple click
optimiseWait('button', clicks=0)  # No click, just wait for image

# Multiple images to search for
result = optimiseWait(['button', 'alt1', 'alt2'])  # Will click first image found
# Returns {'found': True, 'image': 'alt1'} if alt1 was found first

# Different clicks per image
optimiseWait(['button', 'alt1', 'alt2'], clicks=[2, 3, 1])  # Different clicks per image

# Offset clicking - single value
optimiseWait('button', xoff=10, yoff=20)  # Click 10px right, 20px down from center

# Offset clicking - multiple values for different images
optimiseWait(['button1', 'button2'], xoff=[10, 20], yoff=[5, 15])  # Different offsets per image
optimiseWait(['button1', 'button2', 'button3'], xoff=[10, 20])  # Remaining offsets default to 0
```

## Functions

### set_autopath(path)
Sets the default path for image files that will be used by all subsequent optimiseWait calls.
- `path`: String. Directory path where image files are located.

### set_altpath(path)
Sets the default alternative path for image files. If an image is not found in the main path, it will be searched for in this alternative path.
- `path`: String. Directory path for alternative image files location.

### optimiseWait(filename, ...)
Main function for image detection and clicking.

## Parameters

- `filename`: String or list of strings. Image filename(s) without .png extension
- `dontwait`: Boolean (default False). If True, don't wait for image to appear
- `specreg`: Tuple (default None). Specific region to search in (x, y, width, height)
- `clicks`: Integer or list (default 1). Number of clicks per image (0 = no click, 1 = single, 2 = double, 3 = triple)
- `xoff`: Integer or list (default 0). X offset from center for clicking. Can be different for each image
- `yoff`: Integer or list (default 0). Y offset from center for clicking. Can be different for each image
- `autopath`: String (optional). Directory containing image files. If not provided, uses path set by set_autopath()
- `altpath`: String (optional). Alternative directory for image files. If an image is not found in autopath, it will be searched for here. If not provided, uses path set by set_altpath()

## Return Value

Returns a dictionary with:
- `found`: Boolean indicating if any image was found
- `image`: String name of the found image, or None if no image was found

## Notes

- All image files should be PNG format
- Images are searched with 90% confidence level
- Function will wait indefinitely until image is found (unless dontwait=True)
- When using multiple images, it will try each in order until one is found
- Images are first searched in the main path (autopath), then in the alternative path (altpath) if not found
- If clicks is a single integer, it applies to the first found image (others default to 1 click)
- If clicks is a list shorter than filename list, remaining images default to 1 click
- If xoff/yoff are single integers, same offset applies to all images
- If xoff/yoff are lists shorter than filename list, remaining offsets default to 0
- Click offsets are calculated from the center of the found image
- Default image paths can be set once using set_autopath() and set_altpath() and reused across multiple calls

## Dependencies

- PyAutoGUI >= 0.9.53

## License

MIT License
