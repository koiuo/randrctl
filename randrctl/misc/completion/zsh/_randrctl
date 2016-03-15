#compdef randrctl

_randrctl_show() {
    compadd $(_randrctl_profiles)
}

_randrctl_dump() {
    local -a _arguments
    _arguments=(
        '-m:dump with match by supported mode'
        '-e:dump with match by edid'
    )
    _describe "list arguments" _arguments
    compadd $(_randrctl_profiles)
}

_randrctl_switch-to() {
    compadd $(_randrctl_profiles)
}

_randrctl_auto() {
    _message "no more arguments"
}

_randrctl_list() {
    local -a _arguments
    _arguments=(
        '-l:use long listing'
    )
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
        'dump:dump profile'
        'list:list available profiles'
        'show:show profile details'
        'switch-to:switch to profile'
        'auto:guess the best matching profile'
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
    {-h,--help}'[show help message]' \
    {-v,--version}'[print version information]' \
    "-x[be verbose]" \
    '-X[be even more verbose]' \
    '--system[work in system mode]' \
    '*::randrctl commands:_randrctl_command'

