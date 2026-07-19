# region [01] IMPORTS
import maya.cmds as cmds
from core.presets import LayerNode
# endregion

# region [02] CONSTANTS
try:
    from ngSkinTools2.api import MirrorOptions
    MIRROR_DIRECTION_MAP = {
        "positiveToNegative": MirrorOptions.directionPositiveToNegative,
        "negativeToPositive": MirrorOptions.directionNegativeToPositive,
        "flip":               MirrorOptions.directionFlip,
    }
except Exception:
    MIRROR_DIRECTION_MAP = {}
# endregion


# region [03] MESH VALIDATION
def get_skin_cluster(mesh):
    """Return the first skinCluster on a mesh, or None."""
    try:
        history = cmds.listHistory(mesh) or []
        clusters = cmds.ls(history, type="skinCluster")
        return clusters[0] if clusters else None
    except Exception as e:
        print(f"[NGBuddy] Error getting skinCluster for '{mesh}': {e}")
        return None


def is_valid_skinned_mesh(node):
    """
    Returns True if node is a transform with a mesh shape
    and at least one skinCluster.
    """
    try:
        if not cmds.objExists(node):
            return False
        shapes = cmds.listRelatives(node, shapes=True, type="mesh") or []
        if not shapes:
            return False
        return get_skin_cluster(node) is not None
    except Exception as e:
        print(f"[NGBuddy] Validation error for '{node}': {e}")
        return False
# endregion


# region [04] LAYER INITIALIZATION
def init_layers(mesh):
    """
    Initialize NGSkinTools2 layers on a mesh.
    Returns the Layers object or None on failure.
    """
    try:
        from ngSkinTools2 import api as ngst_api
        layers = ngst_api.init_layers(mesh)
        return layers
    except Exception as e:
        print(f"[NGBuddy] Error initializing layers on '{mesh}': {e}")
        return None


def layers_already_initialized(mesh):
    """Returns True if NGSkinTools2 layers are already set up on this mesh."""
    try:
        from ngSkinTools2.api import Layers
        return Layers(mesh).is_enabled()
    except Exception:
        return False
# endregion


# region [05] UI REFRESH
def refresh_ngst_ui(mesh):
    """
    Refresh the NGSkinTools2 UI after layer creation or modification.

    NGSkinTools2 has no public refresh API. The most reliable trigger
    is a deselect + reselect of the mesh, which forces NGSkinTools to
    re-query its target and fully redraw its layer list.
    """
    def _reselect():
        try:
            if mesh and cmds.objExists(mesh):
                cmds.select(mesh)
        except Exception as e:
            print(f"[NGBuddy] Warning: could not reselect mesh: {e}")

    def _deselect_then_reselect():
        try:
            cmds.select(clear=True)
        except Exception as e:
            print(f"[NGBuddy] Warning: could not deselect: {e}")
        # Second defer after the deselect so NGSkinTools sees both events
        cmds.evalDeferred(_reselect, lowestPriority=True)

    # First defer — let layer creation finish completely
    cmds.evalDeferred(_deselect_then_reselect, lowestPriority=True)
# endregion


# region [06] CREATE LAYERS FROM PRESET
def create_layers_from_preset(mesh, layer_nodes, parent_layer=None):
    """
    Recursively create NGSkinTools2 layers from a list of LayerNode objects.

    Args:
        mesh:         mesh node name
        layer_nodes:  list of LayerNode
        parent_layer: parent Layer object (None for root)

    Returns True on success, False on failure.
    """
    try:
        from ngSkinTools2.api import Layers
        layers_api = Layers(mesh)

        for node in layer_nodes:
            layer = layers_api.add(
                node.name,
                force_empty=True,
                parent=parent_layer
            )

            # Apply properties
            layer.opacity = node.opacity
            layer.enabled = node.enabled

            # Apply mirror effects
            direction = MIRROR_DIRECTION_MAP.get(
                node.mirror_direction,
                MirrorOptions.directionPositiveToNegative
            )
            layer.effects.configure_mirror(
                mirror_weights   = node.mirror_weights,
                mirror_mask      = node.mirror_mask,
                mirror_dq        = node.mirror_dq,
                mirror_direction = direction if (
                    node.mirror_weights or node.mirror_mask or node.mirror_dq
                ) else None
            )

            # Apply locked influences if specified
            if node.locked_influences:
                _apply_locked_influences(mesh, layer, node.locked_influences)

            # Recurse into children
            if node.children:
                create_layers_from_preset(mesh, node.children, parent_layer=layer)

        return True

    except Exception as e:
        print(f"[NGBuddy] Error creating layers on '{mesh}': {e}")
        return False
# endregion


