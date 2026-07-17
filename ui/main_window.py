# region [01] IMPORTS
import maya.cmds as cmds
from style.colors import Colors
from style.dimensions import Dimensions
# endregion

# region [02] CONSTANTS
WINDOW_NAME  = "NGBuddyWorkspaceControl"
WINDOW_LABEL = "NGBuddy"
VERSION      = "v0.1"
REPO_URL     = "https://github.com/kaijutd/NGSkinBuddy"
NGST2_DOCK   = "ngSkinTools2_mainWindow"

TABS = [
    {
        "label":  "Build",
        "accent": Colors.ACCENT_BUILD,
        "info":   "Set up your rig for skinning.\nBind your mesh, initialize NGSkin layers\nand establish your base layer stack."
    },
    {
        "label":  "Copy & Paste",
        "accent": Colors.ACCENT_COPYPASTE,
        "info":   "Copy weights between meshes or layers.\nUse presets to transfer weights\nacross LODs or mesh variations."
    },
    {
        "label":  "Utils",
        "accent": Colors.ACCENT_UTILS,
        "info":   "General utilities for skin weight operations.\nMirror weights across all layers,\nand other helpers not covered by NGSkin Tools."
    },
    {
        "label":  "Skinning",
        "accent": Colors.ACCENT_SKINNING,
        "info":   "Your active skinning workspace.\nAll controls accessible without\nleaving this tab or typing."
    },
]
# endregion


class _ResizeFilter:
    """Forwards resize events from a cmds-managed Qt widget to a PySide2 child widget."""
    def __init__(self, child, parent_widget):
        self._child = child
        self._parent = parent_widget

        try:
            from PySide2.QtCore import QObject, QEvent
        except ImportError:
            from PySide6.QtCore import QObject, QEvent

        class _Filter(QObject):
            def __init__(self2, child, parent_widget):
                super().__init__(parent_widget)
                self2._child = child
                self2._parent = parent_widget

            def eventFilter(self2, obj, event):
                if event.type() == QEvent.Resize:
                    self2._child.setGeometry(0, 0,
                        self2._parent.width(), self2._parent.height())
                return False

        self._filter = _Filter(child, parent_widget)
        parent_widget.installEventFilter(self._filter)


