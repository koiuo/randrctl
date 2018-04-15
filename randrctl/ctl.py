from configparser import ConfigParser
from yaml import load, YAMLError
import os
import logging
import subprocess

from randrctl.model import Profile
from randrctl.profile import ProfileManager, ProfileMatcher
from randrctl.xrandr import Xrandr

logger = logging.getLogger(__name__)


class RandrCtl:
    """
    Facade that ties all the classes together and provides simple interface
    """

    def __init__(self, profile_manager: ProfileManager, xrandr: Xrandr):
        self.profile_manager = profile_manager
        self.xrandr = xrandr

    def switch_to(self, profile_name):
        """
        Apply profile settings by profile name
        """
        p = self.profile_manager.read_one(profile_name)
        self.xrandr.apply(p)

    def switch_auto(self):
        """
        Try to find profile by display EDID and apply it
        """
        profiles = self.profile_manager.read_all()
        xrandr_outputs = self.xrandr.get_connected_outputs()

        profileMatcher = ProfileMatcher()
        matching = profileMatcher.find_best(profiles, xrandr_outputs)

        if matching is not None:
            self.xrandr.apply(matching)
        else:
            logger.warning("No matching profile found")

    def dump_current(self, name: str, to_file: bool = False,
                     include_supports_rule: bool = True,
                     include_preferred_rule: bool = True,
                     include_edid_rule: bool = True,
                     include_refresh_rate: bool = True,
                     priority: int = 100,
                     json_compatible: bool = False):
        """
        Dump current profile under specified name. Only xrandr settings are dumped
        """
        xrandr_connections = self.xrandr.get_connected_outputs()
        profile = self.profile_manager.profile_from_xrandr(xrandr_connections, name)
        profile.priority = priority

        # TODO move logic to manager
        if not (include_edid_rule or include_supports_rule or include_preferred_rule):
            profile.rules = None
        else:
            for output, rule in profile.rules.items():
                if not include_supports_rule:
                    rule.supports = None
                if not include_preferred_rule:
                    rule.prefers = None
                if not include_edid_rule:
                    rule.edid = None

        if not include_refresh_rate:
            for output in profile.outputs:
                output.rate = None

        if to_file:
            self.profile_manager.write(profile, yaml_flow_style=json_compatible)
        else:
            self.profile_manager.print(profile, yaml_flow_style=json_compatible)

    def print(self, name: str, json_compatible: bool = False):
        """
        Print specified profile to stdout
        """
        p = self.profile_manager.read_one(name)
        self.profile_manager.print(p, yaml_flow_style=json_compatible)

    def list_all(self):
        """
        List all available profiles
        """
        profiles = self.profile_manager.read_all()
        for p in profiles:
            print(p.name)

    def list_all_long(self):
        """
        List all available profiles along with some details
        """
        profiles = self.profile_manager.read_all()
        for p in profiles:
            print(p.name)
            for o in p.outputs:
                print('  ', o)

    def list_all_scored(self):
        """
        List matched profiles with scores
        """
        profiles = self.profile_manager.read_all()
        xrandr_outputs = self.xrandr.get_connected_outputs()

        profileMatcher = ProfileMatcher()
        matching = profileMatcher.match(profiles, xrandr_outputs)

        for score, p in matching:
            print(p.name, score)


class Hook:
    """
    Intercepts calls to xrandr to support prior-, post-switch and post-fail hooks
    """

    def __init__(self, prior_switch: str = None, post_switch: str = None, post_fail: str = None):
        self.prior_switch = prior_switch
        self.post_switch = post_switch
        self.post_fail = post_fail

    def decorate(self, xrandr: Xrandr):
        do_apply = xrandr.apply

        def apply_hook(p: Profile):
            try:
                self.hook(self.prior_switch, p)
                do_apply(p)
                self.hook(self.post_switch, p)
            except Exception as e:
                self.hook(self.post_fail, p, str(e))
                raise e

        xrandr.apply = apply_hook
        return xrandr

    def hook(self, hook: str, p: Profile, err: str = None):
        if hook is not None and len(hook.strip()) > 0:
            try:
                env = os.environ.copy()
                env["randr_profile"] = p.name
                if err:
                    env["randr_error"] = err
                logger.debug("Calling '%s'", hook)
                subprocess.Popen(hook, env=env, shell=True)
            except Exception as e:
                logger.warning("Error while executing hook '%s': %s", hook, str(e))


