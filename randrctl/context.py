from os import path

import logging
import os
import yaml

from yaml import load, YAMLError

from randrctl.ctl import Hooks, RandrCtl
from randrctl.profile import ProfileManager
from randrctl.xrandr import Xrandr

logger = logging.getLogger(__name__)

CONFIG_NAME = "config.yaml"
PROFILE_DIR_NAME = "profiles"
DEFAULT_CONFIG_LOCATION = ".config/randrctl"
SYS_CONFIG_DIR = "/etc/randrctl"


def default_config_dirs(owner_home="$HOME"):
    """
    :return: default list of directories to look for a config in
    """
    # $HOME is guaranteed to exist on POSIX
    dirs = [
        _recursive_expand(path.join(owner_home, DEFAULT_CONFIG_LOCATION)),
        SYS_CONFIG_DIR,
    ]

    # if XDG_CONFIG_HOME is defined, use it too
    # TODO this won't work if executed by udev. Remove entirely?
    if os.environ.get('XDG_CONFIG_HOME'):
        dirs.insert(0, _recursive_expand('$XDG_CONFIG_HOME/randrctl'))

    return dirs


def _recursive_expand(path: str):
    expanded = os.path.expandvars(path)
    while expanded != path:
        path = expanded
        expanded = os.path.expandvars(path)
    return expanded


def configs(config_dirs: list):
    """
    Lazily visits specified directories and tries to parse a config file. If succeeds, yeilds a tuple (dir, config),
    where config is a dict
    :param config_dirs: list of directories that may contain configs
    :return: an iterator over tuples (config_dir, parsed_config), empty iterator if there are not valid configs
    """
    for randrctl_home in config_dirs:
        config_file = os.path.join(randrctl_home, CONFIG_NAME)
        if os.path.isfile(config_file):
            with open(config_file, 'r') as stream:
                try:
                    logger.debug("reading configuration from %s", config_file)
                    cfg = load(stream, Loader=yaml.FullLoader)
                    if cfg:
                        yield (randrctl_home, cfg)
                except YAMLError as e:
                    logger.warning("error reading configuration file %s", config_file)


def build(display: str, xauthority: str = None, config_dirs=None):
    """
    Builds a RandrCtl instance and all its dependencies given a list of config directories
    :param: display - display
    :return: new ready to use RandrCtl instance
    """
    if config_dirs is None:
        config_dirs = default_config_dirs()

    (primary_config_dir, config) = next(configs(config_dirs), (config_dirs[0], dict()))

    prior_switch = config.get('hooks', dict()).get('prior_switch', None)
    post_switch = config.get('hooks', dict()).get('post_switch', None)
    post_fail = config.get('hooks', dict()).get('post_fail', None)
    hooks = Hooks(prior_switch, post_switch, post_fail)

    profile_read_locations = [os.path.join(primary_config_dir, PROFILE_DIR_NAME)]
    profile_write_location = os.path.join(primary_config_dir, PROFILE_DIR_NAME)
    profile_manager = ProfileManager(profile_read_locations, profile_write_location)

    xrandr = Xrandr(display, xauthority)

    return RandrCtl(profile_manager, xrandr, hooks)




