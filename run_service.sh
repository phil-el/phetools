#!/bin/bash

PYTHONPATH=$HOME/phe/ocr:$HOME/phe/common:$HOME/phe/match_and_split:$HOME/wikisource:/shared/pywikipedia/core:/shared/pywikipedia/core/externals/httplib2:/shared/pywikipedia/core/scripts
LOG_DIR=/data/project/phetools/log/ # + service_name(.out|.err)

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
qalter[match_and_split]="-notify"

env_var[extract_text_layer]=PYTHONPATH=$PYTHONPATH
memory[extract_text_layer]=640M
cmdline[extract_text_layer]="python -u phe/extract_text_layer/extract_text_layer.py"

env_var[ws_ocr_daemon]=PYTHONPATH="$HOME/phe/common"
memory[ws_ocr_daemon]=640M
cmdline[ws_ocr_daemon]="python -u phe/ocr/ocrdaemon.py"

env_var[hocr_daemon]=PYTHONPATH=$PYTHONPATH
memory[hocr_daemon]=1404M
cmdline[hocr_daemon]="python -u phe/hocr/wshocr.py"

memory[wsircdaemon]=256M
cmdline[wsircdaemon]="python -u phe/ircbot/pyirclogs.py"

memory[dummy_robot]=384M
cmdline[dummy_robot]="python -u phe/dummy_robot/dummy_robot.py"


start() {
    cmd="jsub -once -continuous -o $LOG_DIR$1.out -e $LOG_DIR$1.err "
    if [ ${env_var[$1]+_} ]; then
	cmd+="-v ${env_var[$1]} "
    fi
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
