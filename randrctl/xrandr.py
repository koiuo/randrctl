import logging
import re
import subprocess
from randrctl.exception import RandrCtlException, ValidationException
from randrctl.profile import Profile, Mode


__author__ = 'edio'
logger = logging.getLogger(__name__)


class XrandrException(RandrCtlException):
    """
    is thrown when call to xrandr fails
    """

    def __init__(self, err: str, args: list):
        self.args = args
        Exception.__init__(self, err)


class Xrandr:
    """
    Interface for xrandr application. Provides methods for calling xrandr operating with python objects such as
    randrctl.profile.Profile
    """
    EXECUTABLE = "/usr/bin/xrandr"
    OUTPUT_KEY = "--output"
    MODE_KEY = "--mode"
    POS_KEY = "--pos"
    ROTATE_KEY = "--rotate"
    PANNING_KEY = "--panning"
    PRIMARY_KEY = "--primary"
    QUERY_KEY = "-q"
    OFF_KEY = "--off"
    CONNECTION_REGEX = re.compile("(\w+)\s+(\w+)\s+(?:(?:(primary)\s+)?(\d\S+))?")
    MODE_REGEX = re.compile("(\d+x\d+)\+(\d+\+\d+)")

    def apply(self, profile: Profile):
        """
        Apply given profile by calling xrandr
        """
        logger.debug("Applying profile %s", profile.name)

        args = self.__compose_mode_args__(profile, self.get_all_connections())
        self.__xrandr__(args)

    def __xrandr__(self, args: list):
        """
        Perform call to xrandr executable with passed arguments.
        Returns subprocess.Popen object
        """
        logger.debug("Calling xrandr with args %s", args)
        args.insert(0, self.EXECUTABLE)

        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        err = p.stderr.readlines()
        if err:
            err_str = ''.join(map(lambda x: x.decode(), err)).strip()
            raise XrandrException(err_str, args)
        return p

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
            args.append(o.mode.mode)
            args.append(self.POS_KEY)
            args.append(o.mode.pos)
            args.append(self.ROTATE_KEY)
            args.append(o.mode.rotate)
            args.append(self.PANNING_KEY)
            args.append(o.mode.panning)
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
        output.pop(0)  # remove first line
        for line in output:
            l = line.decode()
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
            raise ValidationException("'{0}' is not valid xrandr connection".format(s))  # narrow exception

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
        mode = match.group(1)
        pos = match.group(2).replace('+', 'x')
        return Mode(mode=mode, pos=pos)


class XrandrConnection:
    def __init__(self, name: str, connected: bool=False, current_mode: Mode=None, primary: bool=False):
        self.name = name
        self.connected = connected
        self.current_mode = current_mode
        self.primary = primary



