import argparse
import logging
import os
import shutil
import sys
import textwrap

import argcomplete
import pkg_resources

from randrctl import context
from randrctl.ctl import RandrCtl
from randrctl.exception import RandrCtlException

AUTO = 'auto'
DUMP = 'dump'
LIST = 'list'
SHOW = 'show'
SWITCH_TO = 'switch-to'
VERSION = 'version'

SETUP = 'setup'
SETUP_COMPLETION = 'completion'
SETUP_UDEV = 'udev'
SETUP_CONFIG = 'config'


logger = logging.getLogger('randrctl')


def potential_profiles(config_dirs: list):
    profile_dirs = map(lambda config_dir: os.path.join(config_dir, context.PROFILE_DIR_NAME), config_dirs)
    existing = filter(lambda profile_dir: os.path.isdir(profile_dir), profile_dirs)
    listings = map(lambda profile_dir: os.listdir(profile_dir), existing)
    flat_listing = [item for sublist in listings for item in sublist]
    return sorted(flat_listing)


def complete_profiles(prefix, parsed_args, **kwargs):
    return (profile for profile in potential_profiles(context.default_config_dirs()) if profile.startswith(prefix))


def args_parser():
    parser = argparse.ArgumentParser(prog='randrctl')

    parser.add_argument('-x', help='be verbose', default=False, action='store_const', const=True,
                        dest='debug')

    parser.add_argument('-X', help='be even more verbose', default=False, action='store_const', const=True,
                        dest='extended_debug')

    commands_parsers = parser.add_subparsers(title='Available commands',
                                             description='use "command -h" for details',
                                             dest='command')

    # switch-to
    command_switch_to = commands_parsers.add_parser(SWITCH_TO, help='switch to profile')
    command_switch_to.add_argument('profile_name',
                                   help='name of the profile to switch to').completer = complete_profiles

    # show
    command_show = commands_parsers.add_parser(SHOW, help='show profile')
    command_show.add_argument('-j', '--json', action='store_const', const=True, default=False,
                              help='use JSON-compatible format', dest='json')
    command_show.add_argument('profile_name', help='name of the profile to show. Show current setup if omitted',
                              default=None, nargs='?').completer = complete_profiles

    # list
    command_list = commands_parsers.add_parser(LIST, help='list available profiles')
    command_list.add_argument('-l', action='store_const', const=True, default=False,
                              help='long listing', dest='long_listing')
    command_list.add_argument('-s', action='store_const', const=True, default=False,
                              help='scored listing', dest='scored_listing')

    # dump
    command_dump = commands_parsers.add_parser(DUMP,
                                               help='dump current screen setup')
    command_dump.add_argument('-m', action='store_const', const=True, default=False,
                              help='dump with match by supported mode', dest='match_supports')
    command_dump.add_argument('-p', action='store_const', const=True, default=False,
                              help='dump with match by preferred mode', dest='match_preferred')
    command_dump.add_argument('-e', action='store_const', const=True, default=False,
                              help='dump with match by edid', dest='match_edid')
    command_dump.add_argument('-P', action='store', type=int, default=100, dest='priority',
                              help='profile priority')
    command_dump.add_argument('-j', '--json', action='store_const', const=True, default=False,
                              help='use JSON-compatible format', dest='json')
    command_dump.add_argument('profile_name', help='name of the profile to dump setup to').completer = complete_profiles

    # auto
    command_auto = commands_parsers.add_parser(AUTO,
                                               help='automatically switch to the best matching profile')

    # version
    command_version = commands_parsers.add_parser(VERSION, help='print version information and exit')

    # setup
    command_setup = commands_parsers.add_parser(SETUP, help='perform various setup tasks')
    command_setup_tasks = command_setup.add_subparsers(title='Setup tasks',
                                                       help='use "task -h" for details',
                                                       dest='task')
    command_setup_tasks.add_parser(
        SETUP_UDEV,
        usage="randrctl setup udev > /etc/udev/rules.d/99-randrctl.rules && udevadm control --reload-rules  ",
        help="setup udev rule required for auto-switching",
        description='udev rule is required to notify randrctl about displays being attached or detached, so it can'
                    ' react by applying appropriate profile.'
    )
    command_setup_tasks.add_parser(
        SETUP_COMPLETION, formatter_class=argparse.RawDescriptionHelpFormatter,
        help='setup bash completion',
        usage='randrctl setup completion > /usr/share/bash-completion/completions/randrctl',
        description=textwrap.dedent('''\
        or:
        randrctl setup completion > ~/.bashrc_randrctl 
        echo "source ~/.bashrc_randrctl" >> ~/.bashrc
        ''')
    )
    command_setup_tasks.add_parser(
        SETUP_CONFIG,
        help="create exemplary config.yaml",
        usage="randrctl setup config > ${XDG_CONFIG_HOME:-$HOME/.config}/randrctl/config.yaml",
    )

    argcomplete.autocomplete(parser)

    return parser


