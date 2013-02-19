<?php
define('PUBLIC_HTML', true);
header('Cache-control: no-cache');
header('Access-Control-Allow-Origin: *');

function send_request($cmd, $page, $lang, $user, $port) {
	if ($cmd != 'status')
		header('Content-type: application/json');

	$server_name = file_get_contents('./hocr_server.server');

	$conn = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
	if (socket_connect($conn, $server_name, $port)) {
		$res = '';
		$line = $cmd.'|'.$page.'|'.$lang.'|'.$user;
		socket_write($conn, $line, strlen($line)); 
		while ($out = socket_read($conn, 1024)) {
			$res .= $out;
		}
		socket_close($conn);
	} else {
		$err = "The hOCR robot is not running.\n Please try again later.";
		if ($cmd == 'status') {
			$res = $err;
		} else {
			$res = json_encode(array('error' => 3, 'text' => $err));
		}
	}
	return $res;
}

$cmd = $_GET["cmd"];
$page = $_GET["page"];
$lang = $_GET["lang"];
$user = $_GET["user"];

if ($cmd) {
        $out = send_request($cmd, $page, $lang, $user, 12348);
} else {
        $out = send_request("status", $page, $lang, $user, 12348);
}
print $out;
