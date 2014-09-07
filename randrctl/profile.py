from functools import reduce
import logging
from randrctl.hotplug import Connection

__author__ = 'edio'

import os
import json


class Profile:
    def __init__(self, name, outputs: list, rules: dict={}):
        self.name = name
        self.outputs = outputs
        self.rules = rules

    def matches(self, *connections: Connection):
        for connection in connections:
            rule = self.rules.get(connection.output)
            if not rule:
                logging.debug("Not matched by output name {0}", connection.output)
                return False
            for key, value in rule:
                if getattr(connection, key) != value:
                    logging.debug("Output {0} has unmatched property {1}", connection.output, key)
                    return False
        return True

    def __repr__(self):
        return self.name + str(self.outputs)


class Mode:
    def __init__(self, width: int, height: int, left: int=0, top: int=0):
        self.width = width
        self.height = height
        self.left = left
        self.top = top

    def __repr__(self):
        return "{0}x{1}+{2}+{3}".format(self.width, self.height, self.left, self.top)

    def __eq__(self, other):
        return isinstance(other, Mode) \
            and self.width == other.width \
            and self.height == other.height \
            and self.left == other.left \
            and self.top == other.top

    def __hash__(self):
        return hash(self.width) ^ hash(self.height) ^ hash(self.left) ^ hash(self.top)


class Output:
    def __init__(self, name: str, mode: Mode, primary: bool=False):
        self.name = name
        self.mode = mode
        self.primary = primary

    def __eq__(self, obj):
        return isinstance(obj, Output) \
            and obj.name == self.name \
            and obj.mode == self.mode \
            and obj.primary == self.primary

    def __repr__(self):
        return "{0}{{{1}}}".format(self.name, self.mode, ", primary" if self.primary else "")

    def __hash__(self):
        return hash(self.name) ^ hash(self.primary) ^ (0 if self.mode is None else self.mode.__hash__())


class ProfileManager:
    def __init__(self, profile_dir_path: str):
        self.profile_dir_path = profile_dir_path

    def read_all(self):
        profiles = []
        for entry in os.listdir(self.profile_dir_path):
            path = os.path.join(self.profile_dir_path, entry)
            if os.path.isfile(path):
                with open(path) as profile_file:
                    profiles.append(self.read_file(profile_file))
        return profiles

    def read_one(self, profile_name: str):
        with open(os.path.join(self.profile_dir_path, profile_name)) as profile_file:
            return self.read_file(profile_file)

    def read_file(self, profile_file_descriptor):
        result = json.load(profile_file_descriptor)

        rules = result.get('match')

        primary = result['primary']
        outputs_raw = result['outputs']
        outputs = []
        for name, mode_raw in outputs_raw.items():
            mode = Mode(**mode_raw)
            output = Output(name, mode, primary == name)
            outputs.append(output)

        name = os.path.basename(profile_file_descriptor.name)

        return Profile(name, outputs, rules)

    def write(self, p: Profile):
        """
        Write profile to file into configured profile directory.
        Profile name becomes the name of the file. If name contains illegal characters, only safe part is used.
        For example, if name is my_home_vga/../../passwd, then file will be written as passwd under profile dir
        """
        dict = self.to_dict(p)
        safename = os.path.basename(p.name)
        fullname = os.path.join(self.profile_dir_path, safename)
        if safename != p.name:
            logging.warning("Illegal name provided. Writing as %s", fullname)
        with open(fullname, 'w+') as fp:
            json.dump(dict, fp, indent=4)

    def print(self, p: Profile):
        dict = self.to_dict(p)
        print(json.dumps(dict, indent=4))

    def to_dict(self, p: Profile):
        outputs = {}
        primary = None
        for o in p.outputs:
            outputs[o.name] = o.mode.__dict__
            if o.primary:
                primary = o.name

        result = {'outputs': outputs, 'primary': primary}
        return result

    def profile_from_xrandr(self, xrandr_connections: list, name: str=None):
        outputs = []
        for c in xrandr_connections:
            if not c.connected or c.current_mode is None:
                continue
            output = Output(c.name, c.current_mode, c.primary)
            outputs.append(output)

        logging.debug("Extracted %d outputs from %d xrandr connections", len(outputs), len(xrandr_connections))

        if name is None:
            name = self.guess_name(outputs)

        logging.debug("Name not provided. Guessed %s", name)

        return Profile(name, outputs)

    def guess_name(self, outputs: list):
        ordered = sorted(outputs, key=lambda o: (not o.primary, o.name))
        names = list(map(lambda o: o.name, ordered))
        name = reduce(lambda o1, o2: o1 + "-" + o2, names)
        return name


class ProfileMatcher:
    def findFirst(self, availableProfiles, actualConnections):
        """
        Find first matching profile across availableProfiles for actualConnections
        """
        for p in availableProfiles:
            if p.matches(actualConnections):
                logging.info("Found matching profile {0}", p.name)
                return p
        return None
