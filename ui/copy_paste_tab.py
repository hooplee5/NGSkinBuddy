# region [01] IMPORTS
import os
import maya.cmds as cmds
from style.colors import Colors
from style.dimensions import Dimensions
# endregion

# region [02] CONSTANTS
ACCENT       = Colors.ACCENT_COPYPASTE
BTN_H        = Dimensions.BTN_PRIMARY
PAD          = Dimensions.PADDING_INNER
FIELD_COLOR  = Colors.BG_ELEMENT
LABEL_W      = 52
ICON_BTN_W   = 26   # folder and save icon buttons
# endregion


class CopyPasteTab:

    # region [03] INIT
    def __init__(self, parent, get_mesh_fn):
        self.parent          = parent
        self.get_mesh        = get_mesh_fn
        self.content_layout  = None

        self.source_mesh     = None
        self.source_file     = None
        self.source_btn      = None

        self.target_mesh     = None
        self.target_file     = None
        self.target_btn      = None

        self.vtx_mode_menu   = None
        self.use_name_cb     = None
        self.use_distance_cb = None
        self.use_label_cb    = None
        self.apply_mode_menu = None
    # endregion

    # region [04] BUILD UI
    def build(self):
        cmds.setParent(self.parent)

        self.content_layout = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_MAIN
        )

        cmds.separator(height=6, style='none')
        self._build_source_target_section()
        cmds.separator(height=2, style='in')
        self._build_settings_section()
        cmds.separator(height=2, style='in')
        self._build_influence_mapping_section()
        cmds.separator(height=2, style='in')
        self._build_apply_section()
        cmds.separator(height=6, style='none')

        cmds.setParent('..')
    # endregion

    # region [05] SOURCE / TARGET SECTION
    def _build_source_target_section(self):
        cmds.frameLayout(
            label="  Source & Target",
            collapsable=False,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=PAD,
            marginHeight=0
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=0, backgroundColor=Colors.BG_PANEL)

        cmds.separator(height=4, style='none')
        self._build_mesh_row("Source", is_source=True)
        cmds.separator(height=4, style='none')
        self._build_mesh_row("Target", is_source=False)
        cmds.separator(height=4, style='none')

        cmds.setParent('..')
        cmds.setParent('..')

    def _build_mesh_row(self, label, is_source):
        total_w = Dimensions.WINDOW_WIDTH_DEFAULT - (PAD * 4)
        # Label | Field | Folder | Save
        field_w = total_w - LABEL_W - (ICON_BTN_W * 2) - 6

        cmds.rowLayout(
            numberOfColumns=4,
            columnWidth4=[LABEL_W, field_w, ICON_BTN_W, ICON_BTN_W],
            columnAttach4=["both", "both", "both", "both"],
            columnOffset4=[0, 2, 2, 2],
            backgroundColor=Colors.BG_PANEL
        )
        cmds.text(label=label, align='left', width=LABEL_W, backgroundColor=Colors.BG_PANEL)

        if is_source:
            self.source_btn = cmds.button(
                label="Click to grab selection  |  use icons to load/save file",
                align='left',
                height=BTN_H,
                width=field_w,
                backgroundColor=FIELD_COLOR,
                command=lambda x: self._on_grab_source_mesh()
            )
            cmds.button(
                label=u"\U0001F4C2",
                width=ICON_BTN_W,
                height=BTN_H,
                backgroundColor=Colors.BG_ELEMENT,
                annotation="Load weights from file",
                command=lambda x: self._on_browse_source_file()
            )
            cmds.button(
                label=u"\U0001F4BE",
                width=ICON_BTN_W,
                height=BTN_H,
                backgroundColor=Colors.BG_ELEMENT,
                annotation="Save source mesh weights to file",
                command=lambda x: self._on_save_source_to_file()
            )
        else:
            self.target_btn = cmds.button(
                label="Click to grab selection  |  use icons to load/save file",
                align='left',
                height=BTN_H,
                width=field_w,
                backgroundColor=FIELD_COLOR,
                command=lambda x: self._on_grab_target_mesh()
            )
            cmds.button(
                label=u"\U0001F4C2",
                width=ICON_BTN_W,
                height=BTN_H,
                backgroundColor=Colors.BG_ELEMENT,
                annotation="Set output file path",
                command=lambda x: self._on_browse_target_file()
            )
            cmds.button(
                label=u"\U0001F4BE",
                width=ICON_BTN_W,
                height=BTN_H,
                backgroundColor=Colors.BG_ELEMENT,
                annotation="Save target mesh weights to file",
                command=lambda x: self._on_save_target_to_file()
            )
        cmds.setParent('..')
    # endregion

    # region [06] SETTINGS SECTION
    def _build_settings_section(self):
        cmds.frameLayout(
            label="  Settings",
            collapsable=False,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=PAD,
            marginHeight=0
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=0, backgroundColor=Colors.BG_PANEL)
        cmds.separator(height=4, style='none')

        total_w = Dimensions.WINDOW_WIDTH_DEFAULT - (PAD * 4)
        label_w = 140
        field_w = total_w - label_w - 4

        # Vertex Transfer Mode
        cmds.rowLayout(
            numberOfColumns=2,
            columnWidth2=[label_w, field_w],
            columnAttach2=["both", "both"],
            columnOffset2=[0, 4],
            backgroundColor=Colors.BG_PANEL
        )
        cmds.text(label="Vertex Transfer Mode", align='left', width=label_w, backgroundColor=Colors.BG_PANEL)
        self.vtx_mode_menu = cmds.optionMenu(height=BTN_H, backgroundColor=Colors.BG_ELEMENT)
        cmds.menuItem(label="Closest Point")
        cmds.menuItem(label="Vertex ID")
        cmds.menuItem(label="UV Space")
        cmds.setParent('..')

        cmds.separator(height=4, style='none')
        cmds.setParent('..')
        cmds.setParent('..')
    # endregion

    # region [07] INFLUENCE MAPPING — collapsible, collapsed by default
    def _build_influence_mapping_section(self):
        cmds.frameLayout(
            label="  Influence Mapping",
            collapsable=True,
            collapse=True,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=PAD,
            marginHeight=0
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=0, backgroundColor=Colors.BG_PANEL)
        cmds.separator(height=4, style='none')

        total_w = Dimensions.WINDOW_WIDTH_DEFAULT - (PAD * 4)
        label_w = 140
        field_w = total_w - label_w - 4

        for attr, label, default in [
            ('use_name_cb',     'Use Name Matching',     True),
            ('use_distance_cb', 'Use Distance Matching', False),
            ('use_label_cb',    'Use Label Matching',    False),
        ]:
            cmds.rowLayout(
                numberOfColumns=2,
                columnWidth2=[label_w, field_w],
                columnAttach2=["both", "both"],
                columnOffset2=[0, 4],
                backgroundColor=Colors.BG_PANEL
            )
            cmds.text(label=label, align='left', width=label_w, backgroundColor=Colors.BG_PANEL)
            cb = cmds.checkBox(label="", value=default, backgroundColor=Colors.BG_PANEL)
            setattr(self, attr, cb)
            cmds.setParent('..')
            cmds.separator(height=4, style='none')

        cmds.setParent('..')
        cmds.setParent('..')
    # endregion

    # region [08] APPLY SECTION
    def _build_apply_section(self):
        cmds.frameLayout(
            label="  Apply",
            collapsable=False,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=PAD,
            marginHeight=0
        )
        cmds.columnLayout(adjustableColumn=True, rowSpacing=0, backgroundColor=Colors.BG_PANEL)
        cmds.separator(height=4, style='none')

        total_w = Dimensions.WINDOW_WIDTH_DEFAULT - (PAD * 4)
        apply_w = 80
        menu_w  = total_w - apply_w - 4

        cmds.rowLayout(
            numberOfColumns=2,
            adjustableColumn=1,
            columnWidth2=[menu_w, apply_w],
            columnAttach2=["both", "both"],
            columnOffset2=[0, 4],
            backgroundColor=Colors.BG_PANEL
        )
        self.apply_mode_menu = cmds.optionMenu(height=BTN_H, backgroundColor=Colors.BG_ELEMENT)
        cmds.menuItem(label="Add New Layers")
        cmds.menuItem(label="Replace Current")

        cmds.button(
            label="Apply",
            height=BTN_H,
            width=apply_w,
            backgroundColor=ACCENT,
            command=lambda x: self._on_apply()
        )
        cmds.setParent('..')
        cmds.separator(height=4, style='none')
        cmds.setParent('..')
        cmds.setParent('..')
    # endregion

    # region [09] SOURCE ACTIONS
    def _on_grab_source_mesh(self):
        selection = cmds.ls(selection=True, type='transform')
        if not selection:
            print("[NGBuddy] No transform selected for Source")
            return
        self.source_mesh = selection[0]
        self.source_file = None
        cmds.button(self.source_btn, edit=True,
                    label=f"[mesh]  {self.source_mesh}",
                    backgroundColor=Colors.BG_SURFACE)

    def _on_browse_source_file(self):
        if self.target_file:
            cmds.confirmDialog(title="NGBuddy",
                               message="File-to-file transfer is not supported.\nSet a target mesh instead.",
                               button=["OK"])
            return
        result = cmds.fileDialog2(
            fileMode=1,
            caption="Select Source Weight File",
            fileFilter="NGSkinTools JSON (*.json)"
        )
        if not result:
            return
        self.source_file = result[0]
        self.source_mesh = None
        cmds.button(self.source_btn, edit=True,
                    label=f"[file]  {os.path.basename(self.source_file)}",
                    backgroundColor=Colors.BG_SURFACE)

    def _on_save_source_to_file(self):
        """Export current source mesh weights to a file."""
        if not self.source_mesh:
            cmds.confirmDialog(title="NGBuddy",
                               message="Set a source mesh first.",
                               button=["OK"])
            return
        result = cmds.fileDialog2(
            fileMode=0,
            caption="Save Source Weights",
            fileFilter="NGSkinTools JSON (*.json)"
        )
        if not result:
            return
        from core.ng_api import export_weights
        export_weights(self.source_mesh, result[0])
        print(f"[NGBuddy] Saved source weights: {result[0]}")
    # endregion

    # region [10] TARGET ACTIONS
    def _on_grab_target_mesh(self):
        selection = cmds.ls(selection=True, type='transform')
        if not selection:
            print("[NGBuddy] No transform selected for Target")
            return
        self.target_mesh = selection[0]
        self.target_file = None
        cmds.button(self.target_btn, edit=True,
                    label=f"[mesh]  {self.target_mesh}",
                    backgroundColor=Colors.BG_SURFACE)

    def _on_browse_target_file(self):
        if self.source_file:
            cmds.confirmDialog(title="NGBuddy",
                               message="File-to-file transfer is not supported.\nSet a source mesh instead.",
                               button=["OK"])
            return
        result = cmds.fileDialog2(
            fileMode=0,
            caption="Select or Create Target Weight File",
            fileFilter="NGSkinTools JSON (*.json)"
        )
        if not result:
            return
        self.target_file = result[0]
        self.target_mesh = None
        cmds.button(self.target_btn, edit=True,
                    label=f"[file]  {os.path.basename(self.target_file)}",
                    backgroundColor=Colors.BG_SURFACE)

    def _on_save_target_to_file(self):
        """Export current target mesh weights to a file."""
        if not self.target_mesh:
            cmds.confirmDialog(title="NGBuddy",
                               message="Set a target mesh first.",
                               button=["OK"])
            return
        result = cmds.fileDialog2(
            fileMode=0,
            caption="Save Target Weights",
            fileFilter="NGSkinTools JSON (*.json)"
        )
        if not result:
            return
        from core.ng_api import export_weights
        export_weights(self.target_mesh, result[0])
        print(f"[NGBuddy] Saved target weights: {result[0]}")
    # endregion

    # region [11] APPLY ACTION
    def _on_apply(self):
        # Validate source
        if not self.source_mesh and not self.source_file:
            cmds.confirmDialog(title="NGBuddy",
                               message="Please set a Source mesh or file.",
                               button=["OK"])
            return

        # Validate target
        if not self.target_mesh and not self.target_file:
            cmds.confirmDialog(title="NGBuddy",
                               message="Please set a Target mesh or file.",
                               button=["OK"])
            return

        # Read settings
        vtx_label    = cmds.optionMenu(self.vtx_mode_menu,   query=True, value=True)
        apply_mode   = cmds.optionMenu(self.apply_mode_menu, query=True, value=True)
        use_name     = cmds.checkBox(self.use_name_cb,       query=True, value=True)
        use_distance = cmds.checkBox(self.use_distance_cb,   query=True, value=True)
        use_label    = cmds.checkBox(self.use_label_cb,      query=True, value=True)

        vtx_str_map = {
            "Closest Point": "closestPoint",
            "Vertex ID":     "vertexId",
            "UV Space":      "uvSpace",
        }
        vtx_mode = vtx_str_map.get(vtx_label, "closestPoint")

        # Source mesh -> Target file: just export, mode doesn't apply
        if self.target_file:
            if not self.source_mesh:
                cmds.confirmDialog(title="NGBuddy",
                                   message="File-to-file transfer is not supported.\nSet a source mesh.",
                                   button=["OK"])
                return
            from core.ng_api import export_weights
            export_weights(self.source_mesh, self.target_file)
            print(f"[NGBuddy] Exported '{self.source_mesh}' to '{self.target_file}'")
            return

        # Target is a mesh
        target = self.target_mesh

        try:
            from ngSkinTools2 import api as ngst_api
            from ngSkinTools2.api import InfluenceMappingConfig, VertexTransferMode, Layers

            infl_config = InfluenceMappingConfig()
            infl_config.use_name_matching     = use_name
            infl_config.use_distance_matching = use_distance
            infl_config.use_label_matching    = use_label

            vtx_const_map = {
                "closestPoint": VertexTransferMode.closestPoint,
                "vertexId":     VertexTransferMode.vertexId,
                "uvSpace":      VertexTransferMode.uvSpace,
            }
            vtx_const = vtx_const_map.get(vtx_mode, VertexTransferMode.closestPoint)

            # Replace Current — clear all existing layers on target first
            if apply_mode == "Replace Current":
                layers_api = Layers(target)
                if layers_api.is_enabled():
                    layers_api.clear()
                    print(f"[NGBuddy] Cleared existing layers on '{target}'")

            # Transfer from file
            if self.source_file:
                ngst_api.import_json(
                    target,
                    file=self.source_file,
                    vertex_transfer_mode=vtx_const,
                    influences_mapping_config=infl_config,
                )
                print(f"[NGBuddy] Imported '{self.source_file}' onto '{target}'")

            # Transfer from mesh
            elif self.source_mesh:
                ngst_api.transfer_layers(
                    self.source_mesh,
                    target,
                    vertex_transfer_mode=vtx_const,
                    influences_mapping_config=infl_config,
                )
                print(f"[NGBuddy] Transferred '{self.source_mesh}' -> '{target}'")

            from core.ng_api import refresh_ngst_ui
            refresh_ngst_ui(target)

        except Exception as e:
            import traceback
            print(f"[NGBuddy] Transfer error: {e}")
            print(traceback.format_exc())
    # endregion

    # region [12] ENABLE / DISABLE
    def set_enabled(self, enabled):
        # Copy & Paste tab stays enabled regardless of mesh selection —
        # source and target manage their own state independently
        pass
    # endregion