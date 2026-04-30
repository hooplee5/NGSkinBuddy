# region [01] IMPORTS
import os
import json
# endregion

# region [02] CONSTANTS
def _find_repo_root():
    path = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        if os.path.exists(os.path.join(path, "main.py")):
            return path
        path = os.path.dirname(path)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_REPO_ROOT = _find_repo_root()
PRESET_DIR = os.path.join(_REPO_ROOT, "data", "presets")
WEIGHT_DIR = os.path.join(_REPO_ROOT, "data", "weights")
# endregion


# region [03] LAYER NODE
class LayerNode:
    """Represents a single layer or layer group in a preset tree."""

    def __init__(self,
                 name="",
                 opacity=1.0,
                 enabled=True,
                 index=0,
                 locked_influences=None,
                 mirror_weights=False,
                 mirror_mask=False,
                 mirror_dq=False,
                 mirror_direction="positiveToNegative",
                 use_dq=False,
                 children=None):
        self.name              = name
        self.opacity           = opacity
        self.enabled           = enabled
        self.index             = index
        self.locked_influences = locked_influences or []
        self.mirror_weights    = mirror_weights
        self.mirror_mask       = mirror_mask
        self.mirror_dq         = mirror_dq
        self.mirror_direction  = mirror_direction
        self.use_dq            = use_dq
        self.children          = children or []

    def to_dict(self):
        return {
            "name":              self.name,
            "opacity":           self.opacity,
            "enabled":           self.enabled,
            "index":             self.index,
            "locked_influences": self.locked_influences,
            "mirror_weights":    self.mirror_weights,
            "mirror_mask":       self.mirror_mask,
            "mirror_dq":         self.mirror_dq,
            "mirror_direction":  self.mirror_direction,
            "use_dq":            self.use_dq,
            "children":          [c.to_dict() for c in self.children]
        }

    @classmethod
    def from_dict(cls, data):
        children = [cls.from_dict(c) for c in data.get("children", [])]
        return cls(
            name              = data.get("name", ""),
            opacity           = data.get("opacity", 1.0),
            enabled           = data.get("enabled", True),
            index             = data.get("index", 0),
            locked_influences = data.get("locked_influences", []),
            mirror_weights    = data.get("mirror_weights", False),
            mirror_mask       = data.get("mirror_mask", False),
            mirror_dq         = data.get("mirror_dq", False),
            mirror_direction  = data.get("mirror_direction", "positiveToNegative"),
            use_dq            = data.get("use_dq", False),
            children          = children
        )
# endregion


# region [04] PRESET NODE
class PresetNode:
    """
    A node in the preset category tree.
    Leaf nodes (no children) carry layer data.
    Branch nodes (with children) are categories/subcategories.
    """

    def __init__(self, name="", children=None, layers=None):
        self.name     = name
        self.children = children or []
        self.layers   = layers   or []

    @property
    def is_leaf(self):
        return len(self.children) == 0

    def to_dict(self):
        data = {"name": self.name}
        if self.children:
            data["children"] = [c.to_dict() for c in self.children]
        if self.layers:
            data["layers"] = [l.to_dict() for l in self.layers]
        return data

    @classmethod
    def from_dict(cls, data):
        children = [cls.from_dict(c) for c in data.get("children", [])]
        layers   = [LayerNode.from_dict(l) for l in data.get("layers", [])]
        return cls(
            name     = data.get("name", ""),
            children = children,
            layers   = layers
        )
# endregion


# region [05] PRESET FILE
class Preset:
    """Top-level preset file. Contains a category tree of PresetNodes."""

    def __init__(self, name="", description="", author="", version="1.0", root=None):
        self.name        = name
        self.description = description
        self.author      = author
        self.version     = version
        self.root        = root or PresetNode(name=name)

    def to_dict(self):
        return {
            "name":        self.name,
            "description": self.description,
            "author":      self.author,
            "version":     self.version,
            "root":        self.root.to_dict()
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name        = data.get("name", ""),
            description = data.get("description", ""),
            author      = data.get("author", ""),
            version     = data.get("version", "1.0"),
            root        = PresetNode.from_dict(data.get("root", {}))
        )
# endregion


