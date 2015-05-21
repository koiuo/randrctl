__author__ = 'edio'


class Profile:
    def __init__(self, name, outputs: list, rules: dict={}):
        """
        :param name: name of the profile
        :param outputs: list of Output objects (i.e. settings to apply for each output)
        :param rules: dictionary of rules for match section. Keys of the dictionary are outputs names (e.g. "LVDS1"),
        values are Rule instances
        """

        self.name = name
        self.outputs = outputs
        self.rules = rules

    def __repr__(self):
        return self.name + str(self.outputs)


class Rule:
    """
    Rule to match profile to xrandr connections
    """
    def __init__(self, edid: str=None, prefers: str=None, supports: str=None):
        """
        Rule to match against edid, supported mode, preferred mode or any combination of them.
        Rule matches anything if nothing is passed
        :param edid: edid of a display to match
        :param prefers: preferred mode of a display to match
        :param supports: supported mode of a display to match
        """
        self.edid = edid
        self.prefers = prefers
        self.supports = supports

    def __eq__(self, other):
        return isinstance(other, Rule) and self.edid == other.edid \
            and self.prefers == other.prefers\
            and self.supports == other.supports


class Geometry:
    def __init__(self, mode: str, pos: str='0x0', rotate: str='normal', panning: str='0x0', rate: int=None):
        self.mode = mode
        self.pos = pos
        self.rotate = rotate
        self.panning = panning
        self.rate = rate

    def __repr__(self):
        return '{:s}+{:s}@{:s}'.format(self.mode, self.pos.replace('x', '+'), str(self.rate))

    def __eq__(self, other):
        return isinstance(other, Geometry) \
            and self.mode == other.mode \
            and self.pos == other.pos \
            and self.rotate == other.rotate \
            and self.panning == other.panning \
            and self.rate == other.rate

    def __hash__(self):
        return hash(self.mode) ^ hash(self.pos) ^ hash(self.rotate) ^ hash(self.panning)


class Output:
    def __init__(self, name: str, geometry: Geometry, primary: bool=False):
        self.name = name
        self.geometry = geometry
        self.primary = primary

    def __eq__(self, obj):
        return isinstance(obj, Output) \
            and obj.name == self.name \
            and obj.geometry == self.geometry \
            and obj.primary == self.primary

    def __repr__(self):
        return "{0}{{{1}}}".format(self.name, self.geometry, ", primary" if self.primary else "")

    def __hash__(self):
        return hash(self.name) ^ hash(self.primary) ^ (0 if self.geometry is None else self.geometry.__hash__())


class XrandrOutput:
    def __init__(self, name: str, connected: bool=False, current_geometry: Geometry=None, primary: bool=False,
                 supported_modes: list=None, preferred_mode=None, edid: str=None):
        self.name = name
        self.connected = connected
        self.current_geometry = current_geometry
        self.primary = primary
        self.supported_modes = supported_modes
        self.preferred_mode = preferred_mode
        self.edid = edid

    def is_active(self):
        return self.current_geometry is not None
