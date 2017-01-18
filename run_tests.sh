#!/bin/sh

basedir="$(dirname "$(readlink -f "$0")")"

args="tests/"
if [ "$@" ]; then
    args="$@"
fi

PYTHONPATH="$basedir" py.test "$args"
