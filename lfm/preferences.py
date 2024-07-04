# -*- coding: utf-8 -*-


from os.path import exists
from shutil import copyfile
from configparser import ConfigParser
from collections import OrderedDict
import pickle

from utils import get_lfm_data_file_contents, ConfigParserWithComments, get_public_actions
from key_defs import key_str2bin, key_bin2str
from common import *


########################################################################
##### Default options and preferences
CONFIGFILE_HEADER = '{0} {1} Configuration File v3.x {0}'.format('#'*10, LFM_NAME)

DEF_OPTIONS = {'save_configuration_at_exit': True,
               'save_history_at_exit': True,
               'show_output_after_exec': True,
               'use_wide_chars': False,
               'rebuild_vfs': False,
               'detach_terminal_at_exec': True,
               'show_dotfiles': True,
               'sort_type': SortType.byName,
               'sort_reverse': False,
               'sort_mix_dirs': False,
               'sort_mix_cases': True,
               'automatic_file_encoding_conversion': False, # ask
               'find_ignorecase': False,
               'grep_ignorecase': True,
               'grep_regex': True}
OPTIONS_TEXT = 'automatic_file_encoding_conversion: {}\nsort_type: {}'.format("never = -1, ask = 0, always = 1", ', '.join([str(s) for s in SortType]))

DEF_CONFIRMATIONS = {'delete': True,
                     'overwrite': True,
                     'quit': True,
                     'ask_rebuild_vfs': True}

DEF_MISC = {'backup_extension': '.bak',
            'diff_type': 'unified'}
MISC_TEXT = 'diff_type: context, unified, ndiff'

DEF_PROGRAMS = {'shell': 'bash',
                'pager': 'less',
                'editor': 'vi',
                'web': 'firefox',
                'audio': 'vlc',
                'video': 'vlc',
                'graphics': 'eog',
                'pdf': 'evince',
                'ebook': 'FBReader'}
FILES_EXT = {'archive': ['gz', 'bz2', 'xz', 'lz', 'lz4', 'tar', 'tgz', 'tbz2',
                         'txz', 'tlz', 'tlz4', 'Z', 'zip', 'rar', '7z', 'arj',
                         'cab', 'lzh', 'lha', 'zoo', 'arc', 'ark',
                         'rpm', 'deb'],
             'audio': ['au', 'flac', 'mid', 'midi', 'mp2', 'mp3', 'mpg', 'ogg', 'wma', 'xm'],
             'data': ['dta', 'nc', 'dbf', 'mdn', 'db', 'mdb', 'dat',
                      'fox', 'dbx', 'mdx', 'sql', 'mssql', 'msql',
                      'ssql', 'pgsql', 'cdx', 'dbi', 'sqlite'],
             'devel': ['c', 'h', 'cc', 'hh', 'cpp', 'hpp',
                       'py', 'pyw', 'hs', 'lua', 'pl', 'pm', 'inc', 'rb',
                       'asm', 'pas', 'f', 'f90', 'pov', 'm', 'pas',
                       'cgi', 'php', 'phps', 'tcl', 'tk',
                       'js', 'java', 'jav', 'jasm', 'vala', 'glade', 'ui',
                       'diff', 'patch', 'css',
                       'sh', 'bash', 'awk', 'm4', 'el',
                       'st', 'mak', 'sl', 'ada', 'caml',
                       'ml', 'mli', 'mly', 'mll', 'mlp', 'prg'],
             'document': ['txt', 'text', 'rtf',
                          'odt', 'odc', 'odp',
                          'abw', 'gnumeric',
                          'sxw', 'sxc', 'sxp', 'sdw', 'sdc', 'sdp',
                          'djvu', 'dvi', 'bib', 'tex',
                          'doc', 'xls', 'ppt', 'pps', 'docx', 'xlsx', 'pptx',
                          'xml', 'xsd', 'xslt', 'sgml', 'dtd',
                          'mail', 'msg', 'letter', 'ics', 'vcs', 'vcard',
                          'lsm', 'po', 'man', '1', 'info'],
             'ebook': ['azw', 'azw3', 'chm', 'epub', 'fb2', 'imp', 'lit', 'mobi', 'prc'],
             'graphics': ['jpg', 'jpeg', 'gif', 'png', 'tif', 'tiff',
                          'pcx', 'bmp', 'xpm', 'xbm', 'eps', 'pic',
                          'rle', 'ico', 'wmf', 'omf', 'ai', 'cdr',
                          'xcf', 'dwb', 'dwg', 'dxf', 'svg', 'dia'],
             'pdf': ['pdf', 'ps'],
             'temp': ['tmp', '$$$', '~', 'bak'],
             'web': ['html', 'shtml', 'htm'],
             'video': ['acc', 'avi', 'asf', 'flv', 'mkv', 'mov', 'mol', 'mpl', 'med',
                       'mp4', 'mpg', 'mpeg', 'ogv', 'swf', 'ogv', 'wmv']}

