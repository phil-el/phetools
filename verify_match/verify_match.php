<?php
define('PUBLIC_HTML', true);
header('Cache-control: no-cache');
header('Access-Control-Allow-Origin: *');

function send_request($params, $port) {

	if (!isset($params['cmd']))
	    $params['cmd'] = 'status';

	if ($params['cmd'] != 'status')
		header('Content-type: application/json');

	$server_name = file_get_contents('./verify_match.server');

	$conn = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
	if (socket_connect($conn, $server_name, $port)) {
		$res = '';
		$line = json_encode($params);
		socket_write($conn, $line, strlen($line)); 
		while ($out = socket_read($conn, 1024)) {
			$res .= $out;
		}
		socket_close($conn);
	} else {
		$err = "Verify match robot is not running.\n Please try again later.";
		if ($params['cmd'] == 'status') {
			$res = $err;
		} else {
			$res = json_encode(array('error' => 3, 'text' => $err));
		}
	}
	return $res;
}

print send_request($_GET, 12349);
