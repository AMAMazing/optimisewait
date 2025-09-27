# OptimiseWait

[![PyPI version](https://badge.fury.io/py/optimisewait.svg)](https://badge.fury.io/py/optimisewait)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python utility function for robust, automated image detection and clicking using PyAutoGUI.

## Installation

```bash
# Install latest stable version from PyPI
pip install optimisewait

# Install latest pre-release (beta) version from PyPI
pip install --pre optimisewait

# Or install from source (gets the latest code from the repository)
git clone https://github.com/AMAMazing/optimisewait.git
cd optimisewait
pip install .
```

## Quick Start

```python
from optimisewait import optimiseWait, set_autopath, set_altpath

# Set a global default path for all subsequent optimiseWait calls
set_autopath(r'D:\Images')

# Optional: Set a global fallback path if images aren't in the primary path
set_altpath(r'D:\Images\Alt')

# Basic usage: waits for 'button.png' and clicks it once.
# Searches in D:\Images first, then D:\Images\Alt.
result = optimiseWait('button')
# Returns {'found': True, 'image': 'button', 'location': Point(x=123, y=456)}
```

## Usage Examples

```python
# Override default path for a specific call
result = optimiseWait('button', autopath=r'D:\OtherImages')

# Don't wait; check once if the image exists and return immediately
result = optimiseWait('button', dontwait=True)
# Returns {'found': False, ...} if not found on the first check

# Multiple click options
optimiseWait('button', clicks=2)  # Double-clicks the button
optimiseWait('button', clicks=0)  # Finds the button but does not click

# Search for multiple images; acts on the first one found
result = optimiseWait(['save_button', 'confirm_button', 'ok_button'])

# Different clicks per image using a list
# Clicks 'save' 2x, 'confirm' 0x, and 'ok' defaults to 1x.
optimiseWait(['save', 'confirm', 'ok'], clicks=[2, 0])

# Offset clicking from the center of the image
optimiseWait('button', xoff=10, yoff=-5)  # Clicks 10px right and 5px up

# Different offsets for different images
optimiseWait(['user_icon', 'pass_icon'], xoff=[10, 20], yoff=[5, 15])

# Scroll to find an image (when dontwait=False)
# Scrolls pagedown repeatedly until 'image_far_down.png' is found
result = optimiseWait('image_far_down', scrolltofind='pagedown')
```

## Functions

### set_autopath(path)
Sets the global default path for image files. This path will be used by all subsequent `optimiseWait` calls unless overridden by the `autopath` parameter.
- `path` (str): Directory path where your primary image files are located.

### set_altpath(path)
Sets the global default alternative path. If an image isn't found in the main path, this fallback path will be searched.
- `path` (str): Directory path for alternative image files.

### optimiseWait(filename, ...)
The main function for finding an image on screen and interacting with it.

## Parameters

- `filename` (str or list[str]): Image filename(s) without the `.png` extension. If a list is provided, they are searched in order.
- `dontwait` (bool, default `False`): If `True`, the function checks only once and returns immediately. If `False`, it loops until an image is found.
- `specreg` (tuple, default `None`): A specific region to search in `(x, y, width, height)`. Searching a smaller region is much faster.
- `clicks` (int or list[int], default `1`): The number of times to click.
    - **int**: Applies that many clicks to *any* image found (e.g., `clicks=0` finds but doesn't click).
    - **list[int]**: Assigns clicks by index corresponding to `filename`. If the list is shorter, remaining images default to `1` click.
- `xoff` (int or list[int], default `0`): Horizontal pixel offset for the click, relative to the image's center.
- `yoff` (int or list[int], default `0`): Vertical pixel offset for the click, relative to the image's center.
- `autopath` (str, optional): Overrides the global default path for this specific call.
- `altpath` (str, optional): Overrides the global alternative path for this specific call.
- `scrolltofind` (str, optional): Can be `'pageup'` or `'pagedown'`. If an image isn't found, this key will be pressed before re-scanning. Only active when `dontwait=False`.

## Return Value

Returns a dictionary containing the search result:
- `found` (bool): `True` if an image was found, otherwise `False`.
- `image` (str | None): The filename of the found image, or `None`.
- `location` (Point | Box | None): The PyAutoGUI location object (`Point` or `Box`) of the found image.

## Notes

- All image files must be in `.png` format.
- Image searching uses a 90% confidence level by default.
- If `clicks` is a single integer, it applies to **any** image that is found.
- If `xoff`/`yoff` lists are shorter than the `filename` list, remaining images default to an offset of `0`.
- Click offsets are **always** calculated from the center of the found image, even when using `specreg`.

## Dependencies

- PyAutoGUI >= 0.9.53

## License

MIT License