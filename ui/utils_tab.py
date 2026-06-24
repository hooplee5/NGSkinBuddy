# region [01] IMPORTS
import os
import maya.cmds as cmds
from style.colors import Colors
from style.dimensions import Dimensions
# endregion

# region [02] CONSTANTS
ACCENT     = Colors.ACCENT_UTILS
BTN_H      = Dimensions.BTN_PRIMARY
PAD        = Dimensions.PADDING_INNER
CONTENT_W  = Dimensions.WINDOW_WIDTH_DEFAULT - (PAD * 4)
LOG_H      = 75
LIST_H     = 120
HC_LABEL_W = 138
HC_BTN_W   = 28
HC_ICON_W  = 20
HC_FIELD_W = CONTENT_W - HC_LABEL_W - HC_BTN_W - HC_ICON_W - 8
HC_LIST_H  = 200
# endregion

# region [03] HEALTH CHECK DEFINITIONS
HEALTH_CHECKS = [
    {
        "id":      "unskinned",
        "label":   "Unskinned meshes",
        "tooltip": "Finds meshes in the scene with no skinCluster attached",
        "fn":      "_hc_unskinned",
    },
    {
        "id":      "zero_weight",
        "label":   "Verts with zero weight",
        "tooltip": "Finds vertices whose total skin weight sums to zero",
        "fn":      "_hc_zero_weight",
    },
    {
        "id":      "not_normalized",
        "label":   "Weights not summing to 1",
        "tooltip": "Finds vertices whose raw total weight deviates from 1.0 by more than 0.001",
        "fn":      "_hc_not_normalized",
    },
    {
        "id":      "unused_influences",
        "label":   "Unused influences bound",
        "tooltip": "Finds meshes with influences that have zero weight on every vertex",
        "fn":      "_hc_unused_influences",
    },
    {
        "id":      "zero_infl_joints",
        "label":   "Joints with no influence",
        "tooltip": "Finds joints bound to a skinCluster but with no weight on any vertex",
        "fn":      "_hc_zero_infl_joints",
    },
    {
        "id":      "over_n",
        "label":   "Verts > N influences",
        "tooltip": "Finds vertices influenced by more joints than the limit N",
        "fn":      "_hc_over_n",
        "has_n":   True,
    },
    {
        "id":      "missing_ngst",
        "label":   "Missing NGST layer data",
        "tooltip": "Finds skinned meshes with no NGSkinTools2 layer data initialized",
        "fn":      "_hc_missing_ngst",
    },
]
# endregion