POWERCLI_FAVS = ['mv "$f" "{$f.replace(\'\', \'\')}"',
                 'less "$f" $',
                 'find "$p" -name "*" -print0 | xargs --null -0 grep -EHcni "TODO|WARNING|FIXME|BUG"',
                 'find "$p" -name "*" -print0 | xargs --null -0 grep -EHcni "TODO|WARNING|FIXME|BUG" >output.txt &',
                 'cp $s "$o"',
                 '',
                 '',
                 '',
                 '',
                 '']


########################################################################
##### Config
class SectContainer:
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)

    def prepare_to_save(self, comment=''):
        # convert True->1, False->0 except non booleans values
        NO_BOOL = ('sort_type', 'backup_extension', 'diff_type')
        d = dict((k, (v if k in NO_BOOL else (1 if v else 0))) for k, v in self.__dict__.items())
        if comment:
            d['#'] = comment
        return OrderedDict(sorted(d.items(), key=lambda k: k[0]))


class Config:
    """Configuration class for lfm"""

    def __init__(self):
        # fill with default values
        self.options = SectContainer(DEF_OPTIONS)
        self.confirmations = SectContainer(DEF_CONFIRMATIONS)
        self.misc = SectContainer(DEF_MISC)
        self.programs = DEF_PROGRAMS
        self.files_ext = FILES_EXT
        self.bookmarks = dict([(b, '/') for b in BOOKMARKS_KEYS])
        self.powercli_favs = POWERCLI_FAVS

    def load(self):
        if not exists(CONFIG_FILE):
            log.warning('Configuration file "{}" does not exist, using default values'.format(CONFIG_FILE))
            self.save()
            return
        try:
            with open(CONFIG_FILE) as f:
                hdr = f.readline()[:-1]
                if hdr and hdr != CONFIGFILE_HEADER:
                    log.error('Configuration file "{}" looks corrupted, using default values'.format(CONFIG_FILE))
                    return
        except:
            log.critical('Can\'t read configuration file "{}", quitting'.format(CONFIG_FILE))
            return
        log.debug('Load configuration file "{}"'.format(CONFIG_FILE))
        cp = ConfigParser()
        cp.read(CONFIG_FILE)
        if cp.has_section('Options'):
            for k, v in cp.items('Options'):
                if k in DEF_OPTIONS:
                    try:
                        exec('self.options.{} = {}'.format(k, v if k=='sort_type' else int(v)!=0))
                    except:
                        log.warning('CONFIGURATION FILE: Invalid value "{}" for "{}" in Options section'.format(v, k))
                else:
                    log.warning('CONFIGURATION FILE: Unknown "{}" in section Options, ignoring'.format(k))
        else:
            log.warning('CONFIGURATION FILE: No "Options" section, using defaults')
        if cp.has_section('Confirmations'):
            for k, v in cp.items('Confirmations'):
                if k in DEF_CONFIRMATIONS:
                    try:
                        exec('self.confirmations.{} = {}'.format(k, int(v)!=0))
                    except:
                        log.warning('CONFIGURATION FILE: Invalid value "{}" for "{}" in Confirmations section'.format(v, k))
                else:
                    log.warning('CONFIGURATION FILE: Unknown "{}" in section Confirmations, ignoring'.format(k))
        else:
            log.warning('CONFIGURATION FILE: No "Confirmations" section, using defaults')
        if cp.has_section('Misc'):
            for k, v in cp.items('Misc'):
                if k in DEF_MISC:
                    try:
                        if k == 'diff_type' and v not in ('context', 'unified', 'ndiff'):
                            raise ValueError
                        exec('self.misc.{} = "{}"'.format(k, v))
                    except:
                        log.warning('CONFIGURATION FILE: Invalid value "{}" for "{}" in Misc section'.format(v, k))
                else:
                    log.warning('CONFIGURATION FILE: Unknown "{}" in section Misc, ignoring'.format(k))
        else:
            log.warning('CONFIGURATION FILE: No "Misc" section, using defaults')
        if cp.has_section('Programs'):
            for k, v in cp.items('Programs'):
                if k in DEF_PROGRAMS:
                    # Don't check if program exists
                    self.programs[k] = v.strip()
                else:
                    log.warning('CONFIGURATION FILE: Unknown "{}" in section Programs, ignoring'.format(k))
        else:
            log.warning('CONFIGURATION FILE: No "Programs" section, using defaults')
        if cp.has_section('Files'):
            for k, v in cp.items('Files'):
                if k in FILES_EXT:
                    self.files_ext[k] = list(map(str.lower, [e.strip() for e in v.split(',')]))
                else:
                    log.warning('CONFIGURATION FILE: Unknown "{}" key in section Files, ignoring'.format(k))
        else:
            log.warning('CONFIGURATION FILE: No "Files" section, filling with defaults')
        if cp.has_section('Bookmarks'):
            for k, v in cp.items('Bookmarks'):
                if k in BOOKMARKS_KEYS:
                    # Don't check if exists
                    # if not exists(v.split()) or not isdir(v.split()):
                    #     continue
                    self.bookmarks[k] = v.strip()
                else:
                    log.warning('CONFIGURATION FILE: Unknown "{}" key in section Bookmarks, ignoring'.format(k))
        else:
            log.warning('CONFIGURATION FILE: No "Bookmarks" section, filling with defaults')
        if cp.has_section('PowerCLI Favs'):
            for i, (_, v) in enumerate(cp.items('PowerCLI Favs')):
                self.powercli_favs[i] = v.strip()
        else:
            log.warning('CONFIGURATION FILE: No "PowerCLI Favs" section, filling with defaults')

    def save(self):
        log.debug('Save configuration file "{}"'.format(CONFIG_FILE))
        cfg = ConfigParserWithComments(CONFIGFILE_HEADER)
        cfg['Options'] = self.options.prepare_to_save(OPTIONS_TEXT)
        cfg['Confirmations'] = self.confirmations.prepare_to_save()
        cfg['Misc'] = self.misc.prepare_to_save(MISC_TEXT)
        cfg['Programs'] = OrderedDict(sorted(self.programs.items(), key=lambda k: k[0]))
        d = dict((k, ', '.join(sorted(v))) for k, v in self.files_ext.items())
        cfg['Files'] = OrderedDict(sorted(d.items(), key=lambda k: k[0]))
        cfg['Bookmarks'] = OrderedDict(sorted(self.bookmarks.items(), key=lambda k: k[0]))
        cfg['PowerCLI Favs'] = OrderedDict(dict(((i, c) for i, c in enumerate(self.powercli_favs))))
        try:
            with open(CONFIG_FILE, 'w') as cfgfile:
                cfg.write(cfgfile)
        except:
            log.error('Couldn\'t write configuration file "{}"'.format(CONFIG_FILE))
            raise


