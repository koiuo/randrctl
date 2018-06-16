import argparse
import logging
import shutil
import sys

import argcomplete
import pkg_resources

from randrctl import context, cli
from randrctl.exception import RandrCtlException

logger = logging.getLogger('randrctl')


class Main:
    def __init__(self):
        self.randrctl = None

    def run(self):
        parser = cli.parser()
        args = parser.parse_args(sys.argv[1:])

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

        self.randrctl = context.build()

        try:
            {
                cli.AUTO: self.auto,
                cli.DUMP: self.dump,
                cli.LIST: self.list,
                cli.SHOW: self.show,
                cli.SWITCH_TO: self.switch_to,
                cli.VERSION: self.version,
                cli.SETUP: self.setup,
            }[args.command](args)
        except RandrCtlException as e:
            logger.error(e)
            sys.exit(1)

    def list(self, args: argparse.Namespace):
        if args.long_listing:
            self.randrctl.list_all_long()
        elif args.scored_listing:
            self.randrctl.list_all_scored()
        else:
            self.randrctl.list_all()

    def switch_to(self, args: argparse.Namespace):
        self.randrctl.switch_to(args.profile_name)

    def show(self, args: argparse.Namespace):
        if args.profile_name:
            self.randrctl.print(args.profile_name, json_compatible=args.json)
        else:
            self.randrctl.dump_current('current', json_compatible=args.json)

    def dump(self, args: argparse.Namespace):
        self.randrctl.dump_current(name=args.profile_name, to_file=True,
                                   include_supports_rule=args.match_supports,
                                   include_preferred_rule=args.match_preferred,
                                   include_edid_rule=args.match_edid,
                                   include_refresh_rate=args.match_edid,
                                   priority=args.priority,
                                   json_compatible=args.json)

    def auto(self, args: argparse.Namespace):
        self.randrctl.switch_auto()

    def version(self, args: argparse.Namespace):
        print(pkg_resources.get_distribution("randrctl").version)

    def setup(self, args: argparse.Namespace):
        try:
            {
                cli.SETUP_COMPLETION: self.setup_completion,
                cli.SETUP_CONFIG: self.setup_config,
                cli.SETUP_UDEV: self.setup_udev,
            }[args.task](args)
        except RandrCtlException as e:
            logger.error(e)
            sys.exit(1)

    def setup_completion(self, args: argparse.Namespace):
        print(argcomplete.shellcode('randrctl', True, 'bash', None))

    def setup_config(self, args: argparse.Namespace):
        with (open(pkg_resources.resource_filename('randrctl', 'misc/config.yaml'), 'r')) as f:
            shutil.copyfileobj(f, sys.stdout)

    def setup_udev(self, args: argparse.Namespace):
        with (open(pkg_resources.resource_filename('randrctl', 'misc/udev/99-randrctl.rules'), 'r')) as f:
            shutil.copyfileobj(f, sys.stdout)


if __name__ == '__main__':
    Main().run()
