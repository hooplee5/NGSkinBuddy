# NGSkinBuddy

This is my companion panel for [NGSkinTools2](https://www.ngSkinTools.com) that keeps my most-used skinning controls in one clean UI, without having to dig through multiple layers of menus.

I built it to give myself a consistent starting point I can share across rigs, and to cut down on the biggest pain points during skinning — like model and rig changes. I also wanted quick access to a few NGSkinTools2 utilities without going deeper into their menus.

Here is a small video of how it looks in action



https://github.com/user-attachments/assets/fdb45d93-018b-41a4-a5d1-471942ea65d2



Read below for how to use the tool, and a detailed breakdown of what each tab does.

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
Set up a mesh for skinning:
- **Initialize** — initialize NGSkinTools2 layers on the selected mesh and apply a saved layer stack preset. Presets are organized in a tree (e.g. by rig type) so you get a consistent layer hierarchy every time. Save the current mesh's layers as a new preset, or delete existing ones, from the ⚙ menu.
- **Assign Initial Weights** — import a saved weight preset onto the mesh as an `IMPORTED_WEIGHTS` group without touching existing layers. Save the current mesh's weights as a new preset from the ⚙ menu.

### Copy & Paste
Transfer skin weights between meshes, or to/from a weight file:
- Source and target can each be a grabbed mesh selection or a `.json` weight file
- **Vertex Transfer Mode** — Closest Point, Vertex ID, or UV Space
- **Influence Mapping** — match by name, distance, and/or label
- **Apply mode** — add the transferred weights as new layers, or replace the target's current layers entirely

### Utils
Utility operations that complement the NGST2 workflow:
- **Weight Cleanup & Rebind** — saves NGST2 layer data, optionally deletes construction history, detaches and rebinds the skinCluster to the same influences, then restores the layer data automatically. Options to remove unused influences and force-normalize after rebind.
- **Influence Management** — per-layer Available/Active lists to lock or unlock influences on the current layer, plus a Source → Target joint weight transfer tool
- **Health Checks** — run scene-wide diagnostics: unskinned meshes, zero-weight vertices, weights not summing to 1, unused bound influences, joints with no influence, vertices over an influence-count limit, and meshes missing NGST2 layer data
- **Bake Pose** — redefine the bind pose to the current joint positions, saving and restoring NGST2 layer data automatically

### Skinning
Your active skinning workspace. Always reflects what is selected in NGSkinTools2:
- Current **layer** display with mute toggle and opacity control, and current **influence** display with a mask/joint paint-target swap
- **Joint hierarchy tree** — lock/unlock, flood to full or zero, and select-influenced-verts per influence, plus a mask row
- **Test Poses** — jump to bind pose, or save/recall up to three custom test poses to check deformation
- **Vertex weight inspector** — per-influence weights for selected vertices, viewable/editable in Layer mode or read-only in Final (post-deformation) mode, with an adjustable display threshold
