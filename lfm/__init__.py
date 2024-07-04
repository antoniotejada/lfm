"""
Copyright (C) 2001-2, Iñigo Serna <inigoserna@terra.es>.
All rights reserved.

This software has been realised under the GPL License, see the COPYING
file that comes with this package. There is NO WARRANTY.

'Last File Manager' is (tries to be) a simple 'midnight commander'-type
application for UNIX console.
"""


##################################################
##################################################
VERSION = '0.8'
DATE = '2001-2'
AUTHOR = 'Iñigo Serna'
VERSION = '0.8'

LFM_NAME = 'lfm - Last File Manager'
PYVIEW_NAME = 'pyview'

PREFSFILE = '.lfmrc'


##################################################
##### lfm
app = None

defaultprogs = { 'shell': ('bash', 'ksh', 'tcsh', 'csh', 'sh'),
                 'pager': ('pyview', 'less', 'more', 'biew'),
                 'editor': ('mcedit', 'emacs', 'vi', 'joe'),
                 'find': ('find', ),
                 'egrep': ('egrep', 'grep'),
                 'tar': ('tar', ),
                 'gzip': ('gzip', ),
                 'bzip2': ('bzip2', ),
                 'web': ('galeon', 'mozilla', 'netscape', 'lynx', 'opera'),
                 'ogg': ('ogg123', ),
                 'mp3': ('mpg123', ),
                 'audio': ('esdplay', 'play', ),
                 'video': ('mplayer', 'xanim', 'aviplay'),
                 'graphics': ('ee', 'eog', 'gthumb', 'xv', 'gimp'),
                 'pdf' :('acroread', 'ggv', 'xpdf'),
                 'ps': ('ggv', 'gv'),
                 'tururu': ('tururu', 'sdfdsf', 'just to test') }

filetypes = { 'web': ('html', 'htm'),
              'ogg': ('ogg', ),
              'mp3': ('mp3', ),
              'audio': ('wav', 'au', 'midi'),
              'video': ('mpeg', 'mpg', 'avi', 'asf'),
              'graphics': ('png', 'jpeg', 'jpg', 'gif', 'tiff', 'tif', 'xpm'),
              'pdf': ('pdf', ),
              'ps': ('ps', ) }


##################################################
##### pyview
MODE_TEXT, MODE_HEX = 0, 1
PYVIEW_README = """
    %s is a pager (viewer) written in Python.
Though  initially it was written to be used with 'lfm',
it can be used standalone too.

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
    - g, G, F5: goto line / byte
    - /: find
    - F6: find previous or find
    - F7: find next or find
    - q, Q, x, X, F3, F10: exit

Goto Line / Byte
================
    Enter the line number / byte offset you want to show.
If number / byte is preceded by '0x' it is interpreted as hexadecimal.
You can scroll relative lines using '+' or '-' char.

Find
====
    Type the string to search. It ignores case.
""" % PYVIEW_NAME

##################################################
##################################################
