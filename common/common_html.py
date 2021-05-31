#!/usr/bin/python3

html_head = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
   "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
  <head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <title>%s</title>
  %s</head>"""

html5_head = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<title>%s</title>
%s
</head>
"""


def get_head(title, css=None, html5=False):
    if not css:
        css = ''
    else:
        css = '<link href="%s" rel="stylesheet" type="text/css">' % css
    html = html5_head if html5 else html_head
    return html % (title, css)
