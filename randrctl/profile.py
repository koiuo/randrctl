import hashlib
import logging
import os
import yaml

from randrctl.exception import InvalidProfileException, NoSuchProfileException
from randrctl.model import Profile, Rule, Output, XrandrConnection

logger = logging.getLogger(__name__)


def hash(string: str):
    if string:
        return hashlib.md5(string.encode()).hexdigest()
    else:
        return None


class ProfileManager:
    def __init__(self, read_locations: list, write_location: str):
        self.read_locations = list(filter(lambda location: os.path.isdir(location), read_locations))
        self.write_location = write_location

    def read_all(self):
        profiles = []
        for profile_dir in self.read_locations:
            for entry in os.listdir(profile_dir):
                path = os.path.join(profile_dir, entry)
                if os.path.isfile(path):
                    try:
                        with open(path) as profile_file:
                            profiles.append(self.read_file(profile_file))
                    except InvalidProfileException as e:
                        logger.warning(e)
        return profiles

    def read_one(self, profile_name: str):
        # TODO handle missing profile
        profile = None
        for profile_dir in self.read_locations:
            profile_path = os.path.join(profile_dir, profile_name)
            if not os.path.isfile(profile_path):
                continue
            with open(profile_path) as profile_file:
                profile = self.read_file(profile_file)
                break

        if profile:
            return profile
        else:
            raise NoSuchProfileException(profile_name, self.read_locations)

    def read_file(self, profile_file_descriptor):
        try:
            result = yaml.load(profile_file_descriptor, Loader=yaml.FullLoader)

            rules = result.get('match')
            priority = int(result.get('priority', 100))

            if rules:
                for k, v in rules.items():
                    # backward compatibility for match.mode
                    if v.get('mode'):
                        logger.warning("%s\n\tmatch.mode is deprecated"
                                    "\n\tConsider changing to 'supports' or 'prefers'", profile_file_descriptor.name)
                        v['supports'] = v['mode']
                        del v['mode']
                    rules[k] = Rule(**v)

            primary = result.get('primary')
            outputs_raw = result['outputs']
            outputs = {}
            for name, mode_raw in outputs_raw.items():
                outputs[name] = Output(**mode_raw)

            name = os.path.basename(profile_file_descriptor.name)

            return Profile(name, outputs, rules, primary, priority)
        except (KeyError, ValueError):
            raise InvalidProfileException(profile_file_descriptor.name)

    def write(self, p: Profile, yaml_flow_style: bool=False):
        """
        Write profile to file into configured profile directory.
        Profile name becomes the name of the file. If name contains illegal characters, only safe part is used.
        For example, if name is my_home_vga/../../passwd, then file will be written as passwd under profile dir
        """
        os.makedirs(self.write_location, exist_ok=True)
        dict = p.to_dict()
        safename = os.path.basename(p.name)
        fullname = os.path.join(self.write_location, safename)
        if safename != p.name:
            logger.warning("Illegal name provided. Writing as %s", fullname)
        with open(fullname, 'w+') as fp:
            yaml.dump(dict, fp, default_flow_style=yaml_flow_style)

    def print(self, p: Profile, yaml_flow_style: bool=False):
        print(yaml.dump(p.to_dict(), default_flow_style=yaml_flow_style))

    def profile_from_xrandr(self, xrandr_connections: list, profile_name: str='profile'):
        outputs = {}
        rules = {}
        primary = None
        for connection in xrandr_connections:
            output_name = connection.name
            display = connection.display
            if not display or not connection.is_active():
                continue
            output = Output.fromconnection(connection)
            if connection.primary:
                primary = output_name
            outputs[output_name] = output
            rule = Rule(hash(display.edid), display.preferred_mode, display.mode)
            rules[output_name] = rule

        logger.debug("Extracted %d outputs from %d xrandr connections", len(outputs), len(xrandr_connections))

        return Profile(profile_name, outputs, rules, primary)


class ProfileMatcher:
    """
    Matches profile to xrandr connections
    """
    def match(self, available_profiles: list, xrandr_outputs: list):
        """
        return a sorted list of matched profiles
        """
        output_names = set(map(lambda o: o.name, xrandr_outputs))

        # remove those with disconnected outputs
        with_rules = filter(lambda p: p.match and len(p.match) > 0, available_profiles)
        with_rules_covering_outputs = filter(lambda p: len(set(p.match) - output_names) == 0, with_rules)
        profiles = list(with_rules_covering_outputs)

        logger.debug("%d/%d profiles match outputs sets", len(profiles), len(available_profiles))

        matching = []
        for p in profiles:
            score = self._calculate_profile_score(p, xrandr_outputs)
            if score >= 0:
                matching.append((score, p))
        return sorted(matching, key=lambda x: (x[0], x[1].priority), reverse=True)

    def find_best(self, available_profiles: list, xrandr_outputs: list):
        """
        Find first matching profile across availableProfiles for actualConnections
        """
        matching = self.match(available_profiles, xrandr_outputs)

        if not matching:
            return None

        max_score, p = matching[0]
        logger.debug("Found %d profiles with maximum score %d", len(matching), max_score)
        logger.debug("Selected profile %s with score %d and priority %d", p.name, max_score, p.priority)
        return p

    def _calculate_profile_score(self, p: Profile, xrandr_outputs: list):
        """
        Calculate how profile matches passed specific outputs.
        Return numeric score
        """
        score = 0
        logger.debug("Trying profile %s", p.name)
        for o in xrandr_outputs:
            rule = p.match.get(o.name)
            s = self._score_rule(rule, o) if rule is not None else 0
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
        Starting rule score is 0 (a rule without any additional criteria for a connection still triggers auto-matching).
        Criteria, if defined, are checked and resulting rule score increases with every matched criterion.
        If any of the defined criteria fails to match, -1 is immediately returned.
        """
        score = 0
        if rule.edid:
            if rule.edid == hash(xrandr_output.display.edid):
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
