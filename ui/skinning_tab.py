# region [01] IMPORTS
import os
import json
import maya.cmds as cmds
from style.colors import Colors

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QPushButton,
        QTreeWidget, QTreeWidgetItem, QSlider, QDoubleSpinBox, QScrollArea,
        QAbstractItemView, QHeaderView, QFrame, QSizePolicy, QSplitter
    )
    from PySide6.QtCore import Qt, QSize
    from PySide6.QtGui import QIcon, QColor, QPixmap, QPainter, QPen
    try:
        import PySide6.QtSvg  # noqa: registers SVG image plugin so QIcon can load .svg files
    except ImportError:
        pass
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QPushButton,
        QTreeWidget, QTreeWidgetItem, QSlider, QDoubleSpinBox, QScrollArea,
        QAbstractItemView, QHeaderView, QFrame, QSizePolicy, QSplitter
    )
    from PySide2.QtCore import Qt, QSize
    from PySide2.QtGui import QIcon, QColor, QPixmap, QPainter, QPen
    try:
        import PySide2.QtSvg  # noqa
    except ImportError:
        pass
# endregion

# region [01b] SHIBOKEN — widget validity guard
try:
    import shiboken6 as _shiboken
except ImportError:
    try:
        import shiboken2 as _shiboken
    except ImportError:
        _shiboken = None
# endregion

# region [02] STYLE CONSTANTS
def _hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))

BG_MAIN    = _hex(Colors.BG_MAIN)
BG_SURFACE = _hex(Colors.BG_SURFACE)
BG_PANEL   = _hex(Colors.BG_PANEL)
BG_ELEMENT = _hex(Colors.BG_ELEMENT)
BG_DARK    = _hex(Colors.BG_DARK)
ACCENT     = _hex(Colors.ACCENT_SKINNING)
ERROR      = _hex(Colors.ERROR)
SUCCESS    = _hex(Colors.SUCCESS)

DEPTH_BG = [
    _hex([0.260, 0.252, 0.240]),
    _hex([0.218, 0.220, 0.232]),
    _hex([0.214, 0.228, 0.216]),
    _hex([0.230, 0.216, 0.214]),
]

ROW_H             = 24
BTN_W             = 24
COL2_W            = BTN_W * 4 + 8   # 4 buttons: lock + 1 + 0 + select
S4_H              = 130
THRESHOLD         = 0.001
_VERT_JOB_OPVAR   = "NGBuddy_vert_inspect_sj_id"
_INSP_MAX_VERTS   = 20   # cap for vertex inspector display
# endregion

# region [03] ICONS — Qt resources + NGST2 bundled SVGs
_ICONS = {}

def _icon(name):
    if name not in _ICONS:
        _ICONS[name] = QIcon(name)
    return _ICONS[name]

def _ngst_icon(filename, size=16):
    """Load a bundled NGST2 SVG via QSvgRenderer -> QPixmap (works without SVG image plugin)."""
    key = f"__ngst__{filename}"
    if key not in _ICONS:
        try:
            import ngSkinTools2.ui as _nui
            path = os.path.join(os.path.dirname(_nui.__file__), "images", filename)
            if not os.path.exists(path):
                _ICONS[key] = QIcon()
            else:
                try:
                    try:
                        from PySide6.QtSvg import QSvgRenderer
                        from PySide6.QtGui import QPixmap, QPainter
                        from PySide6.QtCore import Qt
                    except ImportError:
                        from PySide2.QtSvg import QSvgRenderer
                        from PySide2.QtGui import QPixmap, QPainter
                        from PySide2.QtCore import Qt
                    renderer = QSvgRenderer(path)
                    pm = QPixmap(size, size)
                    pm.fill(Qt.transparent)
                    painter = QPainter(pm)
                    renderer.render(painter)
                    painter.end()
                    _ICONS[key] = QIcon(pm)
                except Exception:
                    _ICONS[key] = QIcon(path)  # fallback: direct load
        except Exception:
            _ICONS[key] = QIcon()
    return _ICONS[key]
def _make_muted_icon(base_icon, size=20):
    """Eye icon with a red diagonal slash drawn over it — muted layer state."""
    try:
        pm = base_icon.pixmap(size, size)
        if pm.isNull():
            return base_icon
        result = QPixmap(pm)
        p = QPainter(result)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(ERROR))
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(size - 3, 3, 3, size - 3)  # top-right to bottom-left
        p.end()
        return QIcon(result)
    except Exception:
        return base_icon
# endregion

# region [04] SIGNAL BLOCKER helper
class _Blocker:
    def __init__(self, widget):
        self._w = widget
    def __enter__(self):
        self._prev = self._w.blockSignals(True)
    def __exit__(self, *_):
        self._w.blockSignals(self._prev)
# endregion


