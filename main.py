# region [01] PATH SETUP
import sys
import importlib

NGBUDDY_ROOT = r"C:\Users\KaiJu\Documents\GitHub\NGSkinBuddy"
if NGBUDDY_ROOT not in sys.path:
    sys.path.insert(0, NGBUDDY_ROOT)
# endregion

# region [02] MODULE RELOADS
import style.colors;        importlib.reload(style.colors)
import style.dimensions;    importlib.reload(style.dimensions)
import style.widgets;       importlib.reload(style.widgets)
import core.presets;        importlib.reload(core.presets)
import core.ng_api;         importlib.reload(core.ng_api)
import ui.build_tab;        importlib.reload(ui.build_tab)
import ui.copy_paste_tab;   importlib.reload(ui.copy_paste_tab)
import ui.main_window;      importlib.reload(ui.main_window)
# endregion

# region [03] IMPORTS
from ui.main_window import MainWindow
# endregion

# region [04] ENTRY POINT
def show_ui():
    window = MainWindow()
    window.create()

if __name__ == "__main__":
    show_ui()
# endregion