#! /usr/bin/env bash

function grove() {
    blue_sbc_grove $@
}

function blue_sbc_grove() {
    local task=$(abcli_unpack_keyword $1 help)

    if [ $task == "help" ] ; then
        abcli_show_usage "grove validate [button]" \
            "validate grove."

        if [ "$(abcli_keyword_is $2 verbose)" == true ] ; then
            python3 -m blue_sbc.hat --help
        fi

        return
    fi

    if [ "$task" == "validate" ] ; then
        local what=$(abcli_clarify_input $2 button)

        if [ "$what" == "button" ]; then
            local filename=grove_button.py
        else
            abcli_log_error "-blue-sbc: grove: $task: $what: hardware not found."
            return
        fi

        abcli_log "validating grove $what: $filename"
        pushd $abcli_path_git/grove.py/grove > /dev/null
        python3 $filename
        popd > /dev/null

        return
    fi

    abcli_log_error "-blue-sbc: grove: $task: command not found."
}