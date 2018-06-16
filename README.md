[![Build Status](https://travis-ci.org/edio/randrctl.svg?branch=master)](https://travis-ci.org/edio/randrctl)

# randrctl

Screen profiles manager for X.org.

_randrctl_ remembers your X.org screen configurations (position of displays, rotation, scaling, etc.) and switches
between them automatically as displays are connected or manually, when necessary:
```
randrctl switch-to home
randrctl switch-to office
```

## Install

_randrctl_ depends on `xrandr` utility and won't work without it. Please install it first.

### Archlinux

https://aur.archlinux.org/packages/randrctl-git/
https://aur.archlinux.org/packages/randrctl/

```
$ randrctl setup config > ${XDG_CONFIG_HOME:-$HOME/.config}/randrctl/config.yaml
```

### PyPi

```
# pip install randrctl

# randrctl setup udev > /etc/udev/rules.d/99-randrctl.rules
# randrctl setup completion > /usr/share/bash-completion/completions/randrctl

$ randrctl setup config > ${XDG_CONFIG_HOME:-$HOME/.config}/randrctl/config.yaml
```

### Manually from sources

```
$ git clone https://github.com/edio/randrctl.git
$ cd randrctl

# python setup.py install

# randrctl setup udev > /etc/udev/rules.d/99-randrctl.rules
# randrctl setup completion > /usr/share/bash-completion/completions/randrctl

$ randrctl setup config > ${XDG_CONFIG_HOME:-$HOME/.config}/randrctl/config.yaml
```

## Usage

Usage is very simple:

0. Setup your screen to suit your needs (randrctl does not handle that)

1. Dump settings with randrctl to a named profile

  ```randrctl dump -e home```

2. Re-apply those settings, whenever you need them

  ```randrctl switch-to home```

3. ... or let randrctl to inspect currently connected displays and choose profile that fits them best

  ```randrctl auto```

  Auto-switching will also happen automatically if provided udev rules are installed to the system.
  
4. For more info on usage refer to help

  ```randrctl --help```

### Auto-switching<a name="auto"></a>

```randrctl``` can associate profile with currently connected displays and switch to this profile automatically whenever
same (or similar) set of displays is connected.

Profile is matched to the set of connected displays by evaluating one or more of the following rules for every connected
display:

* list of supported modes of connected display includes the current mode

  ```randrctl dump -m profile1```

  You can use this to create profile that is activated whenever connected display supports the mode that is currently
  set for that output.

* preferred mode of connected display is the current mode

  ```randrctl dump -p profile2```

  Display can support wide range of modes from 640x480 to 1920x1200, but prefer only one of those. When dumped this way,
  profile is considered a match if connected display prefers the mode, that is currently set for it.

* unique identifier of connected display is exactly tha same

  ```randrctl dump -e profile3```

  Unique identifier (edid) of every display is dumped with the profile, so it matches, only if exactly same displays
  are connected.

Naturally, the more specific the rule, the bigger weight it has, so in case if you invoked those 3 dump commands above
with the same displays connected, `profile3` will be chosen as the best (i.e. the most specific) match.

It is possible to specify any combination of `-m -p -e` keys to dump command. In this case randrctl will try to match
all the rules combining them with logical AND (for example, display must support and at the same time prefer the mode).
Although such combination of rules might seem redundant (because if the more specific rule matches, the more generic
will do too), it might have sense if rule is edited manually.

If `randrctl dump` is invoked without additional options, it dumps only screen setup, so profile won't be considered
during auto-switching.


### Prior/Post hooks

randrctl can execute custom commands (hooks) before and after switching to profile or if switching fails. Hooks are
specified in config file `$XDG_CONFIG_HOME/randrctl/config.yaml`

```
hooks:
    prior_switch: /usr/bin/killall -SIGSTOP i3
    post_switch: /usr/bin/killall -SIGCONT i3 && /usr/bin/notify-send -u low "randrctl" "switched to $randr_profile"
    post_fail: /usr/bin/killall -SIGCONT i3 && /usr/bin/notify-send -u critical "randrctl error" "$randr_error"
```

The typical use-case of this is displaying desktop notification with libnotify.

I also use it to pause i3 window manager as it was known to crash sometimes during the switch.


### Profile format

Profile is a simple text file in YAML format. It can be edited manually, however it is rarely required in practice
because `randrctl dump` handles most common cases.

```
match:
    LVDS1: {}
    DP1:
        prefers: 1920x1080
outputs:
    LVDS1:
        mode: 1366x768
        panning: 1366x1080
    DP1:
        mode: 1920x1080
        pos: 1366x0
        rotate: inverted
primary: DP1
```

Profile is required to contain 2 sections (`outputs` and `primary`). That is what dumped when `randrctl dump` is invoked
without additional options.

The `match` section is optional and is dumped only when one of the auto-switching rules is specified.


#### Outputs

Each property of `outputs` section references output as seen in xrandr (i.e. *DP1*, *HDMI2*, etc.). Meaning of the
properties is the same as in the xrandr utility.

`mode` is mandatory, the others may be omitted.

```
DP1-2: 
    mode: 1920x1200
    panning: 2496x1560+1920+0
    pos: 1920x0
    rate: 60
    rotate: normal
    scale: 1.3x1.3
```


#### Primary

Name of the primary output as seen in xrandr.

```
primary: eDP1
```

#### Match

Set of rules for auto-switching.

The minimum rule is

```
HDMI1: {}
```

which means, that something must be connected to that output.

Rule corresponding to `randrctl dump -m` would be

```
HDMI1:
    supports: 1920x1080
```

`randrctl dump -p` is

```
HDMI1:
    prefers: 1920x1080
```

and `randrctl dump -e` is

```
HDMI1:
    edid: efdbca373951c898c5775e1c9d26c77f
```

`edid` is md5 hash of actual display's `edid`. To obtain that value, use `randrctl show`.

As was mentioned, `prefers`, `supports` and `edid` can be combined in the same rule, so it is possible to manually
create a more sophisticated rule

```
match:
    LVDS1: {}
    HDMI1:
        prefers: 1600x1200
        supports: 800x600
outputs:
    LVDS1: 
        ...
    HDMI1:
        ...
```

#### Priority

When more than one profile matches current output configuration priority can be used to highlight preferred profile.
```
priority: 100
match:
    ...
outputs:
    ...
```
Default priority is `100`. To set profile priority use `-P <priority>` with `dump` command. Like this:
`randrctl dump -e default -P 50`

## Develop

### Run tests

```
$ python setup.py test
```

