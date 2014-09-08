#compdef randrctl

# Copy this file to /usr/share/zsh/site-functions

(( $+function[_randrctl_command] )) ||
_randrctl_command() {
    case $words[1] in
        switch-to|show|dump)
          compadd "${(f)$(find -L /etc/randrctl/profiles -maxdepth 1 -type f -not -name '.*' -not -name '*~' -not -name '*.conf' -not -name '*.service' -printf "%f\n")}"
        ;;
        list)
          _randrctl_list_options
        ;;
    esac
}

_randrctl_commands() {
    local -a _commands
    _commands=(
        'list:List available profiles'
        'dump:Dump current settings to profile'
        'show:Show a profile'
        'switch-to:Switch to a profile'
      )
    _describe "randrctl commands" _commands
}

_randrctl_list_options() {
    local -a _commands
    _commands=(
        '-l:long listing'
      )
    _describe "randrctl list" _commands
}

case $CURRENT in
      2)
        _arguments \
          '(- :)--help[display help message]' \
          '(-)::randrctl commands:_randrctl_commands'
      ;;
      3)
        shift words
        [[ $words[1] != -* ]] &&
          curcontext="${curcontext%:*}-${words[1]}:" _randrctl_command
      ;;
esac