class SkinningTab(QWidget):

    # region [05] INIT
    def __init__(self, get_mesh_fn, parent=None):
        super(SkinningTab, self).__init__(parent)

        self._get_mesh = get_mesh_fn

        # Section 1
        self._layer_label     = None
        self._mute_btn        = None
        self._opacity_spinner = None
        self._opacity_slider  = None
        self._infl_label      = None
        self._pre_mask_infl   = None

        # Section 2
        self._tree         = None
        self._tree_items   = {}   # infl_idx (int) -> QTreeWidgetItem
        self._mask_item    = None
        self._lock_btn_map = {}   # infl_idx (int) -> QToolButton
        self._locked_infls = set()

        # Section 3
        self._pose_labels       = {}
        self._poses             = {"A": None, "B": None, "C": None}
        self._poses_file        = None
        self._active_pose       = None
        self._bind_btn          = None
        self._pose_slot_widgets = {}

        # Section 4
        self._vert_container  = None
        self._vert_layout     = None
        self._vert_header_lbl = None
        self._layer_mode_btn  = None
        self._final_mode_btn  = None
        self._vert_thresh_field = None
        self._vert_mode       = "final"
        self._vert_thresh     = THRESHOLD
        self._vert_job_id     = None

        # Shared state
        self._current_layer_id       = None
        self._current_infl_idx       = None
        self._last_mesh              = None
        self._enabled                = False
        self._ngst_events_connected  = False
        self._joint_depth_map        = {}
    # endregion

    # region [06] BUILD
    def build(self):
        SkinningTab._kill_stale_job()   # kill any orphaned scriptJob from a previous run

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_section1())
        root.addWidget(self._make_sep())
        root.addWidget(self._build_section2(), stretch=1)
        root.addWidget(self._make_sep())
        root.addWidget(self._build_section3())
        root.addWidget(self._make_sep())
        root.addWidget(self._build_section4())

        self.setLayout(root)

        self._init_poses_file()
        self._load_poses()
        self._start_vert_job()
        self._connect_ngst_events()

    def _make_sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setStyleSheet("color: #3a3a3a;")
        f.setMaximumHeight(1)
        return f
    # endregion

    # region [07] SECTION 1 — Layer + Influence
    def _build_section1(self):
        wrap = QFrame()
        wrap.setStyleSheet(f"background-color: {BG_SURFACE};")
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(3)

        # ── Row 1: Layer ──────────────────────────────────────────────────
        r1 = QHBoxLayout()
        r1.setSpacing(3)

        r1.addWidget(self._small_label("Layer:"))

        self._mute_btn = QToolButton()
        self._mute_btn.setFixedSize(BTN_W, ROW_H)
        self._mute_btn.setCheckable(True)
        self._mute_btn.setToolTip("Mute / unmute this layer")
        _eye_on = _ngst_icon("eye-fill.svg", size=20)
        if not _eye_on.isNull():
            _eye_off = _make_muted_icon(_eye_on, size=20)
            self._mute_btn.setIcon(_eye_on)
            self._mute_btn.setIconSize(QSize(20, 20))
            self._mute_btn._icon_on  = _eye_on
            self._mute_btn._icon_off = _eye_off
        else:
            self._mute_btn.setText("●")
            self._mute_btn._icon_on  = None
            self._mute_btn._icon_off = None
        self._mute_btn.setStyleSheet(
            f"QToolButton {{ background: {BG_ELEMENT}; border: none; color: #ccc; }}"
            f"QToolButton:checked {{ background: {ERROR}; }}"
        )
        self._mute_btn.clicked.connect(self._on_mute_toggle)
        r1.addWidget(self._mute_btn)

        self._layer_label = self._info_label("  —")
        r1.addWidget(self._layer_label, stretch=1)

        self._opacity_spinner = QDoubleSpinBox()
        self._opacity_spinner.setRange(0.0, 1.0)
        self._opacity_spinner.setSingleStep(0.01)
        self._opacity_spinner.setDecimals(2)
        self._opacity_spinner.setFixedSize(58, ROW_H)
        self._opacity_spinner.setToolTip("Layer opacity")
        self._opacity_spinner.setStyleSheet(self._spinbox_style())
        r1.addWidget(self._opacity_spinner)

        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setFixedHeight(ROW_H - 4)
        self._opacity_slider.setMinimumWidth(50)
        self._opacity_slider.setToolTip("Layer opacity")
        slider_frame = QFrame()
        slider_frame.setStyleSheet(
            f"QFrame {{ background: {BG_DARK}; border-radius: 3px; }}"
        )
        sf_lay = QHBoxLayout(slider_frame)
        sf_lay.setContentsMargins(4, 2, 4, 2)
        sf_lay.addWidget(self._opacity_slider)
        r1.addWidget(slider_frame, stretch=1)

        self._opacity_spinner.valueChanged.connect(self._on_opacity_spinner_changed)
        self._opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)

        lay.addLayout(r1)

        # ── Row 2: Influence ─────────────────────────────────────────────
        r2 = QHBoxLayout()
        r2.setSpacing(3)

        r2.addWidget(self._small_label("Infl:"))

        self._infl_label = self._info_label("  —")
        r2.addWidget(self._infl_label, stretch=1)

        swap = QPushButton("Swap Mask/Joint")
        swap.setFixedHeight(ROW_H)
        swap.setMinimumWidth(120)
        swap.setToolTip("Swap paint target between influence and mask")
        swap.setStyleSheet(self._push_btn_style())
        swap.clicked.connect(self._on_mask_swap)
        r2.addWidget(swap)

        lay.addLayout(r2)
        return wrap
    # endregion

    # region [08] SECTION 2 — Joint Tree
    def _build_section2(self):
        wrap = QWidget()
        wrap.setStyleSheet(f"background-color: {BG_PANEL};")
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Column header bar
        hdr = QWidget()
        hdr.setFixedHeight(ROW_H)
        hdr.setStyleSheet(f"background-color: {BG_PANEL};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(20, 0, 4, 0)
        hl.setSpacing(0)

        lh = QLabel("Joint Hierarchy")
        lh.setStyleSheet(f"color: #cccccc; font-weight: bold; background: transparent;")
        hl.addWidget(lh, stretch=1)

        for t in ("🔒", "1", "0", "↗"):
            lb = QLabel(t)
            lb.setAlignment(Qt.AlignCenter)
            lb.setFixedWidth(BTN_W)
            lb.setStyleSheet("color: #888888; background: transparent;")
            hl.addWidget(lb)

        lay.addWidget(hdr)

        # Tree
        self._tree = QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderHidden(True)
        self._tree.header().setStretchLastSection(False)
        self._tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self._tree.setColumnWidth(1, COL2_W)
        self._tree.setIndentation(14)
        self._tree.setIconSize(QSize(14, 14))
        self._tree.setUniformRowHeights(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setStyleSheet(
            f"QTreeWidget {{ background-color: {BG_PANEL}; color: #cccccc;"
            f"  border: none; outline: none; }}"
            f"QTreeWidget::item {{ height: {ROW_H}px; }}"
            f"QTreeWidget::item:selected {{ background-color: {ACCENT}; color: #ffffff; }}"
            f"QTreeWidget::item:hover:!selected {{ background-color: #404040; }}"
        )
        self._tree.itemClicked.connect(self._on_tree_item_clicked)

        lay.addWidget(self._tree, stretch=1)
        return wrap

    def _build_mask_row(self):
        item = QTreeWidgetItem()
        item.setData(0, Qt.UserRole, "mask")
        item.setText(0, "  [Mask]")
        item.setIcon(0, _icon(":/blendColors.svg"))
        item.setSizeHint(0, QSize(0, ROW_H))
        item.setSizeHint(1, QSize(COL2_W, ROW_H))
        self._mask_item = item
        self._tree.addTopLevelItem(item)
        self._tree.setItemWidget(item, 1, self._row_btns(
            infl_idx="mask", is_mask=True, bg=BG_DARK
        ))

    def _build_joint_row(self, qt_parent, infl_name, infl_idx, depth):
        bg = DEPTH_BG[depth % len(DEPTH_BG)]
        item = QTreeWidgetItem()
        item.setData(0, Qt.UserRole, infl_idx)
        item.setText(0, "  " + infl_name)
        item.setIcon(0, _icon(":/joint.svg"))
        item.setSizeHint(0, QSize(0, ROW_H))
        item.setSizeHint(1, QSize(COL2_W, ROW_H))
        item.setBackground(0, QColor(bg))
        item.setBackground(1, QColor(bg))

        if qt_parent is None:
            self._tree.addTopLevelItem(item)
        else:
            qt_parent.addChild(item)

        self._tree.setItemWidget(item, 1, self._row_btns(
            infl_idx=infl_idx, is_mask=False,
            infl_name=infl_name, bg=bg
        ))
        self._tree_items[infl_idx] = item
        return item

    def _row_btns(self, infl_idx, is_mask, infl_name="", bg=BG_DARK):
        w = QWidget()
        w.setStyleSheet(f"background-color: {bg};")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(1, 1, 1, 1)
        hl.setSpacing(1)

        # ── Lock / Unlock ────────────────────────────────────────────────
        bl = QToolButton(); bl.setFixedSize(BTN_W - 2, ROW_H - 2)
        bl.setCheckable(True)
        if is_mask:
            bl.setEnabled(False)
            bl.setIcon(_icon(":/Lock_OFF_grey.png"))
        else:
            bl.setIcon(_icon(":/Lock_OFF_grey.png"))
            bl.setToolTip("Lock / unlock this influence")
            bl.setStyleSheet(
                f"QToolButton {{ background: {BG_ELEMENT}; border: none; }}"
                f"QToolButton:checked {{ background: {ACCENT}; }}"
            )
            bl.clicked.connect(lambda _=False, i=infl_idx: self._on_lock_row(i))
            self._lock_btn_map[infl_idx] = bl
        hl.addWidget(bl)

        # ── Flood Full / Zero ────────────────────────────────────────────
        b1 = QToolButton(); b1.setFixedSize(BTN_W + 2, ROW_H - 2)
        b1.setText("Full")
        b1.setToolTip("Flood to 1.0")
        b1.setStyleSheet(
            "QToolButton { background: #2d4a50; border: none; color: #cccccc; font-size: 9px; }"
            "QToolButton:hover { background: #3a5f68; }"
        )
        if is_mask:
            b1.clicked.connect(lambda: self._on_flood_mask(1.0))
        else:
            b1.clicked.connect(lambda _=False, i=infl_idx: self._on_flood_infl(i, 1.0))
        hl.addWidget(b1)

        b0 = QToolButton(); b0.setFixedSize(BTN_W + 2, ROW_H - 2)
        b0.setText("Zero")
        b0.setToolTip("Flood to 0.0")
        b0.setStyleSheet(
            f"QToolButton {{ background: {BG_ELEMENT}; border: none; color: #ccc; font-size: 9px; }}"
            f"QToolButton:hover {{ background: #505050; }}"
        )
        if is_mask:
            b0.clicked.connect(lambda: self._on_flood_mask(0.0))
        else:
            b0.clicked.connect(lambda _=False, i=infl_idx: self._on_flood_infl(i, 0.0))
        hl.addWidget(b0)

        # ── Select influenced verts ──────────────────────────────────────
        bs = QToolButton(); bs.setFixedSize(BTN_W - 2, ROW_H - 2)
        bs.setText(chr(0x2316))  # position-indicator cross (confirmed visible)
        bs.setToolTip("Select influenced verts")
        bs.setStyleSheet(f"QToolButton {{ background: {BG_ELEMENT}; border: none; color: #aaa; }}")
        if is_mask:
            bs.clicked.connect(self._on_select_verts_by_mask)
        else:
            bs.clicked.connect(lambda _=False, n=infl_name, i=infl_idx: self._on_select_verts(n, i))
        hl.addWidget(bs)

        return w
    # endregion

    # region [09] SECTION 3 — Test Poses
    def _build_section3(self):
        BIND_W = 86
        BTN_H  = 24
        SLOT_H = ROW_H + BTN_H + BTN_H + 10

        wrap = QFrame()
        wrap.setStyleSheet(f"background-color: {BG_SURFACE};")
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(3)

        hdr = QLabel("  Test Poses")
        hdr.setStyleSheet(f"color: #cccccc; font-weight: bold; background: transparent;")
        lay.addWidget(hdr)

        row = QHBoxLayout()
        row.setSpacing(2)

        bind = QPushButton("Bind\nPose")
        bind.setFixedSize(BIND_W, SLOT_H)
        bind.setStyleSheet(self._push_btn_style())
        bind.setToolTip("Restore bind pose for all influences")
        bind.clicked.connect(self._on_bind_pose)
        row.addWidget(bind)
        self._bind_btn = bind

        for slot in ("A", "B", "C"):
            slot_w = QWidget()
            slot_w.setStyleSheet(f"background-color: {BG_DARK};")
            sl = QVBoxLayout(slot_w)
            sl.setContentsMargins(2, 2, 2, 2)
            sl.setSpacing(2)

            lbl = QLabel(f"  Pose {slot}")
            lbl.setFixedHeight(ROW_H)
            lbl.setStyleSheet(f"color: #888888; background: transparent;")
            self._pose_labels[slot] = lbl
            sl.addWidget(lbl)

            sv = QPushButton()
            sv.setFixedHeight(BTN_H)
            sv.setToolTip("Save pose")
            _sv_ic = _icon(":/save.png")
            if not _sv_ic.isNull():
                sv.setIcon(_sv_ic)
                sv.setIconSize(QSize(BTN_H - 4, BTN_H - 4))
            else:
                sv.setText("Save")
            sv.setStyleSheet(self._push_btn_style())
            sv.clicked.connect(lambda _=False, s=slot: self._on_save_pose(s))
            sl.addWidget(sv)

            ld = QPushButton()
            ld.setFixedHeight(BTN_H)
            ld.setToolTip("Load pose")
            _ld_ic = _icon(":/playblast.png")
            if not _ld_ic.isNull():
                ld.setIcon(_ld_ic)
                ld.setIconSize(QSize(BTN_H - 4, BTN_H - 4))
            else:
                ld.setText("Load")
            ld.setStyleSheet(self._push_btn_style())
            ld.clicked.connect(lambda _=False, s=slot: self._on_recall_pose(s))
            sl.addWidget(ld)

            self._pose_slot_widgets[slot] = slot_w
            row.addWidget(slot_w, stretch=1)

        lay.addLayout(row)
        return wrap
    # endregion

    # region [10] SECTION 4 — Vertex Inspector
    def _build_section4(self):
        wrap = QFrame()
        wrap.setStyleSheet(f"background-color: {BG_MAIN};")
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(3)

        # Header row
        hr = QHBoxLayout()

        self._vert_header_lbl = QLabel("  Vertex Inspector")
        self._vert_header_lbl.setStyleSheet(
            f"color: #cccccc; font-weight: bold; background: transparent;"
        )
        hr.addWidget(self._vert_header_lbl, stretch=1)

        self._layer_mode_btn = QPushButton("Layer")
        self._layer_mode_btn.setFixedSize(48, ROW_H)
        self._layer_mode_btn.setStyleSheet(self._push_btn_style())
        self._layer_mode_btn.clicked.connect(lambda: self._set_vert_mode("layer"))
        hr.addWidget(self._layer_mode_btn)

        self._final_mode_btn = QPushButton("Final")
        self._final_mode_btn.setFixedSize(48, ROW_H)
        self._final_mode_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #fff; border: none; }}"
        )
        self._final_mode_btn.clicked.connect(lambda: self._set_vert_mode("final"))
        hr.addWidget(self._final_mode_btn)

        hr.addWidget(self._small_label("Thr:"))

        self._vert_thresh_field = QDoubleSpinBox()
        self._vert_thresh_field.setRange(0.0, 1.0)
        self._vert_thresh_field.setSingleStep(0.001)
        self._vert_thresh_field.setDecimals(3)
        self._vert_thresh_field.setValue(THRESHOLD)
        self._vert_thresh_field.setFixedSize(60, ROW_H)
        self._vert_thresh_field.setStyleSheet(self._spinbox_style())
        self._vert_thresh_field.valueChanged.connect(self._set_vert_threshold)
        hr.addWidget(self._vert_thresh_field)

        lay.addLayout(hr)

        scroll = QScrollArea()
        scroll.setFixedHeight(S4_H)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {BG_DARK}; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background: {BG_DARK}; }}"
        )

        self._vert_container = QWidget()
        self._vert_container.setStyleSheet(f"background: {BG_DARK};")
        self._vert_layout = QVBoxLayout(self._vert_container)
        self._vert_layout.setContentsMargins(0, 0, 0, 0)
        self._vert_layout.setSpacing(1)

        initial = QLabel("  Select vertices to inspect.")
        initial.setStyleSheet(f"color: #888888; background: transparent;")
        self._vert_layout.addWidget(initial)
        self._vert_layout.addStretch()

        scroll.setWidget(self._vert_container)
        lay.addWidget(scroll)
        return wrap
    # endregion

    # region [11] STYLE HELPERS
    def _small_label(self, text):
        lbl = QLabel(text)
        lbl.setFixedWidth(40)
        lbl.setStyleSheet("color: #888888; background: transparent;")
        return lbl

    def _info_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"background: {BG_DARK}; color: #cccccc; padding-left: 4px;"
        )
        lbl.setMinimumWidth(10)
        return lbl

    def _tool_btn(self, icon=None, text="", tooltip="", checkable=False, checked_style=""):
        btn = QToolButton()
        btn.setFixedSize(BTN_W, ROW_H)
        if icon:
            ic = _icon(icon)
            if not ic.isNull():
                btn.setIcon(ic)
            else:
                btn.setText(text)
        else:
            btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        base = f"QToolButton {{ background: {BG_ELEMENT}; border: none; color: #ccc; }}"
        if checked_style:
            base += f" QToolButton:checked {{ {checked_style} }}"
        btn.setStyleSheet(base)
        return btn

    def _push_btn_style(self):
        return (
            f"QPushButton {{ background: {BG_ELEMENT}; color: #cccccc; border: none; }}"
            f"QPushButton:hover {{ background: #505050; }}"
            f"QPushButton:pressed {{ background: #383838; }}"
        )

    def _spinbox_style(self):
        return (
            f"QDoubleSpinBox {{ background: {BG_ELEMENT}; color: #cccccc;"
            f"  border: none; padding-left: 2px; }}"
            f"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button"
            f"  {{ width: 12px; background: #505050; border: none; }}"
        )
    # endregion

    # region [12] NGST2 EVENT HANDLING
    def _connect_ngst_events(self):
        if self._ngst_events_connected:
            return
        try:
            from ngSkinTools2.api.session import session
            if not session.active():
                return
            session.events.currentLayerChanged.addHandler(self._on_ngst_layer_changed)
            session.events.currentInfluenceChanged.addHandler(self._on_ngst_infl_changed)
            self._ngst_events_connected = True
        except Exception as e:
            print(f"[NGBuddy] Could not connect NGST events: {e}")

    def _disconnect_ngst_events(self):
        if not self._ngst_events_connected:
            return
        try:
            from ngSkinTools2.api.session import session
            session.events.currentLayerChanged.removeHandler(self._on_ngst_layer_changed)
            session.events.currentInfluenceChanged.removeHandler(self._on_ngst_infl_changed)
        except Exception:
            pass
        self._ngst_events_connected = False

    def _on_ngst_layer_changed(self, *_):
        self._pre_mask_infl = None
        try:
            self._update_active_indicator()  # tree first — ground truth
            self._refresh_section1()
        except Exception as e:
            if "already deleted" not in str(e):
                print(f"[NGBuddy] layer-changed handler error: {type(e).__name__}: {e}")

    def _on_ngst_infl_changed(self, *_):
        try:
            self._update_active_indicator()  # tree first — ground truth
            self._refresh_section1()
        except Exception as e:
            if "already deleted" not in str(e):
                print(f"[NGBuddy] infl-changed handler error: {type(e).__name__}: {e}")
    # endregion

    def _sync_infl_label_from_tree(self):
        """Read the currently selected tree item and push its name to the Infl label."""
        if not self._infl_label:
            return
        infl_name = "—"
        if self._tree:
            cur = self._tree.currentItem()
            if cur:
                data = cur.data(0, Qt.UserRole)
                if data == "mask":
                    infl_name = "Mask"
                    self._current_infl_idx = None
                elif isinstance(data, int):
                    infl_name = cur.text(0).strip()
                    self._current_infl_idx = data
        self._infl_label.setText(f"  {infl_name}")

    # region [13] REFRESH METHODS
    def _refresh_section1(self):
        try:
            mesh = self._get_mesh()
            if not mesh:
                if self._layer_label:
                    self._layer_label.setText("  —")
                self._sync_infl_label_from_tree()
                return

            from ngSkinTools2.api import Layers
            layer = Layers(mesh).current_layer()
            if not layer:
                self._current_layer_id = None
                if self._layer_label:
                    self._layer_label.setText("  —")
                self._sync_infl_label_from_tree()
                return

            self._current_layer_id = layer.id

            if self._layer_label:
                self._layer_label.setText(f"  {layer.name}")

            self._sync_mute_btn(not layer.enabled)

            opacity = layer.opacity
            if self._opacity_spinner:
                with _Blocker(self._opacity_spinner):
                    self._opacity_spinner.setValue(opacity)
            if self._opacity_slider:
                with _Blocker(self._opacity_slider):
                    self._opacity_slider.setValue(int(opacity * 100))

            self._sync_infl_label_from_tree()

            self._locked_infls = set(layer.locked_influences or [])
            self._update_lock_buttons()

        except Exception as e:
            if "already deleted" not in str(e):
                print(f"[NGBuddy] Error refreshing S1: {e}")

    @staticmethod
    def _sort_influences_hierarchically(influences):
        infl_set = set(influences)
        infl_idx_map = {name: i for i, name in enumerate(influences)}
        children = {j: [] for j in influences}
        roots = []

        for jnt in influences:
            par = (cmds.listRelatives(jnt, parent=True) or [None])[0]
            if par and par in infl_set:
                children[par].append(jnt)
            else:
                roots.append(jnt)

        result = []

        def dfs(node, depth):
            result.append((node, infl_idx_map[node], depth))
            for child in children[node]:
                dfs(child, depth + 1)

        for root in sorted(roots):
            dfs(root, 0)

        return result

    def _rebuild_joint_list(self):
        if self._tree:
            self._tree.clear()
        self._tree_items   = {}
        self._lock_btn_map = {}
        self._mask_item    = None

        mesh = self._get_mesh()
        self._last_mesh = mesh
        if not mesh or not self._tree:
            return

        try:
            from core.ng_api import get_skin_cluster
            sc = get_skin_cluster(mesh)
            if not sc:
                return
            influences = cmds.skinCluster(sc, q=True, influence=True) or []
            sorted_infls = self._sort_influences_hierarchically(influences)
            self._joint_depth_map = {n: d for n, _, d in sorted_infls}

            # Mask row always first
            self._build_mask_row()

            # Build tree items — track Qt parents
            infl_set    = set(influences)
            qt_item_map = {}  # infl_name -> QTreeWidgetItem

            for infl_name, infl_idx, depth in sorted_infls:
                par = (cmds.listRelatives(infl_name, parent=True) or [None])[0]
                qt_par = qt_item_map.get(par) if par and par in infl_set else None
                item = self._build_joint_row(qt_par, infl_name, infl_idx, depth)
                qt_item_map[infl_name] = item

            self._tree.expandAll()
            self._update_active_indicator()
            self._update_lock_buttons()

        except Exception as e:
            print(f"[NGBuddy] Error rebuilding joint list: {e}")

    def _update_active_indicator(self):
        mesh = self._get_mesh()
        if not mesh or not self._tree:
            return

        paint_targets  = []
        is_mask_active = False
        try:
            from ngSkinTools2.api import Layers, NamedPaintTarget
            layer = Layers(mesh).current_layer()
            if layer:
                self._current_layer_id = layer.id
                paint_targets  = layer.paint_targets or []
                is_mask_active = NamedPaintTarget.MASK in paint_targets
        except Exception:
            pass

        old = self._tree.blockSignals(True)
        try:
            self._tree.clearSelection()
            if is_mask_active and self._mask_item:
                self._mask_item.setSelected(True)
                self._tree.setCurrentItem(self._mask_item)
            elif paint_targets:
                item = self._tree_items.get(paint_targets[0])
                if item:
                    item.setSelected(True)
                    self._tree.setCurrentItem(item)
        finally:
            self._tree.blockSignals(old)

    def _refresh_vertex_inspector(self):
        try:
            self._refresh_vertex_inspector_inner()
        except Exception as e:
            if "already deleted" in str(e):
                self._kill_vert_job()
            else:
                print(f"[NGBuddy] Error in vertex inspector: {e}")

    def _refresh_vertex_inspector_inner(self):
        if not self._vert_layout or not self._vert_container:
            return

        # Clear existing rows (keep stretch at end)
        while self._vert_layout.count() > 1:
            item = self._vert_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        mesh = self._get_mesh()
        sel  = cmds.ls(selection=True, flatten=True) or []

        # If the stored mesh is stale/empty (SelectionChanged race), derive it from
        # the component selection so the inspector doesn't flicker "No mesh selected."
        if not mesh:
            for _item in sel:
                if '.' in _item:
                    _node = _item.split('.')[0]
                    if (cmds.objExists(_node) and
                            cmds.listRelatives(_node, shapes=True, type='mesh')):
                        mesh = _node
                        break

        vert_strs = [v for v in sel if mesh and f"{mesh}.vtx[" in v]

        def _status(msg):
            lbl = QLabel(msg)
            lbl.setStyleSheet(f"color: #888888; background: transparent;")
            self._vert_layout.insertWidget(0, lbl)
            if self._vert_header_lbl:
                self._vert_header_lbl.setText("  Vertex Inspector")

        if not mesh:
            _status("  No mesh selected.")
            return
        if not vert_strs:
            _status("  Select vertices to inspect weights.")
            return

        vert_indices = []
        for v in vert_strs:
            try:
                vert_indices.append(int(v.split('[')[1].rstrip(']')))
            except Exception:
                pass
        if not vert_indices:
            return

        total_n  = len(vert_indices)
        capped   = total_n > _INSP_MAX_VERTS
        vert_indices = vert_indices[:_INSP_MAX_VERTS]
        n = len(vert_indices)

        mode_lbl = "Layer" if self._vert_mode == "layer" else "Final"
        cap_note = f"  (showing {n} of {total_n})" if capped else ""
        if self._vert_header_lbl:
            self._vert_header_lbl.setText(
                f"  Vertex Inspector  [{mode_lbl}]{cap_note}"
            )

        try:
            from core.ng_api import get_skin_cluster
            sc = get_skin_cluster(mesh)
            if not sc:
                _status("  No skinCluster.")
                return

            influences   = cmds.skinCluster(sc, q=True, influence=True) or []
            infl_idx_map = {name: i for i, name in enumerate(influences)}

            per_vert = self._get_weights_per_vert(mesh, sc, influences, vert_indices)

            any_weights = any(d for _, d in per_vert)
            if not any_weights:
                _status("  All weights below threshold.")
                return

            insert_pos = 0
            for vi, weight_dict in per_vert:
                if not weight_dict:
                    continue

                # ── Vert header ──────────────────────────────────────────
                hdr = QWidget()
                hdr.setStyleSheet(f"background: {BG_PANEL};")
                hdr_lay = QHBoxLayout(hdr)
                hdr_lay.setContentsMargins(4, 1, 4, 1)
                hdr_lay.setSpacing(2)

                sel_btn = QToolButton()
                sel_btn.setFixedSize(ROW_H - 4, ROW_H - 4)
                sel_btn.setText(chr(0x2316))  # position-indicator cross
                sel_btn.setToolTip(f"Select vtx[{vi}] only")
                sel_btn.setStyleSheet(
                    f"QToolButton {{ background: {BG_ELEMENT}; border: none;"
                    f"  color: #aaa; font-size: 10px; }}"
                    f"QToolButton:hover {{ background: #505050; }}"
                )
                sel_btn.clicked.connect(
                    lambda _=False, _mesh=mesh, _vi=vi:
                        cmds.select(f"{_mesh}.vtx[{_vi}]")
                )
                hdr_lay.addWidget(sel_btn)

                hdr_lbl = QLabel(f"vtx[{vi}]")
                hdr_lbl.setStyleSheet(
                    "color: #aaaaaa; font-weight: bold; background: transparent;"
                )
                hdr_lay.addWidget(hdr_lbl, stretch=1)
                self._vert_layout.insertWidget(insert_pos, hdr)
                insert_pos += 1

                # ── Influence rows ────────────────────────────────────────
                for infl_name, w in sorted(weight_dict.items(),
                                            key=lambda kv: kv[1], reverse=True):
                    infl_idx = infl_idx_map.get(infl_name, -1)
                    depth    = self._joint_depth_map.get(infl_name, 0)
                    bg       = DEPTH_BG[depth % len(DEPTH_BG)]

                    row_w = QWidget()
                    row_w.setStyleSheet(f"background: {bg};")
                    row_h = QHBoxLayout(row_w)
                    row_h.setContentsMargins(16, 1, 4, 1)
                    row_h.setSpacing(4)

                    lbl = QLabel(infl_name)
                    lbl.setStyleSheet("color: #cccccc; background: transparent;")
                    row_h.addWidget(lbl, stretch=1)

                    spin = QDoubleSpinBox()
                    spin.setRange(0.0, 1.0)
                    spin.setSingleStep(0.001)
                    spin.setDecimals(4)
                    spin.setValue(w)
                    spin.setFixedSize(70, ROW_H - 4)
                    spin.setStyleSheet(self._spinbox_style())
                    editable = self._vert_mode == "layer"
                    spin.setReadOnly(not editable)
                    spin.setToolTip(
                        f"Set {infl_name} weight for vtx[{vi}]" if editable
                        else "Switch to Layer mode to edit"
                    )
                    if editable:
                        spin.valueChanged.connect(
                            lambda v, nm=infl_name, idx=infl_idx, _vi=vi:
                                self._on_vert_weight_change_single(nm, idx, _vi, v)
                        )
                    row_h.addWidget(spin)

                    self._vert_layout.insertWidget(insert_pos, row_w)
                    insert_pos += 1

        except Exception as e:
            import traceback
            traceback.print_exc()
            _status(f"  Error: {e}")
    # endregion

    # region [14] WEIGHT HELPERS
    def _get_weights_per_vert(self, mesh, sc, influences, vert_indices):
        """Return [(vi, {infl_name: weight}), ...] — one entry per selected vert."""
        result = []

        if self._vert_mode == "layer":
            try:
                from ngSkinTools2.api import Layers
                layer = Layers(mesh).current_layer()
                if not layer:
                    return [(vi, {}) for vi in vert_indices]

                # Pre-fetch all influence weight arrays for this layer once
                infl_arrays = {}
                for i, infl in enumerate(influences):
                    arr = layer.get_weights(i)
                    if arr:
                        infl_arrays[infl] = arr

                for vi in vert_indices:
                    vert_dict = {
                        infl: arr[vi]
                        for infl, arr in infl_arrays.items()
                        if vi < len(arr) and arr[vi] > self._vert_thresh
                    }
                    result.append((vi, vert_dict))
            except Exception as e:
                print(f"[NGBuddy] Layer weight fetch error: {e}")
                result = [(vi, {}) for vi in vert_indices]
        else:
            # Final mode: batch-fetch via Maya API 2.0 (single call, no per-vert loop)
            try:
                import maya.api.OpenMaya as om
                import maya.api.OpenMayaAnim as oma

                msel = om.MSelectionList()
                msel.add(sc)
                msel.add(mesh)
                fn_skin  = oma.MFnSkinCluster(msel.getDependNode(0))
                mesh_dag = msel.getDagPath(1)

                comp_fn   = om.MFnSingleIndexedComponent()
                vert_comp = comp_fn.create(om.MFn.kMeshVertComponent)
                for vi in vert_indices:
                    comp_fn.addElement(vi)

                weights_flat, num_infls = fn_skin.getWeights(mesh_dag, vert_comp)
                ni = int(num_infls)
                for j, vi in enumerate(vert_indices):
                    off = j * ni
                    vert_dict = {
                        influences[i]: float(weights_flat[off + i])
                        for i in range(ni)
                        if i < len(influences) and float(weights_flat[off + i]) > self._vert_thresh
                    }
                    result.append((vi, vert_dict))

            except Exception as e:
                print(f"[NGBuddy] Maya API weight fetch failed, falling back: {e}")
                for vi in vert_indices:
                    vals = cmds.skinPercent(sc, f"{mesh}.vtx[{vi}]", q=True, value=True) or []
                    vert_dict = {
                        influences[i]: w
                        for i, w in enumerate(vals)
                        if i < len(influences) and w > self._vert_thresh
                    }
                    result.append((vi, vert_dict))

        return result
    # endregion

    # region [15] TREE CALLBACK
    def _on_tree_item_clicked(self, item, _col):
        mesh = self._get_mesh()
        if not mesh:
            return
        data = item.data(0, Qt.UserRole)
        try:
            from ngSkinTools2.api import Layers, NamedPaintTarget
            layer = Layers(mesh).current_layer()
            if not layer:
                return
            if data == "mask":
                layer.paint_targets = [NamedPaintTarget.MASK]
            elif isinstance(data, int):
                layer.paint_targets = [data]
                self._current_infl_idx = data
            self._refresh_section1()
            try:
                from ngSkinTools2.api.session import session
                if session.active():
                    session.events.currentInfluenceChanged.emitIfChanged()
            except Exception:
                pass
        except Exception as e:
            print(f"[NGBuddy] Error setting paint target: {e}")
    # endregion

    # region [16] SECTION 1 CALLBACKS
    def _on_mute_toggle(self):
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from ngSkinTools2.api import Layers
            layer = Layers(mesh).current_layer()
            if not layer:
                return
            layer.enabled = not layer.enabled
            # Sync the button immediately — NGST2 doesn't emit a property-changed
            # event for layer.enabled, so we can't rely on _refresh_layer_ui firing.
            self._sync_mute_btn(not layer.enabled)
        except Exception as e:
            print(f"[NGBuddy] Error toggling mute: {e}")

    def _sync_mute_btn(self, muted: bool):
        """Update the mute button icon and checked state without waiting for NGST2 events."""
        if not self._mute_btn:
            return
        with _Blocker(self._mute_btn):
            self._mute_btn.setChecked(muted)
        ic_on  = getattr(self._mute_btn, '_icon_on',  None)
        ic_off = getattr(self._mute_btn, '_icon_off', None)
        if ic_on and ic_off:
            self._mute_btn.setIcon(ic_off if muted else ic_on)
            self._mute_btn.setIconSize(QSize(20, 20))

    def _on_opacity_spinner_changed(self, value):
        with _Blocker(self._opacity_slider):
            self._opacity_slider.setValue(int(value * 100))
        self._apply_opacity(value)

    def _on_opacity_slider_changed(self, int_val):
        value = int_val / 100.0
        with _Blocker(self._opacity_spinner):
            self._opacity_spinner.setValue(value)
        self._apply_opacity(value)

    def _apply_opacity(self, value):
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from ngSkinTools2.api import Layers
            layer = Layers(mesh).current_layer()
            if layer:
                layer.opacity = float(value)
        except Exception as e:
            print(f"[NGBuddy] Error setting opacity: {e}")

    def _on_lock_row(self, infl_idx):
        """Toggle lock state for a specific influence (called from per-row lock button)."""
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from ngSkinTools2.api import Layers
            from ngSkinTools2.api.session import session
            layer = Layers(mesh).current_layer()
            if not layer:
                return
            locked = list(layer.locked_influences or [])
            if infl_idx in locked:
                locked.remove(infl_idx)
            else:
                locked.append(infl_idx)
            layer.locked_influences = locked
            self._locked_infls = set(locked)
            self._update_lock_buttons()
            if session.active():
                session.events.influencesListUpdated.emit()
        except Exception as e:
            print(f"[NGBuddy] Error toggling lock for influence {infl_idx}: {e}")

    def _update_lock_buttons(self):
        """Sync all per-row lock button visuals to the current _locked_infls set."""
        for infl_idx, btn in self._lock_btn_map.items():
            is_locked = infl_idx in self._locked_infls
            with _Blocker(btn):
                btn.setChecked(is_locked)
            btn.setIcon(
                _icon(":/Lock_ON.png") if is_locked else _icon(":/Lock_OFF_grey.png")
            )

    def _on_mask_swap(self):
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from ngSkinTools2.api import Layers, NamedPaintTarget
            layer = Layers(mesh).current_layer()
            if not layer:
                return
            current = layer.paint_targets or []
            if NamedPaintTarget.MASK in current:
                target = self._pre_mask_infl if self._pre_mask_infl is not None else 0
                layer.paint_targets = [target]
            else:
                self._pre_mask_infl = current[0] if current else 0
                layer.paint_targets = [NamedPaintTarget.MASK]
            self._refresh_section1()
            self._update_active_indicator()
        except Exception as e:
            print(f"[NGBuddy] Error swapping mask: {e}")
    # endregion

    # region [17] JOINT LIST CALLBACKS
    def _on_flood_infl(self, infl_idx, value):
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from ngSkinTools2.api import Layers
            layer = Layers(mesh).current_layer()
            if not layer:
                return
            n_verts   = cmds.polyEvaluate(mesh, vertex=True)
            sel       = cmds.ls(selection=True, flatten=True) or []
            vert_idxs = [int(v.split('[')[1].rstrip(']')) for v in sel if f"{mesh}.vtx[" in v]
            weights   = list(layer.get_weights(infl_idx) or [0.0] * n_verts)
            if vert_idxs:
                for vi in vert_idxs:
                    if vi < len(weights):
                        weights[vi] = value
            else:
                weights = [value] * n_verts
            layer.set_weights(infl_idx, weights)
        except Exception as e:
            print(f"[NGBuddy] Error flooding influence {infl_idx}: {e}")

    def _on_flood_mask(self, value):
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from ngSkinTools2.api import Layers, NamedPaintTarget
            layer = Layers(mesh).current_layer()
            if not layer:
                return
            n_verts   = cmds.polyEvaluate(mesh, vertex=True)
            sel       = cmds.ls(selection=True, flatten=True) or []
            vert_idxs = [int(v.split('[')[1].rstrip(']')) for v in sel if f"{mesh}.vtx[" in v]
            if vert_idxs:
                mask = list(layer.get_weights(NamedPaintTarget.MASK) or [0.0] * n_verts)
                for vi in vert_idxs:
                    if vi < len(mask):
                        mask[vi] = value
                layer.set_weights(NamedPaintTarget.MASK, mask)
            else:
                layer.set_weights(NamedPaintTarget.MASK, [value] * n_verts)
        except Exception as e:
            print(f"[NGBuddy] Error flooding mask: {e}")

    def _on_select_verts(self, infl_name, infl_idx):
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from ngSkinTools2.api import Layers
            layer = Layers(mesh).current_layer()
            if not layer:
                return
            weights  = layer.get_weights(infl_idx) or []
            vert_sel = [f"{mesh}.vtx[{i}]" for i, w in enumerate(weights) if w > self._vert_thresh]
            if vert_sel:
                cmds.select(vert_sel)
            # no selection = do nothing (avoids confusing deselect)
        except Exception as e:
            print(f"[NGBuddy] Error selecting verts for {infl_name}: {e}")

    def _on_select_verts_by_mask(self):
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from ngSkinTools2.api import Layers, NamedPaintTarget
            layer = Layers(mesh).current_layer()
            if not layer:
                return
            mask     = layer.get_weights(NamedPaintTarget.MASK) or []
            vert_sel = [f"{mesh}.vtx[{i}]" for i, w in enumerate(mask) if w > self._vert_thresh]
            if vert_sel:
                cmds.select(vert_sel)
        except Exception as e:
            print(f"[NGBuddy] Error selecting verts by mask: {e}")
    # endregion

    # region [18] SECTION 3 CALLBACKS
    def _on_bind_pose(self):
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from core.ng_api import get_skin_cluster
            sc = get_skin_cluster(mesh)
            if not sc:
                return
            influences = cmds.skinCluster(sc, q=True, influence=True) or []
            if influences:
                prev = cmds.ls(selection=True) or []
                cmds.select(influences, replace=True)
                cmds.dagPose(restore=True, bindPose=True)
                cmds.select(prev, replace=True) if prev else cmds.select(clear=True)
            self._active_pose = "bind"
            self._update_pose_highlights()
        except Exception as e:
            print(f"[NGBuddy] Error going to bind pose: {e}")

    def _on_save_pose(self, slot):
        mesh = self._get_mesh()
        if not mesh:
            return
        try:
            from core.ng_api import get_skin_cluster
            sc = get_skin_cluster(mesh)
            if not sc:
                return
            influences = cmds.skinCluster(sc, q=True, influence=True) or []
            pose = {j: cmds.xform(j, q=True, ws=True, matrix=True)
                    for j in influences if cmds.objExists(j)}
            self._poses[slot] = pose
            self._save_poses_to_disk()
            self._update_pose_label(slot)
        except Exception as e:
            print(f"[NGBuddy] Error saving pose {slot}: {e}")

    def _on_recall_pose(self, slot):
        pose = self._poses.get(slot)
        if not pose:
            return
        try:
            for jnt, mat in pose.items():
                if cmds.objExists(jnt):
                    cmds.xform(jnt, ws=True, matrix=mat)
            self._active_pose = slot
            self._update_pose_highlights()
        except Exception as e:
            print(f"[NGBuddy] Error recalling pose {slot}: {e}")

    def _update_pose_highlights(self):
        ACTIVE_SLOT_BG  = "#1a1025"
        active_btn_style = (
            f"QPushButton {{ background: {ACCENT}; color: #ffffff; border: none; }}"
            f"QPushButton:hover {{ background: {ACCENT}; }}"
        )

        if self._bind_btn:
            is_active = self._active_pose == "bind"
            self._bind_btn.setStyleSheet(
                active_btn_style if is_active else self._push_btn_style()
            )

        for slot in ("A", "B", "C"):
            w        = self._pose_slot_widgets.get(slot)
            is_active = self._active_pose == slot
            has_data  = self._poses.get(slot) is not None

            if w:
                w.setStyleSheet(
                    f"background-color: {ACTIVE_SLOT_BG};" if is_active
                    else f"background-color: {BG_DARK};"
                )

            lbl = self._pose_labels.get(slot)
            if lbl:
                if is_active:
                    lbl.setStyleSheet("color: #c8a0ff; background: transparent;")
                elif has_data:
                    lbl.setStyleSheet("color: #cccccc; background: transparent;")
                else:
                    lbl.setStyleSheet("color: #888888; background: transparent;")
    # endregion

    # region [19] SECTION 4 CALLBACKS
    def _on_vert_weight_change_single(self, infl_name, infl_idx, vert_idx, value):
        """Edit weight for one specific vertex in layer mode."""
        mesh = self._get_mesh()
        if not mesh or infl_idx < 0:
            return
        try:
            from ngSkinTools2.api import Layers
            layer = Layers(mesh).current_layer()
            if not layer:
                return
            n_verts = cmds.polyEvaluate(mesh, vertex=True)
            weights = list(layer.get_weights(infl_idx) or [0.0] * n_verts)
            if vert_idx < len(weights):
                weights[vert_idx] = float(value)
            layer.set_weights(infl_idx, weights)
        except Exception as e:
            print(f"[NGBuddy] Error setting vtx[{vert_idx}] weight for {infl_name}: {e}")

    def _set_vert_mode(self, mode):
        self._vert_mode = mode
        active   = f"QPushButton {{ background: {ACCENT}; color: #fff; border: none; }}"
        inactive = self._push_btn_style()
        if self._layer_mode_btn:
            self._layer_mode_btn.setStyleSheet(active if mode == "layer" else inactive)
        if self._final_mode_btn:
            self._final_mode_btn.setStyleSheet(active if mode == "final" else inactive)
        self._refresh_vertex_inspector()

    def _set_vert_threshold(self, value):
        self._vert_thresh = float(value)
        self._refresh_vertex_inspector()
    # endregion

    # region [20] POSE PERSISTENCE
    def _init_poses_file(self):
        try:
            app_dir   = cmds.internalVar(userAppDir=True)
            poses_dir = os.path.join(app_dir, "NGBuddy")
            os.makedirs(poses_dir, exist_ok=True)
            self._poses_file = os.path.join(poses_dir, "skinning_poses.json")
        except Exception as e:
            print(f"[NGBuddy] Could not init poses file: {e}")

    def _load_poses(self):
        if not self._poses_file or not os.path.exists(self._poses_file):
            return
        try:
            with open(self._poses_file, 'r') as f:
                data = json.load(f)
            for slot in ("A", "B", "C"):
                self._poses[slot] = data.get(slot)
            self._update_pose_highlights()
        except Exception as e:
            print(f"[NGBuddy] Error loading poses: {e}")

    def _save_poses_to_disk(self):
        if not self._poses_file:
            return
        try:
            with open(self._poses_file, 'w') as f:
                json.dump(self._poses, f, indent=2)
        except Exception as e:
            print(f"[NGBuddy] Error saving poses: {e}")

    def _update_pose_label(self, slot):
        self._update_pose_highlights()
    # endregion

    # region [21] SCRIPTJOB
    @staticmethod
    def _kill_stale_job():
        """Kill any scriptJob left over from a previous SkinningTab instance.
        The ID is persisted in a Maya optionVar so it survives module reloads."""
        try:
            if cmds.optionVar(exists=_VERT_JOB_OPVAR):
                stale_id = cmds.optionVar(q=_VERT_JOB_OPVAR)
                if isinstance(stale_id, int) and cmds.scriptJob(exists=stale_id):
                    cmds.scriptJob(kill=stale_id, force=True)
                cmds.optionVar(remove=_VERT_JOB_OPVAR)
        except Exception:
            pass

    def _start_vert_job(self):
        try:
            self._vert_job_id = cmds.scriptJob(
                event=["SelectionChanged", self._refresh_vertex_inspector],
                protected=False
            )
            cmds.optionVar(iv=(_VERT_JOB_OPVAR, self._vert_job_id))
        except Exception as e:
            print(f"[NGBuddy] Could not start vert inspector job: {e}")

    def _kill_vert_job(self):
        if self._vert_job_id is not None:
            try:
                if cmds.scriptJob(exists=self._vert_job_id):
                    cmds.scriptJob(kill=self._vert_job_id, force=True)
            except Exception:
                pass
            try:
                cmds.optionVar(remove=_VERT_JOB_OPVAR)
            except Exception:
                pass
            self._vert_job_id = None
    # endregion

    # region [22] PUBLIC API
    def set_enabled(self, enabled):
        self._enabled = enabled
        if not enabled:
            self._pre_mask_infl = None
        if enabled:
            mesh = self._get_mesh()
            if mesh != self._last_mesh:
                self._rebuild_joint_list()
            self._update_active_indicator()
            self._refresh_section1()
            self._connect_ngst_events()
        else:
            self._last_mesh = None
            if self._layer_label:
                self._layer_label.setText("  —")
            if self._infl_label:
                self._infl_label.setText("  —")
            if self._tree:
                self._tree.clear()
            self._tree_items = {}
            self._mask_item  = None

    def on_activated(self):
        self._last_mesh = None
        self._connect_ngst_events()
        self._rebuild_joint_list()
        self._update_active_indicator()
        self._refresh_section1()
        self._refresh_vertex_inspector()

    def teardown(self):
        self._disconnect_ngst_events()
        self._kill_vert_job()
    # endregion
