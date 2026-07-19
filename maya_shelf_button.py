# Manual fallback — use install_shelf.py instead (run once from Script Editor).
#
#     import runpy; runpy.run_path(r"C:\path\to\NGSkinBuddy\install_shelf.py")
#
# If that doesn't work, paste this into a Maya shelf button manually
# and update NGBUDDY_ROOT to match your path.
import sys, importlib
NGBUDDY_ROOT = r"C:\path\to\NGSkinBuddy"
if NGBUDDY_ROOT not in sys.path:
    sys.path.insert(0, NGBUDDY_ROOT)
import main; importlib.reload(main); main.show_ui()
