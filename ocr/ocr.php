<?php
define('PUBLIC_HTML', true);
header('Cache-control: no-cache');
header('Access-Control-Allow-Origin: *');

function send_request($url, $lang, $user, $port) {
	if ($url != 'status')
		header('Content-type: application/json');

	$server_name = file_get_contents('./ocr_server.server');

	$conn = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
	if (socket_connect($conn, $server_name, $port)) {
		$res = '';
		$line = $url.'|'.$lang.'|'.$user;
		socket_write($conn, $line, strlen($line)); 
		while ($out = socket_read($conn, 1024)) {
			$res .= $out;
		}
		socket_close($conn);
	} else {
		$err = "The OCR robot is not running.\n Please try again later.";
		if ($url == 'status') {
			$res = $err;
		} else {
			$res = json_encode(array('error' => 3, 'text' => $err));
		}
	}
	return $res;
}

$url = $_GET["url"];
$lang = $_GET["lang"];
$user = $_GET["user"];

if ($url) {
        $out = send_request($url, $lang, $user, 12347);
} else {
        $out = send_request("status", $lang, $user, 12347);
}
print $out;
