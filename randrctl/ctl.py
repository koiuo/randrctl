from configparser import ConfigParser
import os
import logging
import subprocess
import sys
from randrctl.model import Profile

from randrctl.profile import ProfileManager, ProfileMatcher
from randrctl.xrandr import Xrandr


__author__ = 'edio'

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
            logger.warn("No matching profile found")

    def dump_current(self, name: str, to_file: bool=False,
                     include_supports_rule: bool=True,
                     include_preferred_rule: bool=True,
                     include_edid_rule: bool=True,
                     include_refresh_rate: bool=False):
        """
        Dump current profile under specified name. Only xrandr settings are dumped
        """
        xrandr_connections = self.xrandr.get_connected_outputs()
        profile = self.profile_manager.profile_from_xrandr(xrandr_connections, name)

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
                output.geometry.rate = None

        if to_file:
            self.profile_manager.write(profile)
        else:
            self.profile_manager.print(profile)

    def print(self, name: str):
        """
        Print specified profile to stdout
        """
        p = self.profile_manager.read_one(name)
        self.profile_manager.print(p)

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


class Hook:
    """
    Intercepts calls to xrandr to support prior-, post-switch and post-fail hooks
    """

    def __init__(self, prior_switch: str=None, post_switch: str=None, post_fail: str=None):
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

    def hook(self, hook: str, p: Profile, err: str=None):
        if hook is not None and len(hook.strip()) > 0:
            try:
                env = os.environ.copy()
                env["randr_profile"] = p.name
                if err:
                    env["randr_error"] = err
                logger.debug("Calling '%s'", hook)
                subprocess.Popen(hook, env=env, shell=True)
            except Exception as e:
                logger.warn("Error while executing hook '%s': %s", hook, str(e))


class CtlFactory:
    """
    Parses config and creates appropriate Randrctl object
    """

    config_name = "config.ini"
    profile_dir = "profiles"

    def __init__(self, homes: list):
        """
        param homes: list of homes to use. The first one is preferred. Others are alternative
        """
        self.preferred_home = homes[0]
        self.homes = homes

    def ensure_homes(self):
        valid_homes = list(filter(self.is_valid_home, self.homes))

        if len(valid_homes) == 0:
            logger.warn("No home directories found among %s", self.homes)
            self.init_home(self.preferred_home)
            valid_homes = [self.preferred_home]
        elif valid_homes.count(self.preferred_home) == 0:
            logger.warn("No home directory found under preferred location %s", self.preferred_home)

        self.homes = valid_homes
        logger.info("Using %s as home directories", self.homes)

    def get_safe(self, config, section, property):
        return config.get(section, property) if config.has_option(section, property) else None

    def get_randrctl(self):
        config = ConfigParser(allow_no_value=True, strict=False)

        config_files = list(map(lambda x: os.path.join(x, self.config_name), self.homes))
        config_files.reverse()
        read = config.read(config_files)
        logger.debug("read configuration from %s", read)

        # profile manager
        profile_paths = list(map(lambda x: os.path.join(x, self.profile_dir), self.homes))
        profile_reader = ProfileManager(profile_paths)

        # xrandr
        xrandr = Xrandr()

        # hooks
        prior_switch = self.get_safe(config, "hooks", "prior_switch")
        post_switch = self.get_safe(config, "hooks", "post_switch")
        post_fail = self.get_safe(config, "hooks", "post_fail")
        if (prior_switch is not None) | (post_switch is not None) | (post_fail is not None):
            hook = Hook(prior_switch, post_switch, post_fail)
            xrandr = hook.decorate(xrandr)

        return RandrCtl(profile_reader, xrandr)

    def is_valid_home(self, home_dir: str):
        profiles = os.path.join(home_dir, self.profile_dir)
        return os.path.isdir(profiles)

    def init_home(self, home_dir: str):
        logger.warn("Creating home under %s", home_dir)
        config = os.path.join(home_dir, self.config_name)
        profiles = os.path.join(home_dir, self.profile_dir)
        os.makedirs(profiles, exist_ok=True)
        with open(config, mode="w+") as cf:
            print("# autogenerated\n", file=cf)
