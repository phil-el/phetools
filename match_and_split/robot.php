<?php
define('PUBLIC_HTML',true);
header('Cache-control: no-cache');
//header('Content-type: application/json');

function send_request( $cmd, $title, $lang, $user, $port ) {
	$conn = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
	$server_name = file_get_contents('./match_and_split.server');
	$result = socket_connect($conn, $server_name, $port);
	if($result){
		$res = "";
		// FIXME, isn't it broken if a title contains a " ?
		$line = '("'.$cmd.'","'.$title.'","'.$lang.'","'.$user.'")';
		socket_write($conn, $line, strlen($line));
		while ($out = socket_read($conn, 1024)) {
			$res.=$out;
		}
		socket_close($conn);

		if ($cmd == "status")
			return $res;
		else
			return 'match_callback("'.$res.'");';
	} else {
		return 'alert("The robot is not running.\n Please try again later.");';
	}
}

$cmd = isset($_GET["cmd"]) ? $_GET["cmd"] : FALSE;
$title = isset($_GET["title"]) ? $_GET["title"] : FALSE;
$lang = isset($_GET["lang"]) ? $_GET["lang"] : FALSE;
$user = isset($_GET["user"]) ? $_GET["user"] : FALSE;

if(!$cmd) {
	$out = send_request("status", "", $lang, $user, 12346);
	print $out;
	exit();
}

$out = send_request($cmd, $title, $lang, $user, 12346);
print $out;

?>
