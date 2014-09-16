import os
from unittest import TestCase
from randrctl.profile import ProfileManager, Output
from randrctl.xrandr import XrandrConnection, Mode

__author__ = 'edio'


class Test_ProfileManager(TestCase):

    manager = ProfileManager(".")

    TEST_PROFILE_FILE = os.path.join(os.path.dirname(__file__), 'profile_example')

    def test_read(self):
        with open(self.TEST_PROFILE_FILE) as f:
            p = self.manager.read_file(f)

            self.assertIsNotNone(p)
            self.assertSetEqual(set([Output("LVDS1", Mode(1366, 768, 0, 0), True), Output("DP1", Mode(1920, 1080, 1366, 0), False)]), set(p.outputs))
            self.assertEqual({"DP1": {"edid": "base64encoded"}, "LVDS1": {}}, p.rules)

    def test_profile_from_xrandr(self):
        xc = [XrandrConnection("LVDS1", True, Mode(1366, 768, 0, 0), False),
              XrandrConnection("DP1", True, Mode(1920, 1080, 1366, 0), True),
              XrandrConnection("HDMI1", False, Mode(1366, 768, 0, 0), False)]

        p = self.manager.profile_from_xrandr(xc)

        self.assertEqual("profile", p.name)
        self.assertEqual(2, len(p.outputs))

    def test_to_dict(self):
        with open(self.TEST_PROFILE_FILE) as f:
            p = self.manager.read_file(f)

            d = self.manager.to_dict(p)
            self.assertDictEqual(
                {'primary': 'LVDS1', 'outputs': {'DP1': {'width': 1920, 'height': 1080, 'left': 1366, 'top': 0},
                                                 'LVDS1': {'width': 1366, 'height': 768, 'left': 0, 'top': 0}}}, d)

