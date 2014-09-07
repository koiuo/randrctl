#compdef randrctl

# Copy this file to /usr/share/zsh/site-functions

(( $+function[_randrctl_command] )) ||
_randrctl_command() {
    [[ $words[1] = (switch-to|show) ]] &&
      compadd "${(f)$(find -L /etc/randrctl/profiles -maxdepth 1 -type f -not -name '.*' -not -name '*~' -not -name '*.conf' -not -name '*.service' -printf "%f\n")}"
}


_randrctl_commands() {
    local -a _commands
    _commands=(
        'list:List available profiles'
        'dump:Dump current settings to profile'
        'show:Show a profile'
        'switch-to:Switch to a profile'
      )
    _describe "netctl commands" _commands
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
