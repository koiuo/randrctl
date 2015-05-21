import hashlib
import logging
import os
from unittest import TestCase
from randrctl import profile
from randrctl.model import Profile, Rule, Geometry, Output, XrandrOutput
from randrctl.profile import ProfileManager, ProfileMatcher

__author__ = 'edio'


class Test_ProfileManager(TestCase):
    manager = ProfileManager(".")

    TEST_PROFILE_FILE = os.path.join(os.path.dirname(__file__), 'profile_example')
    TEST_SIMPLE_PROFILE_FILE = os.path.join(os.path.dirname(__file__), 'simple_profile_example')

    def test_read(self):
        with open(self.TEST_PROFILE_FILE) as f:
            p = self.manager.read_file(f)

            self.assertIsNotNone(p)
            self.assertSetEqual(set([Output("LVDS1", Geometry("1366x768"), True),
                                     Output("DP1", Geometry("1920x1080", pos="1366x0"), False),
                                     Output("VGA1", Geometry("800x600", pos="3286x0", rotate="inverted",
                                                             panning="800x1080", rate=80), False)]), set(p.outputs))
            self.assertEqual(Rule("d8578edf8458ce06fbc5bb76a58c5ca4", "1920x1200", "1920x1080"), p.rules["DP1"])
            self.assertEqual(Rule(), p.rules["LVDS1"])

    def test_simple_read(self):
        with open(self.TEST_SIMPLE_PROFILE_FILE) as f:
            p = self.manager.read_file(f)

            self.assertIsNotNone(p)
            self.assertSetEqual(set([Output("LVDS1", Geometry("1366x768"), True)]), set(p.outputs))
            self.assertSetEqual(set(), set(p.rules))

    def test_profile_from_xrandr(self):
        xc = [XrandrOutput("LVDS1", True, Geometry("1366x768"), False),
              XrandrOutput("DP1", True, Geometry("1920x1080", pos="1366x0"), True),
              XrandrOutput("HDMI1", False, Geometry("1366x768"), False)]

        p = self.manager.profile_from_xrandr(xc)

        self.assertEqual("profile", p.name)
        self.assertEqual(2, len(p.outputs))

    def test_to_dict(self):
        with open(self.TEST_PROFILE_FILE) as f:
            p = self.manager.read_file(f)

            d = self.manager.to_dict(p)
            self.maxDiff = None
            self.assertDictEqual(
                {'primary': 'LVDS1',
                 'match': {'LVDS1': {},
                           'DP1': {'edid': "d8578edf8458ce06fbc5bb76a58c5ca4",
                                   'supports': "1920x1080",
                                   'prefers': "1920x1200"}},
                 'outputs': {'DP1': {'mode': "1920x1080", 'pos': "1366x0", 'rotate': "normal", 'panning': "0x0"},
                             'LVDS1': {'mode': "1366x768", 'pos': "0x0", 'rotate': "normal", 'panning': "0x0"},
                             'VGA1': {'mode': "800x600", 'pos': "3286x0", 'rotate': "inverted",
                                      'panning': "800x1080", 'rate': 80}}}, d)

    def test_to_dict_no_rules(self):
        with open(self.TEST_PROFILE_FILE) as f:
            p = self.manager.read_file(f)
            p.rules = None

            d = self.manager.to_dict(p)
            self.maxDiff = None
            self.assertDictEqual(
                {'primary': 'LVDS1',
                 'outputs': {'DP1': {'mode': "1920x1080", 'pos': "1366x0", 'rotate': "normal", 'panning': "0x0"},
                             'LVDS1': {'mode': "1366x768", 'pos': "0x0", 'rotate': "normal", 'panning': "0x0"},
                             'VGA1': {'mode': "800x600", 'pos': "3286x0", 'rotate': "inverted",
                                      'panning': "800x1080", 'rate': 80}}}, d)

    def test_to_dict_no_edid_rule(self):
        with open(self.TEST_PROFILE_FILE) as f:
            p = self.manager.read_file(f)
            p.rules['DP1'].edid = None

            d = self.manager.to_dict(p)
            self.maxDiff = None
            self.assertDictEqual(
                {'primary': 'LVDS1',
                 'match': {'LVDS1': {},
                           'DP1': {'supports': "1920x1080", 'prefers': "1920x1200"}},
                 'outputs': {'DP1': {'mode': "1920x1080", 'pos': "1366x0", 'rotate': "normal", 'panning': "0x0"},
                             'LVDS1': {'mode': "1366x768", 'pos': "0x0", 'rotate': "normal", 'panning': "0x0"},
                             'VGA1': {'mode': "800x600", 'pos': "3286x0", 'rotate': "inverted",
                                      'panning': "800x1080", 'rate': 80}}}, d)


