import base64
import os
from unittest import TestCase
from randrctl import hotplug
from randrctl.hotplug import SysfsDevice

__author__ = 'edio'


class TestSysfsDevice(TestCase):
    sysfs = SysfsDevice(os.path.join(os.path.dirname(__file__), "sys"), "/test/card0")

    def test_get_active_connections(self):
        connections = self.sysfs.get_active_connections()
        expected = set([hotplug.Connection("LVDS-1", base64.b64encode(b"lvds edid\n")),
                        hotplug.Connection("DP-1", base64.b64encode(b"dp edid\n"))])
        self.assertSetEqual(set(connections), expected)
