import os
import pathlib
import sys

FPS = 25


def _get_output_dir() -> str:
    if getattr(sys, 'frozen', False):
        # Packaged (PyInstaller) — write to user's Documents for easy access
        return str(pathlib.Path.home() / "Documents" / "RibAnnotationApp" / "output")
    # Running from source — keep output/ next to the script
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


OUTPUT_DIR = _get_output_dir()

PITCH_LENGTH = 105.0
PITCH_WIDTH  = 68.0

# Trail: current frame + this many previous frames
TRAIL_STEPS = 26         # indices 0..25, 25 = current frame

HOME_COLOR = "#5B9BD5"   # blue
AWAY_COLOR = "#FF6B6B"   # red/salmon
BALL_COLOR = "#FFFFFF"   # white

# Player-click detection radius (metres in DFL coordinate system)
CLICK_THRESHOLD_M = 3.5

# Boundary drag detection (pixels)
BOUNDARY_THRESHOLD_PX = 10
