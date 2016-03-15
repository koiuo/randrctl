import os
import sys
import argparse
import logging

import pkg_resources

from randrctl.ctl import CtlFactory
from randrctl.exception import RandrCtlException

__author__ = 'edio'
logger = logging.getLogger('randrctl')

AUTO = 'auto'
DUMP = 'dump'
LIST = 'list'
SHOW = 'show'
SWITCH_TO = 'switch-to'

SYS_HOME_DIR = "/etc/randrctl/"
USER_HOME_DIR = "~/.config/randrctl/"


class Main:
    def run(self):
        parser = argparse.ArgumentParser(prog='randrctl')

        parser.add_argument('-v', '--version', help='print version information and exit', action='store_const',
                            const=True, default=False)

        parser.add_argument('-x', help='be verbose', default=False, action='store_const', const=True,
                            dest='debug')

        parser.add_argument('-X', help='be even more verbose', default=False, action='store_const', const=True,
                            dest='extended_debug')

        parser.add_argument('--system',
                            help="read profiles and config only from {}. By default {} are used".format(SYS_HOME_DIR,
                                                                                                        [USER_HOME_DIR,
                                                                                                         SYS_HOME_DIR]),
                            action='store_const', const=True, default=False, dest="sys")

        commands_parsers = parser.add_subparsers(title='Available commands',
                                                 description='use "command -h" for details',
                                                 # metavar='command',
                                                 dest='command', )
        # commands_parsers.required = True

        # switch-to
        command_switch_to = commands_parsers.add_parser(SWITCH_TO, help='switch to profile')
        command_switch_to.add_argument('profile_name', help='name of the profile to switch to')

        # show
        command_show = commands_parsers.add_parser(SHOW, help='show profile')
        command_show.add_argument('profile_name', help='name of the profile to show. Show current setup if omitted',
                                  default=None, nargs='?')

        # list
        command_list = commands_parsers.add_parser(LIST, help='list available profiles')
        command_list.add_argument('-l', action='store_const', const=True, default=False,
                                  help='long listing', dest='long_listing')

        # dump
        command_dump = commands_parsers.add_parser(DUMP,
                                                   help='dump current screen setup')
        command_dump.add_argument('-m', action='store_const', const=True, default=False,
                                  help='dump with match by supported mode', dest='match_supports')
        command_dump.add_argument('-p', action='store_const', const=True, default=False,
                                  help='dump with match by preferred mode', dest='match_preferred')
        command_dump.add_argument('-e', action='store_const', const=True, default=False,
                                  help='dump with match by edid', dest='match_edid')
        command_dump.add_argument('-r', action='store_const', const=True, default=False,
                                  help='dump current refresh rate (for all outputs)', dest='dump_rate')
        command_dump.add_argument('profile_name', help='name of the profile to dump setup to')

        # auto
        command_auto = commands_parsers.add_parser(AUTO,
                                                   help='automatically switch to the best matching profile')

        args = parser.parse_args(sys.argv[1:])

        if args.version:
            print(self.get_version())
            sys.exit(0)

        if args.command is None:
            parser.print_help()
            sys.exit(1)

        # configure logging
        level = logging.WARN
        format = '%(levelname)-5s %(message)s'
        if args.debug:
            level = logging.DEBUG

        if args.extended_debug:
            level = logging.DEBUG
            format = '%(levelname)-5s %(name)s: %(message)s'

        logging.basicConfig(format=format, level=level)

        homes = [SYS_HOME_DIR] if args.sys else [os.path.expanduser(USER_HOME_DIR), SYS_HOME_DIR]

        # randrctl
        factory = CtlFactory(homes)
        factory.ensure_homes()
        self.randrctl = factory.get_randrctl()

        try:
            {
                SWITCH_TO: self.switch_to,
                LIST: self.list,
                SHOW: self.show,
                DUMP: self.dump,
                AUTO: self.auto
            }[args.command](args)
        except RandrCtlException as e:
            logger.error(e)
            sys.exit(1)

    def list(self, args: argparse.Namespace):
        if args.long_listing:
            self.randrctl.list_all_long()
        else:
            self.randrctl.list_all()

    def switch_to(self, args: argparse.Namespace):
        self.randrctl.switch_to(args.profile_name)

    def show(self, args: argparse.Namespace):
        if args.profile_name:
            self.randrctl.print(args.profile_name)
        else:
            self.randrctl.dump_current('current')

    def dump(self, args: argparse.Namespace):
        self.randrctl.dump_current(name=args.profile_name, to_file=True,
                                   include_supports_rule=args.match_supports,
                                   include_preferred_rule=args.match_preferred,
                                   include_edid_rule=args.match_edid,
                                   include_refresh_rate=args.dump_rate)

    def auto(self, args: argparse.Namespace):
        self.randrctl.switch_auto()

    def get_version(self):
        return pkg_resources.get_distribution("randrctl").version

if __name__ == '__main__':
    Main().run()
