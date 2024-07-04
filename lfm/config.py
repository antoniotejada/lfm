# -*- coding: utf-8 -*-

"""config.py

This module contains the configuration class for lfm.
"""


import os, os.path
import codecs
from ConfigParser import SafeConfigParser

from __init__ import LFM_NAME, sysprogs, g_encoding
from files import SORTTYPE_byName
from utils import get_shell_output, encode, decode


######################################################################
##### Some variables and default values
CONFIG_FILE = '.lfmrc'
defaultprogs = { 'shell': 'bash',
                 'pager': 'pyview',
                 'editor': 'vi',
                 'web': 'firefox',
                 'audio': 'mplayer',
                 'video': 'mplayer',
                 'graphics': 'gthumb',
                 'pdf': 'evince',
                 'ebook': 'FBReader' }
filetypes = { 'web': ('html', 'htm'),
              'audio': ('ogg', 'flac', 'mp3', 'wav', 'au', 'midi'),
              'video': ('mpeg', 'mpg', 'avi', 'asf', 'ogv', 'flv'),
              'graphics': ('png', 'jpeg', 'jpg', 'gif', 'tiff', 'tif', 'xpm', 'svg'),
              'pdf': ('pdf', 'ps'),
              'ebook': ('epub', 'chm', 'mobi', 'prc', 'azw', 'lit') }
bookmarks = [u'/'] * 10
colors = { 'title': ('yellow', 'blue'),
           'files': ('white', 'black'),
           'current_file': ('blue', 'cyan'),
           'messages': ('magenta', 'cyan'),
           'help': ('green', 'black'),
           'file_info': ('red', 'black'),
           'error_messages1': ('white', 'red'),
           'error_messages2': ('black', 'red'),
           'buttons': ('yellow', 'red'),
           'selected_file': ('yellow', 'black'),
           'current_selected_file': ('yellow', 'cyan'),
           'tabs': ('white', 'blue'),
           'temp_files': ( 'white', 'black'),
           'document_files': ('blue', 'black'),
           'media_files': ('blue', 'black'),
           'archive_files': ('yellow', 'black'),
           'source_files': ('cyan', 'black'),
           'graphics_files': ('magenta', 'black'),
           'data_files': ('magenta', 'black'),
           'current_file_otherpane': ('black', 'white'),
           'current_selected_file_otherpane': ('yellow', 'white'),
           'directories': ('green', 'black'),
           'exe_files': ('red', 'black') }
options = { 'save_conf_at_exit': 1,
            'show_output_after_exec': 1,
            'rebuild_vfs': 0,
            'detach_terminal_at_exec': 1,
            'show_dotfiles': 1,
            'num_panes': 2,
            'sort': SORTTYPE_byName,
            'sort_mix_dirs': 0,
            'sort_mix_cases': 1,
            'color_files': 1,
            'manage_otherpane': 0,
            'automatic_file_encoding_conversion': 0 } # ask
misc = { 'backup_extension': '.bak' }
confirmations = { 'delete': 1,
                  'overwrite': 1,
                  'quit': 1,
                  'ask_rebuild_vfs': 1 }