class UtilsTab:

    # region [04] INIT
    def __init__(self, parent, get_mesh_fn):
        self.parent    = parent
        self.get_mesh  = get_mesh_fn
        self._last_mesh = None

        # Section 1
        self.del_history_cb     = None
        self.remove_unused_cb   = None
        self.force_normalize_cb = None
        self.rebind_log         = None
        self._rebind_col        = None

        # Section 2
        self.layer_menu         = None
        self.available_list     = None
        self.active_list        = None
        self.src_joint_btn      = None
        self.tgt_joint_btn      = None
        self.transfer_status    = None
        self._infl_layer_col    = None   # 2a only — disabled without mesh
        self._src_joint         = None
        self._tgt_joint         = None
        self._layer_id_map      = []

        # Section 3
        self._hc_icons          = {}
        self._hc_fields         = {}
        self._hc_n_field        = None

        # Section 4
        self.bake_log           = None
        self._bake_col          = None
    # endregion

    # region [05] BUILD
    def build(self):
        cmds.setParent(self.parent)
        cmds.separator(height=6, style='none')
        self._build_cleanup_rebind_section()
        cmds.separator(height=2, style='in')
        self._build_influence_management_section()
        cmds.separator(height=2, style='in')
        self._build_health_checks_section()
        cmds.separator(height=2, style='in')
        self._build_bake_pose_section()
        cmds.separator(height=6, style='none')
    # endregion

    # region [06] UI — Weight Cleanup & Rebind
    def _build_cleanup_rebind_section(self):
        cmds.frameLayout(
            label="  Weight Cleanup & Rebind",
            collapsable=True,
            collapse=False,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=PAD,
            marginHeight=0
        )
        self._rebind_col = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_PANEL
        )
        cmds.separator(height=4, style='none')
        cmds.text(
            label="Saves NG layer data, optionally cleans history, detaches and\n"
                  "rebuilds the skinCluster with the same influences, then restores.",
            align='left',
            backgroundColor=Colors.BG_PANEL
        )
        cmds.separator(height=6, style='none')

        self.del_history_cb = cmds.checkBox(
            label="Delete construction history",
            value=True,
            backgroundColor=Colors.BG_PANEL
        )
        self.remove_unused_cb = cmds.checkBox(
            label="Remove unused influences after rebind",
            value=True,
            backgroundColor=Colors.BG_PANEL
        )
        self.force_normalize_cb = cmds.checkBox(
            label="Force normalize after rebind",
            value=True,
            backgroundColor=Colors.BG_PANEL
        )

        cmds.separator(height=6, style='none')
        cmds.button(
            label="Clean & Rebind",
            height=BTN_H,
            backgroundColor=ACCENT,
            command=lambda x: self._on_clean_rebind()
        )
        cmds.separator(height=4, style='none')
        self.rebind_log = cmds.scrollField(
            editable=False,
            height=LOG_H,
            wordWrap=True,
            backgroundColor=Colors.BG_DARK,
            text=""
        )
        cmds.separator(height=4, style='none')
        cmds.setParent('..')
        cmds.setParent('..')
    # endregion

    # region [07] UI — Influence Management
    def _build_influence_management_section(self):
        cmds.frameLayout(
            label="  Influence Management",
            collapsable=True,
            collapse=True,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=PAD,
            marginHeight=0
        )
        # Outer column — always enabled, holds both 2a and 2b
        cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_PANEL
        )
        cmds.separator(height=4, style='none')

        # ── 2a: Per-layer influence lock/unlock (disabled without mesh) ──
        self._infl_layer_col = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_PANEL
        )
        cmds.text(
            label="  Add / Remove Per Layer",
            align='left',
            font='smallBoldLabelFont',
            backgroundColor=Colors.BG_PANEL
        )
        cmds.separator(height=4, style='none')

        lbl_w  = 50
        menu_w = CONTENT_W - lbl_w - 4
        cmds.rowLayout(
            numberOfColumns=2,
            columnWidth2=[lbl_w, menu_w],
            columnAttach2=["both", "both"],
            columnOffset2=[0, 4],
            backgroundColor=Colors.BG_PANEL
        )
        cmds.text(label="Layer", align='left', width=lbl_w, backgroundColor=Colors.BG_PANEL)
        self.layer_menu = cmds.optionMenu(
            height=BTN_H,
            backgroundColor=Colors.BG_ELEMENT,
            changeCommand=lambda x: self._on_layer_changed()
        )
        cmds.menuItem(label=u"—  select mesh first  —")
        cmds.setParent('..')

        cmds.separator(height=4, style='none')

        list_w    = int((CONTENT_W - 34) / 2)
        arrow_w   = 34

        cmds.rowLayout(
            numberOfColumns=3,
            columnWidth3=[list_w, arrow_w, list_w],
            columnAttach3=["both", "both", "both"],
            columnOffset3=[0, 2, 2],
            backgroundColor=Colors.BG_PANEL
        )

        # Left: Available (locked on this layer)
        cmds.columnLayout(width=list_w, rowSpacing=0, backgroundColor=Colors.BG_PANEL)
        cmds.text(
            label=" Available", align='left', height=16,
            font='smallBoldLabelFont', backgroundColor=Colors.BG_PANEL
        )
        self.available_list = cmds.textScrollList(
            height=LIST_H,
            width=list_w,
            allowMultiSelection=True,
            backgroundColor=Colors.BG_DARK
        )
        cmds.setParent('..')

        # Middle: arrows
        cmds.columnLayout(width=arrow_w, rowSpacing=4, backgroundColor=Colors.BG_PANEL)
        cmds.separator(height=int(LIST_H / 2) - 26, style='none')
        cmds.button(
            label=u"→",
            width=arrow_w,
            height=24,
            backgroundColor=Colors.BG_ELEMENT,
            annotation="Add to Active (unlock on layer)",
            command=lambda x: self._on_add_influence()
        )
        cmds.button(
            label=u"←",
            width=arrow_w,
            height=24,
            backgroundColor=Colors.BG_ELEMENT,
            annotation="Remove from Active (lock on layer)",
            command=lambda x: self._on_remove_influence()
        )
        cmds.setParent('..')

        # Right: Active (unlocked on this layer)
        cmds.columnLayout(width=list_w, rowSpacing=0, backgroundColor=Colors.BG_PANEL)
        cmds.text(
            label=" Active", align='left', height=16,
            font='smallBoldLabelFont', backgroundColor=Colors.BG_PANEL
        )
        self.active_list = cmds.textScrollList(
            height=LIST_H,
            width=list_w,
            allowMultiSelection=True,
            backgroundColor=Colors.BG_DARK
        )
        cmds.setParent('..')

        cmds.setParent('..')  # 3-col rowLayout

        cmds.separator(height=4, style='none')
        cmds.button(
            label="Apply",
            height=BTN_H,
            backgroundColor=ACCENT,
            command=lambda x: self._on_apply_influence_changes()
        )
        cmds.separator(height=4, style='none')
        cmds.setParent('..')  # close _infl_layer_col — back to outer column

        # ── Divider ──────────────────────────────────────────────────────
        cmds.separator(height=8, style='none')
        cmds.separator(height=2, style='in')
        cmds.separator(height=8, style='none')

        # ── 2b: Move weights A → B (always enabled) ───────────────────────
        cmds.text(
            label=u"  Move Weights  A → B",
            align='left',
            font='smallBoldLabelFont',
            backgroundColor=Colors.BG_PANEL
        )
        cmds.separator(height=4, style='none')

        lbl_w2   = 82
        picker_w = CONTENT_W - lbl_w2 - 4

        for attr, label in [('src_joint_btn', 'Source Joint'), ('tgt_joint_btn', 'Target Joint')]:
            cmds.rowLayout(
                numberOfColumns=2,
                columnWidth2=[lbl_w2, picker_w],
                columnAttach2=["both", "both"],
                columnOffset2=[0, 4],
                backgroundColor=Colors.BG_PANEL
            )
            cmds.text(label=label, align='left', width=lbl_w2, backgroundColor=Colors.BG_PANEL)
            btn = cmds.button(
                label="Click to grab selected joint",
                height=BTN_H,
                backgroundColor=Colors.BG_ELEMENT,
                command=lambda x, a=attr: self._on_grab_joint(a)
            )
            setattr(self, attr, btn)
            cmds.setParent('..')
            cmds.separator(height=4, style='none')

        transfer_btn_w = 80
        status_w       = CONTENT_W - transfer_btn_w - 4
        cmds.rowLayout(
            numberOfColumns=2,
            columnWidth2=[status_w, transfer_btn_w],
            columnAttach2=["both", "both"],
            columnOffset2=[0, 4],
            backgroundColor=Colors.BG_PANEL
        )
        self.transfer_status = cmds.text(
            label="",
            align='left',
            width=status_w,
            backgroundColor=Colors.BG_PANEL
        )
        cmds.button(
            label="Transfer",
            height=BTN_H,
            width=transfer_btn_w,
            backgroundColor=ACCENT,
            command=lambda x: self._on_transfer_weights()
        )
        cmds.setParent('..')

        cmds.separator(height=4, style='none')
        cmds.setParent('..')  # close outer column
        cmds.setParent('..')  # close frameLayout
    # endregion

    # region [08] UI — Health Checks
    def _build_health_checks_section(self):
        cmds.frameLayout(
            label="  Health Checks",
            collapsable=True,
            collapse=True,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=PAD,
            marginHeight=0
        )
        cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_PANEL
        )
        cmds.separator(height=4, style='none')
        cmds.button(
            label="Run All Checks",
            height=BTN_H,
            backgroundColor=Colors.BG_ELEMENT,
            command=lambda x: self._on_run_all_checks()
        )
        cmds.separator(height=4, style='none')

        cmds.scrollLayout(
            childResizable=True,
            height=HC_LIST_H,
            backgroundColor=Colors.BG_DARK
        )
        cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_DARK
        )
        for check in HEALTH_CHECKS:
            self._build_health_check_row(check)
        cmds.setParent('..')  # inner columnLayout
        cmds.setParent('..')  # scrollLayout

        cmds.separator(height=4, style='none')
        cmds.setParent('..')
        cmds.setParent('..')

    def _build_health_check_row(self, check):
        has_n  = check.get("has_n", False)
        row_bg = Colors.BG_DARK

        cmds.rowLayout(
            numberOfColumns=4,
            columnWidth4=[HC_LABEL_W, HC_BTN_W, HC_ICON_W, HC_FIELD_W],
            columnAttach4=["both", "both", "both", "both"],
            columnOffset4=[0, 2, 2, 2],
            backgroundColor=row_bg,
            height=26
        )

        if has_n:
            # Label + inline N intField share the label column
            txt_w = HC_LABEL_W - 36
            cmds.rowLayout(
                numberOfColumns=2,
                columnWidth2=[txt_w, 34],
                columnAttach2=["both", "both"],
                columnOffset2=[0, 2],
                backgroundColor=row_bg,
                height=26
            )
            cmds.text(
                label=check["label"],
                align='left',
                annotation=check["tooltip"],
                backgroundColor=row_bg
            )
            self._hc_n_field = cmds.intField(
                value=4,
                minValue=1,
                maxValue=64,
                width=34,
                height=22,
                backgroundColor=Colors.BG_ELEMENT
            )
            cmds.setParent('..')  # back to outer 4-col rowLayout
        else:
            cmds.text(
                label=check["label"],
                align='left',
                width=HC_LABEL_W,
                annotation=check["tooltip"],
                backgroundColor=row_bg
            )

        cmds.button(
            label=u"▶",
            width=HC_BTN_W,
            height=22,
            backgroundColor=Colors.BG_ELEMENT,
            annotation=f"Run: {check['label']}",
            command=lambda x, c=check: self._run_single_check(c)
        )

        icon = cmds.text(
            label=u"□",   # ⬜ not yet run
            width=HC_ICON_W,
            height=22,
            align='center',
            backgroundColor=row_bg
        )
        self._hc_icons[check["id"]] = icon

        field = cmds.textField(
            text="",
            editable=True,
            width=HC_FIELD_W,
            height=22,
            backgroundColor=Colors.BG_ELEMENT,
            annotation="Select text here to copy names/IDs"
        )
        self._hc_fields[check["id"]] = field

        cmds.setParent('..')  # outer 4-col rowLayout
    # endregion

    # region [09] UI — Bake Pose
    def _build_bake_pose_section(self):
        cmds.frameLayout(
            label="  Bake Pose",
            collapsable=True,
            collapse=True,
            labelIndent=4,
            backgroundColor=Colors.BG_PANEL,
            marginWidth=PAD,
            marginHeight=0
        )
        self._bake_col = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0,
            backgroundColor=Colors.BG_PANEL
        )
        cmds.separator(height=4, style='none')
        cmds.text(
            label=u"⚠  Move the rig to the desired bind pose before running.\n"
                  "This redefines the bind pose to the current joint positions.",
            align='left',
            backgroundColor=Colors.BG_PANEL
        )
        cmds.separator(height=6, style='none')
        cmds.button(
            label="Bake Current Pose",
            height=BTN_H,
            backgroundColor=ACCENT,
            command=lambda x: self._on_bake_pose()
        )
        cmds.separator(height=4, style='none')
        self.bake_log = cmds.scrollField(
            editable=False,
            height=LOG_H,
            wordWrap=True,
            backgroundColor=Colors.BG_DARK,
            text=""
        )
        cmds.separator(height=4, style='none')
        cmds.setParent('..')
        cmds.setParent('..')
    # endregion

    # region [10] LOGIC — Weight Cleanup & Rebind
    def _on_clean_rebind(self):
        mesh = self.get_mesh()
        if not mesh:
            cmds.confirmDialog(title="NGBuddy", message="No valid mesh selected.", button=["OK"])
            return

        del_history   = cmds.checkBox(self.del_history_cb,     query=True, value=True)
        remove_unused = cmds.checkBox(self.remove_unused_cb,   query=True, value=True)
        force_norm    = cmds.checkBox(self.force_normalize_cb, query=True, value=True)

        confirm = cmds.confirmDialog(
            title="Clean & Rebind",
            message=(
                f"Detach and rebuild the skinCluster on '{mesh}'?\n"
                "NG Skin Tools layer data will be saved and restored.\n\nThis cannot be undone."
            ),
            button=["Continue", "Cancel"],
            defaultButton="Cancel",
            cancelButton="Cancel"
        )
        if confirm != "Continue":
            return

        self._clear_log(self.rebind_log)
        self.set_enabled(False)
        cmds.refresh()

        try:
            from core.ng_api import (
                get_skin_cluster, export_weights, restore_weights,
                refresh_ngst_ui, layers_already_initialized
            )
            import tempfile

            # 1. Save NGST layer data
            has_ngst = layers_already_initialized(mesh)
            tmp_path = None
            if has_ngst:
                fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="ngbuddy_rebind_")
                os.close(fd)
                if not export_weights(mesh, tmp_path):
                    self._log(self.rebind_log, "ERROR: Failed to save layer data — aborting.")
                    return
                from ngSkinTools2.api import Layers
                n = len(Layers(mesh).list())
                self._log(self.rebind_log, f"Layer data saved ({n} layers)")
            else:
                self._log(self.rebind_log, "No NGST layers — skipping save")

            # 2. Capture skinCluster settings before touching anything
            sc = get_skin_cluster(mesh)
            if not sc:
                self._log(self.rebind_log, "ERROR: No skinCluster found — aborting.")
                return
            joints    = cmds.skinCluster(sc, query=True, influence=True) or []
            max_infl  = cmds.skinCluster(sc, query=True, maximumInfluences=True) or 4
            norm_mode = cmds.skinCluster(sc, query=True, normalizeWeights=True) or 1

            # 3. Detach skinCluster first — must happen before delete history
            # (delete history also removes the skinCluster if it's still attached)
            cmds.skinCluster(sc, edit=True, unbind=True)
            self._log(self.rebind_log, "SkinCluster detached")

            # 4. Delete construction history (safe now — skinCluster already gone)
            if del_history:
                cmds.delete(mesh, constructionHistory=True)
                self._log(self.rebind_log, "History deleted")

            # 5. Rebind with same joints at current pose
            result = cmds.skinCluster(
                joints + [mesh],
                toSelectedBones=True,
                maximumInfluences=max_infl,
                normalizeWeights=norm_mode
            )
            new_sc = result[0] if result else None
            if not new_sc:
                self._log(self.rebind_log, "ERROR: Rebind failed — aborting.")
                return
            self._log(self.rebind_log, f"Rebound to {len(joints)} joints")

            # 6. Restore NGST layer data (exact copy, no wrapper layer)
            if has_ngst and tmp_path:
                if restore_weights(mesh, tmp_path):
                    self._log(self.rebind_log, "Layer data restored")
                else:
                    self._log(self.rebind_log, "WARNING: Layer data restore failed")
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            # 7. Remove unused influences
            if remove_unused:
                sc2      = get_skin_cluster(mesh)
                weighted = cmds.skinCluster(sc2, query=True, weightedInfluence=True) or []
                unused   = [j for j in joints if j not in weighted]
                for j in unused:
                    try:
                        cmds.skinCluster(sc2, edit=True, removeInfluence=j)
                    except Exception:
                        pass
                if unused:
                    self._log(self.rebind_log, f"Removed {len(unused)} unused influence(s)")

            # 8. Force normalize
            if force_norm:
                sc3 = get_skin_cluster(mesh)
                if sc3:
                    cmds.skinCluster(sc3, edit=True, normalizeWeights=1)
                    self._log(self.rebind_log, "Weights normalized")

            refresh_ngst_ui(mesh)
            self._log(self.rebind_log, "Done.")

        except Exception as e:
            import traceback
            self._log(self.rebind_log, f"ERROR: {e}")
            print(traceback.format_exc())
        finally:
            self.set_enabled(True)
    # endregion

    # region [11] LOGIC — Influence Management
    def refresh_layer_menu(self):
        """Rebuild the layer dropdown for the current mesh. Called when mesh selection changes."""
        if not self.layer_menu or not cmds.optionMenu(self.layer_menu, exists=True):
            return

        items = cmds.optionMenu(self.layer_menu, query=True, itemListLong=True) or []
        for item in items:
            cmds.deleteUI(item)
        self._layer_id_map = []

        mesh = self.get_mesh()
        if not mesh:
            cmds.menuItem(label=u"—  select mesh first  —", parent=self.layer_menu)
            self._refresh_dual_lists()
            return

        try:
            from ngSkinTools2.api import Layers
            api = Layers(mesh)
            if not api.is_enabled():
                cmds.menuItem(label=u"—  no NGST layers  —", parent=self.layer_menu)
                self._refresh_dual_lists()
                return

            all_layers = api.list()
            if not all_layers:
                cmds.menuItem(label=u"—  no layers  —", parent=self.layer_menu)
                self._refresh_dual_lists()
                return

            for layer in all_layers:
                cmds.menuItem(label=f"  {layer.name}", parent=self.layer_menu)
                self._layer_id_map.append(layer.id)

        except Exception as e:
            cmds.menuItem(label=u"—  error reading layers  —", parent=self.layer_menu)
            print(f"[NGBuddy] Error reading layers for influence menu: {e}")

        self._refresh_dual_lists()

    def _on_layer_changed(self):
        self._refresh_dual_lists()

    def _refresh_dual_lists(self):
        """
        Populate Available / Active lists for the selected layer.
        A joint is Active if it has any non-zero weight on this layer;
        Available if all its weights are zero (no contribution).
        This is weight-based so it stays accurate regardless of NGST lock API state.
        """
        for lst in [self.available_list, self.active_list]:
            if lst and cmds.textScrollList(lst, exists=True):
                cmds.textScrollList(lst, edit=True, removeAll=True)

        mesh = self.get_mesh()
        if not mesh or not self._layer_id_map:
            return

        try:
            from core.ng_api import get_skin_cluster
            from ngSkinTools2.api import Layers

            sc = get_skin_cluster(mesh)
            if not sc:
                return

            all_infl = cmds.skinCluster(sc, query=True, influence=True) or []

            sel_idx = cmds.optionMenu(self.layer_menu, query=True, select=True) - 1
            if sel_idx < 0 or sel_idx >= len(self._layer_id_map):
                return

            target_id = self._layer_id_map[sel_idx]
            layer = next(
                (l for l in Layers(mesh).list() if l.id == target_id),
                None
            )
            if not layer:
                return

            for i, infl in enumerate(all_infl):
                short   = infl.split('|')[-1]
                weights = layer.get_weights(i)
                has_weight = any(w > 1e-5 for w in (weights or []))
                target = self.active_list if has_weight else self.available_list
                cmds.textScrollList(target, edit=True, append=short)

        except Exception as e:
            print(f"[NGBuddy] Error refreshing influence lists: {e}")

    def _on_add_influence(self):
        """Move selected joints from Available → Active."""
        selected = cmds.textScrollList(self.available_list, query=True, selectItem=True) or []
        for item in selected:
            cmds.textScrollList(self.available_list, edit=True, removeItem=item)
            cmds.textScrollList(self.active_list,    edit=True, append=item)

    def _on_remove_influence(self):
        """Move selected joints from Active → Available."""
        selected = cmds.textScrollList(self.active_list, query=True, selectItem=True) or []
        for item in selected:
            cmds.textScrollList(self.active_list,    edit=True, removeItem=item)
            cmds.textScrollList(self.available_list, edit=True, append=item)

    def _on_apply_influence_changes(self):
        """
        Write the current Available/Active state onto the selected layer.
        Active → Available: zero out weights for that joint on this layer.
        Available → Active: leave weights at zero, user paints when ready.
        Also attempts to update the NGST locked_influences state on the layer.
        """
        mesh = self.get_mesh()
        if not mesh or not self._layer_id_map:
            cmds.confirmDialog(
                title="NGBuddy",
                message="No valid mesh or layer selected.",
                button=["OK"]
            )
            return

        try:
            from core.ng_api import get_skin_cluster
            from ngSkinTools2.api import Layers

            sc       = get_skin_cluster(mesh)
            all_infl = cmds.skinCluster(sc, query=True, influence=True) or []
            short_to_idx = {infl.split('|')[-1]: i for i, infl in enumerate(all_infl)}

            sel_idx = cmds.optionMenu(self.layer_menu, query=True, select=True) - 1
            if sel_idx < 0 or sel_idx >= len(self._layer_id_map):
                return

            target_id  = self._layer_id_map[sel_idx]
            layers_api = Layers(mesh)
            layer = next((l for l in layers_api.list() if l.id == target_id), None)
            if not layer:
                return

            available   = cmds.textScrollList(self.available_list, query=True, allItems=True) or []
            want_locked = {short_to_idx[j] for j in available if j in short_to_idx}
            have_locked = set(getattr(layer, 'locked_influences', None) or [])

            to_lock   = want_locked - have_locked   # Active → Available: zero weights
            to_unlock = have_locked - want_locked   # Available → Active: no weight added

            vert_count = cmds.polyEvaluate(mesh, vertex=True)
            zeros      = [0.0] * vert_count

            # Zero weights for every joint being moved to Available
            for idx in to_lock:
                layer.set_weights(idx, zeros)

            # Attempt to update the lock state on the layer object directly.
            # If NGSkinTools2 exposes locked_influences as a writable property this
            # will persist the lock flag; if not, the weight-zeroing above still
            # achieves the desired zero-contribution state.
            try:
                layer.locked_influences = list(want_locked)
            except (AttributeError, Exception):
                pass

            print(
                f"[NGBuddy] Layer '{layer.name}': "
                f"zeroed {len(to_lock)} influence(s), "
                f"unlocked {len(to_unlock)} influence(s)"
            )

            # Refresh both our lists and the NGST UI
            self._refresh_dual_lists()
            from core.ng_api import refresh_ngst_ui
            refresh_ngst_ui(mesh)

        except Exception as e:
            import traceback
            cmds.confirmDialog(title="NGBuddy", message=f"Apply failed:\n{e}", button=["OK"])
            print(traceback.format_exc())

    def _on_grab_joint(self, attr):
        sel = cmds.ls(selection=True, type='joint') or cmds.ls(selection=True, type='transform')
        if not sel:
            print("[NGBuddy] No joint selected")
            return
        joint = sel[0]
        short = joint.split('|')[-1]
        btn   = getattr(self, attr)
        if attr == 'src_joint_btn':
            self._src_joint = joint
        else:
            self._tgt_joint = joint
        cmds.button(btn, edit=True,
                    label=f"[joint]  {short}",
                    backgroundColor=Colors.BG_SURFACE)

    def _on_transfer_weights(self):
        if not self._src_joint or not self._tgt_joint:
            cmds.confirmDialog(
                title="NGBuddy",
                message="Set both Source and Target joints first.",
                button=["OK"]
            )
            return

        mesh = self.get_mesh()
        if not mesh:
            cmds.confirmDialog(title="NGBuddy", message="No valid mesh selected.", button=["OK"])
            return

        src_s = self._src_joint.split('|')[-1]
        tgt_s = self._tgt_joint.split('|')[-1]

        confirm = cmds.confirmDialog(
            title="Transfer Weights",
            message=(
                f"Transfer all weights from '{src_s}' to '{tgt_s}'?\n"
                "This cannot be undone."
            ),
            button=["Transfer", "Cancel"],
            defaultButton="Cancel",
            cancelButton="Cancel"
        )
        if confirm != "Transfer":
            return

        self.set_enabled(False)
        cmds.refresh()
        try:
            from core.ng_api import get_skin_cluster, refresh_ngst_ui
            from ngSkinTools2.api import Layers

            sc       = get_skin_cluster(mesh)
            all_infl = cmds.skinCluster(sc, query=True, influence=True) or []
            shorts   = [j.split('|')[-1] for j in all_infl]

            if src_s not in shorts or tgt_s not in shorts:
                cmds.confirmDialog(
                    title="NGBuddy",
                    message="One or both joints are not bound to this mesh's skinCluster.",
                    button=["OK"]
                )
                return

            a_idx      = shorts.index(src_s)
            b_idx      = shorts.index(tgt_s)
            vert_count = cmds.polyEvaluate(mesh, vertex=True)
            affected   = 0

            layers_api = Layers(mesh)
            if layers_api.is_enabled():
                for layer in layers_api.list():
                    a_w = list(layer.get_weights(a_idx))
                    b_w = list(layer.get_weights(b_idx))
                    if any(w > 0 for w in a_w):
                        affected += sum(1 for w in a_w if w > 0)
                        layer.set_weights(b_idx, [aw + bw for aw, bw in zip(a_w, b_w)])
                        layer.set_weights(a_idx, [0.0] * vert_count)
            else:
                # Raw skinCluster fallback — transfer per vertex so weight goes to B,
                # not redistributed proportionally across all other joints
                joint_a_full = all_infl[a_idx]
                joint_b_full = all_infl[b_idx]
                for v in range(vert_count):
                    vtx = f"{mesh}.vtx[{v}]"
                    w_a = cmds.skinPercent(sc, vtx, transform=joint_a_full, query=True)
                    if w_a and w_a > 1e-5:
                        w_b = cmds.skinPercent(sc, vtx, transform=joint_b_full, query=True) or 0.0
                        cmds.skinPercent(sc, vtx, transformValue=[
                            (joint_a_full, 0.0),
                            (joint_b_full, w_a + w_b),
                        ])
                        affected += 1

            refresh_ngst_ui(mesh)

            msg = f"Transferred {src_s} → {tgt_s}  ({affected:,} verts)"
            if self.transfer_status and cmds.text(self.transfer_status, exists=True):
                cmds.text(self.transfer_status, edit=True, label=msg)
            print(f"[NGBuddy] {msg}")

        except Exception as e:
            import traceback
            cmds.confirmDialog(title="NGBuddy", message=f"Transfer failed:\n{e}", button=["OK"])
            print(traceback.format_exc())
        finally:
            self.set_enabled(True)
    # endregion

    # region [12] LOGIC — Health Checks
    def _on_run_all_checks(self):
        for check in HEALTH_CHECKS:
            self._run_single_check(check)

    def _run_single_check(self, check):
        fn = getattr(self, check["fn"], None)
        if not fn:
            return
        try:
            passed, info = fn()
            self._set_check_result(check["id"], passed, info)
        except Exception as e:
            self._set_check_result(check["id"], False, f"Error: {e}")
            print(f"[NGBuddy] Health check '{check['id']}' raised: {e}")

    def _set_check_result(self, check_id, passed, info):
        icon  = self._hc_icons.get(check_id)
        field = self._hc_fields.get(check_id)
        if icon and cmds.text(icon, exists=True):
            cmds.text(icon, edit=True, label=u"✅" if passed else u"❌")
        if field and cmds.textField(field, exists=True):
            cmds.textField(field, edit=True, text=info)

    def _all_skinned_meshes(self):
        """Return [(transform, skinCluster)] for every skinned mesh in the scene."""
        from core.ng_api import get_skin_cluster
        result = []
        for shape in cmds.ls(type='mesh', noIntermediate=True) or []:
            parents = cmds.listRelatives(shape, parent=True, type='transform') or []
            if not parents:
                continue
            xform = parents[0]
            sc    = get_skin_cluster(xform)
            if sc:
                result.append((xform, sc))
        return result

    def _get_skin_weights(self, mesh, sc):
        """
        Return (weights_flat, n_verts, n_infl) via OpenMaya for speed.
        weights[v * n_infl + i] = weight of influence i on vertex v.
        Falls back to None if OpenMaya is unavailable.
        """
        try:
            import maya.api.OpenMaya as om
            import maya.api.OpenMayaAnim as oma

            sel = om.MSelectionList()
            sel.add(sc)
            fn_skin = oma.MFnSkinCluster(sel.getDependNode(0))

            sel2 = om.MSelectionList()
            sel2.add(mesh)
            dag = sel2.getDagPath(0)
            dag.extendToShape()

            n_verts = cmds.polyEvaluate(mesh, vertex=True)
            fn_comp = om.MFnSingleIndexedComponent()
            comp    = fn_comp.create(om.MFn.kMeshVertComponent)
            fn_comp.setCompleteData(n_verts)

            weights, n_infl = fn_skin.getWeights(dag, comp)
            return (weights, n_verts, int(n_infl))
        except Exception:
            return None

    def _hc_unskinned(self):
        unskinned = []
        for shape in cmds.ls(type='mesh', noIntermediate=True) or []:
            parents = cmds.listRelatives(shape, parent=True, type='transform') or []
            if not parents:
                continue
            xform   = parents[0]
            history = cmds.listHistory(xform) or []
            if not cmds.ls(history, type='skinCluster'):
                unskinned.append(xform)
        if not unskinned:
            return (True, "All meshes are skinned")
        return (False, f"{len(unskinned)} mesh(es): {', '.join(unskinned)}")

    def _hc_zero_weight(self):
        issues = []
        for xform, sc in self._all_skinned_meshes():
            result = self._get_skin_weights(xform, sc)
            if result:
                weights, n_verts, n_infl = result
                count = sum(
                    1 for v in range(n_verts)
                    if sum(weights[v * n_infl:(v + 1) * n_infl]) < 1e-4
                )
            else:
                n_verts = cmds.polyEvaluate(xform, vertex=True)
                count = sum(
                    1 for i in range(n_verts)
                    if sum(cmds.skinPercent(sc, f"{xform}.vtx[{i}]",
                                           query=True, value=True) or []) < 1e-4
                )
            if count:
                issues.append(f"{xform} ({count:,}v)")
        if not issues:
            return (True, "No zero-weight vertices")
        return (False, " | ".join(issues))

    def _hc_not_normalized(self):
        issues = []
        for xform, sc in self._all_skinned_meshes():
            result = self._get_skin_weights(xform, sc)
            if result:
                weights, n_verts, n_infl = result
                count = sum(
                    1 for v in range(n_verts)
                    if abs(sum(weights[v * n_infl:(v + 1) * n_infl]) - 1.0) > 1e-3
                )
            else:
                n_verts = cmds.polyEvaluate(xform, vertex=True)
                count = sum(
                    1 for i in range(n_verts)
                    if abs(sum(cmds.skinPercent(sc, f"{xform}.vtx[{i}]",
                                               query=True, value=True) or []) - 1.0) > 1e-3
                )
            if count:
                issues.append(f"{xform} ({count:,}v)")
        if not issues:
            return (True, "All weights sum to 1.0")
        return (False, " | ".join(issues))

    def _hc_unused_influences(self):
        issues = []
        for xform, sc in self._all_skinned_meshes():
            all_infl     = cmds.skinCluster(sc, query=True, influence=True) or []
            weighted     = set(cmds.skinCluster(sc, query=True, weightedInfluence=True) or [])
            unused_names = [j.split('|')[-1] for j in all_infl if j not in weighted]
            if unused_names:
                issues.append(f"{xform}: {', '.join(unused_names)}")
        if not issues:
            return (True, "No unused influences found")
        return (False, " | ".join(issues))

    def _hc_zero_infl_joints(self):
        seen     = {}   # joint_path -> True/False (has weight anywhere)
        for xform, sc in self._all_skinned_meshes():
            all_infl = cmds.skinCluster(sc, query=True, influence=True) or []
            weighted = set(cmds.skinCluster(sc, query=True, weightedInfluence=True) or [])
            for j in all_infl:
                if j not in seen:
                    seen[j] = False
                if j in weighted:
                    seen[j] = True
        zero = sorted(j.split('|')[-1] for j, has_w in seen.items() if not has_w)
        if not zero:
            return (True, "All bound joints have influence")
        return (False, ", ".join(zero))

    def _hc_over_n(self):
        n = 4
        if self._hc_n_field and cmds.intField(self._hc_n_field, exists=True):
            n = cmds.intField(self._hc_n_field, query=True, value=True)

        issues = []
        for xform, sc in self._all_skinned_meshes():
            result = self._get_skin_weights(xform, sc)
            if result:
                weights, n_verts, n_infl = result
                count = sum(
                    1 for v in range(n_verts)
                    if sum(1 for w in weights[v * n_infl:(v + 1) * n_infl] if w > 1e-4) > n
                )
            else:
                n_verts = cmds.polyEvaluate(xform, vertex=True)
                count = sum(
                    1 for i in range(n_verts)
                    if sum(1 for w in (
                        cmds.skinPercent(sc, f"{xform}.vtx[{i}]", query=True, value=True) or []
                    ) if w > 1e-4) > n
                )
            if count:
                issues.append(f"{xform} ({count:,}v)")
        if not issues:
            return (True, f"No verts exceed {n} influences")
        return (False, f"limit={n}: {' | '.join(issues)}")

    def _hc_missing_ngst(self):
        from core.ng_api import layers_already_initialized
        missing = [
            xform for xform, _ in self._all_skinned_meshes()
            if not layers_already_initialized(xform)
        ]
        if not missing:
            return (True, "All skinned meshes have NGST layer data")
        return (False, ", ".join(missing))
    # endregion

    # region [13] LOGIC — Bake Pose
    def _on_bake_pose(self):
        mesh = self.get_mesh()
        if not mesh:
            cmds.confirmDialog(title="NGBuddy", message="No valid mesh selected.", button=["OK"])
            return

        confirm = cmds.confirmDialog(
            title="Bake Current Pose",
            message=(
                f"Redefine the bind pose of '{mesh}' to the current joint positions?\n"
                "NG Skin Tools layer data will be saved and restored.\n\nThis cannot be undone."
            ),
            button=["Continue", "Cancel"],
            defaultButton="Cancel",
            cancelButton="Cancel"
        )
        if confirm != "Continue":
            return

        self._clear_log(self.bake_log)
        self.set_enabled(False)
        cmds.refresh()

        try:
            from core.ng_api import (
                get_skin_cluster, export_weights, restore_weights,
                refresh_ngst_ui, layers_already_initialized
            )
            import tempfile

            # 1. Save NGST layer data
            has_ngst = layers_already_initialized(mesh)
            tmp_path = None
            if has_ngst:
                fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="ngbuddy_bake_")
                os.close(fd)
                if not export_weights(mesh, tmp_path):
                    self._log(self.bake_log, "ERROR: Failed to save layer data — aborting.")
                    return
                from ngSkinTools2.api import Layers
                n = len(Layers(mesh).list())
                self._log(self.bake_log, f"Layer data saved ({n} layers)")
            else:
                self._log(self.bake_log, "No NGST layers — skipping save")

            # 2. Capture skinCluster settings
            sc = get_skin_cluster(mesh)
            if not sc:
                self._log(self.bake_log, "ERROR: No skinCluster found — aborting.")
                return
            joints    = cmds.skinCluster(sc, query=True, influence=True) or []
            max_infl  = cmds.skinCluster(sc, query=True, maximumInfluences=True) or 4
            norm_mode = cmds.skinCluster(sc, query=True, normalizeWeights=True) or 1

            # 3. Detach
            cmds.skinCluster(sc, edit=True, unbind=True)
            self._log(self.bake_log, "SkinCluster detached")

            # 4. Rebind at current pose — current joint positions become the new bind pose
            result = cmds.skinCluster(
                joints + [mesh],
                toSelectedBones=True,
                maximumInfluences=max_infl,
                normalizeWeights=norm_mode
            )
            new_sc = result[0] if result else None
            if not new_sc:
                self._log(self.bake_log, "ERROR: Rebind failed — aborting.")
                return
            self._log(self.bake_log, f"Bound at current pose ({len(joints)} joints)")

            # 5. Restore NGST layer data (exact copy, no wrapper layer)
            if has_ngst and tmp_path:
                if restore_weights(mesh, tmp_path):
                    self._log(self.bake_log, "Layer data restored")
                else:
                    self._log(self.bake_log, "WARNING: Layer data restore failed")
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            refresh_ngst_ui(mesh)
            self._log(self.bake_log, "Done.")

        except Exception as e:
            import traceback
            self._log(self.bake_log, f"ERROR: {e}")
            print(traceback.format_exc())
        finally:
            self.set_enabled(True)
    # endregion

    # region [14] HELPERS
    def _log(self, field, message):
        if not field or not cmds.scrollField(field, exists=True):
            return
        current = cmds.scrollField(field, query=True, text=True) or ""
        cmds.scrollField(field, edit=True, text=(current + "\n" + message).strip())

    def _clear_log(self, field):
        if field and cmds.scrollField(field, exists=True):
            cmds.scrollField(field, edit=True, text="")
    # endregion

    # region [15] ENABLE / DISABLE
    def set_enabled(self, enabled):
        for col in [self._rebind_col, self._infl_layer_col, self._bake_col]:
            if col and cmds.columnLayout(col, exists=True):
                cmds.columnLayout(col, edit=True, enable=enabled)
        # Health checks section is always enabled (scene-wide, not mesh-dependent)

        # Refresh the layer dropdown when the active mesh changes
        if enabled:
            current_mesh = self.get_mesh()
            if current_mesh != self._last_mesh:
                self._last_mesh = current_mesh
                self.refresh_layer_menu()
    # endregion
