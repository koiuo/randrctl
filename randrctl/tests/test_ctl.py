from unittest import TestCase
from randrctl.ctl import CtlFactory
from randrctl.profile import Profile

__author__ = 'edio'


class TestCtlFactory(TestCase):

    def test_run_hook(self):
        factory = CtlFactory()
        p = Profile("test_profile", None)
        hook = factory.run_hook("/usr/bin/echo switched to $randr_profile > /tmp/test")
        hook(p)
        with open("/tmp/test") as f:
            self.assertEqual(f.readline().strip(), "switched to test_profile")
