# NGBuddy Dimensions & Spacing

class Dimensions:
    # Button heights
    BTN_PRIMARY    = 28
    BTN_SECONDARY  = 24
    BTN_ICON       = 24

    # Input heights
    INPUT_HEIGHT   = 24

    # Spacing
    PADDING_OUTER  = 8
    PADDING_INNER  = 6
    ROW_SPACING    = 4
    SECTION_SPACING = 8

    # Separator
    SEPARATOR_HEIGHT = 8

    # Tab bar
    TAB_HEIGHT     = 26
    TAB_BTN_WIDTH  = 95   # Fixed width per tab button
    HELP_BTN_WIDTH = 30   # Small square ? button

    # Status bar
    STATUS_HEIGHT  = 22

    # Column widths
    LABEL_WIDTH    = 120
    SLIDER_WIDTH   = 180
    FIELD_WIDTH    = 50

    # Window
    WINDOW_WIDTH_DEFAULT = 420
    WINDOW_WIDTH_MIN     = 380

    # Build tab tree panels — 40/60 split of usable content width
    # Usable = window width minus frame margins on both sides
    _CONTENT_WIDTH = WINDOW_WIDTH_DEFAULT - (PADDING_INNER * 4)
    PRESET_PANEL_W = int(_CONTENT_WIDTH * 0.40)   # ~40%
    LAYER_PANEL_W  = int(_CONTENT_WIDTH * 0.60)   # ~60%
    TREE_PANEL_GAP = 4                             # px gap between panels