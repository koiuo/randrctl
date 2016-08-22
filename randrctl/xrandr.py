from functools import reduce
import logging
import re
import subprocess
from randrctl.exception import XrandrException, ParseException
from randrctl.model import Profile, Viewport, XrandrConnection, Display

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
    SCALE_KEY = "--scale"
    PRIMARY_KEY = "--primary"
    QUERY_KEY = "-q"
    VERBOSE_KEY = "--verbose"
    OFF_KEY = "--off"
    OUTPUT_DETAILS_REGEX = re.compile(
        '(?P<primary>primary )?(?P<geometry>[\dx\+]+) (?:(?P<rotate>\w+) )?.*?(?:panning (?P<panning>[\dx\+]+))?$')
    MODE_REGEX = re.compile("(\d+x\d+)\+(\d+\+\d+)")
    CURRENT_MODE_REGEX = re.compile("\s*([0-9x]+)\s+([0-9\.]+)(.*$)")

    def apply(self, profile: Profile):
        """
        Apply given profile by calling xrandr
        """
        logger.debug("Applying profile %s", profile.name)

        args = self._compose_mode_args(profile, self.get_all_outputs())
        self._xrandr(args)

    def _xrandr(self, args: list):
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

    def _compose_mode_args(self, profile: Profile, xrandr_connections: list):
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
            args.append(o.mode)
            args.append(self.POS_KEY)
            args.append(o.pos)
            args.append(self.ROTATE_KEY)
            args.append(o.rotate)
            args.append(self.PANNING_KEY)
            args.append(o.panning)
            args.append(self.SCALE_KEY)
            args.append(o.scale)
            if o.rate:
                args.append(self.RATE_KEY)
                args.append(str(o.rate))
            if o.name == profile.primary:
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

        p = self._xrandr([self.QUERY_KEY])
        query_result = p.stdout.readlines()
        query_result.pop(0)  # remove first line. It describes Screen

        items = self._group_query_result(map(lambda x: x.decode(), query_result))
        logger.debug("Detected total %d outputs", len(items))

        for i in items:
            o = self._parse_xrandr_connection(i)
            outputs.append(o)

        return outputs

    def get_connected_outputs(self):
        """
        Query xrandr and return list of connected outputs.
        Performs call to xrandr with -q and --verbose keys.
        Returns list of connected outputs with all properties set
        """
        outputs = list(filter(lambda o: o.display is not None, self.get_all_outputs()))
        edids = self._get_edids()
        for o in outputs:
            o.edid = edids[o.name]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Connected outputs: %s", list(map(lambda o: o.name, outputs)))
        return outputs

    def _get_edids(self):
        """
        Get EDIDs of all connected displays.
        Return dictionary of {"connection_name": "edid"}
        """
        edids = dict()

        p = self._xrandr([self.QUERY_KEY, self.VERBOSE_KEY])
        query_result = p.stdout.readlines()
        query_result.pop(0)  # remove first line

        items = self._group_query_result(map(lambda x: x.decode(), query_result))

        items = filter(lambda x: x[0].find(' connected') > 0, items)

        for i in items:
            name_idx = i[0].find(' ')
            name = i[0][:name_idx]
            edids[name] = self._edid_from_query_item(i)

        return edids

    def _edid_from_query_item(self, item_lines: list):
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

    def _parse_xrandr_connection(self, item_lines: list):
        """
        Creates XrandrConnection from lines returned by xrandr --query.
        Example:
        LVDS1 connected primary 1366x768+0+312 (normal left inverted right x axis y axis) 277mm x 156mm
           1366x768      60.02*+
           1024x768      60.00
        """
        connection_info = item_lines[0]

        name, status, state = connection_info.split(' ', 2)

        if status != 'connected':
            # We are not connected, do not parse the rest.
            return XrandrConnection(name)

        # We are connected parse connected display.
        display = self._parse_display(item_lines[1:])

        if not display.is_on():
            # inactive output
            return XrandrConnection(name, display)

        parsed = self.OUTPUT_DETAILS_REGEX.match(state)
        if parsed is None:
            raise ParseException(name, status, state)

        primary = parsed.group('primary') is not None
        rotate = parsed.group('rotate')
        panning = parsed.group('panning')
        geometry = parsed.group('geometry')
        size, pos = self._parse_geometry(geometry)
        scale = '1x1'
        if size != display.mode:
            dw, dh = map(lambda s: int(s), display.mode.split('x'))
            vw, vh = map(lambda s: int(s), size.split('x'))
            sw, sh = vw/dw, vh/dh
            scale = "{}x{}".format(sw, sh)

        viewport = Viewport(size, pos, rotate, panning, scale)

        return XrandrConnection(name, display, viewport, primary)

    def _parse_display(self, lines: list):
        supported_modes = []
        preferred_mode = None
        current_mode = None
        current_rate = None
        for mode_line in lines:
            mode_line = mode_line.strip()
            (mode, rate, extra) = self.CURRENT_MODE_REGEX.match(mode_line).groups()
            current = (extra.find("*") >= 0)
            preferred = (extra.find("+") >= 0)
            supported_modes.append(mode)
            if current:
                current_mode = mode
                current_rate = int(round(float(rate)))
            if preferred:
                preferred_mode = mode

        return Display(supported_modes, preferred_mode, current_mode, current_rate)

    def _group_query_result(self, query_result: list):
        """
        Group input list of lines such that every line starting with a non-whitespace character is a start of a
        group, and every subsequent line starting with whitespace is a member of that group.
        :param query_result: list of lines
        :return: list of lists of lines
        """
        def group_fn(result, line):
            # We append
            if type(result) is str:
                if line.startswith(' ') or line.startswith('\t'):
                    return [[result, line]]
                else:
                    return [[result], [line]]
            else:
                if line.startswith(' ') or line.startswith('\t'):
                    last = result[len(result) - 1]
                    last.append(line)
                    return result
                else:
                    result.append([line])
                    return result

        # TODO rewrite in imperative code
        grouped = reduce(lambda result, line: group_fn(result, line), query_result)

        return grouped

    def _parse_geometry(self, s: str):
        """
        Parses geometry string (i.e. 1111x2222+333+444) into tuple (widthxheight, leftxtop)
        """
        match = self.MODE_REGEX.match(s)
        mode = match.group(1)
        pos = match.group(2).replace('+', 'x')
        return mode, pos