# region [06] PRESET MANAGER
class PresetManager:
    """Handles loading and saving preset JSON files from the presets directory."""

    def __init__(self, preset_dir=None):
        self.preset_dir = preset_dir or PRESET_DIR
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(self.preset_dir):
            os.makedirs(self.preset_dir)

    def list_presets(self):
        """Return list of preset file names (without extension)."""
        if not os.path.exists(self.preset_dir):
            return []
        return [
            os.path.splitext(f)[0]
            for f in os.listdir(self.preset_dir)
            if f.endswith(".json")
        ]

    def load(self, preset_name):
        """Load a preset by name. Returns Preset object or None on failure."""
        path = os.path.join(self.preset_dir, f"{preset_name}.json")
        if not os.path.exists(path):
            print(f"[NGBuddy] Preset not found: {path}")
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return Preset.from_dict(data)
        except Exception as e:
            print(f"[NGBuddy] Error loading preset '{preset_name}': {e}")
            return None

    def save(self, preset):
        """Save a Preset object to disk. Returns True on success."""
        path = os.path.join(self.preset_dir, f"{preset.name}.json")
        try:
            with open(path, "w") as f:
                json.dump(preset.to_dict(), f, indent=2)
            print(f"[NGBuddy] Preset saved: {path}")
            return True
        except Exception as e:
            print(f"[NGBuddy] Error saving preset '{preset.name}': {e}")
            return False

    def delete(self, preset_name):
        """Delete a preset file by name. Returns True on success."""
        path = os.path.join(self.preset_dir, f"{preset_name}.json")
        if not os.path.exists(path):
            return False
        try:
            os.remove(path)
            return True
        except Exception as e:
            print(f"[NGBuddy] Error deleting preset '{preset_name}': {e}")
            return False
# endregion


# region [07] WEIGHT MANAGER
class WeightManager:
    """
    Manages NGSkinTools2 weight export files in data/weights/.

    One file per preset — we embed NGBuddy metadata directly into the
    NGSkinTools export JSON under the key 'ngbuddy_meta'. No sidecar files.
    """

    def __init__(self, weight_dir=None):
        self.weight_dir = weight_dir or WEIGHT_DIR
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(self.weight_dir):
            os.makedirs(self.weight_dir)

    def weight_path(self, name):
        """Return the full path for a weight preset file."""
        return os.path.join(self.weight_dir, f"{name}.json")

    def list_weights(self):
        """
        Return list of (name, meta) tuples for all weight presets.
        Structured as a tree via meta['tree'] if present, else flat list.
        """
        if not os.path.exists(self.weight_dir):
            return []
        names = []
        for f in sorted(os.listdir(self.weight_dir)):
            if not f.endswith(".json"):
                continue
            path = os.path.join(self.weight_dir, f)
            try:
                with open(path, "r") as fh:
                    data = json.load(fh)
                # Only count files that have our metadata key
                if "ngbuddy_meta" in data:
                    names.append(os.path.splitext(f)[0])
            except Exception:
                continue
        return names

    def load_meta(self, name):
        """Load NGBuddy metadata embedded in the weight file."""
        path = self.weight_path(name)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return data.get("ngbuddy_meta", {})
        except Exception as e:
            print(f"[NGBuddy] Error loading weight meta '{name}': {e}")
            return None

    def save_meta(self, name, mesh, description="", tree_path=None):
        """
        Embed NGBuddy metadata into an existing weight file.
        tree_path: list of strings representing category path e.g. ['Creature', 'Biped']
        """
        path = self.weight_path(name)
        if not os.path.exists(path):
            print(f"[NGBuddy] Cannot save meta — weight file not found: {path}")
            return False
        try:
            with open(path, "r") as f:
                data = json.load(f)
            data["ngbuddy_meta"] = {
                "name":        name,
                "mesh":        mesh,
                "description": description,
                "tree_path":   tree_path or [],
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[NGBuddy] Error saving weight meta '{name}': {e}")
            return False

    def get_weight_tree(self):
        """
        Build a nested tree structure from all weight presets using their tree_path metadata.
        Returns a dict tree: {category: {subcategory: [name, ...], ...}, ...}
        Flat presets (no tree_path) go under '__root__'.
        """
        tree = {}
        for name in self.list_weights():
            meta = self.load_meta(name) or {}
            path = meta.get("tree_path", [])
            node = tree
            for part in path:
                node = node.setdefault(part, {})
            node.setdefault("__presets__", []).append(name)
        return tree

    def build_menu_items(self, max_label_length=40):
        """
        Return a flat list of (label, name) for populating optionMenu.
        Each label shows the full path: Category/Subcategory/name
        If the full path is too long, truncate from the left so the
        preset name is always visible: ...Subcategory/name
        Categories are walked depth-first before presets at each level.
        """
        items = []

        def walk(node, path_parts):
            # Walk subcategories first (depth-first), then presets at this level
            categories = {k: v for k, v in node.items()
                          if k != "__presets__" and isinstance(v, dict)}
            for key in sorted(categories):
                walk(categories[key], path_parts + [key])

            for name in sorted(node.get("__presets__", [])):
                parts = path_parts + [name]
                full_label = "/".join(parts)
                if len(full_label) > max_label_length:
                    full_label = "..." + full_label[-(max_label_length - 3):]
                items.append((full_label, name))

        walk(self.get_weight_tree(), [])
        return items

    def delete(self, name):
        """Delete a weight preset file. Returns True on success."""
        path = self.weight_path(name)
        if not os.path.exists(path):
            return False
        try:
            os.remove(path)
            return True
        except Exception as e:
            print(f"[NGBuddy] Error deleting weight preset '{name}': {e}")
            return False

    def open_folder(self):
        """Open the weights folder in Windows Explorer."""
        import subprocess
        subprocess.Popen(f'explorer "{os.path.normpath(self.weight_dir)}"')
# endregion