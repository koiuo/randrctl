import hashlib
import logging
import os
import json

from randrctl.exception import InvalidProfileException, NoSuchProfileException
from randrctl.model import Profile, Rule, Output, XrandrConnection

logger = logging.getLogger(__name__)


def md5(string: str):
    if string:
        return hashlib.md5(string.encode()).hexdigest()
    else:
        return None


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
        # TODO handle missing profile
        profile = None
        for profile_dir in self.profile_dirs:
            profile_path = os.path.join(profile_dir, profile_name)
            if not os.path.isfile(profile_path):
                continue
            with open(profile_path) as profile_file:
                profile = self.read_file(profile_file)
                break

        if profile:
            return profile
        else:
            raise NoSuchProfileException(profile_name, self.profile_dirs)

    def read_file(self, profile_file_descriptor):
        try:
            result = json.load(profile_file_descriptor)

            rules = result.get('match')

            if rules:
                for k, v in rules.items():
                    # backward compatibility for match.mode
                    if v.get('mode'):
                        logger.warn("%s\n\tmatch.mode is deprecated"
                                    "\n\tConsider changing to 'supports' or 'prefers'", profile_file_descriptor.name)
                        v['supports'] = v['mode']
                        del v['mode']
                    rules[k] = Rule(**v)
            else:
                rules = {}

            primary = result['primary']
            outputs_raw = result['outputs']
            outputs = []
            for name, mode_raw in outputs_raw.items():
                output = Output(name, **mode_raw)
                outputs.append(output)

            name = os.path.basename(profile_file_descriptor.name)

            return Profile(name, outputs, rules, primary)
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
            json.dump(dict, fp, indent=4, sort_keys=True)

    def print(self, p: Profile):
        dict = self.to_dict(p)
        print(json.dumps(dict, indent=4, sort_keys=True))

    def to_dict(self, p: Profile):
        outputs = {}
        primary = None
        for o in p.outputs:
            outputs[o.name] = o.todict()
            if p.primary == o.name:
                primary = o.name

        result = {'outputs': outputs, 'primary': primary}

        if p.rules:
            rules = {}
            for o, r in p.rules.items():
                rules[o] = dict((k, v) for k, v in r.__dict__.items() if v is not None)
            result['match'] = rules

        return result

    def profile_from_xrandr(self, xrandr_connections: list, name: str='profile'):
        outputs = []
        rules = {}
        primary = None
        for c in xrandr_connections:
            display = c.display
            if not display or not c.is_active():
                continue
            output = Output.fromconnection(c)
            if c.primary:
                primary = c.name
            outputs.append(output)
            rule = Rule(md5(display.edid), display.preferred_mode, display.mode)
            rules[c.name] = rule

        logger.debug("Extracted %d outputs from %d xrandr connections", len(outputs), len(xrandr_connections))

        return Profile(name, outputs, rules, primary)


class ProfileMatcher:
    """
    Matches profile to xrandr connections
    """
    def find_best(self, available_profiles: list, xrandr_outputs: list):
        """
        Find first matching profile across availableProfiles for actualConnections
        """
        output_names = set(map(lambda o: o.name, xrandr_outputs))

        # remove those with different outputs set
        profiles = filter(lambda p: set(p.rules) == output_names, available_profiles)
        profiles = list(profiles)

        logger.debug("%d/%d profiles match outputs sets", len(profiles), len(available_profiles))

        if len(profiles) == 0:
            return None

        matching = []
        for p in profiles:
            score = self._calculate_profile_score(p, xrandr_outputs)
            if score >= 0:
                matching.append((score, p))

        if len(matching) > 0:
            # profiles are unorderable, so we only consider score
            (s, p) = max(matching, key=lambda t: t[0])
            logger.debug("Selected profile %s with score %d", p.name, s)
            return p
        else:
            return None

    def _calculate_profile_score(self, p: Profile, xrandr_outputs: list):
        """
        Calculate how profile matches passed specific outputs.
        Return numeric score
        """
        score = 0
        logger.debug("Trying profile %s", p.name)
        for o in xrandr_outputs:
            rule = p.rules.get(o.name)
            s = self._score_rule(rule, o)
            logger.debug("%s scored %d for output %s", p.name, s, o.name)
            if s >= 0:
                score += s
            else:
                logger.debug("%s doesn't match %s", p.name, o.name)
                score = -1
                break
        logger.debug("%s total score: %d", p.name, score)
        return score

    def _score_rule(self, rule: Rule, xrandr_output: XrandrConnection):
        """
        0 if match is not needed by a criterion (i.e. edid is not set, mode is not set)
        1 if matches by supported mode
        2 if matches by preferred mode
        3 if matches by edid
        returns sum of scores, -1 if doesn't match
        """
        score = 0
        if rule.edid:
            if rule.edid == md5(xrandr_output.display.edid):
                score += 3
            else:
                return -1

        if rule.prefers:
            if xrandr_output.display.preferred_mode == rule.prefers:
                score += 2
            else:
                return -1

        if rule.supports:
            if xrandr_output.display.supported_modes.count(rule.supports) > 0:
                score += 1
            else:
                return -1
        return score
