<?php


$header= <<<EOT
<html>
<head>
<title>ProofreadPage Statistics</title>
<link rel="stylesheet" href="screen.css" type="text/css" media="screen" />
<link rel="stylesheet" href="shared.css" type="text/css" media="screen" />
<link rel="stylesheet" href="sorttable.css" type="text/css" media="screen" />
<link rel="stylesheet" href="commonPrint.css" type="text/css" media="print" />
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
<!--<li>There may be a delay between Wikisource and the Toolserver. The replication lag (in seconds) can be checked <a href="http://toolserver.org/~bryan/stats/replag/#s3-hourly" class="external text" rel="nofollow">here</a>.</li>-->
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



$diff = isset($_GET["diff"]) ? $_GET["diff"] : 0;
$daysago = isset($_GET["daysago"]) ? $_GET["daysago"] : 0;
$lang = isset($_GET["lang"]) ? $_GET["lang"] : '';

if ($daysago || ($diff != 0 && $diff != 1 && $diff != 7 && $diff != 30 && $diff != 365) ) {
	$n = $daysago+1;

	if($diff) $dd =" -d$diff "; else $dd="";
        // FIXME: use a relative path
	$cmd = "python3 /data/project/phetools/phe/statistics/gen_stats.py -y$n $dd" ;
	$retval = 1; 
	ob_start();
	passthru( $cmd, $retval );
	$txt = ob_get_contents();
	ob_end_clean();

} else if ($diff == 1 || $diff == 7 || $diff == 30 || $diff == 365) {
      $txt = file_get_contents("data/stats_diff_$diff.txt");
} else {
      $txt = file_get_contents('data/stats.txt');
}

$lines = explode( "\n", $txt ) ;


$out = "<table id=\"statsTable\" class=\"sortable\" style=\"text-align:right; border:1px solid #999;\" rules=\"all\" cellpadding=\"3px\">";
$out.='
<thead>
<tr>
<td><input type="text" id="langFilter" name="lang" value="'.$lang.'" placeholder="Filter by language code(s)" title="Insert any language codes (separated by space or comma)"/></td>
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
</tr></thead><tbody>';


foreach ($lines as $line_num => $line) {
  $a = preg_split('/[ ]+/',$line);
  if($a[0]=='total') array_unshift( $a,'-');

  if( ( count($a) == 15 && $a[1]!='all') ) {
    if ($a[1] == 'total') {
      $out .= '</tbody><tfoot>';
    }
    $out .= "<tr data-lang=".$a[1]."><td>". $a[1] 
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

$out .="</tfoot></table>";



echo $header . $out . 

$footer = <<<EOT
</div></div>

<div id="mw-panel" class="noprint">
 <div id="p-logo">
   <a style="background-image: url(//upload.wikimedia.org/wikipedia/sources/b/bc/Wiki.png);" href="index.html" ></a>
 </div>
 <div class="portal" id='p-Channels'>
  <h5>Statistics</h5>
  <div class="body">
   <ul>
    <li><a href="?diff=0">Today's table</a></li>
    <li><a href="?diff=1">Today's increase</a></li>
    <li><a href="?diff=7">1 week increase</a></li>
    <li><a href="?diff=30">1 month increase</a></li>
    <li><a href="?diff=365">1 year increase</a></li>
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

 <div class="portal" id='index_tool'>
  <h5>Index tool</h5>
  <div class="body">
   <ul>
    <li><a href="not_transcluded">Index tool</a></li>
   </ul>
  </div>
 </div>

</div>
<script src="sorttable.js"></script>
<script src="jquery-3.5.1.min.js"></script>
<script src="statistics.js"></script>
</body></html>
EOT;


?>
