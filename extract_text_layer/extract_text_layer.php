<?php
define('PUBLIC_HTML',true);
header('Cache-control: no-cache');

// FIXME: handle title containing a &
function send_request( $cmd, $title, $lang, $user, $port ) {
	// FIXME: try with SOL_UDP.
	$conn = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
	$server_name = file_get_contents('./extract_text_layer.server');
	$result = socket_connect($conn, $server_name, $port);
	if($result){
		$res = "";
		$line = $cmd.'|'.$title.'|'.$lang.'|'.$user;
		socket_write($conn, $line, strlen($line));
		while ($out = socket_read($conn, 1024)) {
			$res.=$out;
		}
		socket_close($conn);

		if ($cmd == "status")
			return $res;
		else
			return 'extract_text_layer.callback("'.$res.'");';
	} else {
		if ($cmd == 'status')
			return 'The robot is not running.<br />Please try again later.';
		else
			return 'alert("The robot is not running.\n Please try again later.");';
	}
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

?>
