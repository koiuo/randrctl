import os
import shutil
import tempfile
import unittest

import yaml

from randrctl.context import default_config_dirs, configs


class TestDefaultConfigDirs(unittest.TestCase):

    def setUp(self):
        os.environ['HOME'] = '/home/user'
        os.environ['XDG_CONFIG_HOME'] = ''

    @unittest.skip("broken by PR #23")
    def test_should_use_xdg_conig_home_if_defined(self):
        os.environ['XDG_CONFIG_HOME'] = '/home/user/.xdgconfig'
        assert default_config_dirs() == ['/home/user/.xdgconfig/randrctl', '/home/user/.config/randrctl']

    @unittest.skip("broken by PR #23")
    def test_should_expand_nested_vars(self):
        os.environ['XDG_CONFIG_HOME'] = '$HOME/.xdgconfig'
        assert default_config_dirs() == ['/home/user/.xdgconfig/randrctl', '/home/user/.config/randrctl']

    @unittest.skip("broken by PR #23")
    def test_should_not_use_xdg_config_home_if_not_set(self):
        assert default_config_dirs() == ['/home/user/.config/randrctl']


class TestConfigs(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="randrctl-test-")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def write_config(self, config: dict, dir: str = "."):
        config_dir = os.path.normpath(os.path.join(self.tmpdir, dir))
        os.makedirs(config_dir, exist_ok=True)
        with open(os.path.join(config_dir, dir, 'config.yaml'), 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

    def write_config_str(self, content: str, dir: str = "."):
        config_dir = os.path.normpath(os.path.join(self.tmpdir, dir))
        os.makedirs(config_dir, exist_ok=True)
        with open(os.path.join(config_dir, dir, 'config.yaml'), 'w') as f:
            f.write(content)

    def test_should_skip_non_existing_config_dir(self):
        assert list(configs(["/doesnotexist"])) == []

    def test_should_skip_empty_config_dir(self):
        assert list(configs([self.tmpdir])) == []

    def test_should_skip_invalid_config(self):
        self.write_config_str("%")
        assert list(configs([self.tmpdir])) == []

    def test_should_parse_valid_config(self):
        # given
        config = {"hooks": {"post_switch": "/usr/bin/echo 42"}}
        self.write_config(config)

        # expect
        assert list(configs([self.tmpdir])) == [(self.tmpdir, config)]

    def test_should_pick_parse_multiple_locations(self):
        # given
        dir1 = os.path.join(self.tmpdir, "dir1")
        config1 = {"hooks": {"post_switch": "/usr/bin/echo 41"}}
        self.write_config(config1, dir1)

        dir2 = os.path.join(self.tmpdir, "dir2")
        config2 = {"hooks": {"post_switch": "/usr/bin/echo 42"}}
        self.write_config(config2, dir2)

        # expect
        assert list(configs([dir1, dir2])) == [(dir1, config1), (dir2, config2)]


if __name__ == '__main__':
    unittest.main()
