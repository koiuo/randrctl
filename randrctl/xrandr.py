from functools import reduce
import logging
import re
import subprocess
from randrctl.exception import XrandrException
from randrctl.model import Profile, Geometry, XrandrOutput


__author__ = 'edio'
logger = logging.getLogger(__name__)


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
    RATE_KEY = "--rate"
    PRIMARY_KEY = "--primary"
    QUERY_KEY = "-q"
    VERBOSE_KEY = "--verbose"
    OFF_KEY = "--off"
    OUTPUT_DETAILS_REGEX = re.compile('(?P<primary>primary )?(?P<geometry>[\dx\+]+) (?:(?P<rotate>\w+) )?.*$')
    MODE_REGEX = re.compile("(\d+x\d+)\+(\d+\+\d+)")
    CURRENT_MODE_REGEX = re.compile("\s*([0-9x]+)\s+([0-9\.]+)(.*$)")

    def apply(self, profile: Profile):
        """
        Apply given profile by calling xrandr
        """
        logger.debug("Applying profile %s", profile.name)

        args = self.__compose_mode_args__(profile, self.get_all_outputs())
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
            # close descriptors
            p.stderr.close()
            p.stdout.close()
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
            args.append(o.geometry.mode)
            args.append(self.POS_KEY)
            args.append(o.geometry.pos)
            args.append(self.ROTATE_KEY)
            args.append(o.geometry.rotate)
            args.append(self.PANNING_KEY)
            args.append(o.geometry.panning)
            if o.geometry.rate:
                args.append(self.RATE_KEY)
                args.append(str(o.geometry.rate))
            if o.primary:
                args.append(self.PRIMARY_KEY)

        # turn off the others
        for c in xrandr_connections:
            if active_names.count(c.name) == 0:
                args.append(self.OUTPUT_KEY)
                args.append(c.name)
                args.append(self.OFF_KEY)

        return args

    def get_all_outputs(self):
        """
        Query xrandr for all supported outputs.
        Performs call to xrandr with -q key and parses output.
        Returns list of outputs with some properties missing (only name and status are guaranteed)
        """
        outputs = []

        p = self.__xrandr__([self.QUERY_KEY])
        query_result = p.stdout.readlines()
        query_result.pop(0)  # remove first line. It describes Screen

        items = self.group_query_result(map(lambda x: x.decode(), query_result))

        for i in items:
            o = self.output_from_query_item(i)
            outputs.append(o)
        return outputs

    def get_connected_outputs(self):
        """
        Query xrandr and return list of connected outputs.
        Performs call to xrandr with -q and --verbose keys.
        Returns list of connected outputs with all properties set
        """
        outputs = list(filter(lambda o: o.connected, self.get_all_outputs()))
        edids = self.get_edids()
        for o in outputs:
            o.edid = edids[o.name]
        logger.debug("Connected outputs: %s", outputs)
        return outputs

    def get_edids(self):
        """
        Get EDIDs of all connected displays.
        Return dictionary of {"connection_name": "edid"}
        """
        edids = dict()

        p = self.__xrandr__([self.QUERY_KEY, self.VERBOSE_KEY])
        query_result = p.stdout.readlines()
        query_result.pop(0)  # remove first line

        items = self.group_query_result(map(lambda x: x.decode(), query_result))

        items = filter(lambda x: x[0].find(' connected') > 0, items)

        for i in items:
            name_idx = i[0].find(' ')
            name = i[0][:name_idx]
            edids[name] = self.edid_from_query_item(i)

        return edids

    def edid_from_query_item(self, item_lines: list):
        """
        Extracts display EDID from xrandr --verbose output
        """
        edid_start = 0
        for i, line in enumerate(item_lines):
            if line.find('EDID:') >= 0:
                edid_start = i + 1
                break
        edid_lines = map(lambda x: x.strip(), item_lines[edid_start:edid_start + 8])
        edid = ''.join(edid_lines)
        return edid

    def output_from_query_item(self, item_lines: list):
        """
        Creates XrandrOutput from lines returned by xrandr --query.
        First line is an output description. Subsequent, if any, are supported modes.
        Example:
        LVDS1 connected 1366x768+0+312 (normal left inverted right x axis y axis) 277mm x 156mm
           1366x768      60.02*+
           1024x768      60.00
        """
        output_info = item_lines[0]

        tokens = output_info.split(' ', 2)
        name = tokens[0]
        status = tokens[1]
        connected = status == 'connected'

        if not connected:
            # if we are not connected, do not parse the rest
            return XrandrOutput(name, connected)

        # we are connected parse supported modes
        supported_modes = []
        preferred_mode = None
        current_mode = None
        current_rate = None
        for mode_line in item_lines[1:]:
            mode_line = mode_line.strip()
            (mode, rate, extra) = self.CURRENT_MODE_REGEX.match(mode_line).groups()
            current = (extra.find("*") >= 0)
            preferred = (extra.find("+") >= 0)
            supported_modes.append(mode)
            if current:
                current_mode = mode
                current_rate = round(float(rate))
            if preferred:
                preferred_mode = mode

        if current_mode is None:
            # inactive output
            return XrandrOutput(name, connected, supported_modes=supported_modes, preferred_mode=preferred_mode)

        # if we are active parse the rest and return full-blown output
        details = tokens[2]
        output_details = self.parse_output_details(details)

        res = output_details['res']
        pos = output_details['pos']
        primary = output_details['primary']
        rotate = output_details['rotate']

        panning = res if res != current_mode else '0x0'
        rotate = rotate if rotate else 'normal'

        geometry = Geometry(current_mode, pos, rotate, panning, current_rate)

        return XrandrOutput(name, connected, geometry, primary, supported_modes, preferred_mode)

    def group_query_result(self, query_result: list):
        def group_fn(x, y):
            if type(x) is str:
                if y.startswith(' ') or y.startswith('\t'):
                    return [[x, y]]
                else:
                    return [[x], [y]]
            else:
                if y.startswith(' ') or y.startswith('\t'):
                    last = x[len(x) - 1]
                    last.append(y)
                    return x
                else:
                    x.append([y])
                    return x

        grouped = reduce(lambda x, y: group_fn(x, y), query_result)

        return grouped

    def parse_output_details(self, s: str):
        """
        Creates connection from line provided by xrandr output.
        Param s: line from xrandr output.
        Example:
        primary 1366x1080+0+0 left (normal left inverted right x axis y axis) 277mm x 156mm panning 1366x1080+0+0
        """
        match = self.OUTPUT_DETAILS_REGEX.match(s)
        if match is None:
            # we got inactive output
            return {}

        is_primary = match.group('primary') is not None
        geometry_string = match.group('geometry')
        rotate = match.group('rotate')

        geometry_tokens = self.parse_geometry(geometry_string)
        res = geometry_tokens[0]
        pos = geometry_tokens[1]

        all = {'primary': is_primary, 'pos': pos, 'res': res, 'rotate': rotate}

        return all

    def parse_geometry(self, s: str):
        """
        Parses geometry string (i.e. 1111x2222+333+444) into tuple (widthxheight, leftxtop)
        """
        match = self.MODE_REGEX.match(s)
        mode = match.group(1)
        pos = match.group(2).replace('+', 'x')
        return mode, pos



