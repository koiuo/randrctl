randrctl
========

Minimalistic profile based screen manager for X. It allows to store current screen setup in a declarative configuration file (a profile) and apply stored settigns later with a simple command.

Tool may be usefull to people who work on the same laptop at home, in the office (different external displays and different screen setup) and on the go (no external display).

Currently randrctl can
* handle *mode*, *position*, *rotation*, *panning* and *rate*
* dump current screen setup to a profile
* automatically (via udev) or manually switch between stored profiles
* list all available profiles and show profile details
* run custom commands before/after the switch or when it fails for some reason

Usage is very simple:

1. Setup your screen to suit your needs and dump settings to use them later

  ```randrctl dump home```

2. After this you can reapply these settings whenever you need them

  ```randrctl switch-to home```

3. ... or let randrctl to guess your settings automatically

  ```randrctl auto```
  
4. You can list all available profiles

  ```randrctl list```
  
5. And if you are interested in some particular profile

  ```randrctl show home```


Profile format
--------------

Simple text file in JSON format, can be edited manually. All values are case-sensitive, white-spaces don't matter.

```
{
  "match": {
    "LVDS1": {},
    "DP1": {
        "prefers": "1920x1080"
    }
  },
  "outputs": {
    "LVDS1": {
      "mode": "1366x768",
      "panning": "1366x1080
    },
    "DP1": {
      "mode": "1920x1080",
      "pos": "1366x0",
      "rotate": "inverted"
    }
  },
  "primary": "DP1"
}
```

Profile should contain 2 sections (```outputs``` and ```primary```) for manual switching. The ```match``` section is optional and is used for auto-switching.


### Outputs

Each property of ```outputs``` section references output as seen in xrandr (i.e. *DP1*, *HDMI2*, etc.). Each output must contain ```mode``` property. Here is a list of output properties:

* ```mode``` — output resolution. Value example: *"1920x1080"*

* ```pos``` — output position. Value example: *"312x0"*

* ```panning``` — output panning (it's fun http://crunchbang.org/forums/viewtopic.php?id=20634). Value example: *"1366x1080"*

* ```rotate``` — output rotation. Possible values: *"normal"*, *"left"*, *"right"*, *"inverted"*

* ```rate``` — output refresh rate. Optional field. If omitted xrandr will chose the best suitable rate. Values example: *60*


### Primary

Just name of the primary output.


### Match

See [auto-switching](auto) section.


Auto-switching<a name="auto"></a>
---------------------------------------

```randrctl``` is able to associate profiles with your hardware configuration and switch between them automatically. To do so, ```match``` section should be declared in profile. As in ```outputs``` section, properties of this section are names of outputs to match.

Profile is considered for matching if and only if all stated outputs are currently connected.

Example:

```
"match": {
  "LVDS1": {},
  "DP1": {}
}
```
This profile will be considered if *DP1* and *LVDS1* are connected. It won't be if *HDMI1* is additionally connected at the same time.

Also each stated output can be matched by supported ```supports``` or preferred ```prefers``` modes or by connected display ```edid```.

```supports``` matches display if it supports specified mode.

Example:

```
"match": {
  "DP1": {
    "supports": "1920x1080"
  }
}
```

```prefers``` matches display if its preferred mode (usually the most advanced one) matches

Example:

```
"match": {
  "DP1": {
    "prefers": "1920x1080"
  }
}
```
The examples above will match any display on *DP1* port that supports (in the first case) or prefers *1920x1080* resolution. This, for example, may be very useful if you want to create profile that is activated whenever full-HD display is connected to *HDMI* port of your laptop:

```
{
  "match": {
    "LVDS1": {},
    "HDMI1": {
      "mode": "1920x1080"
    }
  },
  "outputs": {
    "LVDS1": {
      ...
    },
    "HDMI1": {
      ...
    }
  }
}
```

```edid``` matching will look for specific display identified by edid.

Example:

```
"match": {
  "DP1": {
    "edid": "d8578edf8458ce06fbc5bb76a58c5ca4",
  }
}
```
will match display whichs EDID md5-sum is equal to the specified one (to generate profile with proper edid value use ```randrctl dump```)


### Order of matching

The most specific profile is chosen among all that matched. So *edid* > *prefers* > *supports*. Naturally, *edid* is more specific than preferred or supported mode.


Prior/Post hooks
------------------

Some window managers (i.e. i3) are known to crash when screen setup is changed. Common workaround for this is:

```
killall -SIGSTOP i3
xrandr ...
killall -SIGCONT i3
```

randrctl handles this by allowing to declare hooks to be executed before and after call to xrandr. This is also useful if you want to show desktop notification on profile switch or failure. Declare them all in /etc/randrctl/config.ini

```
[hooks]
prior_switch = /usr/bin/killall -SIGSTOP i3
post_switch = /usr/bin/killall -SIGCONT i3 && /usr/bin/notify-send -u low "randrctl" "switched to $randr_profile"
post_fail = /usr/bin/killall -SIGCONT i3 && /usr/bin/notify-send -u critical "randrctl error" "$randr_error"
```


Installation
------------


###Archlinux
There is AUR package https://aur.archlinux.org/packages/randrctl-git/


###PyPi
```
# pip install randrctl
# randrctl-setup
```


###Manual from sources

```
$ git clone https://github.com/edio/randrctl.git
$ cd randrctl
$ cp -r etc/randrctl ~/.config
# python setup.py install
# randrct-setup
```


Feedback/contribution
---------------------

This is my very first python project. Comments regarding code quality and suggestions are welcome. 


License
-------
GPLv3
