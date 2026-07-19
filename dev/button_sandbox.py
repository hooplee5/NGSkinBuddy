"""
NGBuddy Button Sandbox -- final verification view.
Run from Maya Script Editor to confirm all buttons look correct.

  Usage:
      exec(open(r"C:\\...\\NGSkinBuddy\\dev\\button_sandbox.py").read())

  ALL DECIDED:
      Mute      -> NGST2 eye-fill.svg / eye-slash-fill.svg  (via QSvgRenderer)
      Lock      -> :/Lock_ON.png (locked) / :/Lock_OFF_grey.png (unlocked)
      Flood 1   -> "Full"  purple ACCENT bg
      Flood 0   -> "Zero"  grey bg
      Sel verts -> chr(0x2316) position-indicator cross
      Swap      -> QPushButton "Swap Mask/Joint"  w=120
      Save      -> :/save.png
      Load      -> :/playblast.png
"""

import os
import sys

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QToolButton, QPushButton, QScrollArea, QApplication,
    )
    from PySide6.QtCore import Qt, QSize
    from PySide6.QtGui import QIcon, QPixmap, QPainter
    try:
        from PySide6.QtSvg import QSvgRenderer
        _HAS_SVG = True
    except ImportError:
        _HAS_SVG = False
except ImportError:
    from PySide2.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QToolButton, QPushButton, QScrollArea, QApplication,
    )
    from PySide2.QtCore import Qt, QSize
    from PySide2.QtGui import QIcon, QPixmap, QPainter
    try:
        from PySide2.QtSvg import QSvgRenderer
        _HAS_SVG = True
    except ImportError:
        _HAS_SVG = False

# -- Theme (mirrors skinning_tab.py) ------------------------------------------
BG     = "#1e1e1e"
PANEL  = "#2d2d2d"
ELEM   = "#404040"
ACCENT = "#6b4f9e"
TEXT   = "#cccccc"
MUTED  = "#666666"
H, W   = 24, 24

# -- Symbols via chr() so file stays pure ASCII -------------------------------
CROSS  = chr(0x2316)   # position-indicator cross


# -- Icon helpers -------------------------------------------------------------

_CACHE = {}

def _qt_icon(res):
    if res not in _CACHE:
        _CACHE[res] = QIcon(res)
    return _CACHE[res]


def _ngst_icon(filename, size=16):
    """Same logic as skinning_tab._ngst_icon -- renders SVG via QSvgRenderer."""
    key = "__ngst__" + filename
    if key not in _CACHE:
        try:
            import ngSkinTools2.ui as _nui
            path = os.path.join(os.path.dirname(_nui.__file__), "images", filename)
            if not os.path.exists(path):
                _CACHE[key] = QIcon()
            elif _HAS_SVG:
                renderer = QSvgRenderer(path)
                pm = QPixmap(size, size)
                pm.fill(Qt.transparent)
                painter = QPainter(pm)
                renderer.render(painter)
                painter.end()
                _CACHE[key] = QIcon(pm)
            else:
                _CACHE[key] = QIcon(path)
        except Exception:
            _CACHE[key] = QIcon()
    return _CACHE[key]


# -- Widget helpers -----------------------------------------------------------

def _tbtn(text="", res=None, ngst=None, w=W, bg=ELEM, fg="#ccc", fs=11):
    b = QToolButton()
    b.setFixedSize(w, H)
    ic = None
    if ngst:
        ic = _ngst_icon(ngst)
    elif res:
        ic = _qt_icon(res)
    if ic and not ic.isNull():
        b.setIcon(ic)
        b.setIconSize(QSize(w - 4, H - 4))
    else:
        b.setText(text or (ngst or res or "?"))
    b.setStyleSheet(
        "QToolButton{background:" + bg + ";border:none;color:" + fg + ";"
        "font-size:" + str(fs) + "px;}"
        "QToolButton:hover{background:#505050;}"
    )
    return b


def _pbtn(text, w=80):
    b = QPushButton(text)
    b.setFixedHeight(H)
    b.setMinimumWidth(w)
    b.setStyleSheet(
        "QPushButton{background:" + ELEM + ";border:1px solid #555;"
        "border-radius:3px;color:" + TEXT + ";font-size:11px;padding:0 6px;}"
        "QPushButton:hover{background:#505050;}"
    )
    return b


def _section(title, decided=False):
    lbl = QLabel("  " + title)
    lbl.setFixedHeight(22)
    lbl.setStyleSheet(
        "background:" + ("#1e3a1e" if decided else PANEL) + ";color:" + MUTED + ";"
        "font-size:9px;font-weight:bold;padding:4px;"
    )
    return lbl


