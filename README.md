randrctl
========

Minimalistic profile based screen manager for X. It allows to store current screen setup in a declarative configuration file (a profile) and apply stored settigns later with a simple command.

Tool may be usefull to people who work on the same laptop at home, in the office (different external displays and different screen setup) and on the go (no external display).

Currently randrctl can
* handle *mode*, *position*, *rotation* and *panning*
* dump current screen setup to a profile
* switch between stored profiles
* list all available profiles and show profile details
* run custom commands before/after the switch or when it fails for some reason

Usage is very simple:

1. Setup your screen to suit your needs and dump settings to use them later

  ```randrctl dump home```

2. After this you can reapply these settings whenever you need them

  ```randrctl switch-to home```
  
3. You can list all available profiles

  ```randrctl list```
  
4. And if you are interested in some particular profile

  ```randrctl show home```
  

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

Profile format
--------------

Simple text file in JSON format, can be edited manually.

```
{
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


Upcoming features
-----------------

* detecting connected display and choosing the most appropriate profile (only opensource linux drivers allow this). There is a prototype already
* ~~completion functions for popular shells~~
* per-user profiles and configuration (no need for su/sudo)

Installation
------------

###Archlinux
There is AUR package https://aur.archlinux.org/packages/randrctl-git/

###Generic

```
$ git clone https://github.com/edio/randrctl.git
$ cd randrctl
# python setup.py install
# cp -r etc/randrctl /etc
# cp etc/randrctl/completion/randrctl.zsh /usr/share/zsh/site-functions/_randrctl
# cp etc/randrctl/completion/randrctl.bash /usr/share/bash-completion/completions/randrctl
```

Feedback/contribution
---------------------

This is my very first python project. Comments regarding code quality and suggestions are welcome. 


License
-------
GPLv3