########################################################################
##### Color Theme
def load_colortheme():
    log.debug('Parse ColorTheme file')
    if not exists(THEME_FILE):
        log.warning('ColorTheme file does not exist, copying default')
        copy_default_colortheme_file()
    cp = ConfigParser()
    cp.read(THEME_FILE)
    if not cp.has_section('Colors'):
        log.warning('ColorTheme file corrupted, copying default')
        copy_default_colortheme_file()
    # parse file
    colors = dict()
    rels = []
    for it, color_desc in cp.items('Colors'):
        it = it.strip().lower()
        if it not in COLOR_ITEMS:
            log.warning('Color item invalid: {}'.format(it))
            continue
        if color_desc[0] == '=':
            toit = color_desc[1:]
            if toit not in COLOR_ITEMS:
                log.warning('Color item pointed to an invalid item: {}: {}'.format(it, toit))
                continue
            rels.append((it, toit))
            continue
        (fg, bg) = map(str.lower, color_desc.split(maxsplit=1))
        if fg not in VALID_COLORS or bg not in VALID_COLORS:
            log.warning('Color item contain invalid colors: {}: {}'.format(it, color_desc))
            continue
        colors[it] = (fg, bg)
    # fill ='s
    for it, toit in rels:
        if toit not in colors:
            log.warning('Color item pointed to undefined item: {}: {}'.format(it, toit))
            continue
        colors[it] = colors[toit]
    # check if missing items
    for it in set(COLOR_ITEMS) - set(colors.keys()):
        log.warning('Missing Color item {}, added as white on black'.format(it))
        colors[it] = ('white', 'black')
    return colors


