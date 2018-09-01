from unittest import TestCase

from randrctl.model import Serializable, Profile, Output, Rule


class Node(Serializable):
    def __init__(self, name, children=None, named=None):
        self.name = name
        self.children = children
        self.named = named


class TestSerializable(TestCase):

    def test_to_dict(self):
        # given
        n = Node("foo", [Node("foo1"), Node("foo2")], {"foo3": Node("foo3", [Node("foo3-1")])})

        # when
        d = n.to_dict()

        # then
        self.assertDictEqual(d, {
            'name': "foo",
            'children': [
                {
                    'name': "foo1"
                },
                {
                    'name': "foo2"
                },
            ],
            'named': {
                'foo3': {
                    'name': "foo3",
                    'children': [
                        {
                            'name': "foo3-1"
                        }
                    ]
                }
            }
        })


class TestProfile(TestCase):

    def test_profile_from_dict(self):
        # given
        data = [
            (
                Profile("no_rules", {"lvds1": Output("800x600")}, priority=100),
                {
                    'name': 'no_rules',
                    'outputs': {
                        'lvds1': {
                            'mode': '800x600',
                            'pos': '0x0',
                            'rotate': 'normal',
                            'panning': '0x0',
                            'scale': '1x1',
                        }
                    },
                    'priority': 100
                }
            ),
            (
                Profile(
                    name="with_rules",
                    outputs={
                        "lvds1": Output("800x600", rate="60"),
                        "vga1": Output("1024x768", pos="800x0", rate="75")
                    },
                    match={
                        "lvds1": Rule("edid", "800x600", "800x600")
                    },
                    primary="lvds1",
                    priority=100
                ),
                {
                    'name': 'with_rules',
                    'match': {
                        'lvds1': {
                            'edid': 'edid',
                            'supports': '800x600',
                            'prefers': '800x600'
                        }
                    },
                    'outputs': {
                        'lvds1': {
                            'mode': '800x600',
                            'pos': '0x0',
                            'rotate': 'normal',
                            'panning': '0x0',
                            'scale': '1x1',
                            'rate': '60'
                        },
                        'vga1': {
                            'mode': '1024x768',
                            'pos': '800x0',
                            'rotate': 'normal',
                            'panning': '0x0',
                            'scale': '1x1',
                            'rate': 75
                        }
                    },
                    'primary': 'lvds1',
                    'priority': 100
                }
            )
        ]

        for expected_profile, dict in data:
            # when
            p = Profile.from_dict(dict)

            # then
            self.assertEqual(expected_profile, p)
            self.assertDictEqual(dict, p.to_dict())
