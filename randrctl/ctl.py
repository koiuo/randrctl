from configparser import ConfigParser
import os
import logging
import subprocess

from randrctl.hotplug import SysfsDevice
from randrctl.profile import ProfileManager, ProfileMatcher, Profile
from randrctl.xrandr import Xrandr


__author__ = 'edio'


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


class CtlFactory:
    """
    Parses config and creates appropriate Randrctl object
    """

    config_name = "config.ini"
    profile_dir = "profiles"

    def getRandrCtl(self, home_dir: str):
        config = ConfigParser(allow_no_value=True, strict=False)

        logging.debug("reading config from %s", os.path.abspath(os.path.join(home_dir, self.config_name)))
        config.read(os.path.join(home_dir, self.config_name))

        # profile manager
        profile_reader = ProfileManager(os.path.join(home_dir, self.profile_dir))

        # xrandr
        before_hook = self.run_hook(config.get("hooks", "before_apply")) if config.has_option("hooks",
                                                                                              "before_apply") else None
        after_hook = self.run_hook(config.get("hooks", "after_apply")) if config.has_option("hooks",
                                                                                            "after_apply") else None
        xrandr = Xrandr(before_hook, after_hook)

        # sysfs
        # sysfs_device = SysfsDevice(config.get("sysfs", "root"), config.get("sysfs", "devpath"))

        return RandrCtl(profile_reader, xrandr)

    def run_hook(self, hook: str):
        def hook_fn(p: Profile):
            if hook is not None:
                env = os.environ.copy()
                env["randr_profile"] = p.name
                subprocess.Popen(hook, env=env, shell=True)

        return hook_fn
