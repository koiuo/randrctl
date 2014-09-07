import sys
import argparse
import randrctl
from randrctl.ctl import CtlFactory

__author__ = 'edio'

DUMP = 'dump'
LIST = 'list'
SWITCH_TO = 'switch-to'
SHOW = 'show'

HOME_DIR = "/etc/randrctl"


class Main:
    def run(self):
        parser = argparse.ArgumentParser(prog='randrctl',
                                         formatter_class=lambda prog: argparse.HelpFormatter(prog,
                                                                                             max_help_position=30))

        parser.add_argument('-v', '--version', help='print version information', action='store_const', const=True,
                            default=False)

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
        command_show.add_argument('profile_name', help='name of the profile to show')

        # list
        command_list = commands_parsers.add_parser(LIST, help='list available profiles')
        command_list.add_argument('-d', action='store_const', const=True, default=False,
                                  help='print brief profile details instead of just names', dest='details')

        #dump
        command_dump = commands_parsers.add_parser(DUMP,
                                                   help='dump current screen setup')
        command_dump.add_argument('-f', help='store profile to file under profile directory', dest='file_name')

        args = parser.parse_args(sys.argv[1:])

        if args.version:
            print(randrctl.__version__)
            sys.exit(0)

        if args.command is None:
            parser.print_help()
            sys.exit(1)

        factory = CtlFactory()
        self.randrctl = factory.getRandrCtl(HOME_DIR)

        {
            SWITCH_TO: self.switch_to,
            LIST: self.list,
            SHOW: self.show,
            DUMP: self.dump
        }[args.command](args)

    def list(self, args: argparse.Namespace):
        if args.details:
            self.randrctl.list_all_details()
        else:
            self.randrctl.list_all()

    def switch_to(self, args: argparse.Namespace):
        self.randrctl.switch_to(args.profile_name)

    def show(self, args: argparse.Namespace):
        self.randrctl.print(args.profile_name)

    def dump(self, args: argparse.Namespace):
        name = args.file_name
        self.randrctl.dump_current(name=name, to_file=name is not None)


if __name__ == '__main__':
    Main().run()