class MainWindow:

    # region [03] INIT
    def __init__(self):
        self.current_tab      = 0
        self.tab_buttons      = []
        self.tab_panels       = []
        self.tab_instances    = {}
        self.info_text        = None
        self.info_frame       = None
        self.status_text      = None
        self.content_parent   = None
        self.script_job_id    = None
        self.current_mesh     = None
        self.scroll_layout    = None
        self.skinning_layout  = None
    # endregion

    # region [04] CREATE WINDOW
    def create(self):
        if cmds.workspaceControl(WINDOW_NAME, exists=True):
            cmds.deleteUI(WINDOW_NAME)

        cmds.workspaceControl(
            WINDOW_NAME,
            label=WINDOW_LABEL,
            initialWidth=Dimensions.WINDOW_WIDTH_DEFAULT,
            minimumWidth=Dimensions.WINDOW_WIDTH_MIN,
            widthProperty="preferred",
            retain=False
        )

        outer = cmds.formLayout(
            parent=WINDOW_NAME,
            backgroundColor=Colors.BG_MAIN
        )

        status_bar = self._build_status_bar(outer)

        # Header + info box sit above both the scroll and skinning layouts
        header_col = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            parent=outer,
            backgroundColor=Colors.BG_MAIN
        )
        self._build_header(header_col)
        self._build_info_box(header_col)
        cmds.setParent(outer)

        # scrollLayout for tabs 0–2
        self.scroll_layout = cmds.scrollLayout(
            childResizable=True,
            backgroundColor=Colors.BG_MAIN,
            parent=outer
        )
        root = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_MAIN
        )
        self._build_content_area(root)
        cmds.setParent(outer)

        # Skinning tab gets its own stretch-aware formLayout (shown only on tab 3)
        self.skinning_layout = cmds.formLayout(
            parent=outer,
            backgroundColor=Colors.BG_MAIN,
            visible=False
        )
        self._build_skinning_area(self.skinning_layout)
        cmds.setParent(outer)

        cmds.formLayout(
            outer, edit=True,
            attachForm=[
                (header_col,          'top',    0),
                (header_col,          'left',   0),
                (header_col,          'right',  0),
                (self.scroll_layout,  'left',   0),
                (self.scroll_layout,  'right',  0),
                (self.skinning_layout,'left',   0),
                (self.skinning_layout,'right',  0),
                (status_bar,          'left',   0),
                (status_bar,          'right',  0),
                (status_bar,          'bottom', 0),
            ],
            attachControl=[
                (self.scroll_layout,   'top',    0, header_col),
                (self.scroll_layout,   'bottom', 0, status_bar),
                (self.skinning_layout, 'top',    0, header_col),
                (self.skinning_layout, 'bottom', 0, status_bar),
            ]
        )

        self._switch_tab(0)
        self._start_selection_job()
        self._update_status()

        # Auto-dock alongside NGSkinTools2 if it is already open
        if cmds.workspaceControl(NGST2_DOCK, q=True, exists=True):
            cmds.evalDeferred(lambda: self._dock_to_ngst2())
    # endregion

    # region [05] HEADER — tab bar + help button
    def _build_header(self, parent):
        header = cmds.rowLayout(
            numberOfColumns=3,
            adjustableColumn=1,
            columnWidth3=[
                Dimensions.TAB_BTN_WIDTH * len(TABS),
                Dimensions.HELP_BTN_WIDTH,
                Dimensions.HELP_BTN_WIDTH
            ],
            parent=parent,
            backgroundColor=Colors.BG_SURFACE,
            height=Dimensions.TAB_HEIGHT
        )

        cmds.rowLayout(
            numberOfColumns=len(TABS),
            columnWidth4=[Dimensions.TAB_BTN_WIDTH] * len(TABS),
            backgroundColor=Colors.BG_SURFACE,
            height=Dimensions.TAB_HEIGHT
        )

        for i, tab in enumerate(TABS):
            btn = cmds.button(
                label=tab["label"],
                width=Dimensions.TAB_BTN_WIDTH,
                height=Dimensions.TAB_HEIGHT,
                backgroundColor=Colors.BG_SURFACE,
                command=lambda x, idx=i: self._switch_tab(idx)
            )
            self.tab_buttons.append(btn)

        cmds.setParent('..')

        cmds.button(
            label=u"\u21ba",
            width=Dimensions.HELP_BTN_WIDTH,
            height=Dimensions.TAB_HEIGHT,
            backgroundColor=Colors.BG_ELEMENT,
            parent=header,
            command=lambda x: self.refresh_ui()
        )

        help_btn = cmds.button(
            label="?",
            width=Dimensions.HELP_BTN_WIDTH,
            height=Dimensions.TAB_HEIGHT,
            backgroundColor=Colors.BG_ELEMENT,
            parent=header
        )

        help_menu = cmds.popupMenu(parent=help_btn, button=1)
        cmds.menuItem(label=f"NGBuddy  {VERSION}", enable=False, parent=help_menu)
        cmds.menuItem(divider=True, parent=help_menu)
        cmds.menuItem(
            label="Documentation",
            parent=help_menu,
            command=lambda x: self._open_url(REPO_URL + "/wiki")
        )
        cmds.menuItem(
            label="GitHub Repository",
            parent=help_menu,
            command=lambda x: self._open_url(REPO_URL)
        )
        cmds.menuItem(divider=True, parent=help_menu)
        cmds.menuItem(
            label="Changelog",
            parent=help_menu,
            command=lambda x: self._open_url(REPO_URL + "/releases")
        )
        cmds.menuItem(divider=True, parent=help_menu)
        cmds.menuItem(
            label="Dock to NGSkinTools2",
            parent=help_menu,
            command=lambda x: self._dock_to_ngst2()
        )

        cmds.setParent('..')
        cmds.separator(height=2, style='in', parent=parent)
    # endregion

    # region [06] INFO BOX — collapsible, per tab
    def _build_info_box(self, parent):
        self.info_frame = cmds.frameLayout(
            label="Info",
            collapsable=True,
            collapse=True,
            parent=parent,
            backgroundColor=Colors.BG_DARK,
            marginWidth=Dimensions.PADDING_INNER,
            marginHeight=Dimensions.PADDING_INNER
        )
        self.info_text = cmds.text(
            label="",
            align='left',
            backgroundColor=Colors.BG_DARK
        )
        cmds.setParent('..')
        cmds.separator(height=2, style='in', parent=parent)
    # endregion

    # region [07] CONTENT AREA — one panel per tab
    def _build_content_area(self, parent):
        self.content_parent = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            parent=parent,
            backgroundColor=Colors.BG_MAIN
        )

        for i, tab in enumerate(TABS):
            panel = cmds.columnLayout(
                adjustableColumn=True,
                rowSpacing=Dimensions.ROW_SPACING,
                parent=self.content_parent,
                backgroundColor=Colors.BG_MAIN,
                visible=(i == 0)
            )

            if tab["label"] == "Build":
                from ui.build_tab import BuildTab
                instance = BuildTab(panel, self._get_current_mesh)
                instance.build()
                self.tab_instances[i] = instance

            elif tab["label"] == "Copy & Paste":
                from ui.copy_paste_tab import CopyPasteTab
                instance = CopyPasteTab(panel, self._get_current_mesh)
                instance.build()
                self.tab_instances[i] = instance

            elif tab["label"] == "Utils":
                from ui.utils_tab import UtilsTab
                instance = UtilsTab(panel, self._get_current_mesh)
                instance.build()
                self.tab_instances[i] = instance

            elif tab["label"] == "Skinning":
                pass  # Skinning tab is built separately in _build_skinning_area

            else:
                self._build_placeholder(tab["label"])

            cmds.setParent('..')
            self.tab_panels.append(panel)
    # endregion

    # region [08] SKINNING AREA — PySide2 widget embedded in cmds formLayout
    def _build_skinning_area(self, parent_form):
        from ui.skinning_tab import SkinningTab
        skinning_idx = next(i for i, t in enumerate(TABS) if t["label"] == "Skinning")

        try:
            import maya.OpenMayaUI as omui
            try:
                import shiboken2
                from PySide2.QtWidgets import QWidget
            except ImportError:
                import shiboken6 as shiboken2  # noqa: F401
                from PySide6.QtWidgets import QWidget

            ptr = omui.MQtUtil.findLayout(parent_form)
            qt_parent = shiboken2.wrapInstance(int(ptr), QWidget)

            instance = SkinningTab(self._get_current_mesh, parent=qt_parent)
            instance.build()
            instance.setGeometry(0, 0, qt_parent.width(), qt_parent.height())
            _ResizeFilter(instance, qt_parent)

        except Exception as e:
            import traceback
            print(f"[NGBuddy] Could not embed skinning tab: {e}")
            traceback.print_exc()
            instance = SkinningTab(self._get_current_mesh)
            instance.build()

        self.tab_instances[skinning_idx] = instance
    # endregion

    # region [09] PLACEHOLDER CONTENT
    def _build_placeholder(self, tab_label):
        cmds.separator(height=Dimensions.SECTION_SPACING, style='none')
        cmds.text(
            label=f"{tab_label} — coming soon",
            align='center',
            height=40,
            backgroundColor=Colors.BG_PANEL
        )
        cmds.separator(height=Dimensions.SECTION_SPACING, style='none')
    # endregion

    # region [10] STATUS BAR — pinned to bottom
    def _build_status_bar(self, parent):
        bar = cmds.columnLayout(
            adjustableColumn=True,
            parent=parent,
            backgroundColor=Colors.BG_SURFACE
        )
        cmds.separator(height=2, style='in')
        cmds.rowLayout(
            numberOfColumns=2,
            adjustableColumn=1,
            columnWidth2=[270, 80],
            backgroundColor=Colors.BG_SURFACE,
            height=Dimensions.STATUS_HEIGHT
        )
        self.status_text = cmds.text(
            label="No mesh selected",
            align='left',
            backgroundColor=Colors.BG_SURFACE
        )
        cmds.text(
            label=f"NGBuddy {VERSION}",
            align='right',
            backgroundColor=Colors.BG_SURFACE
        )
        cmds.setParent('..')
        cmds.setParent('..')
        return bar
    # endregion

    # region [10] TAB SWITCHING
    def _switch_tab(self, index):
        self.current_tab = index
        is_skinning = (TABS[index]["label"] == "Skinning")

        # Toggle scroll vs skinning layout
        if self.scroll_layout and cmds.scrollLayout(self.scroll_layout, exists=True):
            cmds.scrollLayout(self.scroll_layout, edit=True, visible=not is_skinning)
        if self.skinning_layout and cmds.formLayout(self.skinning_layout, exists=True):
            cmds.formLayout(self.skinning_layout, edit=True, visible=is_skinning)

        # Show/hide individual scroll-based tab panels
        for i, panel in enumerate(self.tab_panels):
            cmds.columnLayout(panel, edit=True, visible=(i == index))

        for i, btn in enumerate(self.tab_buttons):
            active_color = TABS[i]["accent"] if i == index else Colors.BG_SURFACE
            cmds.button(btn, edit=True, backgroundColor=active_color)

        if self.info_text and cmds.text(self.info_text, exists=True):
            cmds.text(self.info_text, edit=True, label=TABS[index]["info"])

        # Notify skinning tab on activation so it can refresh live state
        skinning_idx = next((i for i, t in enumerate(TABS) if t["label"] == "Skinning"), None)
        if skinning_idx is not None and skinning_idx in self.tab_instances:
            inst = self.tab_instances[skinning_idx]
            if is_skinning and hasattr(inst, 'on_activated'):
                inst.on_activated()
    # endregion

    # region [11] SELECTION SCRIPTJOB
    def _start_selection_job(self):
        self.script_job_id = cmds.scriptJob(
            event=["SelectionChanged", self._update_status],
            protected=False
        )

    def _update_status(self):
        if not self.status_text or not cmds.text(self.status_text, exists=True):
            return

        selection = cmds.ls(selection=True, type='transform')

        if not selection:
            # Check if a component (vertex/face/edge) is selected — extract parent node
            all_sel = cmds.ls(selection=True) or []
            mesh = None
            for item in all_sel:
                if '.' in item:
                    node = item.split('.')[0]
                    if (cmds.objExists(node) and
                            cmds.listRelatives(node, shapes=True, type='mesh')):
                        mesh = node
                        break
            if not mesh:
                self._set_status("No mesh selected", valid=False)
                return
            history = cmds.listHistory(mesh) or []
            skin_clusters = cmds.ls(history, type='skinCluster')
            if not skin_clusters:
                self._set_status(f"{mesh}  |  no skinCluster", valid=False)
                return
            self.current_mesh = mesh
            self._set_status(f"{mesh}  |  {skin_clusters[0]}", valid=True)
            return

        mesh = selection[0]
        history = cmds.listHistory(mesh) or []
        skin_clusters = cmds.ls(history, type='skinCluster')

        if not cmds.listRelatives(mesh, shapes=True, type='mesh'):
            self._set_status(f"{mesh}  |  not a mesh", valid=False)
            return

        if not skin_clusters:
            self._set_status(f"{mesh}  |  no skinCluster", valid=False)
            return

        self.current_mesh = mesh
        self._set_status(f"{mesh}  |  {skin_clusters[0]}", valid=True)

    def _set_status(self, message, valid=True):
        if self.status_text and cmds.text(self.status_text, exists=True):
            cmds.text(
                self.status_text,
                edit=True,
                label=message,
                backgroundColor=Colors.BG_SURFACE if valid else Colors.BG_DARK
            )

        if not valid:
            self.current_mesh = None

        for tab in self.tab_instances.values():
            tab.set_enabled(valid)
    # endregion

    # region [12] PUBLIC METHODS
    def refresh_ui(self):
        from ui.main_window import MainWindow
        window = MainWindow()
        window.create()

    def _get_current_mesh(self):
        return self.current_mesh

    def set_status(self, message):
        if self.status_text and cmds.text(self.status_text, exists=True):
            cmds.text(self.status_text, edit=True, label=message)

    def _open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def _dock_to_ngst2(self):
        if not cmds.workspaceControl(NGST2_DOCK, q=True, exists=True):
            cmds.confirmDialog(
                title="NGBuddy",
                message="NGSkinTools2 is not open. Open it first, then dock.",
                button=["OK"]
            )
            return
        cmds.workspaceControl(WINDOW_NAME, edit=True, dockToControl=(NGST2_DOCK, 'right'))
    # endregion