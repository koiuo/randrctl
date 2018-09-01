class Display:
    """
    Display (i.e. physical device) connected to graphical adapter output
    """

    def __init__(self, supported_modes=None, preferred_mode: str = None, current_mode: str = None,
                 current_rate: str = None, edid: str = None):
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

    def __init__(self, size: str, pos: str = '0x0', rotate: str = 'normal', panning: str = '0x0', scale: str = '1x1'):
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

    def __init__(self, name: str, display: Display = None, current_geometry: Viewport = None, primary: bool = False,
                 crtc: int = None):
        self.name = name
        self.display = display
        self.viewport = current_geometry
        self.primary = primary
        self.crtc = crtc

    def is_active(self):
        return self.viewport is not None

    def __repr__(self, *args, **kwargs):
        return str(self.__dict__)


class Deserializable(object):
    # TODO implement deserialization
    pass


class Serializable(Deserializable):
    def _traverse(self, child):
        if child is None:
            pass
        elif isinstance(child, Serializable):
            return child.to_dict()
        elif isinstance(child, dict):
            return dict(map(lambda kv: (kv[0], self._traverse(kv[1])), child.items()))
        elif isinstance(child, list):
            return list(map(lambda el: self._traverse(el), child))
        else:
            return child

    def to_dict(self):
        not_empty = lambda kv: (kv[1] is not None)
        return self._traverse(dict(filter(not_empty, self.__dict__.items())))


class Profile(Serializable):
    def __init__(self, name, outputs: dict, match: dict = None, primary: str = None, priority: int = 100):
        """
        :param name: name of the profile
        :param outputs: list of Output objects (i.e. settings to apply for each output)
        :param match: dictionary of rules for match section. Keys of the dictionary are outputs names (e.g. "LVDS1"),
        values are Rule instances
        """
        self.name = name
        self.outputs = outputs
        self.match = match
        self.primary = primary
        self.priority = priority

    @staticmethod
    def from_dict(d: dict):
        outputs = d.get('outputs')
        match = d.get('match')
        return Profile(
            name=d.get('name'),
            outputs=dict(map(lambda kv: (kv[0], Output.from_dict(kv[1])), outputs.items())) if outputs else None,
            match=dict(map(lambda kv: (kv[0], Rule.from_dict(kv[1])), match.items())) if match else None,
            primary=d.get('primary'),
            priority=d.get('priority')
        )

    def __repr__(self):
        return str(self.__dict__)

    def __eq__(self, o: object):
        return isinstance(o, Profile) and self.__dict__ == o.__dict__

    def __hash__(self):
        return hash(self.name)


class Rule(Serializable):
    """
    Rule to match profile to xrandr connections.
    Corresponds to a single entry in a match section in profile json.
    """

    def __init__(self, edid: str = None, prefers: str = None, supports: str = None):
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

    @staticmethod
    def from_dict(d: dict):
        return Rule(**d)

    def __repr__(self):
        return str(self.__dict__)

    def __eq__(self, o: object):
        return isinstance(o, Rule) and self.__dict__ == o.__dict__

    def __hash__(self):
        return hash((self.edid, self.prefers, self.supports))


class Output(Serializable):
    """
    Output in randrctl profile.
    """

    def __init__(self, mode: str, pos: str = "0x0", rotate: str = "normal", panning: str = "0x0",
                 scale: str = "1x1", rate: str = None, crtc: int = None):
        self.mode = mode
        self.pos = pos
        self.rotate = rotate
        self.panning = panning
        self.scale = scale
        self.rate = rate
        self.crtc = crtc

    @staticmethod
    def from_dict(d: dict):
        # old json profiles may contain rate stored as int
        # TODO test how PyYaml handles json with numberic value as rate
        if d.get('rate'):
            d['rate'] = str(d['rate'])
        return Output(**d)

    @staticmethod
    def fromconnection(connection: XrandrConnection):
        return Output(connection.display.mode,
                      connection.viewport.pos,
                      connection.viewport.rotate,
                      connection.viewport.panning,
                      connection.viewport.scale,
                      connection.display.rate,
                      connection.crtc)

    def __repr__(self):
        return str(self.__dict__)

    def __eq__(self, o: object):
        return isinstance(o, Output) and self.__dict__ == o.__dict__

    def __hash__(self):
        return hash(self.mode)

