"""
Run this once from Maya's Script Editor to add NGSkinBuddy to your shelf.

    import runpy; runpy.run_path("C:/path/to/NGSkinBuddy/install_shelf.py")

Re-run only if you move the repo folder — the path in the button needs updating then.
After a git pull, changes are picked up automatically on the next shelf button click.
"""
import os
import maya.cmds as cmds
import maya.mel as mel

NGBUDDY_ROOT = os.path.dirname(os.path.abspath(__file__))
BUTTON_LABEL = "NGBuddy"


def _make_icon():
    icon_path = os.path.join(NGBUDDY_ROOT, "icons", "ngbuddy.png")
    try:
        os.makedirs(os.path.join(NGBUDDY_ROOT, "icons"), exist_ok=True)
        try:
            from PySide6 import QtGui, QtCore
        except ImportError:
            from PySide2 import QtGui, QtCore

        # Resolve enums that moved between PySide2 and PySide6
        try:
            _AA           = QtGui.QPainter.RenderHint.Antialiasing
            _KeepAspect   = QtCore.Qt.AspectRatioMode.KeepAspectRatio
            _Smooth       = QtCore.Qt.TransformationMode.SmoothTransformation
            _AlignCenter  = int(QtCore.Qt.AlignmentFlag.AlignCenter)
        except AttributeError:
            _AA           = QtGui.QPainter.Antialiasing
            _KeepAspect   = QtCore.Qt.KeepAspectRatio
            _Smooth       = QtCore.Qt.SmoothTransformation
            _AlignCenter  = int(QtCore.Qt.AlignCenter)

        size = 32

        # Find the NGSkinTools2 shelf icon from its package
        base_img = None
        try:
            import ngSkinTools2
            pkg_dir = os.path.dirname(ngSkinTools2.__file__)
            candidates = []
            for root, _dirs, files in os.walk(pkg_dir):
                for f in files:
                    if f.lower().endswith('.png'):
                        candidates.append(os.path.join(root, f))
            # Prefer files named shelf/icon/logo, then largest
            candidates.sort(key=lambda p: (
                not any(k in os.path.basename(p).lower() for k in ('shelf', 'icon', 'logo')),
                -os.path.getsize(p)
            ))
            for candidate in candidates:
                test = QtGui.QImage(candidate)
                if not test.isNull() and test.width() >= 16:
                    base_img = test.scaled(size, size, _KeepAspect, _Smooth)
                    print(f"[NGBuddy] Using base icon: {candidate}")
                    break
        except Exception as e:
            print(f"[NGBuddy] Could not load NGST2 icon: {e}")

        img = QtGui.QImage(size, size, QtGui.QImage.Format_ARGB32)
        img.fill(0)

        painter = QtGui.QPainter(img)
        painter.setRenderHint(_AA)

        if base_img and not base_img.isNull():
            x = (size - base_img.width()) // 2
            y = (size - base_img.height()) // 2
            painter.drawImage(x, y, base_img)
        else:
            # Fallback: teal rounded background
            painter.setBrush(QtGui.QBrush(QtGui.QColor(45, 74, 80)))
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 0)))
            painter.drawRoundedRect(0, 0, size, size, 6, 6)

        # Stamp "Bud" diagonally over the base icon
        painter.save()
        painter.translate(size / 2, size / 2 + 2)
        painter.rotate(-28)

        font = QtGui.QFont("Arial", 10)
        font.setBold(True)
        painter.setFont(font)
        rect = QtCore.QRect(-size // 2, -size // 2, size, size)

        # Dark outline pass for legibility over any background
        painter.setPen(QtGui.QColor(0, 0, 0, 200))
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (0, 1), (-1, 0), (1, 0)):
            painter.drawText(
                QtCore.QRect(rect.x() + dx, rect.y() + dy, rect.width(), rect.height()),
                _AlignCenter, "Bud"
            )

        painter.setPen(QtGui.QColor(255, 255, 255, 240))
        painter.drawText(rect, _AlignCenter, "Bud")

        painter.restore()
        painter.end()

        img.save(icon_path)
        print(f"[NGBuddy] Icon saved: {icon_path}")
        return icon_path

    except Exception as e:
        print(f"[NGBuddy] Could not create icon: {e}")
        return "pythonFamily.png"


icon = _make_icon()

shelf_cmd = (
    "import sys, importlib\n"
    f"if r\"{NGBUDDY_ROOT}\" not in sys.path:\n"
    f"    sys.path.insert(0, r\"{NGBUDDY_ROOT}\")\n"
    "import main; importlib.reload(main); main.show_ui()"
)

shelf_top  = mel.eval("$tmpVar = $gShelfTopLevel")
active_tab = cmds.tabLayout(shelf_top, q=True, selectTab=True)
shelf      = f"{shelf_top}|{active_tab}"

# Remove existing NGBuddy button so re-runs stay clean
for btn in cmds.shelfLayout(shelf, q=True, childArray=True) or []:
    try:
        if cmds.shelfButton(btn, q=True, label=True) == BUTTON_LABEL:
            cmds.deleteUI(btn)
            break
    except Exception:
        pass

cmds.shelfButton(
    parent=shelf,
    label=BUTTON_LABEL,
    annotation="Open NGSkinBuddy",
    sourceType="python",
    command=shelf_cmd,
    image1=icon,
)
print(f"[NGBuddy] Shelf button installed on '{active_tab}'. Click it to launch.")