files_ext  = { 'temp_files': ('.tmp', '.$$$', '~', '.bak'),
               'document_files': ('.txt', '.text', '.rtf',
                                  '.odt', '.odc', '.odp',
                                  '.abw', '.gnumeric',
                                  '.sxw', '.sxc', '.sxp', '.sdw', '.sdc', '.sdp',
                                  '.ps', '.pdf', '.djvu', '.dvi', '.bib', '.tex',
                                  '.epub', '.chm', '.prc', '.mobi', '.azw', '.lit', '.imp',
                                  '.xml', '.xsd', '.xslt', '.sgml', '.dtd',
                                  '.html', '.shtml', '.htm', '.css',
                                  '.mail', '.msg', '.letter', '.ics', '.vcs', '.vcard',
                                  '.lsm', '.po', '.man', '.1', '.info',
                                  '.doc', '.xls', '.ppt', '.pps'),
               'media_files': ('.mp2', '.mp3', '.mpg', '.ogg', '.flac', '.mpeg', '.wav',
                               '.avi', '.asf', '.mov', '.mol', '.mpl', '.xm', '.med',
                               '.mid', '.midi', '.umx', '.wma', '.acc', '.wmv',
                               '.swf', '.flv', '.ogv'),
               'archive_files': ('.gz', '.bz2', '.xz', '.tar', '.tgz', '.Z', '.zip',
                                 '.rar', '.7z', '.arj', '.cab', '.lzh', '.lha',
                                 '.zoo', '.arc', '.ark',
                                  '.rpm', '.deb'),
               'source_files': ('.c', '.h', '.cc', '.hh', '.cpp', '.hpp',
                                '.py', '.pl', '.pm', '.inc', '.rb.',
                                '.asm', '.pas', '.f', '.f90', '.pov', '.m', '.pas',
                                '.cgi', '.php', '.phps', '.tcl', '.tk',
                                '.js', '.java', '.jav', '.jasm',
                                '.diff', '.patch',
                                '.sh', '.bash', '.awk', '.m4', '.el',
                                '.st', '.mak', '.sl', '.ada', '.caml',
                                '.ml', '.mli', '.mly', '.mll', '.mlp', '.prg'),
               'graphics_files': ('.jpg', '.jpeg', '.gif', '.png', '.tif', '.tiff',
                                  '.pcx', '.bmp', '.xpm', '.xbm', '.eps', '.pic',
                                  '.rle', '.ico', '.wmf', '.omf', '.ai', '.cdr',
                                  '.xcf', '.dwb', '.dwg', '.dxf', '.svg', '.dia'),
               'data_files': ('.dta', '.nc', '.dbf', '.mdn', '.db', '.mdb', '.dat',
                              '.fox', '.dbx', '.mdx', '.sql', '.mssql', '.msql',
                              '.ssql', '.pgsql', '.cdx', '.dbi', '.sqlite') }


######################################################################
##### Configuration
class Config(object):
    """Config class"""

    def __init__(self):
        self.file = os.path.abspath(os.path.expanduser(os.path.join('~', CONFIG_FILE)))
        self.file_start = '#' * 10 + ' ' + LFM_NAME + ' ' + \
                          'Configuration File' + ' ' + '#' * 10
        self.progs = {} # make a copy
        for k, v in defaultprogs.items():
            self.progs[k] = v
        self.filetypes = filetypes
        self.bookmarks = bookmarks
        self.colors = colors
        self.options = options
        self.misc = misc
        self.confirmations = confirmations
        self.files_ext = files_ext


    def check_progs(self):
        for k, v in defaultprogs.items():
            r = get_shell_output('%s \"%s\"' % (sysprogs['which'], v))