# region [07] LOCKED INFLUENCES
def _apply_locked_influences(mesh, layer, locked_influence_names):
    """
    Lock specific influences on a layer so they have no effect.
    locked_influence_names: list of joint name strings to lock out.
    """
    try:
        skin_cluster = get_skin_cluster(mesh)
        if not skin_cluster:
            return

        # Get all influences on the skinCluster
        all_influences = cmds.skinCluster(skin_cluster, query=True, influence=True) or []

        # Build index list of influences to lock
        locked_indices = [
            i for i, inf in enumerate(all_influences)
            if inf in locked_influence_names
        ]

        if not locked_indices:
            return

        # Set those influence weights to zero on this layer via the plugin command
        from ngSkinTools2.api import plugin
        for idx in locked_indices:
            plugin.ngst2Layers(
                mesh,
                edit=True,
                layerId=layer.id,
                lockInfluence=idx
            )

    except Exception as e:
        print(f"[NGBuddy] Warning: could not lock influences on layer '{layer.name}': {e}")


# endregion


# region [08] READ LAYERS FROM MESH
def read_layers_from_mesh(mesh):
    """
    Read existing NGSkinTools2 layers from a mesh and return
    as a list of LayerNode objects preserving hierarchy.
    """
    try:
        from ngSkinTools2.api import Layers
        layers_api = Layers(mesh)
        all_layers = layers_api.list()

        def build_node(layer):
            # Read mirror direction safely
            try:
                from ngSkinTools2.api import MirrorOptions
                dir_map = {
                    MirrorOptions.directionPositiveToNegative: "positiveToNegative",
                    MirrorOptions.directionNegativeToPositive: "negativeToPositive",
                    MirrorOptions.directionFlip:               "flip",
                }
                mirror_dir = dir_map.get(layer.effects.mirror_direction, "positiveToNegative")
            except Exception:
                mirror_dir = "positiveToNegative"

            node = LayerNode(
                name             = layer.name,
                opacity          = layer.opacity,
                enabled          = layer.enabled,
                index            = layer.index,
                mirror_weights   = layer.effects.mirror_weights,
                mirror_mask      = layer.effects.mirror_mask,
                mirror_dq        = layer.effects.mirror_dq,
                mirror_direction = mirror_dir,
                use_dq           = getattr(layer, 'use_dual_quaternion', False),
                locked_influences= list(getattr(layer, 'locked_influences', []) or []),
            )
            for child in layer.children:
                node.children.append(build_node(child))
            return node

        root_layers = [l for l in all_layers if l.parent is None]
        return [build_node(l) for l in root_layers]

    except Exception as e:
        print(f"[NGBuddy] Error reading layers from '{mesh}': {e}")
        return []
# endregion


# region [09] WEIGHT EXPORT / IMPORT
def restore_weights(mesh, filepath):
    """
    Restore NGST layer data onto a freshly rebound mesh from a prior export.

    Uses NGSkinTools2 native import_json with vertex-ID matching (vertex indices
    are unchanged after unbind+rebind on the same mesh) and name-based influence
    mapping. Produces an exact copy of the original layer hierarchy with no wrapper
    layer added on top.

    Distinct from import_weights() which wraps layers in IMPORTED_WEIGHTS_N and is
    intended for the Copy & Paste workflow.

    Returns True on success.
    """
    import os
    if not os.path.exists(filepath):
        print(f"[NGBuddy] Restore file not found: {filepath}")
        return False
    try:
        from ngSkinTools2 import api as ngst_api
        from ngSkinTools2.api import InfluenceMappingConfig, VertexTransferMode, Layers

        layers_api = Layers(mesh)
        if layers_api.is_enabled():
            layers_api.clear()

        infl_config = InfluenceMappingConfig()
        infl_config.use_name_matching     = True
        infl_config.use_distance_matching = False
        infl_config.use_label_matching    = False

        ngst_api.import_json(
            mesh,
            file=filepath,
            vertex_transfer_mode=VertexTransferMode.vertexId,
            influences_mapping_config=infl_config,
        )
        print(f"[NGBuddy] Layer data restored: {filepath}")
        return True
    except Exception as e:
        print(f"[NGBuddy] Error restoring weights for '{mesh}': {e}")
        return False


def export_weights(mesh, filepath):
    """
    Export NGSkinTools2 layer weights for a mesh to a JSON file.
    Uses NGSkinTools2 native export — file= keyword is required by the API.
    Returns True on success.
    """
    try:
        from ngSkinTools2 import api as ngst_api
        ngst_api.export_json(mesh, file=filepath)
        print(f"[NGBuddy] Weights exported: {filepath}")
        return True
    except Exception as e:
        print(f"[NGBuddy] Error exporting weights for '{mesh}': {e}")
        return False


