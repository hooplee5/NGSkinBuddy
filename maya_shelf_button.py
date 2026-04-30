# Paste this into a Maya shelf button (Python)
import sys, importlib

NGBUDDY_ROOT = r"C:\Users\KaiJu\Documents\GitHub\NGSkinBuddy"
if NGBUDDY_ROOT not in sys.path:
    sys.path.insert(0, NGBUDDY_ROOT)

import style.colors;      importlib.reload(style.colors)
import style.dimensions;  importlib.reload(style.dimensions)
import style.widgets;     importlib.reload(style.widgets)
import core.presets;      importlib.reload(core.presets)
import core.ng_api;       importlib.reload(core.ng_api)
import ui.build_tab;      importlib.reload(ui.build_tab)
import ui.main_window;    importlib.reload(ui.main_window)
import main;              importlib.reload(main)

main.show_ui()