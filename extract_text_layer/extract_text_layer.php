<?php
define('PUBLIC_HTML', true);
header('Cache-control: no-cache');
header('Access-Control-Allow-Origin: *');

// FIXME: handle title containing a &
function send_request( $cmd, $title, $lang, $user, $port ) {
	if ($cmd != 'status')
                header('Content-type: application/json');

	$conn = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
	$server_name = file_get_contents('./extract_text_layer.server');
	$result = socket_connect($conn, $server_name, $port);
	if ($result){
		$res = "";
		$line = $cmd.'|'.$title.'|'.$lang.'|'.$user;
		socket_write($conn, $line, strlen($line));
		while ($out = socket_read($conn, 1024)) {
			$res .= $out;
		}
		socket_close($conn);
        } else {
                $err = "The robot is not running.\n Please try again later.";
                if ($cmd == 'status') {
                        $res = $err;
                } else {
                        $res = json_encode(array('error' => 3, 'text' => $err));
                }
        }
	return $res;
}

$cmd = isset($_GET["cmd"]) ? $_GET["cmd"] : FALSE;
$title = isset($_GET["title"]) ? $_GET["title"] : FALSE;
$lang = isset($_GET["lang"]) ? $_GET["lang"] : FALSE;
$user = isset($_GET["user"]) ? $_GET["user"] : FALSE;

if (!$cmd) {
	$cmd = 'status';
}
$out = send_request($cmd, $title, $lang, $user, 12345);
print $out;