#             self.progs[k] = v if r else '' # python v2.5+
            if r:
                self.progs[k] = v
            else:
                self.progs[k] = ''


    def load(self):
        # check config file
        if not os.path.exists(self.file) or not os.path.isfile(self.file):
            return -1
        f = codecs.open(self.file, encoding=g_encoding)
        title = f.readline()[:-1]
        f.close()
        if title and title != self.file_start:
            return -2
        # load config and validate sections
        cfg = SafeConfigParser()
        cfg.read(self.file)
        for sect in ('Programs', 'File Types', 'Bookmarks', 'Colors',
                     'Options', 'Misc', 'Confirmations', 'Files'):
            if not cfg.has_section(sect):
                print 'Section "%s" does not exist, creating' % sect
                cfg.add_section(sect)
        # programs
        for typ, prog in cfg.items('Programs'):
            self.progs[typ] = prog
        # file types
        for typ, exts in cfg.items('File Types'):
            lst = [t.strip() for t in exts.split(',')]
            self.filetypes[typ] = tuple(lst)
        # bookmarks
        for num, path in cfg.items('Bookmarks'):
            try:
                num = int(num)
            except ValueError:
                print 'Bad bookmark number:', num
                continue
            if 0 <= num <= 9:
                if os.path.isdir(os.path.expanduser(path)):
                    self.bookmarks[num] = decode(path)
                elif not path:
                    self.bookmarks[num] = u'/'
                else:
                    print 'Incorrect directory in bookmark[%d]: %s' % \
                          (num, path)
            else:
                print 'Bad bookmark number:', num
        # colours
        for sec, color in cfg.items('Colors'):
            if not self.colors.has_key(sec):
                print 'Bad object name:', sec
            else:
                (fg, bg) = color.split(' ', 2)
                self.colors[sec.lower()] = (fg.lower(), bg.lower())
        # options
        for what, val in cfg.items('Options'):
            try:
                val = int(val)
            except ValueError:
                print 'Bad option value: %s => %s' % (what, val)
            else:
                if what not in self.options.keys():
                    print 'Bad option: %s => %s' % (what, val)
                else:
                    self.options[what] = val
        if self.options['num_panes'] != 1 or self.options['num_panes'] != 2:
            self.options['num_panes'] = 2
        # misc
        for what, val in cfg.items('Misc'):
            if not isinstance(val, str):
                print 'Bad option value: %s => %s' % (what, val)
            else:
                if what not in self.misc.keys():
                    print 'Bad option: %s => %s' % (what, val)
                else:
                    self.misc[what] = val
        # confirmations
        for what, val in cfg.items('Confirmations'):
            try:
                val = int(val)
            except ValueError:
                print 'Bad confirmation value: %s => %s' % (what, val)
            else:
                if what not in self.confirmations.keys():
                    print 'Bad confirmation option: %s => %s' % (what, val)
                elif val not in (0, 1):
                    print 'Bad confirmation value: %s => %s' % (what, val)
                else:
                    self.confirmations[what] = val
        # File types for color
        for typ, exts in cfg.items('Files'):
            lst = [t.strip() for t in exts.split(',')]
            self.files_ext[typ] = tuple(lst)


    def save(self):
        # title
        buf = self.file_start + '\n'
        # progs
        buf += '\n[Programs]\n'
        for k, v in self.progs.items():
            buf += '%s: %s\n' % (k, v)
        # filetypes
        buf += '\n[File Types]\n'
        for k, vs in self.filetypes.items():
            buf += '%s: %s\n' % (k, ', '.join(vs))
        # bookmarks
        buf += '\n[Bookmarks]\n'
        for i, b in enumerate(self.bookmarks):
            buf += '%d: %s\n' % (i, encode(b))
        # colours
        buf += '\n[Colors]\n'
        for k, v in self.colors.items():
            buf += '%s: %s %s\n' % (k, v[0], v[1])
        # options
        buf += '\n[Options]\n'
        buf += '# automatic_file_encoding_conversion: never = -1, ask = 0, always = 1\n'
        buf += '# sort:\tNone = 0, byName = 1, byName_rev = 2, bySize = 3,\n'
        buf += '# \tbySize_rev = 4, byDate = 5, byDate_rev = 6\n'
        for k, v in self.options.items():
            buf += '%s: %s\n' % (k, v)
        # misc
        buf += '\n[Misc]\n'
        for k, v in self.misc.items():
            buf += '%s: %s\n' % (k, v)
        # confirmations
        buf += '\n[Confirmations]\n'
        for k, v in self.confirmations.items():
            buf += '%s: %s\n' % (k, v)
        # File types for color
        buf += '\n[Files]\n'
        for k, vs in self.files_ext.items():
            buf += '%s: %s\n' % (k, ', '.join(vs))
        # write to file
        f = codecs.open(self.file, 'w', encoding=g_encoding)
        f.write(decode(buf))
        f.close()


######################################################################
