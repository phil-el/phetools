#!/bin/bash

PYTHONPATH=/shared/pywikipedia/core:/shared/pywikipedia/core/externals/httplib2:/shared/pywikipedia/core/scripts
LOG_DIR=/data/project/phetools/log/ # + service_name(.out|.err)

declare -A env_var memory cmdline

env_var[verify_match]=PYTHONPATH=$PYTHONPATH
memory[verify_match]=640M
cmdline[verify_match]="python -u phe/verify_match/verify_match_web.py"

env_var[match_and_split]=PYTHONPATH=$PYTHONPATH
memory[match_and_split]=640M
cmdline[match_and_split]="python -u phe/match_and_split/wsdaemon.py"

env_var[extract_text_layer]=PYTHONPATH=$PYTHONPATH
memory[extract_text_layer]=640M
cmdline[extract_text_layer]="python -u phe/extract_text_layer/extract_text_layer.py"

memory[wsircdaemon]=256M
cmdline[wsircdaemon]="python -u phe/ircbot/pyirclogs.py"


start() {
    cmd="jsub -once -continuous -o $LOG_DIR$1.out -e $LOG_DIR$1.err "
    if [ ${env_var[$1]+_} ]; then
	cmd+="-v ${env_var[$1]} "
    fi
    cmd+="-l h_vmem=${memory[$1]} -N $1 ${cmdline[$1]}"
    echo "starting $1"
    eval $cmd
}

stop() {
    echo "stopping $1"
    cmd="qdel $1"
    eval $cmd
    while true; do
	qstat -j wsircdaemon &> /dev/null
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
	do_it $1 $K;
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
