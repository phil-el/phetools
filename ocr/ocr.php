<?php
define('PUBLIC_HTML',true);
header('Cache-control: no-cache');
//header('Content-type: application/json');

function send_request($url,$lang,$user,$port){

  $conn = socket_create( AF_INET, SOCK_STREAM, SOL_TCP );
  $result = socket_connect($conn, 'login', $port); 
  if($result){
    $res = "";
    $line = '("'.$url.'","'.$lang.'","'.$user.'")';
    socket_write($conn, $line, strlen($line)); 
    while ($out = socket_read($conn, 1024)) {
      $res.=$out;
    }
    socket_close($conn);
    if($url=="status") return $res;
    else return 'ocr_callback('.$res.');';
  }
  else { 
    return 'alert("The OCR robot is not running.\n Please try again later.");';
  }
}

$url = $_GET["url"];
$lang = $_GET["lang"];
$user = $_GET["user"];

if(!$url) {
  $out = send_request("status",$lang,$user,12345);
  print $out;
  exit();
}

$out = send_request($url,$lang,$user,12345);
print $out;

?>
