class Display:
    """
    Display (i.e. physical device) connected to graphical adapter output
    """

    def __init__(self, supported_modes=None, preferred_mode: str=None, current_mode: str=None,
                 current_rate: int=None, edid: str=None):
        if supported_modes is None:
            supported_modes = []
        self.mode = current_mode
        self.rate = current_rate
        self.preferred_mode = preferred_mode
        self.supported_modes = supported_modes
        self.edid = edid

    def is_on(self):
        return self.mode is not None

    def __repr__(self, *args, **kwargs):
        return str(self.__dict__)


class Viewport:
    """
    Screen viewport
    """

    def __init__(self, size: str, pos: str='0x0', rotate: str='normal', panning: str='0x0', scale: str='1x1'):
        self.size = size
        self.pos = pos
        self.rotate = rotate if rotate else "normal"
        self.panning = panning if panning else "0x0"
        self.scale = scale if scale else "1x1"

    def __repr__(self, *args, **kwargs):
        return str(self.__dict__)


class XrandrConnection:
    """
    Connection between a graphic adapter output and a display with assigned viewport
    """

    def __init__(self, name: str, display: Display=None, current_geometry: Viewport=None, primary: bool=False, crtc: int=None):
        self.name = name
        self.display = display
        self.viewport = current_geometry
        self.primary = primary
        self.crtc = crtc

    def is_active(self):
        return self.viewport is not None

    def __repr__(self, *args, **kwargs):
        return str(self.__dict__)


class Profile:
    def __init__(self, name, outputs: list, rules: dict=None, primary: str=None, priority: int=100):
        """
        :param name: name of the profile
        :param outputs: list of Output objects (i.e. settings to apply for each output)
        :param rules: dictionary of rules for match section. Keys of the dictionary are outputs names (e.g. "LVDS1"),
        values are Rule instances
        """

        if rules is None:
            rules = {}
        self.name = name
        self.outputs = outputs
        self.rules = rules
        self.primary = primary
        self.priority = priority

    def __repr__(self):
        return self.name + str(self.outputs)


class Rule:
    """
    Rule to match profile to xrandr connections.
    Corresponds to a single entry in a match section in profile json.
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

    def __repr__(self):
        return str(self.__dict__)


class Output:
    """
    Output in randrctl profile.
    """

    def __init__(self, name: str, mode: str, pos: str="0x0", rotate: str="normal", panning: str="0x0",
                 scale: str="1x1", rate: int=None, crtc: int=None):
        self.name = name
        self.mode = mode
        self.pos = pos
        self.rotate = rotate
        self.panning = panning
        self.scale = scale
        self.rate = rate
        self.crtc = crtc

    def todict(self):
        d = {
            'mode': self.mode,
            'pos': self.pos,
            'rotate': self.rotate,
            'panning': self.panning,
            'scale': self.scale,
            'rate': self.rate,
            'crtc': self.crtc
        }
        return dict((k, v) for k, v in d.items() if v is not None)

    @staticmethod
    def fromconnection(connection: XrandrConnection):
        return Output(connection.name,
                      connection.display.mode,
                      connection.viewport.pos,
                      connection.viewport.rotate,
                      connection.viewport.panning,
                      connection.viewport.scale,
                      connection.display.rate,
                      connection.crtc)

    def __repr__(self):
        return "{0}{{{1}}}".format(self.name, self.mode)
