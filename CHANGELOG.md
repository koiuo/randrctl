# Changelog

## 1.9.0 - 2020-06-02

### Added

- `/etc/randrctl` directory is now probed for config and profiles if there's no
  _randrctl_ config in home dir

### Fixed

- deprecation/security warnings caused by outdated pyyaml dependency

## 1.8.2 - 2019-02-09

### Fixed

- regression where hooks were not applied

## 1.8.1 - 2018-10-23

### Fixed

- regression where profiles with no `primary` field were considered invalid

## 1.8.0 - 2018-09-01

### Added

- `setup` command to assist in randrctl setup
- new bash completion generated from application code
- `-d` option to detect `DISPLAY` if executed by udev

### Fixed

- python 3.7 compatibility
- migrated from `packit` to `pbr` (should fix installation issues)
- undesired rounding of refresh rate (#15)

### Removed

- outdated zsh and bash completion files. _bash_ completion can be generated with
    ```
    randrctl setup completion
    ```
  _zsh_ users can enable bash completion support by adding to `.zshrc`
    ```
    autoload bashcompinit
    bashcompinit
    ```
- obsolete `randrctl-auto` wrapper script. Use `randrctl -d` instead

## 1.7.1 - 2018-06-16

### Fixed

- exception during `randrctl dump`

### Changed

- `-v` option is replaced with `version` command. Use `randrctl version` instead of `randrctl -v`

## 1.7.0 - 2018-06-16

### Fixed
- regression #13

### Removed

- support for `config.ini`. Please migrate to `config.yaml`
- support for configuration in `/etc/randrctl`

## 1.6.0 - 2018-04-15

### Added

- support for configs in yaml format (#11)

### Changed

- configs in INI format are now deprecated (#11)

### Fixed

- overwriting existing config when there are no profiles (#9)

## 1.5.0 - 2018-01-24

### Added

- `list -s` to print only matching profiles with their scores [#8](https://github.com/edio/randrctl/pull/8)

### Fixed

- Bug where profiles without `match` section were considered for auto-matching

## 1.4.0 - 2017-11-18

### Added

- This changelog file

### Changed

- Profiles are now stored and displayed in YAML format.

  Conversion of existing profiles to new format is not required.
  There's also `-j` flag for `show` and `dump` to use JSON format.