def _group(row_label, *variants):
    card = QWidget()
    card.setStyleSheet("background:#2a2a2a;border-radius:3px;")
    row = QHBoxLayout(card)
    row.setContentsMargins(10, 6, 10, 6)
    row.setSpacing(20)
    name_lbl = QLabel(row_label)
    name_lbl.setFixedWidth(100)
    name_lbl.setStyleSheet("color:" + TEXT + ";font-size:11px;")
    row.addWidget(name_lbl)
    for tag, widgets in variants:
        col = QVBoxLayout()
        col.setSpacing(3)
        col.setAlignment(Qt.AlignCenter)
        tag_lbl = QLabel(tag)
        tag_lbl.setAlignment(Qt.AlignCenter)
        tag_lbl.setStyleSheet("color:#555;font-size:9px;")
        col.addWidget(tag_lbl)
        brow = QHBoxLayout()
        brow.setSpacing(2)
        brow.setAlignment(Qt.AlignCenter)
        for widget in widgets:
            brow.addWidget(widget)
        col.addLayout(brow)
        row.addLayout(col)
    row.addStretch()
    return card


# -- Sandbox window -----------------------------------------------------------

class ButtonSandbox(QWidget):
    _OBJECT_NAME = "NGBuddy_ButtonSandbox"

    def __init__(self):
        super().__init__(None, Qt.Window)
        self.setObjectName(self._OBJECT_NAME)
        self.setWindowTitle("NGBuddy - Button Sandbox (final)")
        self.resize(760, 560)
        self.setStyleSheet("background:" + BG + ";color:" + TEXT + ";")

        root = QVBoxLayout(self)
        root.setSpacing(2)
        root.setContentsMargins(6, 6, 6, 6)

        tip = QLabel(
            "  All buttons decided. Verify each row looks correct in Maya."
        )
        tip.setStyleSheet(
            "background:#1a2a1a;color:#66bb66;"
            "font-size:9px;padding:5px;border-radius:3px;"
        )
        root.addWidget(tip)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        inner = QWidget()
        inner.setStyleSheet("background:" + BG + ";")
        lay = QVBoxLayout(inner)
        lay.setSpacing(4)
        lay.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        lay.addWidget(_section("ALL DECIDED", decided=True))

        lay.addWidget(_group("Mute (layer)",
            ("active\neye-fill",       [_tbtn(ngst="eye-fill.svg")]),
            ("muted\neye-slash-fill",  [_tbtn(ngst="eye-slash-fill.svg")]),
        ))

        lay.addWidget(_group("Lock (per row)",
            ("unlocked\nLock_OFF_grey", [_tbtn(res=":/Lock_OFF_grey.png")]),
            ("locked\nLock_ON",         [_tbtn(res=":/Lock_ON.png")]),
        ))

        lay.addWidget(_group("Flood weight",
            ("flood to 1\nFull purple",  [_tbtn("Full", w=26, bg=ACCENT, fg="#fff", fs=9)]),
            ("flood to 0\nZero grey",    [_tbtn("Zero", w=26, fs=9)]),
        ))

        lay.addWidget(_group("Select verts",
            ("row button\ncross",       [_tbtn(CROSS)]),
            ("inspector\ncross",        [_tbtn(CROSS, w=H - 4)]),
        ))

        lay.addWidget(_group("Swap target",
            ("120px\ntext btn",         [_pbtn("Swap Mask/Joint", w=120)]),
        ))

        lay.addWidget(_group("Save / Load",
            ("save\nsave.png",          [_tbtn(res=":/save.png")]),
            ("load\nplayblast.png",     [_tbtn(res=":/playblast.png")]),
        ))

        # -- Row simulation: what a full joint row looks like -----------------
        lay.addWidget(_section("FULL ROW SIMULATION (lock + Full + Zero + cross)"))
        sim = QWidget()
        sim.setStyleSheet("background:#212121;border-radius:3px;")
        sim_lay = QHBoxLayout(sim)
        sim_lay.setContentsMargins(4, 4, 4, 4)
        sim_lay.setSpacing(1)
        sim_lay.addWidget(_tbtn(res=":/Lock_OFF_grey.png", w=22))
        sim_lay.addWidget(_tbtn("Full", w=26, bg=ACCENT, fg="#fff", fs=9))
        sim_lay.addWidget(_tbtn("Zero", w=26, fs=9))
        sim_lay.addWidget(_tbtn(CROSS,  w=22))
        sim_lay.addStretch()
        lay.addWidget(sim)

        lay.addStretch()


# -- Launch -------------------------------------------------------------------
_app = QApplication.instance() or QApplication(sys.argv)

for _w in _app.topLevelWidgets():
    if _w.objectName() == ButtonSandbox._OBJECT_NAME:
        _w.close()
        break

_sandbox = ButtonSandbox()
_sandbox.show()

print("\n[Sandbox] SVG renderer: " + ("OK" if _HAS_SVG else "MISSING -- mute eye will be text fallback"))
