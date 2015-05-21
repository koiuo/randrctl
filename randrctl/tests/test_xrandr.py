from unittest import TestCase
from randrctl.exception import ValidationException, XrandrException
from randrctl.model import Profile, Geometry, Output, XrandrOutput
from randrctl.xrandr import Xrandr

__author__ = 'edio'


class TestXrandr(TestCase):
    xrandr = Xrandr()

    def test_compose_mode_args(self):
        xrandr = Xrandr()
        xrandr.EXECUTABLE = "stub"

        outputs = [Output("LVDS1", Geometry(1366, 768), primary=True),
                   Output("DP1", Geometry(1920, 1080, 1366, 0)),
                   Output("VGA1", Geometry(800, 600, 0, 768))]

        p = Profile("default", outputs)

        xrandr_connections = [XrandrOutput("HDMI1"), XrandrOutput("HDMI2")]

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

    def test_parse_output_details(self):
        c1 = self.xrandr.parse_output_details("1366x768+0+312 (foo bar)")
        self.assertDictEqual({'primary': False, 'pos': '0x312', 'res': '1366x768', 'rotate': None}, c1)

        c2 = self.xrandr.parse_output_details(
            "primary 1366x1080+0+0 inverted (foo bar) 130mm x 70mm panning 1366x1080+0+0")
        self.assertDictEqual({'primary': True, 'rotate': 'inverted', 'res': '1366x1080', 'pos': '0x0'}, c2)

        c3 = self.xrandr.parse_output_details("(foo bar)")
        self.assertDictEqual({}, c3)

    def test_mode_from_str(self):
        m = self.xrandr.parse_geometry("1920x1080+100+200")
        expected = ("1920x1080", "100x200")
        self.assertEqual(expected, m)

    def test_xrandr_exception(self):
        try:
            self.xrandr.__xrandr__(["--output", "FOOBAR", "--mode", "800x600+0+0"])
            self.fail("exception expected")
        except XrandrException:
            pass

    def test_group_query_result(self):
        query_result = [
            "LVDS1 connected",
            "  1920x1080+*",
            "  1366x768",
            "  1280x800",
            "DP1 connected",
            "  1920x1080+*",
            "HDMI1 disconnected",
            "VGA1 disconnected"]

        grouped = self.xrandr.group_query_result(query_result)

        self.assertEqual(4, len(grouped))
        self.assertListEqual(query_result[0:4], grouped[0])
        self.assertListEqual(query_result[4:6], grouped[1])
        self.assertListEqual(query_result[6:7], grouped[2])
        self.assertListEqual(query_result[7:], grouped[3])

    def test_edid_from_query_item(self):
        query_result = ["LVDS1 connected foo bar",
                        "\tIdentifier: 0x45",
                        "\tTimestamp: 123456789",
                        "\tEDID:",
                        "\t\t0",
                        "\t\t1",
                        "\t\t2",
                        "\t\t3",
                        "\t\t4",
                        "\t\t5",
                        "\t\t6",
                        "\t\t7",
                        "\tBroadcast RGB: Automatic",
                        "\t\tsupported: Automatic, Full",
                        "\taudio: auto",
                        "\t\tsupported: auto, on"
                        ]

        edid = self.xrandr.edid_from_query_item(query_result)
        self.assertEqual("01234567", edid)