def import_weights(mesh, filepath):
    """
    Import weights from an NGSkinTools2 JSON export file onto a mesh.

    Manually parses the JSON to create layers under a new IMPORTED_WEIGHTS_N
    parent layer at the bottom of the stack. Existing layers are never touched.

    JSON structure (from export_json):
    - influences: list of {index, path, pivot, ...}
    - layers: list of {id, name, parentId, children, influences: {"0": [...], "1": [...]}}

    Layer order: bottom = imported weights (starting point), top = hand work.
    Returns True on success.
    """
    import os
    import json

    if not os.path.exists(filepath):
        print(f"[NGBuddy] Weight file not found: {filepath}")
        return False

    skin = get_skin_cluster(mesh)
    if not skin:
        print(f"[NGBuddy] No skinCluster on '{mesh}' — cannot import weights")
        return False

    try:
        from ngSkinTools2.api import Layers, init_layers, NamedPaintTarget

        print(f"[NGBuddy] Reading weight file: {filepath}")
        with open(filepath, 'r') as f:
            data = json.load(f)
        print(f"[NGBuddy] File loaded — layers: {len(data.get('layers', []))}, influences: {len(data.get('influences', []))}")

        # Build influence map: exported logical index -> joint path
        # influences is a LIST of {index, path, pivot, ...}
        influence_map = {}
        for inf_data in data.get('influences', []):
            idx  = inf_data.get('index')
            path = inf_data.get('path', '')
            if idx is not None:
                influence_map[idx] = path

        # Build scene map: joint path/name -> skinCluster logical index
        all_influences = cmds.skinCluster(skin, query=True, influence=True) or []
        scene_inf_map  = {}
        for i, inf in enumerate(all_influences):
            scene_inf_map[inf] = i
            # also map short name in case paths differ
            scene_inf_map[inf.split('|')[-1]] = i

        # Init layers if not already
        layers_api = Layers(mesh)
        if not layers_api.is_enabled():
            init_layers(mesh)
            layers_api = Layers(mesh)

        # Find next available IMPORTED_WEIGHTS_N name
        existing   = [l.name for l in layers_api.list()]
        n          = 1
        while f"IMPORTED_WEIGHTS_{n}" in existing:
            n += 1
        master_name = f"IMPORTED_WEIGHTS_{n}"

        # Create master layer at root level — sits at bottom of stack
        master_layer         = layers_api.add(master_name, force_empty=True)
        master_layer.opacity = 1.0
        master_layer.enabled = True

        # layers list is flat with parentId references
        # We need to create them in order, tracking id -> Layer object
        # Only create layers whose parentId is null (root) or already created
        layers_list = data.get('layers', [])

        # Map exported id -> Layer object as we create them
        created = {}   # exported_id -> Layer object

        # Build id -> layer_data lookup for fast child resolution
        id_to_data = {l['id']: l for l in layers_list}

        def create_layer(layer_data, parent_layer):
            """Create a single layer under parent_layer and recurse into children."""
            name    = layer_data.get('name', 'layer')
            opacity = layer_data.get('opacity', 1.0)
            enabled = layer_data.get('enabled', True)
            exp_id  = layer_data.get('id')

            print(f"[NGBuddy] Creating layer '{name}' (id={exp_id}) under '{parent_layer.name}'")

            # Add layer — parent is passed directly, NGSkinTools2 sets it via property
            layer         = layers_api.add(name, force_empty=True, parent=parent_layer)
            layer.opacity = opacity
            layer.enabled = enabled

            if exp_id is not None:
                created[exp_id] = layer

            # Set per-influence weights
            # influences is a dict: {"0": [w0,w1,...], "1": [...]}
            influences_dict = layer_data.get('influences', {})
            has_weights = False
            for idx_str, weights in influences_dict.items():
                if not weights:
                    continue
                # Filter out all-zero weight lists — no need to set them
                if all(w == 0.0 for w in weights):
                    continue
                has_weights = True
                logical_idx = int(idx_str)
                joint_path  = influence_map.get(logical_idx, '')
                joint_name  = joint_path.split('|')[-1] if joint_path else ''

                scene_idx = scene_inf_map.get(joint_path)
                if scene_idx is None:
                    scene_idx = scene_inf_map.get(joint_name)
                if scene_idx is None:
                    print(f"[NGBuddy]   Warning: '{joint_path}' not found in scene skinCluster, skipping")
                    continue

                layer.set_weights(scene_idx, weights)

            if has_weights:
                print(f"[NGBuddy]   Set weights for {len(influences_dict)} influences")

            # Set mask if present
            mask = layer_data.get('mask')
            if mask and any(v != 0.0 for v in mask):
                layer.set_weights(NamedPaintTarget.MASK, mask)

            # Recurse into children using the id lookup
            child_ids = layer_data.get('children', [])
            for child_id in child_ids:
                child_data = id_to_data.get(child_id)
                if child_data:
                    create_layer(child_data, layer)
                else:
                    print(f"[NGBuddy]   Warning: child id {child_id} not found in layers list")

        # Create root layers (parentId is null) — children handled recursively
        # Filter out any IMPORTED_WEIGHTS layers that may have been baked into the export
        layers_list = [l for l in layers_list if not l.get('name', '').startswith('IMPORTED_WEIGHTS')]
        root_layers = [l for l in layers_list if l.get('parentId') is None]
        layer_count = len(layers_list)

        print(f"[NGBuddy] Found {len(root_layers)} root layers, {layer_count} total")

        for layer_data in root_layers:
            create_layer(layer_data, master_layer)

        refresh_ngst_ui(mesh)
        print(f"[NGBuddy] Created '{master_name}' with {layer_count} layers on '{mesh}'")
        return True

    except Exception as e:
        import traceback
        print(f"[NGBuddy] Error importing weights for '{mesh}': {e}")
        print(traceback.format_exc())
        return False
# endregion