class Test_ProfileMatcher(TestCase):

    logging.basicConfig()

    matcher = ProfileMatcher()

    HOME_MD5 = hashlib.md5("home".encode()).hexdigest()
    OFFICE_MD5 = hashlib.md5("office".encode()).hexdigest()

    profiles = [
        Profile("default", [
            Output("LVDS1", Geometry("1366x768"))
        ], {"LVDS1": Rule()}),
        Profile("DP1_1920x1080", [
            Output("LVDS1", Geometry("1366x768")),
            Output("DP1", Geometry("1920x1080"))
        ], {"LVDS1": Rule(), "DP1": Rule(None, None, "1920x1080")}),
        Profile("DP1_1920x1200", [
            Output("LVDS1", Geometry("1366x768")),
            Output("DP1", Geometry("1920x1200"))
        ], {"LVDS1": Rule(), "DP1": Rule(None, "1920x1200", None)}),
        Profile("home", [
            Output("LVDS1", Geometry("1366x768")),
            Output("DP1", Geometry("1920x1080"))
        ], {"LVDS1": Rule(), "DP1": Rule(HOME_MD5)}),
        Profile("no_rule", [Output("LVDS1", Geometry("800x600"))]),
        Profile("office", [
            Output("LVDS1", Geometry("1366x768")),
            Output("HDMI1", Geometry("1920x1080"))
        ], {"LVDS1": Rule(), "HDMI1": Rule(OFFICE_MD5)})
    ]

    def test_find_best_default(self):
        outputs = [
            XrandrOutput("LVDS1", True)
        ]
        best = self.matcher.find_best(self.profiles, outputs)
        self.assertEqual(self.profiles[0], best)

    def test_find_best_no_match(self):
        outputs = [
            XrandrOutput("LVDS1", True),
            XrandrOutput("DP1", True, supported_modes=["1280x1024"], edid="guest")
        ]
        best = self.matcher.find_best(self.profiles, outputs)
        self.assertIsNone(best)

    def test_find_best_edid_over_mode(self):
        outputs = [
            XrandrOutput("LVDS1", True),
            XrandrOutput("DP1", True, supported_modes=["1920x1080"], edid="home")
        ]
        best = self.matcher.find_best(self.profiles, outputs)
        self.assertEqual(self.profiles[3], best)

    def test_find_best_prefers_over_supports(self):
        outputs = [
            XrandrOutput("LVDS1", True),
            XrandrOutput("DP1", True,
                         supported_modes=["1920x1080", "1920x1200"],
                         preferred_mode="1920x1200",
                         edid="office")
        ]
        best = self.matcher.find_best(self.profiles, outputs)
        self.assertEqual(self.profiles[2], best)

    def test_find_best_mode(self):
        outputs = [
            XrandrOutput("LVDS1", True),
            XrandrOutput("DP1", True, supported_modes=["1920x1080"], edid="office")
        ]
        best = self.matcher.find_best(self.profiles, outputs)
        self.assertEqual(self.profiles[1], best)

    def test_find_best_ambiguous(self):
        """
        Test matching for similarly scored profiles
        """
        edid = "office"
        edidhash = profile.md5(edid)

        connected_outputs = [
            XrandrOutput("LVDS1", True),
            XrandrOutput("DP1", True, supported_modes=["1920x1080"], edid=edid)
        ]

        profile_outputs = [
            Output("LVDS1", Geometry('1366x768'), True),
            Output("DP1", Geometry('1920x1080'))
        ]

        p1 = Profile("p1", profile_outputs, {"LVDS1": Rule(), "DP1": Rule(edidhash)})
        p2 = Profile("p2", profile_outputs, {"LVDS1": Rule(), "DP1": Rule(edidhash)})

        best = self.matcher.find_best([p1, p2], connected_outputs)
        self.assertEqual(p1, best)
