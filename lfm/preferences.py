"""prefences.py

This module defines the preferences class for lfm.
"""


import os, os.path, re
import curses

import files


PROGNAME = 'lfm - Last File Manager'


##################################################
##### preferences
##################################################
class Preferences:
    """Preferences class"""
    
    def __init__(self, prefsfile, defaultprogs):
        self.file = os.path.abspath(os.path.expanduser(os.path.join('~',
                                                                    prefsfile)))
        self.file_start = '#' * 10 + ' ' + PROGNAME + ' ' + \
                          'Preferences File' + ' ' + '#' * 10
        self.progs = {}
        self.check_defaultprogs(defaultprogs)
        self.modes = { 'sort': files.SORTTYPE_byName,
                       'sort_mix_dirs': 0, 'sort_mix_cases': 0 }
        self.confirmations = { 'delete': 1, 'overwrite': 1, 'quit': 0,
                               'ask_rebuild_vfs': 1}
        self.options = { 'save_conf_at_exit': 1, 'show_output_after_exec': 1,
                         'rebuild_vfs': 0}
        self.bookmarks = [ '/',
                           '/home/inigo',
                           '/home/inigo/personal',
                           '/home/inigo/devel/mine/lfm',
                           '/zzz/compiling/gnome',
                           '/zzz/compiling/python',
                           '/zzz/compiling/linux',
                           '/etc',
                           '/root',
                           '/dfsdf' ]
        self.colors = {
                'title': ('yellow', 'blue'),
                'files': ('white', 'black'),
                'current_file': ('blue', 'cyan'),
                'messages': ('magenta', 'cyan'),
                'help': ('green', 'black'),
                'file_info': ('red', 'black'),
                'error_messages1': ('white', 'red'),
                'error_messages2': ('black', 'red'),
                'buttons': ('yellow', 'red'),
                'selected_file': ('yellow', 'black'),
                'current_selected_file': ('yellow', 'cyan') }


    def check_defaultprogs(self, progs):
        for k, vs in progs.items():
            for v in vs:
                r = files.exec_cmd('which \"%s\"' % v)
                if r:
                    self.progs[k] = r.strip()
                    break
            else:
                self.progs[k] = ''
                

    def load(self):
        if not os.path.exists(self.file) or not os.path.isfile(self.file):
            return -1
        f = open(self.file)
        title = f.readline()
        title = title[:-1]
        if title and title != self.file_start:
            return -2
        pr = re.compile(r'^\[ (.*) \]', re.I)
        section = ''
        for l in f.readlines():
            l = l.strip()
            if not l or l[0] == '#':
                continue
            m = pr.match(l)
            if m:
                section = l[m.start():m.end()].lower()[2:-2]
                m = None
                continue

            # It's better to split only once, so user can use values
            # containing colons.
            b = l.split(':', 1)
            b[0] = b[0].strip()
            b[1] = b[1].strip()
            if section == 'programs':
                for k in self.progs.keys():
                    if b[0] == k:
                        self.progs[k] = b[1]
#                          print 'Program->%s = %s' % (k, b[1])
                        break
                else:
                    print 'Bad program option:', b[0]
            elif section == 'modes':
                try:
                    val = int(b[1])
                except ValueError:
                    print 'Bad mode value:', l
                if val == 0 or val == 1:
                    for k in self.modes.keys():
                        if b[0] == k:
                            self.modes[k] = val
#                            print 'Mode->%s = %d' % (k, val)
                            break
                    else:
                        print 'Bad mode option:', b[0]
                else:
                    print 'Bad mode value:', l
            elif section == 'confirmations':
                try:
                    val = int(b[1])
                except ValueError:
                    print 'Bad confirmation value:', l
                if val == 0 or val == 1:
                    for k in self.confirmations.keys():
                        if b[0] == k:
                            self.confirmations[k] = val
#                            print 'Confirmations->%s = %d' % (k, val)
                            break
                    else:
                        print 'Bad confirmation option:', b[0]
                else:
                    print 'Bad confirmation value:', l
            elif section == 'options':
                try:
                    val = int(b[1])
                except ValueError:
                    print 'Bad option value:', l
                if val == 0 or val == 1:
                    for k in self.options.keys():
                        if b[0] == k:
                            self.options[k] = val
#                            print 'Options->%s = %d' % (k, val)
                            break
                    else:
                        print 'Bad option option:', b[0]
                else:
                    print 'Bad option value:', l
            elif section == 'bookmarks':
                try:
                    n = int(b[0])
                except ValueError:
                    print 'Bad bookmark number:', b[0]
                if 0 <= n <= 9:
                    if os.path.isdir(b[1]):
                        self.bookmarks[n] = b[1]
#                        print 'Bookmark[%d] = %s' % (n, b[1])
                    elif not b[1]:
                        # No bookmark defined -- it's not an error. We should
                        # not be so verbose.
                        self.bookmarks[n] = ''
                    else:
                        print 'Incorrect directory in bookmark[%d]: %s' % (n, b[1])
                else:
                    print 'Bad bookmark number:', b[0]
            elif section == 'colors':
                b = [b[0].lower(), b[1].lower()]
                if not self.colors.has_key(b[0]):
                    print 'Bad object name:', b[0]
                else:
                    (fg, bg) = b[1].split(' ')
                    self.colors[b[0]] = (str(fg), str(bg))
            else:
                print 'Bad section'

        f.close()


    def save(self):
        f = open(self.file, 'w')
        # title
        f.write(self.file_start)
        f.write('\n\n')
        # progs
        f.write('[ Programs ]\n')
        for k, v in self.progs.items():
            f.write('%s: %s\n' % (k, v))
        f.write('\n')
        # modes
        f.write('[ Modes ]\n')
        f.write('# sort:\tNone = 0, byName = 1, byName_rev = 2, bySize = 3,\n')
        f.write('# \tbySize_rev = 4, byDate = 5, byDate_rev = 6\n')
        for k, v in self.modes.items():
            f.write('%s: %s\n' % (k, v))
        f.write('\n')
        # confirmations
        f.write('[ Confirmations ]\n')
        for k, v in self.confirmations.items():
            f.write('%s: %s\n' % (k, v))
        f.write('\n')
        # options
        f.write('[ Options ]\n')
        for k, v in self.options.items():
            f.write('%s: %s\n' % (k, v))
        f.write('\n')
        # bookmarks
        f.write('[ Bookmarks ]\n')
        i = 0
        for b in self.bookmarks:
            f.write('%d: %s\n' % (i, b))
            i += 1
        f.write('\n')
        # colors
        f.write('[ Colors ]\n')
        # FIXME: Keys are written in a random order.
        for k, v in self.colors.items():
            f.write('%s: %s %s\n' % (k, v[0], v[1]))

        f.close()


    def edit(self, app):
        curses.endwin()
        os.system('%s \"%s\"' % (app.prefs.progs['editor'],
                                 self.file))
        curses.curs_set(0)
