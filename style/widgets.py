import maya.cmds as cmds
from style.colors import Colors
from style.dimensions import Dimensions


class Widgets:

    @staticmethod
    def section_header(label):
        """Small uppercase section label"""
        cmds.text(
            label=label.upper(),
            align='left',
            height=18,
            font='smallBoldLabelFont',
            backgroundColor=Colors.BG_PANEL
        )

    @staticmethod
    def primary_button(label, command=None, accent=None):
        """Accented primary action button"""
        color = accent if accent else Colors.ACCENT_BUILD
        cmds.button(
            label=label,
            height=Dimensions.BTN_PRIMARY,
            backgroundColor=color,
            command=command if command else lambda x: None
        )

    @staticmethod
    def secondary_button(label, command=None):
        """Subtle secondary action button"""
        cmds.button(
            label=label,
            height=Dimensions.BTN_SECONDARY,
            backgroundColor=Colors.BG_ELEMENT,
            command=command if command else lambda x: None
        )

    @staticmethod
    def panel(label=None):
        """Returns a framed panel layout, optionally with a label"""
        return cmds.frameLayout(
            label=label if label else '',
            collapsable=False,
            labelVisible=bool(label),
            backgroundColor=Colors.BG_PANEL,
            marginWidth=Dimensions.PADDING_INNER,
            marginHeight=Dimensions.PADDING_INNER
        )

    @staticmethod
    def separator():
        cmds.separator(
            height=Dimensions.SEPARATOR_HEIGHT,
            style='in'
        )

    @staticmethod
    def label(text, secondary=False):
        cmds.text(
            label=text,
            align='left',
            backgroundColor=Colors.BG_PANEL
        )