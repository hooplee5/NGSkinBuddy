# region [01] IMPORTS
import maya.cmds as cmds
from style.colors import Colors
from style.dimensions import Dimensions
import os
import subprocess
from core.presets import PresetManager, Preset, PresetNode, WeightManager
from core.ng_api import (
    init_layers, create_layers_from_preset, layers_already_initialized,
    refresh_ngst_ui, read_layers_from_mesh, export_weights, import_weights
)
# endregion

# region [02] CONSTANTS
INDENT_PER_LEVEL = 10
TREE_ROW_HEIGHT  = 22
TREE_HEIGHT      = 180

# Derived from Dimensions for easy reference
PW = Dimensions.PRESET_PANEL_W   # preset panel width (~40%)
LW = Dimensions.LAYER_PANEL_W    # layer panel width  (~60%)
GAP = Dimensions.TREE_PANEL_GAP  # gap between panels

# Bottom row total width = both panels + gap
BOTTOM_ROW_W = PW + LW + GAP
# endregion


class BuildTab:

    # region [03] INIT
    def __init__(self, parent, get_mesh_fn):
        self.parent               = parent
        self.get_mesh             = get_mesh_fn
        self.preset_manager       = PresetManager()
        self.selected_preset_node = None
        self.selected_preset_btn  = None
        self.selected_layer_btn   = None
        self.layer_layout         = None
        self.content_layout       = None
        self.assign_preset_menu   = None
        self.weight_manager       = WeightManager()
        self.init_settings_btn    = None
        self.assign_settings_btn  = None
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
        self._build_initialize_section()
        cmds.separator(height=2, style='in')
        self._build_assign_weights_section()
        cmds.separator(height=6, style='none')

        cmds.setParent('..')
    # endregion

    # region [05] INITIALIZE SECTION
    def _build_initialize_section(self):
        cmds.frameLayout(
            label="  Initialize",
            collapsable=False,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=Dimensions.PADDING_INNER,
            marginHeight=0
        )
        cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_PANEL
        )

        cmds.separator(height=4, style='none')

        # Side by side columns — 40% preset / 60% layers
        cmds.rowLayout(
            numberOfColumns=2,
            columnWidth2=[PW, LW],
            columnAlign2=["left", "left"],
            columnAttach2=["left", "left"],
            columnOffset2=[0, GAP],
            backgroundColor=Colors.BG_PANEL
        )

        # Left: Presets header + scroll
        cmds.columnLayout(
            width=PW,
            rowSpacing=0,
            backgroundColor=Colors.BG_PANEL
        )
        cmds.text(
            label=" Presets",
            align='left',
            width=PW,
            height=18,
            font='smallBoldLabelFont',
            backgroundColor=Colors.BG_PANEL
        )
        self.preset_scroll = cmds.scrollLayout(
            childResizable=True,
            height=TREE_HEIGHT,
            width=PW,
            backgroundColor=Colors.BG_DARK
        )
        self.preset_tree_layout = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_DARK
        )
        self._build_preset_tree()
        cmds.setParent('..')  # preset_tree_layout
        cmds.setParent('..')  # preset_scroll
        cmds.setParent('..')  # left columnLayout

        # Right: Layers header + scroll
        cmds.columnLayout(
            width=LW,
            rowSpacing=0,
            backgroundColor=Colors.BG_PANEL
        )
        cmds.text(
            label=" Layers",
            align='left',
            width=LW,
            height=18,
            font='smallBoldLabelFont',
            backgroundColor=Colors.BG_PANEL
        )
        self.layer_scroll = cmds.scrollLayout(
            childResizable=True,
            height=TREE_HEIGHT,
            width=LW,
            backgroundColor=Colors.BG_DARK
        )
        self.layer_layout = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_DARK
        )
        cmds.text(
            label=" Select a preset",
            align='left',
            width=LW,
            backgroundColor=Colors.BG_DARK,
            height=TREE_ROW_HEIGHT
        )
        cmds.setParent('..')  # layer_layout
        cmds.setParent('..')  # layer_scroll
        cmds.setParent('..')  # right columnLayout

        cmds.setParent('..')  # rowLayout

        cmds.separator(height=4, style='none')

        # Create + Settings — spans full width of both panels
        cmds.rowLayout(
            numberOfColumns=2,
            adjustableColumn=1,
            columnWidth2=[BOTTOM_ROW_W - 34, 34],
            columnAttach2=["both", "both"],
            columnOffset2=[0, 0],
            backgroundColor=Colors.BG_PANEL
        )
        cmds.button(
            label="Create",
            height=Dimensions.BTN_PRIMARY,
            backgroundColor=Colors.ACCENT_BUILD,
            command=lambda x: self._on_create()
        )
        self.init_settings_btn = cmds.button(
            label=u"\u2699",
            height=Dimensions.BTN_PRIMARY,
            width=34,
            backgroundColor=Colors.BG_ELEMENT,
            command=lambda x: None
        )
        init_menu = cmds.popupMenu(parent=self.init_settings_btn, button=1)
        cmds.menuItem(label="Save current layers", parent=init_menu,
                      command=lambda x: self._on_save_layers())
        cmds.menuItem(label="Delete current selection", parent=init_menu,
                      command=lambda x: self._on_delete_preset())
        cmds.menuItem(divider=True, parent=init_menu)
        cmds.menuItem(label="Open preset location", parent=init_menu,
                      command=lambda x: self._on_open_preset_folder())
        cmds.setParent('..')

        cmds.separator(height=4, style='none')
        cmds.setParent('..')  # inner columnLayout
        cmds.setParent('..')  # frameLayout
    # endregion

    # region [06] PRESET TREE
    def _build_preset_tree(self):
        preset_names = self.preset_manager.list_presets()

        if not preset_names:
            cmds.button(
                label=" No presets found",
                align='left',
                height=TREE_ROW_HEIGHT,
                width=PW,
                backgroundColor=Colors.BG_DARK,
                enable=False
            )
            return

        for name in sorted(preset_names):
            preset = self.preset_manager.load(name)
            if preset and preset.root:
                # Show the root node itself as the top-level category
                # (e.g. "Creature", "Human", "Prop")
                self._build_preset_node(preset.root, depth=0)

    def _build_preset_node(self, node, depth):
        prefix = " " * (depth * 2)

        if node.is_leaf:
            btn = cmds.button(
                label=f"{prefix}• {node.name}",
                align='left',
                height=TREE_ROW_HEIGHT,
                width=PW,
                backgroundColor=Colors.BG_DARK,
                command=lambda x, n=node: self._on_preset_selected(n)
            )
            node._ui_btn = btn

        else:
            is_collapsed = [False]

            header_btn = cmds.button(
                label=f"{prefix}▸ {node.name}",
                align='left',
                height=TREE_ROW_HEIGHT,
                width=PW,
                backgroundColor=Colors.BG_SURFACE,
                command=lambda x, n=node, c=is_collapsed, d=depth: self._toggle_branch(n, c, d)
            )
            node._ui_header_btn = header_btn

            child_col = cmds.columnLayout(
                adjustableColumn=True,
                rowSpacing=0,
                backgroundColor=Colors.BG_DARK,
                visible=True
            )
            node._ui_child_col = child_col

            for child in node.children:
                self._build_preset_node(child, depth + 1)

            cmds.setParent('..')  # child_col
    # endregion

    # region [07] BRANCH TOGGLE
    def _toggle_branch(self, node, is_collapsed, depth):
        is_collapsed[0] = not is_collapsed[0]
        collapsed        = is_collapsed[0]

        if cmds.columnLayout(node._ui_child_col, exists=True):
            cmds.columnLayout(node._ui_child_col, edit=True, visible=not collapsed)

        prefix = " " * (depth * 2)
        arrow  = "▾" if not collapsed else "▸"
        cmds.button(node._ui_header_btn, edit=True, label=f"{prefix}{arrow} {node.name}")
    # endregion

    # region [08] PRESET SELECTION
    def _on_preset_selected(self, node):
        if self.selected_preset_btn and cmds.button(self.selected_preset_btn, exists=True):
            cmds.button(self.selected_preset_btn, edit=True, backgroundColor=Colors.BG_DARK)

        cmds.button(node._ui_btn, edit=True, backgroundColor=Colors.BG_SURFACE)
        self.selected_preset_btn  = node._ui_btn
        self.selected_preset_node = node
        self._rebuild_layer_tree(node.layers)
    # endregion

    # region [09] LAYER TREE
    def _rebuild_layer_tree(self, layer_nodes):
        if not cmds.columnLayout(self.layer_layout, exists=True):
            return

        children = cmds.columnLayout(self.layer_layout, query=True, childArray=True) or []
        for child in children:
            cmds.deleteUI(child)

        cmds.setParent(self.layer_layout)

        if not layer_nodes:
            cmds.button(
                label=" No layers in preset",
                align='left',
                height=TREE_ROW_HEIGHT,
                width=LW,
                backgroundColor=Colors.BG_DARK,
                enable=False
            )
            return

        for layer_node in layer_nodes:
            self._build_layer_node(layer_node, depth=0)

    def _build_layer_node(self, node, depth):
        has_children = bool(node.children)
        indicator    = "▸" if has_children else "▪"
        prefix       = " " * (depth * 2)
        bg           = Colors.BG_PANEL if depth % 2 == 0 else Colors.BG_DARK

        btn = cmds.button(
            label=f"{prefix} {indicator} {node.name}",
            align='left',
            height=TREE_ROW_HEIGHT,
            width=LW,
            backgroundColor=bg,
            command=lambda x, n=node, b=bg: self._on_layer_selected(n, b)
        )
        node._ui_btn = btn
        node._ui_bg  = bg

        for child in node.children:
            self._build_layer_node(child, depth + 1)
    # endregion

    # region [10] LAYER SELECTION
    def _on_layer_selected(self, node, original_bg):
        if self.selected_layer_btn:
            prev_btn, prev_bg = self.selected_layer_btn
            if cmds.button(prev_btn, exists=True):
                cmds.button(prev_btn, edit=True, backgroundColor=prev_bg)

        cmds.button(node._ui_btn, edit=True, backgroundColor=Colors.ACCENT_BUILD)
        self.selected_layer_btn = (node._ui_btn, original_bg)
    # endregion

    # region [11] ASSIGN INITIAL WEIGHTS SECTION
    def _build_assign_weights_section(self):
        cmds.frameLayout(
            label="  Assign Initial Weights",
            collapsable=False,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=Dimensions.PADDING_INNER,
            marginHeight=0
        )
        cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_PANEL
        )

        cmds.separator(height=4, style='none')
        cmds.separator(height=4, style='none')

        cmds.rowLayout(
            numberOfColumns=3,
            adjustableColumn=1,
            columnWidth3=[BOTTOM_ROW_W - 118, 80, 34],
            columnAttach3=["both", "both", "both"],
            columnOffset3=[0, 2, 2],
            backgroundColor=Colors.BG_PANEL
        )
        self.assign_preset_menu = cmds.optionMenu(
            height=Dimensions.BTN_PRIMARY,
            backgroundColor=Colors.BG_ELEMENT
        )
        cmds.menuItem(label="No weight presets found")
        self._refresh_weight_menu()

        cmds.button(
            label="Assign",
            height=Dimensions.BTN_PRIMARY,
            width=80,
            backgroundColor=Colors.ACCENT_BUILD,
            command=lambda x: self._on_assign()
        )
        self.assign_settings_btn = cmds.button(
            label=u"\u2699",
            height=Dimensions.BTN_PRIMARY,
            width=34,
            backgroundColor=Colors.BG_ELEMENT,
            command=lambda x: None
        )
        assign_menu = cmds.popupMenu(parent=self.assign_settings_btn, button=1)
        cmds.menuItem(label="Save current weights", parent=assign_menu,
                      command=lambda x: self._on_save_weights())
        cmds.menuItem(label="Delete current weight", parent=assign_menu,
                      command=lambda x: self._on_delete_weight())
        cmds.menuItem(divider=True, parent=assign_menu)
        cmds.menuItem(label="Open weight location", parent=assign_menu,
                      command=lambda x: self._on_open_weight_folder())
        cmds.setParent('..')

        cmds.separator(height=4, style='none')
        cmds.setParent('..'  )  # inner columnLayout
        cmds.setParent('..'  )  # frameLayout
    # endregion

    # region [12] ACTIONS
    def _on_create(self):
        mesh = self.get_mesh()
        if not mesh:
            print("[NGBuddy] No valid mesh selected")
            return
        if not self.selected_preset_node:
            print("[NGBuddy] No preset selected")
            return

        if layers_already_initialized(mesh):
            confirm = cmds.confirmDialog(
                title="Layers Already Exist",
                message=f"'{mesh}' already has NGSkin layers.\nThis will add layers on top. Continue?",
                button=["Continue", "Cancel"],
                defaultButton="Cancel",
                cancelButton="Cancel"
            )
            if confirm != "Continue":
                return

        # Visual feedback — disable tab during operation
        self.set_enabled(False)
        cmds.refresh()

        try:
            layers_obj = init_layers(mesh)
            if not layers_obj:
                cmds.confirmDialog(title="NGBuddy", message=f"Failed to initialize layers on '{mesh}'.", button=["OK"])
                return

            success = create_layers_from_preset(mesh, self.selected_preset_node.layers)
            if success:
                print(f"[NGBuddy] Layers created on '{mesh}' from preset '{self.selected_preset_node.name}'")
                refresh_ngst_ui(mesh)
                cmds.confirmDialog(
                    title="NGBuddy",
                    message=f"Layers created successfully on '{mesh}'.",
                    button=["OK"]
                )
            else:
                cmds.confirmDialog(title="NGBuddy", message="Layer creation failed.", button=["OK"])
        finally:
            self.set_enabled(True)

    def _on_assign(self):
        mesh = self.get_mesh()
        if not mesh:
            print("[NGBuddy] No valid mesh selected")
            return
        label = cmds.optionMenu(self.assign_preset_menu, query=True, value=True)
        if not label or label == "No weight presets found":
            cmds.confirmDialog(title="NGBuddy", message="No weight preset selected.", button=["OK"])
            return

        # Resolve actual preset name from the label — name is always the last segment
        # Label format: "Category/Subcategory/name" or "...Category/name"
        name = label.split("/")[-1].strip()
        if not name or not self.weight_manager.weight_path(name):
            cmds.confirmDialog(title="NGBuddy", message="Could not resolve weight preset.", button=["OK"])
            return

        confirm = cmds.confirmDialog(
            title="Assign Initial Weights",
            message=f"This will add an IMPORTED_WEIGHTS group to '{mesh}'.\nExisting layers will not be affected. Continue?",
            button=["Assign", "Cancel"],
            defaultButton="Assign",
            cancelButton="Cancel"
        )
        if confirm != "Assign":
            return

        self.set_enabled(False)
        cmds.refresh()
        try:
            filepath = self.weight_manager.weight_path(name)
            import_weights(mesh, filepath)
        finally:
            self.set_enabled(True)

    # --- Initialize settings actions ---

    def _on_save_layers(self):
        """Save current mesh layers as a new preset leaf under the selected path."""
        mesh = self.get_mesh()
        if not mesh:
            cmds.confirmDialog(title="NGBuddy", message="No valid mesh selected.", button=["OK"])
            return

        # Build path prefix from selected preset node
        path_prefix = ""
        if self.selected_preset_node:
            path_prefix = self.selected_preset_node.name

        result = cmds.promptDialog(
            title="Save Layer Preset",
            message=f"Path: {path_prefix}\nNew preset name:",
            button=["Save", "Cancel"],
            defaultButton="Save",
            cancelButton="Cancel",
            dismissString="Cancel"
        )
        if result != "Save":
            return

        name = cmds.promptDialog(query=True, text=True).strip()
        if not name:
            return

        # Read current layers from mesh
        layer_nodes = read_layers_from_mesh(mesh)
        if not layer_nodes:
            cmds.confirmDialog(title="NGBuddy", message="No NGSkin layers found on mesh.", button=["OK"])
            return

        # Build or update preset file
        # Find which preset file holds the selected node's root
        preset_names = self.preset_manager.list_presets()
        target_preset = None

        for pname in preset_names:
            p = self.preset_manager.load(pname)
            if p:
                target_preset = p
                break

        if not target_preset:
            # Create a new preset file named after the mesh
            target_preset = Preset(name=mesh)

        # Find the parent node to attach the new leaf to
        parent_node = target_preset.root
        if self.selected_preset_node:
            # Walk tree to find selected node and use it as parent
            found = self._find_node_in_tree(target_preset.root, self.selected_preset_node.name)
            if found:
                parent_node = found

        # Create new leaf node
        new_leaf = PresetNode(name=name, layers=layer_nodes)
        parent_node.children.append(new_leaf)

        if self.preset_manager.save(target_preset):
            print(f"[NGBuddy] Preset '{name}' saved")
            self._rebuild_preset_tree()
        else:
            cmds.confirmDialog(title="NGBuddy", message="Failed to save preset.", button=["OK"])

    def _on_delete_preset(self):
        if not self.selected_preset_node:
            cmds.confirmDialog(title="NGBuddy", message="No preset selected.", button=["OK"])
            return

        confirm = cmds.confirmDialog(
            title="Delete Preset",
            message=f"Delete '{self.selected_preset_node.name}'? This cannot be undone.",
            button=["Delete", "Cancel"],
            defaultButton="Cancel",
            cancelButton="Cancel"
        )
        if confirm != "Delete":
            return

        # For now delete the entire preset file matching the root
        # A smarter implementation would remove just the leaf node
        preset_names = self.preset_manager.list_presets()
        for pname in preset_names:
            p = self.preset_manager.load(pname)
            if p and self._remove_node_from_tree(p.root, self.selected_preset_node.name):
                self.preset_manager.save(p)
                break

        self.selected_preset_node = None
        self.selected_preset_btn  = None
        self._rebuild_preset_tree()
        print("[NGBuddy] Preset deleted")

    def _on_open_preset_folder(self):
        path = self.preset_manager.preset_dir
        subprocess.Popen(f'explorer "{path}"')

    # --- Assign settings actions ---

    def _on_save_weights(self):
        mesh = self.get_mesh()
        if not mesh:
            cmds.confirmDialog(title="NGBuddy", message="No valid mesh selected.", button=["OK"])
            return

        result = cmds.promptDialog(
            title="Save Weight Preset",
            message="Weight preset name:",
            button=["Save", "Cancel"],
            defaultButton="Save",
            cancelButton="Cancel",
            dismissString="Cancel"
        )
        if result != "Save":
            return
        name = cmds.promptDialog(query=True, text=True).strip()
        if not name:
            return

        # Optional category path for tree structure
        # User can type the path using / or \ as separators e.g. Creature/Biped
        path_result = cmds.promptDialog(
            title="Save Weight Preset",
            message="Category path (optional):\nUse / or \\ to separate levels\ne.g. Creature/Biped",
            button=["OK", "Skip"],
            defaultButton="Skip",
            cancelButton="Skip",
            dismissString="Skip"
        )
        tree_path = []
        if path_result == "OK":
            raw = cmds.promptDialog(query=True, text=True).strip()
            if raw:
                # Normalize both / and \ as separators
                import re
                tree_path = [p.strip() for p in re.split(r'[/\\]+', raw) if p.strip()]

        filepath = self.weight_manager.weight_path(name)
        if export_weights(mesh, filepath):
            self.weight_manager.save_meta(name, mesh, tree_path=tree_path)
            self._refresh_weight_menu()
            print(f"[NGBuddy] Weight preset '{name}' saved")
        else:
            cmds.confirmDialog(title="NGBuddy", message="Failed to save weights.", button=["OK"])



    def _on_delete_weight(self):
        label = cmds.optionMenu(self.assign_preset_menu, query=True, value=True)
        if not label or label == "No weight presets found":
            cmds.confirmDialog(title="NGBuddy", message="No weight preset selected.", button=["OK"])
            return

        # Resolve actual name — always the last segment of the path label
        name = label.split("/")[-1].strip()

        confirm = cmds.confirmDialog(
            title="Delete Weight Preset",
            message=f"Delete weight preset '{name}'? This cannot be undone.",
            button=["Delete", "Cancel"],
            defaultButton="Cancel",
            cancelButton="Cancel"
        )
        if confirm != "Delete":
            return

        self.weight_manager.delete(name)
        self._refresh_weight_menu()
        print(f"[NGBuddy] Weight preset '{name}' deleted")

    def _on_open_weight_folder(self):
        self.weight_manager.open_folder()

    # --- Tree helpers ---

    def _find_node_in_tree(self, root, name):
        """Recursively find a node by name in a PresetNode tree."""
        if root.name == name:
            return root
        for child in root.children:
            result = self._find_node_in_tree(child, name)
            if result:
                return result
        return None

    def _remove_node_from_tree(self, root, name):
        """Remove a node by name from children. Returns True if removed."""
        for i, child in enumerate(root.children):
            if child.name == name:
                root.children.pop(i)
                return True
            if self._remove_node_from_tree(child, name):
                return True
        return False

    def _rebuild_preset_tree(self):
        """Clear and rebuild the preset tree UI."""
        if not cmds.columnLayout(self.preset_tree_layout, exists=True):
            return
        children = cmds.columnLayout(self.preset_tree_layout, query=True, childArray=True) or []
        for child in children:
            cmds.deleteUI(child)
        cmds.setParent(self.preset_tree_layout)
        self.selected_preset_node = None
        self.selected_preset_btn  = None
        self._build_preset_tree()

    def _refresh_weight_menu(self):
        """Rebuild the weight preset optionMenu using tree structure for visual hierarchy."""
        if not self.assign_preset_menu or not cmds.optionMenu(self.assign_preset_menu, exists=True):
            return
        items = cmds.optionMenu(self.assign_preset_menu, query=True, itemListLong=True) or []
        for item in items:
            cmds.deleteUI(item)

        menu_items = self.weight_manager.build_menu_items()
        if menu_items:
            for label, name in menu_items:
                cmds.menuItem(label=label, parent=self.assign_preset_menu)
        else:
            cmds.menuItem(label="No weight presets found", parent=self.assign_preset_menu)
    # endregion
    # region [13] ENABLE / DISABLE
    def set_enabled(self, enabled):
        if cmds.columnLayout(self.content_layout, exists=True):
            cmds.columnLayout(self.content_layout, edit=True, enable=enabled)
    # endregion