def cmd_list(randrctl: RandrCtl, args: argparse.Namespace):
    if args.long_listing:
        randrctl.list_all_long()
    elif args.scored_listing:
        randrctl.list_all_scored()
    else:
        randrctl.list_all()


def cmd_switch_to(randrctl: RandrCtl, args: argparse.Namespace):
    randrctl.switch_to(args.profile_name)


def cmd_show(randrctl: RandrCtl, args: argparse.Namespace):
    if args.profile_name:
        randrctl.print(args.profile_name, json_compatible=args.json)
    else:
        randrctl.dump_current('current', json_compatible=args.json)


def cmd_dump(randrctl: RandrCtl, args: argparse.Namespace):
    randrctl.dump_current(name=args.profile_name, to_file=True,
                          include_supports_rule=args.match_supports,
                          include_preferred_rule=args.match_preferred,
                          include_edid_rule=args.match_edid,
                          include_refresh_rate=args.match_edid,
                          priority=args.priority,
                          json_compatible=args.json)


def cmd_auto(randrctl: RandrCtl, args: argparse.Namespace):
    randrctl.switch_auto()


def cmd_version(randrctl: RandrCtl, args: argparse.Namespace):
    print(pkg_resources.get_distribution("randrctl").version)


def cmd_setup(randrctl: RandrCtl, args: argparse.Namespace):
    if args.task is None:
        sys.stderr.write(f"Available subcommands: {SETUP_COMPLETION}, {SETUP_CONFIG}, {SETUP_UDEV}\n")
        sys.exit(1)

    try:
        {
            SETUP_COMPLETION: cmd_setup_completion,
            SETUP_CONFIG: cmd_setup_config,
            SETUP_UDEV: cmd_setup_udev,
        }[args.task](args)
    except RandrCtlException as e:
        logger.error(e)
        sys.exit(1)


def cmd_setup_completion(args: argparse.Namespace):
    print(argcomplete.shellcode('randrctl', True, 'bash', None))


def cmd_setup_config(args: argparse.Namespace):
    with (open(pkg_resources.resource_filename('randrctl', 'misc/config.yaml'), 'r')) as f:
        shutil.copyfileobj(f, sys.stdout)


def cmd_setup_udev(args: argparse.Namespace):
    with (open(pkg_resources.resource_filename('randrctl', 'misc/99-randrctl.rules'), 'r')) as f:
        shutil.copyfileobj(f, sys.stdout)


def main():
    parser = args_parser()
    args = parser.parse_args(sys.argv[1:])

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # configure logging
    level = logging.WARN
    log_format = '%(levelname)-5s %(message)s'
    if args.debug:
        level = logging.DEBUG

    if args.extended_debug:
        level = logging.DEBUG
        log_format = '%(levelname)-5s %(name)s: %(message)s'

    logging.basicConfig(format=log_format, level=level)

    randrctl = context.build()

    try:
        {
            AUTO: cmd_auto,
            DUMP: cmd_dump,
            LIST: cmd_list,
            SHOW: cmd_show,
            SWITCH_TO: cmd_switch_to,
            VERSION: cmd_version,
            SETUP: cmd_setup,
        }[args.command](randrctl, args)
    except RandrCtlException as e:
        logger.error(e)
        sys.exit(1)
