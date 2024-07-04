#!/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2001-17  Iñigo Serna
# Time-stamp: <2017-06-25 18:31:04 inigo>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""lfm v3.0 - (C) 2001-17, by Iñigo Serna <inigoserna@gmail.com>

'Last File Manager' is a powerful file manager for UNIX console.
It has a curses interface and it's written in Python version 3.4+.
Released under GNU Public License, read COPYING file for more details.
"""

__author__ = 'Iñigo Serna'
__revision__ = '3.0'


import os
from os.path import join, exists
import sys
import argparse
import logging

from common import *
from ui import run_app


########################################################################
######################################################################
##### Main
def lfm_exit(ret_code, ret_path='.'):
    with open('/tmp/lfm-%s.path' % (os.getppid()), 'w') as f:
        f.write(ret_path)
    sys.exit(ret_code)


def helper_delete_item(filename, text):
    try:
        os.unlink(filename)
    except OSError as err:
        print('lfm - ERROR: {}\n{}'.format(text, err))
    else:
        print('lfm: {}!'.format(text))
    sys.exit(0)


def lfm_start():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog='\n'.join(__doc__.split('\n')[2:]))
    parser.add_argument('-d', '--debug', help='Enable debug level in log file', action='store_true')
    parser.add_argument('-w', '--use-wide-chars', help='Enable support for wide chars', action='store_true')
    parser.add_argument('--restore-config', help='Restore default configuration', action='store_true')
    parser.add_argument('--restore-keys', help='Restore default key bindings', action='store_true')
    parser.add_argument('--restore-theme', help='Restore default theme', action='store_true')
    parser.add_argument('--delete-history', help='Delete history', action='store_true')
    parser.add_argument('path1', nargs='?', default='.', help='Path to show in left pane (default: ".")')
    parser.add_argument('path2', nargs='?', default='.', help='Path to show in right pane (default: ".")')
    args = parser.parse_args()

    if not exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    logging.basicConfig(level=logging.DEBUG if args.debug else DEBUG_LEVEL,
                        # format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        format='%(asctime)s  %(name)s(%(module)12s:%(lineno)4d)  %(levelname).1s  %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filename=join(CONFIG_DIR, 'lfm.log'),
                        filemode='w')

    if args.restore_config:
        helper_delete_item(CONFIG_FILE, 'restore default configuration')
    if args.restore_keys:
        helper_delete_item(KEYS_FILE, 'restore default key bindings')
    if args.restore_theme:
        helper_delete_item(THEME_FILE, 'restore default theme')
    if args.delete_history:
        helper_delete_item(HISTORY_FILE, 'delete history')

    try:
        pwd = os.getcwd()
        os.chdir(args.path1)
        os.chdir(args.path2)
        os.chdir(pwd)
    except OSError as err:
        print('lfm - ERROR: cannot initialize path\n{}'.format(err))
        sys.exit(-1)

    logging.info('Start lfm')
    try:
        path = run_app(args.path1, args.path2, args.use_wide_chars)
    except FileNotFoundError as err:
        print('ERROR: Cannot copy default theme or keys file to user configuration folder {}\n{}\nQuitting'.format(CONFIG_DIR, err))
        sys.exit(-1)
    except BaseException as err:
        import traceback
        tb_str = traceback.format_exc()
        logging.critical('ERROR: ' + str(err))
        logging.critical(tb_str)
        print('ERROR:', str(err))
        print(tb_str)
        path = None
        raise

    logging.info('End lfm, returns: "{}"'.format(path))
    if path is not None:
        lfm_exit(0, path)
    else:
        lfm_exit(0)


########################################################################
if __name__ == '__main__':
    lfm_start()


########################################################################
