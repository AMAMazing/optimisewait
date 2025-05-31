from setuptools import setup, find_packages

setup(
    name="optimisewait",
    version="0.3.2b1",
    packages=find_packages(),
    install_requires=[
        "pyautogui>=0.9.53",
    ],
    author="Alex M",
    description="A Python utility for automated image detection and clicking",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/AMAMazing/optimisewait",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
