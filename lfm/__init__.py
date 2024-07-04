# -*- coding: utf-8 -*-

"""
Copyright (C) 2001-7, Iñigo Serna <inigoserna@telefonica.net>.
All rights reserved.

This software has been realised under the GPL License, see the COPYING
file that comes with this package. There is NO WARRANTY.

'Last File Manager' is (tries to be) a simple 'midnight commander'-type
application for UNIX console.
"""


######################################################################
import locale
locale.setlocale(locale.LC_ALL, '')
g_encoding = locale.getpreferredencoding()


######################################################################
AUTHOR = 'Iñigo Serna'
VERSION = '2.0'
DATE = '2001-7'

LFM_NAME = 'lfm - Last File Manager'
PYVIEW_NAME = 'pyview'


######################################################################
##### lfm
sysprogs = { 'tar': 'tar',
             'bzip2': 'bzip2',
             'gzip': 'gzip',
             'zip': 'zip',
             'unzip': 'unzip',
             'rar': 'rar',
             'grep': 'grep',
             'find': 'find',
             'which': 'which',
             'xargs': 'xargs' }

TOGGLE_PANE, TAB_NEW, TAB_CLOSE = xrange(1, 4)
PANE_MODE_HIDDEN, PANE_MODE_LEFT, PANE_MODE_RIGHT, PANE_MODE_FULL = xrange(4)


######################################################################
##### pyview
MODE_TEXT, MODE_HEX = 0, 1
PYVIEW_README = """
    %s is a pager (viewer) written in Python.
Though  initially it was written to be used with 'lfm',
it can be used standalone too.
Since version 0.9 it can read from standard input too
(eg. $ ps efax | pyview)

This software has been realised under the GPL License,
see the COPYING file that comes with this package.
There is NO WARRANTY.

Keys:
=====
+ Movement
    - cursor_up, p, P
    - cursor_down, n, N
    - previous page, backspace, Ctrl-P
    - next page, space, Ctrl-N
    - home: first line
    - end: last line
    - cursor_left
    - cursor_right

+ Actions
    - h, H, F1: help
    - w, W, F2: toggle un / wrap (only in text mode)
    - m, M, F4: toggle text / hex mode
    - g, G, F5: goto line / byte offset
    - /: find (new search)
    - F6: find previous or find
    - F7: find next or find
    - 0..9: go to bookmark #
    - b, B: set bookmark #
    - Ctrl-O: open shell 'sh'. Type 'exit' to return to pyview
    - q, Q, x, X, F3, F10: exit

Goto Line / Byte Offset
=======================
    Enter the line number / byte offset you want to show.
If number / byte is preceded by '0x' it is interpreted as hexadecimal.
You can scroll relative lines from the current position using '+' or '-'
character.

Find
====
    Type the string to search. It ignores case.
""" % PYVIEW_NAME


######################################################################