def copy_default_colortheme_file():
    try:
        with open(THEME_FILE, 'w') as f:
            default_colortheme = get_lfm_data_file_contents('lfm-default.theme')
            f.write(default_colortheme)
    except:
        log.error('Can\'t copy default ColorTheme file: {}'.format(THEME_FILE))
        raise


########################################################################
##### Keys
def load_keys():
    log.debug('Parse Keys file')
    if not exists(KEYS_FILE):
        log.warning('Keys file does not exist, copying default')
        copy_default_keys_file()
    cp = ConfigParser()
    cp.read(KEYS_FILE)
    if not cp.has_section('Main'):
        log.warning('Keys file corrupted, copying default')
        copy_default_keys_file()
    # parse file
    public_api = get_public_actions()
    actions = dict()
    for it, key_desc in cp.items('Main'):
        it = it.strip().lower()
        if it not in public_api:
            log.warning('KEYS: Action item invalid in section Main: {}'.format(it))
            continue
        try:
            actions[it] = [key_str2bin(k) for k in key_desc.split()]
        except:
            log.warning('KEYS: Action "{}" contains invalid key definition in section Main: "{}"'.format(it, key_desc))
    # check if missing items
    for it in set(public_api) - set(actions.keys()):
        log.warning('KEYS: Missing Action item {}'.format(it))
    # transpose dict:  {action: keys} => {keys: action}
    # and check if same key used for different actions
    # keys = dict([(k, a) for a, ks in actions.items() for k in ks])
    keys = dict()
    for a, ks in actions.items():
        for k in ks:
            if k in keys.keys():
                log.warning('KEYS: Can\'t use key "{}" in action "{}", alredy used in "{}"'.format(key_bin2str(k), a, keys[k]))
                continue
            else:
                keys[k] = a
    return keys


def copy_default_keys_file():
    try:
        with open(KEYS_FILE, 'w') as f:
            default_keys = get_lfm_data_file_contents('lfm-default.keys')
            f.write(default_keys)
    except:
        log.error('Can\'t copy default Keys file: {}'.format(KEYS_FILE))
        raise


def dump_keys_to_file(keys):
    log.info('Dump keys into file')
    with open(DUMP_KEYS_FILE, 'w') as f:
        f.write('#'*30 + ' LFM dump keys ' + '#'*30 + '\n\n')
        f.write('#'*20 + ' Key -> Action ' + '#'*20 + '\n')
        lines = ['{:10} ->   {}'.format(key_bin2str(k), a) for k, a in keys.items()]
        f.write('\n'.join(sorted(lines)))
        f.write('\n\n' + '#'*20 + ' Action -> Key ' + '#'*20 + '\n')
        actions = dict()
        for k, a in keys.items():
            if a in actions:
                actions[a].append(key_bin2str(k))
            else:
                actions[a] = [key_bin2str(k)]
        lines = ['{:24} ->  {}'.format(a, ', '.join(sorted(ks))) for a, ks in actions.items()]
        f.write('\n'.join(sorted(lines)))
        missing_actions = set(get_public_actions()) - set(actions)
        if len(missing_actions) > 0:
            f.write('\n\nActions with no keys:\n')
            for a in sorted(missing_actions):
                f.write('. {}\n'.format(a))
        else:
            f.write('\n\nAll actions have key binding\n')
        f.write('\n' + '#'*70)


########################################################################
##### History
class History(dict):
    def __init__(self):
        self._data = HISTORY_BLANK

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, val):
        self._data[key] = val

    def delete(self):
        log.info('Delete history')
        self._data = HISTORY_BLANK
        self.save()

    def load(self):
        log.info('Load history file from "{}"'.format(HISTORY_FILE))
        with open(HISTORY_FILE, 'rb') as f:
            self._data = pickle.load(f)

    def save(self):
        log.info('Save history file to "{}"'.format(HISTORY_FILE))
        with open(HISTORY_FILE, 'wb') as f:
            pickle.dump(self._data, f, -1)

    def append(self, section, new_entry):
        assert section in self._data.keys()
        if new_entry == '':
            return
        if new_entry in self._data[section]:
            self._data[section].remove(new_entry)
        self._data[section].append(new_entry)
        self._data[section] = self._data[section][-HISTORY_MAX:]


########################################################################
