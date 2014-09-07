from functools import reduce

__author__ = 'edio'

import logging
import re
import subprocess
from randrctl.profile import Profile, Mode


class Xrandr:
    """
    Interface for xrandr application. Provides methods for calling xrandr operating with python objects such as
    randrctl.profile.Profile
    """
    EXECUTABLE = "/usr/bin/xrandr"
    OUTPUT_KEY = "--output"
    MODE_KEY = "--mode"
    POS_KEY = "--pos"
    PRIMARY_KEY = "--primary"
    QUERY_KEY = "-q"
    OFF_KEY = "--off"
    CONNECTION_REGEX = re.compile("(\w+)\s+(\w+)\s+(?:(?:(primary)\s+)?(\d\S+))?")
    MODE_REGEX = re.compile("(\d+)x(\d+)\+(\d+)\+(\d+)")

    def __init__(self, before_apply=None, after_apply=None):
        """
        Allows specifying custom functions to be called before and after call to xrandr executable.
        Passed functions should receive 1 argument (to be changed in future)
        """
        self._before_apply = before_apply
        self._after_apply = after_apply

    def apply(self, profile: Profile):
        """
        Apply given profile by calling xrandr
        """
        logging.debug("Applying profile %s", profile.name)

        args = self.__compose_mode_args__(profile, self.get_all_connections())

        if self._before_apply is not None:
            self._before_apply(profile)

        self.__xrandr__(args)

        if self._after_apply is not None:
            self._after_apply(profile)

    def __xrandr__(self, args: list):
        """
        Perform call to xrandr executable with passed arguments.
        Returns subprocess.Popen object
        """
        logging.debug("Performing call to xrandr with args %s", args)
        args.insert(0, self.EXECUTABLE)

        # TODO fix call to shell
        line = reduce(lambda x, y: x + ' ' + y, args)
        return subprocess.Popen(line, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    def __compose_mode_args__(self, profile: Profile, xrandr_connections: list):
        """
        Composes list of arguments to xrandr to apply profile settings and disable the other outputs
        """
        args = []
        active_names = []

        for o in profile.outputs:
            active_names.append(o.name)
            args.append(self.OUTPUT_KEY)
            args.append(o.name)
            args.append(self.MODE_KEY)
            args.append("{0}x{1}".format(o.mode.width, o.mode.height))
            args.append(self.POS_KEY)
            args.append("{0}x{1}".format(o.mode.left, o.mode.top))
            if o.primary:
                args.append(self.PRIMARY_KEY)

        # turn off the others
        for c in xrandr_connections:
            if active_names.count(c.name) == 0:
                args.append(self.OUTPUT_KEY)
                args.append(c.name)
                args.append(self.OFF_KEY)

        return args

    def get_all_connections(self):
        """
        Query xrandr for all supported connections.
        Performs call to xrandr with -q key and parses output.
        """
        connections = []

        p = self.__xrandr__([self.QUERY_KEY])
        output = p.stdout.readlines()
        output.pop(0) # remove first line
        for line in output:
            l = line.decode('utf-8')
            if l[0] == ' ':
                continue
            c = self.connection_from_str(l)
            connections.append(c)

        return connections

    def connection_from_str(self, s: str):
        """
        Creates connection from line provided by xrandr output.
        Param s: line from xrandr output.
        Example: LVDS1 connected 1366x768+0+312 (normal left inverted right x axis y axis) 277mm x 156mm
        """
        match = self.CONNECTION_REGEX.match(s)
        if match is None:
            raise Exception("'{0}' is not valid xrandr connection".format(s)) # narrow exception

        name = match.group(1)
        status = match.group(2)

        primary = match.group(3) is not None
        mode_str = match.group(4)
        mode = self.mode_from_str(mode_str) if mode_str is not None else None

        return XrandrConnection(name, connected=(status == 'connected'), primary=primary, current_mode=mode)

    def mode_from_str(self, s:str):
        """
        Parses mode string (i.e. 1111x2222+333+444) into Mode object
        """
        match = self.MODE_REGEX.match(s)
        r = list(map(int, match.groups()))
        return Mode(*r)


class XrandrConnection:
    def __init__(self, name: str, connected: bool=False, current_mode: Mode=None, primary: bool=False):
        self.name = name
        self.connected = connected
        self.current_mode = current_mode
        self.primary = primary



