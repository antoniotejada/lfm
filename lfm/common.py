# -*- coding: utf-8 -*-


import logging
import os.path
from enum import Enum, IntEnum
from string import digits, ascii_lowercase


########################################################################
##### General
AUTHOR = 'Iñigo Serna'
VERSION = '3.0'
DATE = '2001-17'
LFM_NAME = 'lfm - Last File Manager'

CONFIG_DIR = os.path.abspath(os.path.expanduser('~/.config/lfm'))
CONFIG_FILE = os.path.join(CONFIG_DIR, 'lfm.ini')
THEME_FILE = os.path.join(CONFIG_DIR, 'lfm.theme')
KEYS_FILE = os.path.join(CONFIG_DIR, 'lfm.keys')
HISTORY_FILE = os.path.join(CONFIG_DIR, 'lfm.history')
DUMP_KEYS_FILE = os.path.join(CONFIG_DIR, 'keys.dump')

DEBUG_LEVEL = logging.INFO # DEBUG, WARNING
log = logging.getLogger('lfm')

MAX_TABS = 4
VFS_STRING = '#vfs://'
BOOKMARKS_KEYS = digits + ascii_lowercase
MIN_COLUMNS = 66

HISTORY_MAX = 100
HISTORY_BLANK = {'file': [], 'path': [], 'glob': [], 'find': [], 'grep': [], 'exec': [], 'cli': []}

SYSPROGS = {'tar': 'tar',
            'bzip2': 'bzip2',
            'gzip': 'gzip',
            'zip': 'zip',
            'unzip': 'unzip',
            'rar': 'rar',
            '7z': '7z',
            'xz': 'xz',
            'lzip': 'lzip',
            'lz4': 'lz4',
            'grep': 'grep',
            'find': 'find',
            'which': 'which',
            'xargs': 'xargs'}


FileType = IntEnum('FileType', 'dir link2dir link nlink cdev bdev fifo socket exe reg unknown')
FILETYPES = [('x', 'Placeholder'),
             ('/', 'Directory'),
             ('~', 'Link to Directory'),
             ('@', 'Link'),
             ('!', 'No Link'),
             ('-', 'Char Device'),
             ('+', 'Block Device'),
             ('|', 'Fifo'),
             ('#', 'Socket'),
             ('*', 'Executable'),
             (' ', 'File'),
             ('?', 'Unknown')]

PaneMode = Enum('PaneMode', 'full half hidden info contents')
SortType = Enum('SortType', 'none byName byExt byPath bySize byMTime')
KeyModifier = Enum('KeyModifier', 'none control alt')
RetCode = Enum('RetCode', 'nothing quit_chdir quit_nochdir fix_limits full_redisplay half_redisplay')

ProcCode = Enum('ProcCode', 'end stopped error next confirm')
ProcCodeConfirm = Enum('ProcCodeConfirm', 'stop ok skip')

class LFMFileExistsError(Exception):
    pass

class LFMFileSkipped(Exception):
    pass

class LFMTerminalTooNarrow(Exception):
    pass


########################################################################
##### Color Theme
COLOR_ITEMS = [
    # general interface
    'header', 'tab_active', 'tab_inactive', 'pane_active', 'pane_inactive',
    'pane_header_path', 'pane_header_titles',
    'statusbar', 'powercli_prompt', 'powercli_text', 'selected_files', 'cursor', 'cursor_selected',
    # files. Must match the FILES_EXT from configuration!
    'files_dir', 'files_exe', 'files_reg', 'files_archive', 'files_audio', 'files_data',
    'files_devel', 'files_document', 'files_ebook', 'files_graphics', 'files_pdf',
    'files_temp', 'files_video', 'files_web',
    # dialogs
    'dialog', 'dialog_title', 'button_active', 'button_inactive',
    'dialog_error', 'dialog_error_title', 'dialog_error_text', 'dialog_perms',
    'selectitem', 'selectitem_title', 'selectitem_cursor', 'entryline',
    'progressbar_fg', 'progressbar_bg',
    'view_white_on_black', 'view_red_on_black', 'view_blue_on_black', 'view_green_on_black'
]

VALID_COLORS = ['white', 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan',
                'white*', 'black*', 'red*', 'green*', 'yellow*', 'blue*', 'magenta*', 'cyan*']


########################################################################
