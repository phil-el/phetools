<?php
define('PUBLIC_HTML', true);
header('Cache-control: no-cache');
header('Access-Control-Allow-Origin: *');

function send_request($params, $server) {

	if (!isset($params['cmd']))
		$params['cmd'] = 'status';

	if ($params['cmd'] == 'ping')
		$start = microtime(true);

	if ($params['cmd'] != 'status')
		header('Content-type: application/json');

	// FIXME: relative path, but can this be called from multiple location?
	$data = file_get_contents('/data/project/phetools/wikisource/' . $server . '.server');
	$data = explode(':', $data, 2);
	$server_name = $data[0];
	$port = $data[1];

	$conn = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);

	$timeout = array("sec"=>600, "usec"=>0);
	socket_set_option($conn, SOL_SOCKET, SO_RCVTIMEO, $timeout);
	socket_set_option($conn, SOL_SOCKET, SO_SNDTIMEO, $timeout);

	if (socket_connect($conn, $server_name, $port)) {
		$res = '';
		$line = json_encode($params);
		socket_write($conn, $line, strlen($line));
		while ($out = socket_read($conn, 1024)) {
			$res .= $out;
		}
		socket_close($conn);

		if ($params['cmd'] == 'ping') {
			$stop = microtime(true);
			$answer = json_decode($res, true);
			$answer['server'] = $server;
                        $answer['ping'] = $stop - $start;
			$res = json_encode($answer);
		}
	} else {
		$err = $server . " robot is not running.\n Please try again later.";
		if ($params['cmd'] == 'status') {
			$res = $err;
		} else {
			$res = json_encode(array('error' => 3, 'text' => $err));
		}
	}
	return $res;
}

