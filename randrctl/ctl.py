from configparser import ConfigParser
import os
import logging
import subprocess
import sys

from randrctl.hotplug import SysfsDevice
from randrctl.profile import ProfileManager, ProfileMatcher, Profile
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

    def switch_by_edid(self, sysfsroot, devpath):
        """
        Try to find profile by display EDID and apply it
        """
        device = SysfsDevice(sysfsroot, devpath)
        connections = device.get_active_connections()

        profiles = self.profile_manager.read_all()

        profileMatcher = ProfileMatcher()
        matching = profileMatcher.findFirst(profiles, connections)

        if matching is not None:
            self.xrandr.apply(matching)

    def dump_current(self, name: str, to_file: bool=False):
        """
        Dump current profile under specified name. Only xrandr settings are dumped
        """
        xrandr_connections = self.xrandr.get_all_connections()
        profile = self.profile_manager.profile_from_xrandr(xrandr_connections, name)

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
        if hook is not None:
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

    def get_safe(self, config, section, property):
        return config.get(section, property) if config.has_option(section, property) else None

    def get_randrctl(self, home_dir: str):
        config = ConfigParser(allow_no_value=True, strict=False)

        logger.debug("reading config from %s", os.path.abspath(os.path.join(home_dir, self.config_name)))
        config.read(os.path.join(home_dir, self.config_name))

        # profile manager
        profile_reader = ProfileManager(os.path.join(home_dir, self.profile_dir))

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