class CtlFactory:
    """
    Parses config and creates appropriate Randrctl object
    """

    config_name = ["config.yaml", "config.ini"]
    profile_dir = "profiles"

    PREFERRED = 'preferred'
    OTHER = 'other'

    def __init__(self, homes: list):
        """
        param homes: list of homes to use. The first one is preferred. Others are alternative
        """
        self.preferred_home = homes[0]
        self.homes = homes

    def ensure_homes(self):
        valid_homes = list(filter(self.is_valid_home, self.homes))

        if len(valid_homes) == 0:
            logger.warning("No home directories found among %s", self.homes)
            self.init_home(self.preferred_home)
            valid_homes = [self.preferred_home]
        elif valid_homes.count(self.preferred_home) == 0:
            logger.warning("No home directory found under preferred location %s", self.preferred_home)

        self.homes = valid_homes
        logger.info("Using %s as home directories", self.homes)

    def _config_safe(self, config: dict, section: str, property: str):
        """
        read property from config safely
        :param config: config dictionary
        :param section: section name to read
        :param property: property name to read
        :return: property value or None
        """
        return config.get(section).get(property) if section in config else None

    def _configs(self):
        """
        :return: dictionary of config files in defined home directories if exist
        """
        # Empty container to hold the configs
        configs = {}
        for homedir in self.homes:
            # Configs will be either user's (prefered) or system-wide (other)
            config_group = self.PREFERRED if homedir == self.preferred_home else self.OTHER
            # Create new entry
            configs[config_group] = []
            # Load both YAML and INI config files
            for config_format in self.config_name:
              config = os.path.join(homedir, config_format)
              if os.path.isfile(config):
                  configs[config_group].append(config)

        # Return dictionary with the configuration files
        return configs

    def _load_config_files(self):
        """
        :return: dictionary of configurations loaded from config files
        """
        # Get config file paths
        config_files = self._configs()

        # If available, use preferred configs, otherwise use the others
        use = self.PREFERRED if config_files.get(self.PREFERRED) else self.OTHER

        # Fetch list of yaml files
        yaml_files = [config_file for config_file in config_files[use] if config_file.endswith('yaml')]
        # Fetch list of ini files
        ini_files = [config_file for config_file in config_files[use] if config_file.endswith('ini')]

        # Empty container to hold the configuration
        config = {}

        if yaml_files:
          with open(yaml_files[0], 'r') as stream:
            # Try to parse the YAML file  and update the configuration dictionary
            try:
              config.update(load(stream))
            except YAMLError as e:
              logger.warning("error reading configuration file %s", yaml_files[0])
            else:
              logger.debug("read configuration from %s", yaml_files[0])

        elif ini_files:
          # Warning message indicating deprecation
          logger.warning(
            "INI configuration is deprecated and will be removed in next minor release\n" +
            "Please convert %s to yaml format\n" +
            "Visit https://github.com/edio/randrctl#priorpost-hooks for details", ini_files[0]) 


          # Instantiate config parser
          config_parser = ConfigParser(allow_no_value=True, strict=False)

          # Try to read the config files
          try:
            read = config_parser.read(ini_files[0])
          except Exception as e:
            logger.warning("error reading configuration files")
          else:
            config = {section: dict(config_parser.items(section)) for section in config_parser.sections()}
            logger.debug("read configuration from %s", ini_files[0])

        # Otherwise, there are no configuration files whatsoever
        else:
          logger.debug("there are no configuration files available")

        return config

    def get_randrctl(self):
        # Load configuration files as a dictionary
        config = self._load_config_files()

        # profile manager
        profile_paths = list(map(lambda x: os.path.join(x, self.profile_dir), self.homes))
        profile_reader = ProfileManager(profile_paths)

        # xrandr
        xrandr = Xrandr()

        # hooks
        prior_switch = self._config_safe(config, "hooks", "prior_switch")
        post_switch = self._config_safe(config, "hooks", "post_switch")
        post_fail = self._config_safe(config, "hooks", "post_fail")
        if (prior_switch is not None) | (post_switch is not None) | (post_fail is not None):
            hook = Hook(prior_switch, post_switch, post_fail)
            xrandr = hook.decorate(xrandr)

        return RandrCtl(profile_reader, xrandr)

    def is_valid_home(self, home_dir: str):
        profiles = os.path.join(home_dir, self.profile_dir)
        return os.path.isdir(profiles)

    def init_home(self, home_dir: str):
        logger.warning("Creating home under %s", home_dir)
        profiles = os.path.join(home_dir, self.profile_dir)
        os.makedirs(profiles, exist_ok=True)
