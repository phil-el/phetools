<?php

require_once('/data/project/phetools/phe/common/front-end.php');

print send_request($_GET, 'extract_text_layer');
