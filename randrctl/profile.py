import logging
# from randrctl.xrandr import XrandrOutput # TODO resolve circular import
from randrctl.exception import InvalidProfileException
import os
import json


__author__ = 'edio'
logger = logging.getLogger(__name__)


class Profile:
    def __init__(self, name, outputs: list, rules: dict={}):
        self.name = name
        self.outputs = outputs
        self.rules = rules

    def __repr__(self):
        return self.name + str(self.outputs)


class Rule:
    """
    Rule to match profile to xrandr connections
    """
    def __init__(self, edid: str=None, mode: str=None):
        """
        param edid: edid of a display to match
        param mode: supported mode of a display to match
        """
        self.edid = edid
        self.mode = mode

    def __eq__(self, other):
        return isinstance(other, Rule) and self.edid == other.edid and self.mode == other.mode

    def score(self, xrandr_output):
        """
        TODO doc
        1 if match is not needed by a criterion (i.e. edid is not set, mode is not set)
        2 if matches by supported mode
        3 if matches by edid
        returns sum of scores, -1 if doesn't match
        """

        score = 0
        if self.edid:
            if self.edid == xrandr_output.edid:
                score += 2
            else:
                return -1

        if self.mode:
            if xrandr_output.supported_modes.count(self.mode) > 0:
                score += 1
            else:
                return -1
        return score


class Geometry:
    def __init__(self, mode: str, pos: str='0x0', rotate: str='normal', panning: str='0x0'):
        self.mode = mode
        self.pos = pos
        self.rotate = rotate
        self.panning = panning

    def __repr__(self):
        return '+'.join([self.mode, self.pos.replace('x', '+')])

    def __eq__(self, other):
        return isinstance(other, Geometry) \
                   and self.mode == other.mode \
                   and self.pos == other.pos \
                   and self.rotate == other.rotate \
            and self.panning == other.panning

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


class ProfileManager:
    def __init__(self, profile_dirs: list):
        """
        Create profile manager that searches for profiles under paths passed as a list.
        Paths should be expanded and must exist.
        The first one is considered preferred and will be used for writes and will prevail in case of names conflicts.
        """
        self.profile_dirs = profile_dirs
        self.preferred_profile_dir = profile_dirs[0]

    def read_all(self):
        profiles = []
        for profile_dir in self.profile_dirs:
            for entry in os.listdir(profile_dir):
                path = os.path.join(profile_dir, entry)
                if os.path.isfile(path):
                    try:
                        with open(path) as profile_file:
                            profiles.append(self.read_file(profile_file))
                    except InvalidProfileException as e:
                        logger.warn(e)
        return profiles

    def read_one(self, profile_name: str):
        for profile_dir in self.profile_dirs:
            profile_path = os.path.join(profile_dir, profile_name)
            if not os.path.isfile(profile_path):
                continue
            with open(profile_path) as profile_file:
                return self.read_file(profile_file)

    def read_file(self, profile_file_descriptor):
        try:
            result = json.load(profile_file_descriptor)

            rules = result.get('match')

            if rules:
                for k, v in rules.items():
                    rules[k] = Rule(**v)
            else:
                rules = {}

            primary = result['primary']
            outputs_raw = result['outputs']
            outputs = []
            for name, mode_raw in outputs_raw.items():
                mode = Geometry(**mode_raw)
                output = Output(name, mode, primary == name)
                outputs.append(output)

            name = os.path.basename(profile_file_descriptor.name)

            return Profile(name, outputs, rules)
        except (KeyError, ValueError):
            raise InvalidProfileException(profile_file_descriptor.name)

    def write(self, p: Profile):
        """
        Write profile to file into configured profile directory.
        Profile name becomes the name of the file. If name contains illegal characters, only safe part is used.
        For example, if name is my_home_vga/../../passwd, then file will be written as passwd under profile dir
        """
        dict = self.to_dict(p)
        safename = os.path.basename(p.name)
        fullname = os.path.join(self.preferred_profile_dir, safename)
        if safename != p.name:
            logger.warning("Illegal name provided. Writing as %s", fullname)
        with open(fullname, 'w+') as fp:
            json.dump(dict, fp, indent=4)

    def print(self, p: Profile):
        dict = self.to_dict(p)
        print(json.dumps(dict, indent=4))

    def to_dict(self, p: Profile):
        outputs = {}
        primary = None
        for o in p.outputs:
            outputs[o.name] = o.geometry.__dict__
            if o.primary:
                primary = o.name

        result = {'outputs': outputs, 'primary': primary}
        return result

    def profile_from_xrandr(self, xrandr_connections: list, name: str='profile'):
        outputs = []
        for c in xrandr_connections:
            if not c.connected or c.current_geometry is None:
                continue
            output = Output(c.name, c.current_geometry, c.primary)
            outputs.append(output)

        logger.debug("Extracted %d outputs from %d xrandr connections", len(outputs), len(xrandr_connections))

        return Profile(name, outputs)


class ProfileMatcher:

    def find_best(self, availableProfiles, xrandr_outputs):
        """
        Find first matching profile across availableProfiles for actualConnections
        """
        output_names = map(lambda o: o.name, xrandr_outputs)
        output_names_set = set(output_names)

        # remove those with different outputs set
        profiles = filter(lambda p: set(p.rules) == output_names_set, availableProfiles)
        profiles = list(profiles)

        logger.debug("%d/%d profiles match outputs sets", len(profiles), len(availableProfiles))

        if len(profiles) == 0:
            return None

        matching = []
        for p in profiles:
            score = 0
            logger.debug("Trying profile %s", p.name)
            for o in xrandr_outputs:
                rule = p.rules.get(o.name)
                s = rule.score(o)
                logger.debug("%s scored %d for output %s", p.name, s, o.name)
                if s >= 0:
                    score += s
                else:
                    logger.debug("%s doesn't match %s", p.name, o.name)
                    score = -1
                    break
            logger.debug("%s total score: %d", p.name, s)
            if score >= 0:
                matching.append((score, p))

        if len(matching) > 0:
            (s, p) = max(matching)
            logger.debug("Selected profile %s with score %d", p.name, s)
            return p
        else:
            return None
