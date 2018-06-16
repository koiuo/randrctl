# Changelog

## Unreleased

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
