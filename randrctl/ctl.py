import logging
import os
import subprocess

from randrctl.model import Profile
from randrctl.profile import ProfileManager, ProfileMatcher
from randrctl.xrandr import Xrandr

logger = logging.getLogger(__name__)


class Hooks:
    """
    Intercepts calls to xrandr to support prior-, post-switch and post-fail hooks
    """

    def __init__(self, prior_switch: str, post_switch: str, post_fail: str):
        self._prior_switch = prior_switch
        self._post_switch = post_switch
        self._post_fail = post_fail

    def prior_switch(self, p: Profile):
        if self._prior_switch:
            self._hook(self._prior_switch, p)

    def post_switch(self, p: Profile):
        if self._post_switch:
            self._hook(self._post_switch, p)

    def post_fail(self, p: Profile, err: str):
        if self._post_fail:
            self._hook(self._post_fail, p, err)

    def _hook(self, hook: str, p: Profile, err: str = None):
        if hook is not None and len(hook.strip()) > 0:
            try:
                env = os.environ.copy()
                env["randr_profile"] = p.name
                if err:
                    env["randr_error"] = err
                logger.debug("Calling '%s'", hook)
                subprocess.run(hook, env=env, shell=True)
            except Exception as e:
                logger.warning("Error while executing hook '%s': %s", hook, str(e))


class RandrCtl:
    """
    Facade that ties all the classes together and provides simple interface
    """

    def __init__(self, profile_manager: ProfileManager, xrandr: Xrandr, hooks: Hooks):
        self.profile_manager = profile_manager
        self.xrandr = xrandr
        self.hooks = hooks

    def _apply(self, p: Profile):
        try:
            self.hooks.prior_switch(p)
            self.xrandr.apply(p)
            self.hooks.post_switch(p)
        except Exception as e:
            self.hooks.post_fail(p, str(e))
            raise e

    def switch_to(self, profile_name):
        """
        Apply profile settings by profile name
        """
        p = self.profile_manager.read_one(profile_name)
        self._apply(p)

    def switch_auto(self):
        """
        Try to find profile by display EDID and apply it
        """
        profiles = self.profile_manager.read_all()
        xrandr_outputs = self.xrandr.get_connected_outputs()

        profileMatcher = ProfileMatcher()
        matching = profileMatcher.find_best(profiles, xrandr_outputs)

        if matching is not None:
            self._apply(matching)
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
            profile.match = None
        else:
            for rule in profile.match.values():
                if not include_supports_rule:
                    rule.supports = None
                if not include_preferred_rule:
                    rule.prefers = None
                if not include_edid_rule:
                    rule.edid = None

        if not include_refresh_rate:
            for output in profile.outputs.values():
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



