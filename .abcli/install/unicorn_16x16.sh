#! /usr/bin/env bash

function abcli_install_unicorn_16x16() {
    pushd $abcli_path_git > /dev/null
    git clone https://github.com/pimoroni/unicorn-hat-hd
    popd > /dev/null

    # https://github.com/pimoroni/unicorn-hat-hd
    sudo raspi-config nonint do_spi 0
    sudo apt-get --yes --force-yes install python3-pip python3-dev python3-spidev
    sudo pip3 install unicornhathd
}

if [ "$(abcli cookie read hardware.kind other)" == "unicorn_16x16" ] ; then
    abcli_install_module unicorn_16x16 101
fi