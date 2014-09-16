from unittest import TestCase
from randrctl.profile import Profile, Output
from randrctl.xrandr import Xrandr, XrandrConnection, Mode, XrandrException

__author__ = 'edio'


class TestXrandr(TestCase):
    xrandr = Xrandr()

    def test_compose_mode_args(self):
        xrandr = Xrandr()
        xrandr.EXECUTABLE = "stub"

        outputs = [Output("LVDS1", Mode(1366, 768), primary=True),
                   Output("DP1", Mode(1920, 1080, 1366, 0)),
                   Output("VGA1", Mode(800, 600, 0, 768))]

        p = Profile("default", outputs)

        xrandr_connections = [XrandrConnection("HDMI1"), XrandrConnection("HDMI2")]

        command = xrandr.__compose_mode_args__(p, xrandr_connections)

        num_of_outputs = len(outputs) + len(xrandr_connections)

        self.assertEqual(num_of_outputs, command.count(xrandr.OUTPUT_KEY))
        self.assertEqual(len(outputs), command.count(xrandr.POS_KEY))
        self.assertEqual(len(outputs), command.count(xrandr.MODE_KEY))
        self.assertEqual(len(xrandr_connections), command.count(xrandr.OFF_KEY))
        self.assertEqual(1, command.count(xrandr.PRIMARY_KEY))
        self.assertEqual(1, command.count("LVDS1"))
        self.assertEqual(1, command.count("DP1"))
        self.assertEqual(1, command.count("VGA1"))
        self.assertEqual(1, command.count("HDMI1"))
        self.assertEqual(1, command.count("HDMI2"))

    def test_connection_from_str_invalid(self):
        try:
            self.xrandr.connection_from_str(" foo bar")
            self.fail("Exception expected")
        except Exception:  # TODO narrow exception
            return  # ok

    def test_connection_from_str(self):
        c1 = self.xrandr.connection_from_str("LVDS1 connected 1366x768+0+312 (foo bar)")

        self.assertEqual("LVDS1", c1.name)
        self.assertTrue(c1.connected)
        self.assertEqual(Mode(1366, 768, 0, 312), c1.current_mode)

        c2 = self.xrandr.connection_from_str("DP1 connected primary 1920x1080+1366+0 (foo bar)")

        self.assertEqual("DP1", c2.name)
        self.assertTrue(c2.connected)
        self.assertEqual(Mode(1920, 1080, 1366, 0), c2.current_mode)

        c3 = self.xrandr.connection_from_str("HDMI1 disconnected (foo bar)")

        self.assertEqual("HDMI1", c3.name)
        self.assertFalse(c3.connected)
        self.assertIsNone(c3.current_mode)

    def test_mode_from_str(self):
        m = self.xrandr.mode_from_str("1920x1080+100+200")
        expected = Mode(1920, 1080, 100, 200)
        self.assertEqual(expected, m)

    def test_xrandr_exception(self):
        try:
            self.xrandr.__xrandr__(["--output", "FOOBAR", "--mode", "800x600+0+0"])
            self.fail("exception expected")
        except XrandrException:
            return
