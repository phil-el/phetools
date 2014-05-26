<?php
define('PUBLIC_HTML', true);
header('Cache-control: no-cache');
header('Access-Control-Allow-Origin: *');
header('Content-type: text/plain');

function ping_server($server) {
	$url = 'http://tools-webproxy//phetools/' . $server . '?cmd=ping';
	$response = file_get_contents($url);
	return json_decode($response, true);
}

$serverlist = array(
	'extract_text_layer_cgi.py',
	'match_and_split_cgi.py',
	'verify_match_cgi.py'
);

foreach ($serverlist as $servername) {
	$answer = ping_server($servername);
	printf("ping: %s, error: %d, %s: %s, %.0f ms\n",
	       $servername, $answer['error'], $answer['text'],
	       $answer['server'], $answer['ping'] * 1000);

	//print json_encode($answer) . "\n";
}
