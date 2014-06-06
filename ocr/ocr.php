<?php

require_once('/data/project/phetools/phe/common/front-end.php');

print send_request($_GET, 'ws_ocr_daemon');
