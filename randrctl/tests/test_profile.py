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
            self.assertSetEqual(set([Output("LVDS1", Mode("1366x768"), True),
                                     Output("DP1", Mode("1920x1080", pos="1366x0"), False),
                                     Output("VGA1", Mode("800x600", pos="3286x0", rotate="inverted",
                                                         panning="800x1080"), False)]), set(p.outputs))
            self.assertEqual({"DP1": {"edid": "base64encoded"}, "LVDS1": {}}, p.rules)

    def test_profile_from_xrandr(self):
        xc = [XrandrConnection("LVDS1", True, Mode("1366x768"), False),
              XrandrConnection("DP1", True, Mode("1920x1080", pos="1366x0"), True),
              XrandrConnection("HDMI1", False, Mode("1366x768"), False)]

        p = self.manager.profile_from_xrandr(xc)

        self.assertEqual("profile", p.name)
        self.assertEqual(2, len(p.outputs))

    def test_to_dict(self):
        with open(self.TEST_PROFILE_FILE) as f:
            p = self.manager.read_file(f)

            d = self.manager.to_dict(p)
            self.assertDictEqual(
                {'primary': 'LVDS1',
                 'outputs': {'DP1': {'mode': "1920x1080", 'pos': "1366x0", 'rotate': "normal", 'panning': "0x0"},
                             'LVDS1': {'mode': "1366x768", 'pos': "0x0", 'rotate': "normal", 'panning': "0x0"},
                             'VGA1': {'mode': "800x600", 'pos': "3286x0", 'rotate': "inverted",
                                      'panning': "800x1080"}}}, d)

