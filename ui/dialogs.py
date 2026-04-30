# region [01] IMPORTS
import maya.cmds as cmds
from style.colors import Colors
from style.dimensions import Dimensions
# endregion


# region [02] SAVE LAYER PRESET DIALOG
def show_save_layer_dialog(preset_path, on_save):
    """
    Show a small dialog to name and save a new layer preset leaf.

    Args:
        preset_path: list of strings representing the current tree path
                     e.g. ["Creature", "Biped", "Biped-tail"]
        on_save:     callable(name) called with the entered name on confirm
    """
    win = "NGBuddySaveLayerDialog"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)

    cmds.window(
        win,
        title="Save Layer Preset",
        widthHeight=(320, 160),
        sizeable=False,
        resizeToFitChildren=True
    )

    cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=Dimensions.ROW_SPACING,
        backgroundColor=Colors.BG_MAIN,
        marginWidth=Dimensions.PADDING_OUTER,
        marginHeight=Dimensions.PADDING_OUTER
    )

    # Show the current path as context
    path_str = " > ".join(preset_path) if preset_path else "Root"
    cmds.text(
        label=f"Path:  {path_str}",
        align='left',
        backgroundColor=Colors.BG_MAIN
    )

    cmds.separator(height=6, style='none')

    cmds.text(
        label="New preset name:",
        align='left',
        backgroundColor=Colors.BG_MAIN
    )

    name_field = cmds.textField(
        height=Dimensions.INPUT_HEIGHT,
        backgroundColor=Colors.BG_ELEMENT,
        placeholderText="e.g. Body, Face, Arms..."
    )

    cmds.separator(height=6, style='none')

    # Buttons
    cmds.rowLayout(
        numberOfColumns=2,
        adjustableColumn=1,
        columnWidth2=[180, 100],
        columnAttach2=["both", "both"],
        columnOffset2=[0, 4]
    )

    cmds.button(
        label="Save",
        height=Dimensions.BTN_PRIMARY,
        backgroundColor=Colors.ACCENT_BUILD,
        command=lambda x: _confirm_save_layer(win, name_field, on_save)
    )
    cmds.button(
        label="Cancel",
        height=Dimensions.BTN_PRIMARY,
        backgroundColor=Colors.BG_ELEMENT,
        command=lambda x: cmds.deleteUI(win)
    )
    cmds.setParent('..')
    cmds.setParent('..')

    cmds.showWindow(win)


def _confirm_save_layer(win, name_field, on_save):
    name = cmds.textField(name_field, query=True, text=True).strip()
    if not name:
        cmds.confirmDialog(
            title="Invalid Name",
            message="Please enter a preset name.",
            button=["OK"]
        )
        return
    cmds.deleteUI(win)
    on_save(name)
# endregion


# region [03] SAVE WEIGHT PRESET DIALOG
def show_save_weight_dialog(mesh, on_save):
    """
    Show a dialog to export current NGSkinTools weights and save as a preset.

    Args:
        mesh:     currently selected mesh name
        on_save:  callable(name, export_path) called on confirm
    """
    win = "NGBuddySaveWeightDialog"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)

    cmds.window(
        win,
        title="Save Weight Preset",
        widthHeight=(320, 180),
        sizeable=False,
        resizeToFitChildren=True
    )

    cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=Dimensions.ROW_SPACING,
        backgroundColor=Colors.BG_MAIN,
        marginWidth=Dimensions.PADDING_OUTER,
        marginHeight=Dimensions.PADDING_OUTER
    )

    cmds.text(
        label=f"Mesh:  {mesh}",
        align='left',
        backgroundColor=Colors.BG_MAIN
    )

    cmds.separator(height=6, style='none')

    cmds.text(
        label="Weight preset name:",
        align='left',
        backgroundColor=Colors.BG_MAIN
    )

    name_field = cmds.textField(
        height=Dimensions.INPUT_HEIGHT,
        backgroundColor=Colors.BG_ELEMENT,
        placeholderText="e.g. FaceRig_v1, Biped_base..."
    )

    cmds.separator(height=6, style='none')

    cmds.text(
        label="NGSkinTools will export current weights to a temp file.",
        align='left',
        backgroundColor=Colors.BG_MAIN
    )

    cmds.separator(height=6, style='none')

    cmds.rowLayout(
        numberOfColumns=2,
        adjustableColumn=1,
        columnWidth2=[180, 100],
        columnAttach2=["both", "both"],
        columnOffset2=[0, 4]
    )
    cmds.button(
        label="Export & Save",
        height=Dimensions.BTN_PRIMARY,
        backgroundColor=Colors.ACCENT_BUILD,
        command=lambda x: _confirm_save_weight(win, name_field, mesh, on_save)
    )
    cmds.button(
        label="Cancel",
        height=Dimensions.BTN_PRIMARY,
        backgroundColor=Colors.BG_ELEMENT,
        command=lambda x: cmds.deleteUI(win)
    )
    cmds.setParent('..')
    cmds.setParent('..')

    cmds.showWindow(win)


def _confirm_save_weight(win, name_field, mesh, on_save):
    import tempfile
    import os

    name = cmds.textField(name_field, query=True, text=True).strip()
    if not name:
        cmds.confirmDialog(
            title="Invalid Name",
            message="Please enter a preset name.",
            button=["OK"]
        )
        return

    # Export NGSkinTools weights to a temp file
    try:
        from ngSkinTools2 import api as ngst_api
        tmp_path = os.path.join(tempfile.gettempdir(), f"ngbuddy_weight_export_{name}.json")
        ngst_api.export_json(mesh, tmp_path)
    except Exception as e:
        cmds.confirmDialog(
            title="Export Failed",
            message=f"NGSkinTools export failed:\n{e}",
            button=["OK"]
        )
        return

    cmds.deleteUI(win)
    on_save(name, tmp_path)
# endregion


# region [04] DELETE CONFIRM DIALOG
def show_delete_confirm(name, on_confirm):
    """Generic delete confirmation dialog."""
    result = cmds.confirmDialog(
        title="Delete Preset",
        message=f"Delete '{name}'?\nThis cannot be undone.",
        button=["Delete", "Cancel"],
        defaultButton="Cancel",
        cancelButton="Cancel",
        dismissString="Cancel"
    )
    if result == "Delete":
        on_confirm()
# endregion