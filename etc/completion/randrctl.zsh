#compdef randrctl

_randrctl_show() {
    compadd $(_randrctl_profiles)
}

_randrctl_dump() {
    compadd $(_randrctl_profiles)
}

_randrctl_switch-to() {
    compadd $(_randrctl_profiles)
}

_randrctl_list() {
    local -a _arguments
    _arguments=(
        '-l:use long listing'
    )
    # TODO only one instance
    if (( CURRENT == 2 )); then
        _describe "list arguments" _arguments
    else
        _message "no more arguments"
    fi
}


_randrctl_profiles() {
    # TODO filter by --system
    randrctl list
}


_randrctl_command() {
    local -a _randrctl_cmds
    _randrctl_cmds=(
        'dump:Show current locale settings'
        'list:Set system locale'
        'show:Show known locales'
        'switch-to:Set virtual console keyboard mapping'
    )
    if (( CURRENT == 1 )); then
        _describe -t commands 'randrctl command' _randrctl_cmds
    else
        local curcontext="$curcontext"
        cmd="${${_randrctl_cmds[(r)$words[1]:*]%%:*}}"
        if (( $+functions[_randrctl_$cmd] )); then
            curcontext="${curcontext%:*:*}:systemctl-${cmd}:"
            _randrctl_$cmd
        else
            _message "unknown randrctl command: $words[1]"
        fi
    fi
}

_arguments \
    {-h,--help}'[Show this help]' \
    {-v,--version}'[Show package version]' \
    "-x[Don't convert keyboard mappings]" \
    '-X[Do not pipe output into a pager]' \
    '--system[Do not prompt for password]' \
    '*::randrctl commands:_randrctl_command'

