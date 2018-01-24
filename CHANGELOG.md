# Changelog

## Unreleased

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
