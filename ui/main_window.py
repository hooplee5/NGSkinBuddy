# region [01] IMPORTS
import maya.cmds as cmds
from style.colors import Colors
from style.dimensions import Dimensions
from core.ng_api import is_valid_skinned_mesh
# endregion

# region [02] CONSTANTS
WINDOW_NAME  = "NGBuddyWorkspaceControl"
WINDOW_LABEL = "NGBuddy"
VERSION      = "v0.1"
REPO_URL     = "https://github.com/kaijutd/NGSkinBuddy"

TABS = [
    {
        "label":  "Build",
        "accent": Colors.ACCENT_BUILD,
        "info":   "Set up your rig for skinning.\nBind your mesh, initialize NGSkin layers\nand establish your base layer stack."
    },
    {
        "label":  "Mirror",
        "accent": Colors.ACCENT_MIRROR,
        "info":   "Mirror skin weights across your rig.\nChoose axis, direction and threshold\nusing saved presets per character."
    },
    {
        "label":  "Copy & Paste",
        "accent": Colors.ACCENT_COPYPASTE,
        "info":   "Copy weights between meshes or layers.\nUse presets to transfer weights\nacross LODs or mesh variations."
    },
    {
        "label":  "Skinning",
        "accent": Colors.ACCENT_SKINNING,
        "info":   "Your active skinning workspace.\nAll controls accessible without\nleaving this tab or typing."
    },
]
# endregion


class MainWindow:

    # region [03] INIT
    def __init__(self):
        self.current_tab    = 0
        self.tab_buttons    = []
        self.tab_panels     = []
        self.tab_instances  = {}     # index -> tab object (e.g. BuildTab)
        self.info_text      = None
        self.info_frame     = None
        self.status_text    = None
        self.content_parent = None
        self.script_job_id  = None
        self.current_mesh   = None
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

        scroll = cmds.scrollLayout(
            childResizable=True,
            backgroundColor=Colors.BG_MAIN
        )

        root = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_MAIN
        )

        self._build_header(root)
        self._build_info_box(root)
        self._build_content_area(root)

        cmds.setParent(outer)

        cmds.formLayout(
            outer, edit=True,
            attachForm=[
                (scroll,     'top',    0),
                (scroll,     'left',   0),
                (scroll,     'right',  0),
                (status_bar, 'left',   0),
                (status_bar, 'right',  0),
                (status_bar, 'bottom', 0),
            ],
            attachControl=[
                (scroll, 'bottom', 0, status_bar),
            ]
        )

        self._switch_tab(0)
        self._start_selection_job()
        self._update_status()
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
            label=u"↺",  # refresh arrow ↺
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

        cmds.setParent('..')
        cmds.separator(height=2, style='in', parent=parent)
    # endregion

    # region [06] INFO BOX — collapsible, per tab
    def _build_info_box(self, parent):
        self.info_frame = cmds.frameLayout(
            label="Info",
            collapsable=True,
            collapse=False,
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
                build_tab = BuildTab(panel, self._get_current_mesh)
                build_tab.build()
                self.tab_instances[i] = build_tab
            else:
                self._build_placeholder(tab["label"])

            cmds.setParent('..')
            self.tab_panels.append(panel)
    # endregion

    # region [08] PLACEHOLDER CONTENT
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

    # region [09] STATUS BAR — pinned to bottom
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

        for i, panel in enumerate(self.tab_panels):
            cmds.columnLayout(panel, edit=True, visible=(i == index))

        for i, btn in enumerate(self.tab_buttons):
            active_color = TABS[i]["accent"] if i == index else Colors.BG_SURFACE
            cmds.button(btn, edit=True, backgroundColor=active_color)

        if self.info_text and cmds.text(self.info_text, exists=True):
            cmds.text(self.info_text, edit=True, label=TABS[index]["info"])
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
            self._set_status("No mesh selected", valid=False)
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
        """Update status bar text and enable/disable tab content"""
        if self.status_text and cmds.text(self.status_text, exists=True):
            cmds.text(
                self.status_text,
                edit=True,
                label=message,
                backgroundColor=Colors.BG_SURFACE if valid else Colors.BG_DARK
            )

        if not valid:
            self.current_mesh = None

        # Enable/disable all tab instances
        for tab in self.tab_instances.values():
            tab.set_enabled(valid)
    # endregion

    # region [12] PUBLIC METHODS
    def refresh_ui(self):
        """Refresh the entire UI — rebuilds the current tab content."""
        current = self.current_tab
        # Rebuild the window entirely via show_ui pattern
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
    # endregion