# randrctl completion


_randrctl_profiles()
{
    find -L /etc/randrctl/profiles -maxdepth 1 -type f -not -name '.*' -not -name '*~' -not -name '*.conf' -not -name '*.service' -printf "%f\n"
}


_randrctl()
{
    local cur=${COMP_WORDS[COMP_CWORD]}

    case $COMP_CWORD in
      1)
        COMPREPLY=( $(compgen -W "--help --version list dump show switch-to" -- "$cur") )
      ;;
      2)
        [[ ${COMP_WORDS[COMP_CWORD-1]} = @(show|switch-to) ]] &&
          mapfile -t COMPREPLY < <(IFS=$'\n'; compgen -W "$(_randrctl_profiles)" -- "$cur")
      ;;
    esac
} &&
complete -F _randrctl randrctl

# ex: ts=4 sw=4 et filetype=sh
