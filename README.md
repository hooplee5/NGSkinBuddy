# NGSkinBuddy

A Maya companion panel for [NGSkinTools2](https://www.ngSkinTools.com) that keeps your most-used skinning controls one click away — layer info, influence display, vertex weight inspector, and operation shortcuts — without having to dig through the NGST2 interface.

---

## Requirements

- Maya 2022+  
- [NGSkinTools2](https://www.ngSkinTools.com)

---

## Installation

### One-time shelf setup

1. Clone or download this repo to any folder on your machine
2. In Maya's Script Editor **(Python tab)**, run:

```python
import runpy; runpy.run_path("C:/path/to/NGSkinBuddy/install_shelf.py")
```

> Replace `C:/path/to/NGSkinBuddy` with the actual folder you cloned into.  
> Forward slashes work on Windows — no need for backslashes.

3. An **NGBuddy** button appears on your current shelf. Done.

The installer also generates the shelf icon from your installed NGSkinTools2 icon automatically. Re-run it any time you move the repo to a different folder.

### After a git pull

Just **click the shelf button** — it reloads all modules from disk on every launch. No reinstall needed.

---

## Dev / quick launch

If you're making changes and want to iterate fast from the Script Editor, use this after the first run of the session:

```python
import main, importlib; importlib.reload(main); main.show_ui()
```

First run after Maya launches (path not in `sys.path` yet):

```python
import sys, importlib
NGBUDDY_ROOT = "C:/path/to/NGSkinBuddy"
if NGBUDDY_ROOT not in sys.path:
    sys.path.insert(0, NGBUDDY_ROOT)
import main; importlib.reload(main); main.show_ui()
```

---

## Tabs

### Build
Set up a mesh for skinning. Bind, initialize NGSkinTools2 layers, and apply a saved layer stack preset in one flow. Create and manage presets for different rig types so you get a consistent layer hierarchy every time.

### Copy & Paste
Transfer skin weights between meshes or between layers. Supports copying from a source mesh onto one or multiple targets, with options for influence mapping. Useful for pushing weights across LODs or mesh variations.

### Utils
Utility operations that complement the NGST2 workflow:
- **Clean rebind** — unbind, rebind to selected joints, then restore all NGST2 layer data automatically
- **Bake pose** — bake the current deformed pose back onto the mesh

### Skinning
Your active skinning workspace. Always reflects what is selected in NGSkinTools2:
- Current **layer** and **influence** display
- **Vertex weight inspector** — shows per-influence weights for the selected vertex
- **Lock / mute** controls for the active layer
- Quick-access buttons for common NGST2 operations without leaving the panel
