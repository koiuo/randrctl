from unittest import TestCase

from randrctl.exception import XrandrException, ParseException
from randrctl.model import Profile, Output, XrandrConnection
from randrctl.xrandr import Xrandr


class TestXrandr(TestCase):
    xrandr = Xrandr(":0", None)

    def test_compose_mode_args(self):
        xrandr = Xrandr(":0", None)
        xrandr.EXECUTABLE = "stub"

        outputs = {
            "LVDS1": Output(mode='1366x768'),
            "DP1": Output(mode='1920x1080', pos='1366x0', scale='1.5x1.5', panning='1920x1080'),
            "VGA1": Output(mode='800x600', pos='0x768')
        }

        p = Profile("default", outputs, primary="LVDS1")

        xrandr_connections = [XrandrConnection("HDMI1"), XrandrConnection("HDMI2")]

        command = xrandr._compose_mode_args(p, xrandr_connections)

        num_of_outputs = len(outputs) + len(xrandr_connections)

        self.assertEqual(num_of_outputs, command.count(xrandr.OUTPUT_KEY))
        self.assertEqual(len(outputs), command.count(xrandr.POS_KEY))
        self.assertEqual(len(outputs), command.count(xrandr.MODE_KEY))
        self.assertEqual(len(outputs), command.count(xrandr.PANNING_KEY))
        self.assertEqual(len(outputs), command.count(xrandr.ROTATE_KEY))
        self.assertEqual(len(outputs), command.count(xrandr.SCALE_KEY))
        self.assertEqual(len(xrandr_connections), command.count(xrandr.OFF_KEY))
        self.assertEqual(1, command.count(xrandr.PRIMARY_KEY))
        self.assertEqual(1, command.count("LVDS1"))
        self.assertEqual(1, command.count("DP1"))
        self.assertEqual(1, command.count("VGA1"))
        self.assertEqual(1, command.count("HDMI1"))
        self.assertEqual(1, command.count("HDMI2"))

    def test_compose_mode_args_exact_line(self):
        xrandr = Xrandr(":0", None)
        xrandr.EXECUTABLE = "stub"

        outputs = {"LVDS1": Output(mode='1366x768')}

        p = Profile("default", outputs, primary="LVDS1")

        xrandr_connections = [XrandrConnection("LVDS1"), XrandrConnection("HDMI1")]

        command = xrandr._compose_mode_args(p, xrandr_connections)
        self.assertListEqual([
            '--output', 'LVDS1', '--mode', '1366x768', '--pos', '0x0', '--rotate', 'normal', '--panning', '0x0',
            '--scale', '1x1', '--primary',
            '--output', 'HDMI1', '--off'
        ], command)

    def test_parse_xrandr_connection_not_connected(self):
        query_result = ["DP1 disconnected (normal left inverted right x axis y axis)"]
        connection = self.xrandr._parse_xrandr_connection(query_result)

        self.assertIsNotNone(connection)
        self.assertEqual(connection.name, "DP1")
        self.assertIsNone(connection.display)
        self.assertIsNone(connection.viewport)
        self.assertFalse(connection.primary)

    def test_parse_xrandr_connection_not_active(self):
        query_result = [
            "HDMI1 connected (normal left inverted right x axis y axis)",
            "    1920x1080     60.00 +",
            "    1280x1024     75.02    60.02",
            "    800x600       75.00    60.32",
        ]
        connection = self.xrandr._parse_xrandr_connection(query_result)

        self.assertIsNotNone(connection)
        self.assertEqual("HDMI1", connection.name)

        self.assertIsNotNone(connection.display)
        self.assertIsNone(connection.display.rate)
        self.assertIsNone(connection.display.mode)
        self.assertEqual("1920x1080", connection.display.preferred_mode)
        self.assertEqual(["1920x1080", "1280x1024", "800x600"], connection.display.supported_modes)

        self.assertIsNone(connection.viewport)
        self.assertFalse(connection.primary)

    def test_parse_xrandr_connection_invalid(self):
        query_result = [
            "HDMI1 connected (normal left inverted right x axis y axis)",
            "    1920x1080     60.00*+",
            "    1280x1024     75.02    60.02",
            "    800x600       75.00    60.32",
        ]
        with self.assertRaises(ParseException):
            self.xrandr._parse_xrandr_connection(query_result)

    def test_parse_xrandr_connection_simple_viewport(self):
        query_result = [
            "eDP1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 270mm x 150mm",
            "    1920x1080     60.00*+  48.00",
        ]
        connection = self.xrandr._parse_xrandr_connection(query_result)
        self.assertIsNotNone(connection)
        self.assertEqual("eDP1", connection.name)

        self.assertIsNotNone(connection.display)
        self.assertEqual("60.00", connection.display.rate)
        self.assertEqual("1920x1080", connection.display.mode)
        self.assertEqual("1920x1080", connection.display.preferred_mode)
        self.assertEqual(["1920x1080"], connection.display.supported_modes)

        self.assertIsNotNone(connection.viewport)
        self.assertEqual("1920x1080", connection.viewport.size)
        self.assertEqual("0x0", connection.viewport.panning)
        self.assertEqual("normal", connection.viewport.rotate)
        self.assertEqual("0x0", connection.viewport.pos)
        self.assertEqual("1x1", connection.viewport.scale)

        self.assertTrue(connection.primary)

    def test_parse_xrandr_connection_not_primary(self):
        query_result = [
            "eDP1 connected 1920x1080+0+0 (normal left inverted right x axis y axis) 270mm x 150mm",
            "    1920x1080     60.00*+  48.00",
        ]
        connection = self.xrandr._parse_xrandr_connection(query_result)
        self.assertIsNotNone(connection)
        self.assertEqual("eDP1", connection.name)

        self.assertIsNotNone(connection.display)
        self.assertEqual("60.00", connection.display.rate)
        self.assertEqual("1920x1080", connection.display.mode)
        self.assertEqual("1920x1080", connection.display.preferred_mode)
        self.assertEqual(["1920x1080"], connection.display.supported_modes)

        self.assertIsNotNone(connection.viewport)
        self.assertEqual("1920x1080", connection.viewport.size)
        self.assertEqual("0x0", connection.viewport.panning)
        self.assertEqual("normal", connection.viewport.rotate)
        self.assertEqual("0x0", connection.viewport.pos)
        self.assertEqual("1x1", connection.viewport.scale)

        self.assertFalse(connection.primary)

    def test_parse_xrandr_connection_primary_rotated_positioned(self):
        query_result = [
            "eDP1 connected 1920x1080+1280+800 left (normal left inverted right x axis y axis) 270mm x 150mm",
            "    1920x1080     60.00*+  48.00",
        ]
        connection = self.xrandr._parse_xrandr_connection(query_result)
        self.assertIsNotNone(connection)
        self.assertEqual("eDP1", connection.name)

        self.assertIsNotNone(connection.display)
        self.assertEqual("60.00", connection.display.rate)
        self.assertEqual("1920x1080", connection.display.mode)
        self.assertEqual("1920x1080", connection.display.preferred_mode)
        self.assertEqual(["1920x1080"], connection.display.supported_modes)

        self.assertIsNotNone(connection.viewport)
        self.assertEqual("1080x1920", connection.viewport.size)
        self.assertEqual("0x0", connection.viewport.panning)
        self.assertEqual("left", connection.viewport.rotate)
        self.assertEqual("1280x800", connection.viewport.pos)
        self.assertEqual("1.7777777777777777x0.5625", connection.viewport.scale)

        self.assertFalse(connection.primary)

    def test_parse_xrandr_connection_primary_positioned_panned(self):
        query_result = [
            "eDP1 connected primary 1920x1080+1280+800 (normal left inverted right x axis y axis) 270mm x 150mm panning 1920x1080+1280+800",
            "    1920x1080     60.00*+  48.00",
        ]
        connection = self.xrandr._parse_xrandr_connection(query_result)
        self.assertIsNotNone(connection)
        self.assertEqual("eDP1", connection.name)

        self.assertIsNotNone(connection.display)
        self.assertEqual("60.00", connection.display.rate)
        self.assertEqual("1920x1080", connection.display.mode)
        self.assertEqual("1920x1080", connection.display.preferred_mode)
        self.assertEqual(["1920x1080"], connection.display.supported_modes)

        self.assertIsNotNone(connection.viewport)
        self.assertEqual("1920x1080", connection.viewport.size)
        self.assertEqual("1920x1080+1280+800", connection.viewport.panning)
        self.assertEqual("normal", connection.viewport.rotate)
        self.assertEqual("1280x800", connection.viewport.pos)
        self.assertEqual("1x1", connection.viewport.scale)

        self.assertTrue(connection.primary)

    def test_parse_xrandr_connection_scaled_positioned(self):
        query_result = [
            "eDP1 connected primary 2496x1404+1920+1080 (normal left inverted right x axis y axis) 270mm x 150mm panning 2496x1404+1920+1080",
            "    1920x1080     60.00*+  48.00",
        ]
        connection = self.xrandr._parse_xrandr_connection(query_result)
        self.assertIsNotNone(connection)
        self.assertEqual("eDP1", connection.name)

        self.assertIsNotNone(connection.display)
        self.assertEqual("60.00", connection.display.rate)
        self.assertEqual("1920x1080", connection.display.mode)
        self.assertEqual("1920x1080", connection.display.preferred_mode)
        self.assertEqual(["1920x1080"], connection.display.supported_modes)

        self.assertIsNotNone(connection.viewport)
        self.assertEqual("2496x1404", connection.viewport.size)
        self.assertEqual("2496x1404+1920+1080", connection.viewport.panning)
        self.assertEqual("normal", connection.viewport.rotate)
        self.assertEqual("1920x1080", connection.viewport.pos)
        self.assertEqual("1.3x1.3", connection.viewport.scale)

        self.assertTrue(connection.primary)

    def test_parse_geometry(self):
        m = self.xrandr._parse_geometry("1920x1080+100+200")
        expected = ("1920x1080", "100x200")
        self.assertEqual(expected, m)

    def test_xrandr_exception(self):
        try:
            self.xrandr._xrandr("--output", "FOOBAR", "--mode", "800x600+0+0")
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

        grouped = self.xrandr._group_query_result(query_result)

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
                        "\t\t8",
                        "\t\t9",
                        "\t\t10",
                        "\tBroadcast RGB: Automatic",
                        "\t\tsupported: Automatic, Full",
                        "\taudio: auto",
                        "\t\tsupported: auto, on"
                        ]

        edid = self.xrandr._field_from_query_item(query_result, 'EDID')
        self.assertEqual("01234567", edid)
