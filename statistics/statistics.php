<?php


$header= <<<EOT
<html>
<head>
<link rel="stylesheet" href="http://bits.wikimedia.org/skins-1.5/vector/screen.css" type="text/css" media="screen" />
<link rel="stylesheet" href="http://bits.wikimedia.org/skins-1.5/common/shared.css" type="text/css" media="screen" />
<link rel="stylesheet" href="http://bits.wikimedia.org/skins-1.5/common/commonPrint.css" type="text/css" media="print" />
<style type="text/css">
.quality4 { background:#90ff90; }
.quality3 { background:#ffe867; }
.quality2 { background:#b0b0ff; }
.quality1 { background:#ffa0a0; }
.quality0 { background:#dddddd; }

.withscans { background:#c0c0ff; }
.naked { background:#ffa0a0; }
.disamb { background:#dddddd; }
</style>
</head>
<body class="mediawiki ltr ns--1 ns-special page-Special_RecentChanges skin-vector">

<div id="content">
 <h1 id="firstHeading" class="firstHeading">ProofreadPage Statistics</h1>
 <div id="bodyContent">

<div style="background:#dddddd;" class="plainlinks">
<p>This table shows the number of pages that have been proofread using the <a href="http://www.mediawiki.org/wiki/Extension:Proofread_Page" title="ProofreadPage">ProofreadPage</a> extension, at various Wikisource subdomains. It is updated daily.<br /></p>

Notes:
<ul>
<li>The "proofread" column counts all the pages that <u>have been</u> proofread :  [category q3] + [category q4] </li>
<li>Language subdomains are ranked by the number of page verifications : [category q3] + 2x[category q4] </li>
<li>There may be a delay between Wikisource and the Toolserver. The replication lag (in seconds) can be checked <a href="http://toolserver.org/~bryan/stats/replag/#s3-hourly" class="external text" rel="nofollow">here</a>.</li>
<li>The "with scans" column counts pages whose text is transcluded from the "Page:" namespace. 
<li>The "disamb" column counts disambiguation pages.</li>
<li>The "percent" column shows the percentage of texts backed with scans, excluding disambiguation pages from the total: 
<center>percent = [with scans]/([with scans] + [without scans])</center>
</li>
<li>A large number of texts at de.ws do not use transclusion, although they are backed with scans. In addition, a few wikisources still do not have a namespace for author pages; these pages are counted as texts without scans.</li>
</ul>
</div>
<br/>

EOT;



$diff = $_GET["diff"];
$daysago = $_GET["daysago"];

if($daysago || $diff>1 ) {
	$n = $daysago+1;

	if($diff) $dd =" -d$diff "; else $dd="";
        // FIXME: use a relative path
	$cmd = "/home/phe/stats/stats -y$n $dd" ;
	$retval = 1; 
	ob_start();
	passthru( $cmd, $retval );
	$txt = ob_get_contents();
	ob_end_clean();

} else if($diff==1) {
      $txt = file_get_contents('stats_diff.txt');
} else {
      $txt = file_get_contents('stats.txt');
}

$lines = explode( "\n", $txt ) ;


$out = "<table style=\"text-align:right; border:1px solid #999;\" rules=\"all\" cellpadding=\"3px\">";
$out.='
<tr>
<td></td>
<th colspan="6" style="text-align:center">Page namespace</th>
<th colspan="5" style="text-align:center">Main namespace</th>
</tr>
<tr>
<th>language</th>
<th>all pages</th>
<th class="quality1">not proof.</th>
<th class="quality2">problem.</th>
<th class="quality0">w/o text</th>
<th class="quality3">proofread</th>
<th class="quality4">validated</th>
<th>all pages</th>
<th class="withscans">with scans</th>
<th class="naked">w/o scans</th>
<th class="disamb">disamb</th>
<th>percent</th>
</tr>';


foreach ($lines as $line_num => $line) {
  $a = split('[ ]+',$line);
  if($a[0]=='total') array_unshift( $a,'-');

  if( ( count($a) == 15 && $a[1]!='all') ) {
    $out .= "<tr><td>". $a[1] 
      ."</td><td>".$a[3]
      ."</td><td>".$a[4]
      ."</td><td>".$a[5]
      ."</td><td>".$a[6]
      ."</td><td>".$a[7]
      ."</td><td>".$a[8]
      ."</td><td>".$a[10]
      ."</td><td>".$a[11]
      ."</td><td>".$a[12]
      ."</td><td>".$a[13]
      ."</td><td>". $a[14]
      ."</td></tr>";
  }
  else if( $a[0] == "date:" ) { $out.= substr( $line, 6) . "<br/>"; }

 }
$out .="</table>";



echo $header . $out . 

$footer = <<<EOT
</div></div>

<div id="mw-panel" class="noprint">
 <div id="p-logo">
   <a style="background-image: url(http://upload.wikimedia.org/wikipedia/sources/b/bc/Wiki.png);" href="index.html" ></a>
 </div>
 <div class="portal" id='p-Channels'>
  <h5>Statistics</h5>
  <div class="body">
   <ul>
    <li><a href="statistics.php">Today's table</a></li>
    <li><a href="statistics.php?diff=1">Today's increase</a></li>
    <li><a href="statistics.php?diff=7">1 week increase</a></li>
    <li><a href="statistics.php?diff=30">1 month increase</a></li>
   </ul>
  </div>
 </div>
 <div class="portal" id='graphs'>
  <h5>Graphs</h5>
  <div class="body">
   <ul>
    <li><a href="stats.html">Proofread pages</a></li>
    <li><a href="transclusions.html">Transclusions</a></li>
   </ul>
  </div>
 </div>

</div>
</body></html>
EOT;


?>
