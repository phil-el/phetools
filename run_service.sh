#!/bin/bash

#
# Tweaked by Xover 5 November 2020:
#
# The local pywikibot is now >= 4.0 which requires Python 3.x, and phetools
# requires Python 2.x. As a workaround, use the Toolforge shared pywikibot
# that's pegged to the last Python 2.x-compatible version. This ends up
# mixing and matching different versions due to the httplib2 dep, so try to
# use the system-provided version of that too.
#
# Phabricator: T265640
#
#PYTHONPATH=$HOME/phe:$HOME/wikisource:/data/project/phetools/pywikibot-core:/data/project/phetools/pywikibot-core/externals/httplib2:/data/project/phetools/pywikibot-core/scripts
PYTHONPATH=$HOME/phe:$HOME/wikisource:/shared/pywikibot/core_python2:/shared/pywikibot/core_python2/scripts
# END: Xover's meddling

LOG_DIR=/data/project/phetools/log/ # + service_name(.out|.err)

# Some host don't define $LANG
UTF8_LANG=en_US.UTF8

declare -A env_var memory cmdline

env_var[verify_match]=PYTHONPATH=$PYTHONPATH
memory[verify_match]=640M
cmdline[verify_match]="python -u phe/verify_match/verify_match_web.py"

env_var[match_and_split]=PYTHONPATH=$PYTHONPATH
memory[match_and_split]=640M
cmdline[match_and_split]="python -u phe/match_and_split/match_and_split.py"
# FIXME: this can't work with -continuous because the wrapper script generated
# when using -continuous doesn't trap SIGUSR2 and is killed with a SIGTERM
# so the child die before receiving SIGUSR2.
#qalter[match_and_split]="-notify"

env_var[extract_text_layer]=PYTHONPATH=$PYTHONPATH
memory[extract_text_layer]=640M
cmdline[extract_text_layer]="python -u phe/extract_text_layer/extract_text_layer.py"

env_var[ws_ocr_daemon]=PYTHONPATH="$HOME/phe"
memory[ws_ocr_daemon]=2048M
cmdline[ws_ocr_daemon]="python -u phe/ocr/ocrdaemon.py"

#memory[wsircdaemon]=256M
#cmdline[wsircdaemon]="python -u phe/ircbot/pyirclogs.py"

memory[dummy_robot]=384M
cmdline[dummy_robot]="python -u phe/dummy_robot/dummy_robot.py"


start() {
    cmd="jsub -once -continuous -o $LOG_DIR$1.out -e $LOG_DIR$1.err "
    if [ ${env_var[$1]+_} ]; then
	cmd+="-v ${env_var[$1]} "
    fi
    cmd+="-v $UTF8_LANG "
    cmd+="-l h_vmem=${memory[$1]} -N $1 ${cmdline[$1]}"
    $cmd

    #if [ ${qalter[$1]+_} ]; then
    #    qalter $1 ${qalter[$1]}
    #fi
}

stop() {
    echo "stopping $1"
    cmd="qdel $1"
    $cmd
    while true; do
	qstat -j $1 &> /dev/null
	if [ $? == 0 ]; then
            echo -n "."
	else
            break;
	fi
	sleep 1
    done
}

restart() {
    stop $1
    start $1
}

do_it() {
    if [ "$1"x == "startx" ]; then
        start $2
    elif [ "$1"x == "stopx" ]; then
	stop $2
    elif [ "$1"x == "restartx" ]; then
	restart $2
    else
	syntaxe
    fi;
}

syntaxe() {
    echo "unknown command, syntax: $0 (start|stop|restart) service_name"
    echo "available service name: "
    for K in "${!cmdline[@]}"; do
	echo "$K"
    done
    echo "or all to apply command to all service"
    exit 1
}

if test "$2"x == "allx"; then
    for K in "${!cmdline[@]}"; do
	if [ $K != 'dummy_robot' -o "$1"x = "stopx" ]; then
	    do_it $1 $K;
	fi
    done
else
    if [ "$2"x == "x" ]; then
	syntaxe
    elif [ ${cmdline[$2]+_} ]; then
	do_it $1 $2
    else
	syntaxe
    fi
fi
