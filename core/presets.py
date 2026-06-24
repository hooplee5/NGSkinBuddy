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

    File naming encodes the full category path:
        tree_path=['Creature', 'Biped'], name='legs'
        -> 'Creature__Biped__legs.json'

    This means two presets with the same name but different categories
    are always stored as distinct files. The filename is the source of
    truth for the tree path — metadata mirrors it for readability.

    One file per preset — we embed NGBuddy metadata directly into the
    NGSkinTools export JSON under the key 'ngbuddy_meta'. No sidecar files.
    """

    SEPARATOR = "__"

    def __init__(self, weight_dir=None):
        self.weight_dir = weight_dir or WEIGHT_DIR
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(self.weight_dir):
            os.makedirs(self.weight_dir)

    # ------------------------------------------------------------------
    # Stem helpers
    # ------------------------------------------------------------------

    def make_stem(self, name, tree_path=None):
        """
        Build the filename stem (no extension) from a name + optional path.

        Examples:
            make_stem('legs')                          -> 'legs'
            make_stem('legs', ['Creature', 'Biped'])   -> 'Creature__Biped__legs'
        """
        if tree_path:
            parts = list(tree_path) + [name]
        else:
            parts = [name]
        return self.SEPARATOR.join(parts)

    def decode_stem(self, stem):
        """
        Split a stem back into (tree_path, display_name).

        Examples:
            decode_stem('legs')                  -> ([], 'legs')
            decode_stem('Creature__Biped__legs') -> (['Creature', 'Biped'], 'legs')
        """
        parts = stem.split(self.SEPARATOR)
        return parts[:-1], parts[-1]

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def weight_path(self, name, tree_path=None):
        """
        Return the full filesystem path for a weight preset.

        Pass tree_path when saving a new file so the path is encoded
        into the filename. For lookups by existing stem, use
        weight_path_from_stem() instead.
        """
        stem = self.make_stem(name, tree_path)
        return os.path.join(self.weight_dir, f"{stem}.json")

    def weight_path_from_stem(self, stem):
        """Return the full path for an already-encoded stem."""
        return os.path.join(self.weight_dir, f"{stem}.json")

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_weights(self):
        """
        Return a list of stems for all valid weight presets on disk.
        A valid file must contain the 'ngbuddy_meta' key.

        Stems encode the full path, e.g. 'Creature__Biped__legs'.
        """
        if not os.path.exists(self.weight_dir):
            return []
        stems = []
        for f in sorted(os.listdir(self.weight_dir)):
            if not f.endswith(".json"):
                continue
            path = os.path.join(self.weight_dir, f)
            try:
                with open(path, "r") as fh:
                    data = json.load(fh)
                if "ngbuddy_meta" in data:
                    stems.append(os.path.splitext(f)[0])
            except Exception:
                continue
        return stems

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def load_meta(self, stem):
        """Load NGBuddy metadata embedded in the weight file for the given stem."""
        path = self.weight_path_from_stem(stem)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return data.get("ngbuddy_meta", {})
        except Exception as e:
            print(f"[NGBuddy] Error loading weight meta '{stem}': {e}")
            return None

    def save_meta(self, stem, mesh, description="", tree_path=None):
        """
        Embed NGBuddy metadata into an existing weight file.

        stem:      encoded filename stem, e.g. 'Creature__Biped__legs'
        tree_path: list of category strings, e.g. ['Creature', 'Biped']
        """
        path = self.weight_path_from_stem(stem)
        if not os.path.exists(path):
            print(f"[NGBuddy] Cannot save meta — weight file not found: {path}")
            return False
        try:
            with open(path, "r") as f:
                data = json.load(f)

            _, display_name = self.decode_stem(stem)
            data["ngbuddy_meta"] = {
                "name":        display_name,
                "stem":        stem,
                "mesh":        mesh,
                "description": description,
                "tree_path":   tree_path or [],
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[NGBuddy] Error saving weight meta '{stem}': {e}")
            return False

    # ------------------------------------------------------------------
    # Tree building
    # ------------------------------------------------------------------

    def get_weight_tree(self):
        """
        Build a nested dict tree from all weight presets by decoding
        their filename stems. The filename is the source of truth —
        no metadata reads required to reconstruct the tree.

        Tree shape:
            {
                'Creature': {
                    'Biped': {
                        '__presets__': [('Creature__Biped__legs', 'legs'), ...]
                    }
                },
                '__presets__': [('torso', 'torso'), ...]   # flat / no category
            }
        """
        tree = {}
        for stem in self.list_weights():
            path_parts, display_name = self.decode_stem(stem)
            node = tree
            for part in path_parts:
                node = node.setdefault(part, {})
            node.setdefault("__presets__", []).append((stem, display_name))
        return tree

    def build_menu_items(self, max_label_length=40):
        """
        Return a flat list of (label, stem_or_None) for populating an optionMenu.

        Category rows  -> (label, None)   — not selectable
        Preset rows    -> (label, stem)   — stem is the key used everywhere else

        Labels show the full human-readable path using '/' as separator.
        """
        items = []

        def walk(node, path_parts):
            # Categories first, sorted alphabetically — no header row, just recurse
            categories = {
                k: v for k, v in node.items()
                if k != "__presets__" and isinstance(v, dict)
            }
            for key in sorted(categories):
                walk(categories[key], path_parts + [key])

            # Then presets at this level, sorted by display name
            for stem, display_name in sorted(
                node.get("__presets__", []), key=lambda x: x[1]
            ):
                parts = path_parts + [display_name]
                label = "/".join(parts)
                if len(label) > max_label_length:
                    label = "..." + label[-(max_label_length - 3):]
                items.append((label, stem))

        walk(self.get_weight_tree(), [])
        return items

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, stem):
        """Delete a weight preset file by its encoded stem. Returns True on success."""
        path = self.weight_path_from_stem(stem)
        if not os.path.exists(path):
            return False
        try:
            os.remove(path)
            return True
        except Exception as e:
            print(f"[NGBuddy] Error deleting weight preset '{stem}': {e}")
            return False

    def open_folder(self):
        """Open the weights folder in Windows Explorer."""
        import subprocess
        subprocess.Popen(f'explorer "{os.path.normpath(self.weight_dir)}"')
# endregion