# -*- coding: iso-8859-15 -*-

"""actions.py

This module contains the actions when key pressed.
"""


import os, os.path
import sys
import time
from glob import glob
import curses

from __init__ import *
import files
from utils import *
import vfs
import messages
import pyview


##################################################
##### global variables
##################################################
app = None


##################################################
##### actions
##################################################
keytable= {
    # movement
    ord('p'): 'cursor_up',
    ord('P'): 'cursor_up',
    curses.KEY_UP: 'cursor_up',
    ord('d'): 'cursor_down',
    ord('D'): 'cursor_down',
    curses.KEY_DOWN: 'cursor_down',
    curses.KEY_PPAGE: 'page_previous',
    curses.KEY_BACKSPACE: 'page_previous',
    0x08: 'page_previous',      # BackSpace
    0x10: 'page_previous',      # Ctrl-P
    curses.KEY_NPAGE: 'page_next',
    ord(' '): 'page_next',
    0x0E: 'page_next',          # Ctrl-N
    curses.KEY_HOME: 'home',
    0x16A: 'home',
    0x001: 'home',
    curses.KEY_END: 'end',
    0x181: 'end',
    0x005: 'end',

    # change dir
    curses.KEY_LEFT: 'cursor_left',
    curses.KEY_RIGHT: 'cursor_right',
    10: 'enter',
    13: 'enter',
    ord('g'): 'goto_dir',
    ord('G'): 'goto_dir',
    0x13: 'goto_file',          # Ctrl-S
    0x14: 'tree',               # Ctrl-T
    ord('0'): 'bookmark_0',
    ord('1'): 'bookmark_1',
    ord('2'): 'bookmark_2',
    ord('3'): 'bookmark_3',
    ord('4'): 'bookmark_4',
    ord('5'): 'bookmark_5',
    ord('6'): 'bookmark_6',
    ord('7'): 'bookmark_7',
    ord('8'): 'bookmark_8',
    ord('9'): 'bookmark_9',
    0x04: 'select_bookmark',    # Ctrl-D
    ord('b'): 'set_bookmark',
    ord('B'): 'set_bookmark',

    # panels
    ord('\t'): 'change_panel',  # tab
    ord('.'): 'toggle_panels',
    ord(','): 'swap_panels',
    0x15: 'swap_panels',        # Ctrl-U
    ord('='): 'same_panels',

    # selections
    curses.KEY_IC: 'select_item',
    ord('+'): 'select_group',
    ord('-'): 'deselect_group',
    ord('*'): 'invert_select',

    # misc
    ord('#'): 'show_size',
    ord('s'): 'sort',
    ord('S'): 'sort',
    ord('i'): 'file_info',
    ord('I'): 'file_info',
    ord('@'): 'do_something_on_file',
    0xF1: 'special_regards',    # special regards
    ord('/'): 'find_grep',
    ord('t'): 'touch_file',
    ord('T'): 'touch_file',
    ord('l'): 'create_link',
    ord('L'): 'create_link',
    0x0C: 'edit_link',          # Ctrl-L
    0x0F: 'open_shell',         # Ctrl-O

    # main functions
    ord('v'): 'view_file',
    ord('V'): 'view_file',
    curses.KEY_F3: 'view_file',
    ord('e'): 'edit_file',
    ord('E'): 'edit_file',
    curses.KEY_F4: 'edit_file',
    ord('c'): 'copy',
    ord('C'): 'copy',
    curses.KEY_F5: 'copy',
    ord('m'): 'move',
    ord('M'): 'move',
    curses.KEY_F6: 'move',
    ord('r'): 'rename',
    ord('R'): 'rename',
    curses.KEY_F7: 'make_dir',
    ord('d'): 'delete',
    ord('D'): 'delete',
    curses.KEY_DC: 'delete',
    curses.KEY_F8: 'delete',

    # menu
    ord('h'): 'show_help',
    ord('H'): 'show_help',
    curses.KEY_F1: 'show_help',
    ord('f'): 'file_menu',
    ord('F'): 'file_menu',
    curses.KEY_F2: 'file_menu',
    curses.KEY_F9: 'general_menu',

    # terminal resize:
    curses.KEY_RESIZE: 'resize_window',
    
    # quit & exit
    ord('q'): 'quit',
    ord('Q'): 'quit',
    curses.KEY_F10: 'quit',   
    ord('x'): 'exit',
    ord('X'): 'exit'
}


def do(_app, panel, ch):
    global app
    app = _app
    try:
        act = 'ret = %s(panel)'  % keytable[ch]
    except KeyError:
        curses.beep()
    else:
        exec(act)
        return ret


##################################################
##### actions
##################################################

# movement
def cursor_up(panel):
    panel.file_i -= 1
    panel.fix_limits()


def cursor_down(panel):
    panel.file_i += 1
    panel.fix_limits()


def page_previous(panel):
    panel.file_i -= panel.dims[0]
    if panel.pos == 1 or panel.pos == 2:
        panel.file_i += 3
    panel.fix_limits()


def page_next(panel):
    panel.file_i += panel.dims[0]
    if panel.pos == 1 or panel.pos == 2:
        panel.file_i -= 3
    panel.fix_limits()


def home(panel):
    panel.file_i = 0
    panel.fix_limits()


def end(panel):
    panel.file_i = panel.nfiles - 1
    panel.fix_limits()


# change dir
def cursor_left(panel):
    if not panel.vfs:
        if panel.path != os.sep:
            olddir = os.path.basename(panel.path)
            panel.init_dir(os.path.dirname(panel.path))
            panel.file_i = panel.sorted.index(olddir)
            panel.fix_limits()
    else:
        if panel.path == panel.base:
            olddir = os.path.basename(panel.vbase).replace('#vfs', '')
            vfs.exit(app, panel)                          
            panel.init_dir(os.path.dirname(panel.vbase))
            panel.file_i = panel.sorted.index(olddir)
            panel.fix_limits()
        else:
            olddir = os.path.basename(panel.path)
            pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
            panel.init_dir(os.path.dirname(panel.path))
            panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
            panel.file_i = panel.sorted.index(olddir)
            panel.fix_limits()


def cursor_right(panel):
    filename = panel.sorted[panel.file_i]
    vfstype = check_compressed_tarfile(app, filename)
    if panel.files[filename][files.FT_TYPE] == files.FTYPE_DIR:
        if not panel.vfs:
            if filename == os.pardir:
                olddir = os.path.basename(panel.path)
                panel.init_dir(os.path.dirname(panel.path))
                panel.file_i = panel.sorted.index(olddir)
                panel.fix_limits()
            else:
                panel.init_dir(os.path.join(panel.path, filename))

        else:
            if panel.path == panel.base and filename == os.pardir:
                olddir = os.path.basename(panel.vbase).replace('#vfs', '')
                vfs.exit(app, panel)                          
                panel.init_dir(os.path.dirname(panel.vbase))
                panel.file_i = panel.sorted.index(olddir)
                panel.fix_limits()
            else:
                pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
                panel.init_dir(os.path.join(panel.path, filename))
                panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
    elif panel.files[filename][files.FT_TYPE] == files.FTYPE_LNK2DIR:
        panel.init_dir(files.get_linkpath(panel.path, filename))
    elif (panel.files[filename][files.FT_TYPE] == files.FTYPE_REG or \
       panel.files[filename][files.FT_TYPE] == files.FTYPE_LNK) and \
       vfstype != -1:
        vfs.init(app, panel, filename, vfstype)
    else:
        return


def enter(panel):
    filename = panel.sorted[panel.file_i]
    vfstype = check_compressed_tarfile(app, filename)
    if (panel.files[filename][files.FT_TYPE] == files.FTYPE_REG or \
       panel.files[filename][files.FT_TYPE] == files.FTYPE_LNK) and \
       vfstype != -1:
        vfs.init(app, panel, filename, vfstype)
    elif panel.files[filename][files.FT_TYPE] == files.FTYPE_DIR:
        if not panel.vfs:
            if filename == os.pardir:
                olddir = os.path.basename(panel.path)
                panel.init_dir(os.path.dirname(panel.path))
                panel.file_i = panel.sorted.index(olddir)
                panel.fix_limits()
            else:
                panel.init_dir(os.path.join(panel.path, filename))
        else:
            if panel.path == panel.base and filename == os.pardir:
                olddir = os.path.basename(panel.vbase).replace('#vfs', '')
                vfs.exit(app, panel)                          
                panel.init_dir(os.path.dirname(panel.vbase))
                panel.file_i = panel.sorted.index(olddir)
                panel.fix_limits()
            else:
                pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
                panel.init_dir(os.path.join(panel.path, filename))
                panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
    elif panel.files[filename][files.FT_TYPE] == files.FTYPE_LNK2DIR:
        panel.init_dir(files.get_linkpath(panel.path, filename))
    elif panel.files[filename][files.FT_TYPE] == files.FTYPE_EXE:
        do_execute_file(panel)
    elif panel.files[filename][files.FT_TYPE] == files.FTYPE_REG:
        do_special_view_file(panel)
    else:
        return


def goto_dir(panel):
    todir = doEntry('Go to directory', 'Type directory name')
    app.show()
    if todir == None or todir == "":
        return
    todir = os.path.join(panel.path, todir)
    if panel.vfs:
        vfs.exit(app, panel)
    panel.init_dir(todir)
    panel.fix_limits()


def goto_file(panel):
    tofile = doEntry('Go to file', 'Type how file name begins')
    app.show()
    if tofile == None or tofile == "":
        return
    thefiles = panel.sorted[panel.file_i:]
    for f in thefiles:
        if f.find(tofile) == 0:
            break
    else:
        return
    panel.file_i = panel.sorted.index(f)
    panel.fix_limits()


def tree(panel):
    if panel.vfs:
        return
    panel_i = app.panel
    app.panel = not panel_i
    panel.show()
    t = Tree(panel.path, panel.pos)
    ans = t.run()
    del(t)
    app.panel = panel_i
    if ans != -1:
        panel.init_dir(ans)
        panel.fix_limits()


def bookmark_0(panel):
    goto_bookmark(panel, 0)


def bookmark_1(panel):
    goto_bookmark(panel, 1)


def bookmark_2(panel):
    goto_bookmark(panel, 2)


def bookmark_3(panel):
    goto_bookmark(panel, 3)


def bookmark_4(panel):
    goto_bookmark(panel, 4)


def bookmark_5(panel):
    goto_bookmark(panel, 5)


def bookmark_6(panel):
    goto_bookmark(panel, 6)


def bookmark_7(panel):
    goto_bookmark(panel, 7)


def bookmark_8(panel):
    goto_bookmark(panel, 8)


def bookmark_9(panel):
    goto_bookmark(panel, 9)


def select_bookmark(panel):
    cmd = messages.MenuWin('Select Bookmark', app.prefs.bookmarks).run()
    if cmd == -1:
        return
    if panel.vfs:
        vfs.exit(app, panel)
    panel.init_dir(cmd)
    panel.fix_limits()


def set_bookmark(panel):
    if panel.vfs:
        messages.error('Set bookmark', 'Can\'t bookmark inside vfs')
        return
    while 1:
        ch = messages.get_a_key('Set bookmark',
                                'Press 0-9 to save the bookmark, Ctrl-C to quit')
        if 0x30 <= ch <= 0x39:         # 0..9
            app.prefs.bookmarks[ch-0x30] = panel.path[:]
            break
        elif ch == -1:                 # Ctrl-C
            break


# panels
def change_panel(panel):
    if panel.pos == 3:
        return
    return app.panel

    
def toggle_panels(panel):
    if panel.pos == 3:
        # now => 2 panels mode
        app.panels[0].pos = 1
        app.panels[1].pos = 2
    else:
        # now => full panel mode
        if app.panel == 0:
            app.panels[0].pos = 3
            app.panels[1].pos = 0
        else:
            app.panels[0].pos = 0
            app.panels[1].pos = 3
    app.panels[0].init_curses(app.panels[0].pos)
    app.panels[1].init_curses(app.panels[1].pos)
    panel.fix_limits()
    app.get_otherpanel().fix_limits()


def swap_panels(panel):
    if panel.pos == 3:
        return
    otherpanel = app.get_otherpanel()
    panel.pos, otherpanel.pos = otherpanel.pos, panel.pos
    panel.init_curses(panel.pos)
    otherpanel.init_curses(otherpanel.pos)


def same_panels(panel):
    otherpanel = app.get_otherpanel()
    if not panel.vfs:
        if otherpanel.vfs:
            vfs.exit(app, otherpanel)
        otherpanel.init_dir(panel.path)
        otherpanel.fix_limits()
    else:
        if panel.vfs == 'pan':
            vfs.pan_copy(app, panel, otherpanel)
        else:
            vfs.copy(app, panel, otherpanel)
        pvfs, base, vbase = otherpanel.vfs, otherpanel.base, otherpanel.vbase
        otherpanel.init_dir(base + panel.path.replace(panel.base, ''))
        otherpanel.fix_limits()
        otherpanel.vfs, otherpanel.base, otherpanel.vbase = pvfs, base, vbase


# selections
def select_item(panel):
    filename = panel.sorted[panel.file_i]
    if filename == os.pardir:
        panel.file_i += 1
        panel.fix_limits()
        return
    try:
        panel.selections.index(filename)
    except ValueError:
        panel.selections.append(filename)
    else:
        panel.selections.remove(filename)
    panel.file_i += 1
    panel.fix_limits()


def select_group(panel):
    pattern = doEntry('Select group', 'Type pattern', '*')
    if pattern == None or pattern == '':
        return
    fullpath = os.path.join(panel.path, pattern)
    [panel.selections.append(os.path.basename(f)) for f in glob(fullpath)]


def deselect_group(panel):
    pattern = doEntry('Deselect group', 'Type pattern', '*')
    if pattern == None or pattern == '':
        return
    fullpath = os.path.join(panel.path, pattern)
    for f in [os.path.basename(f) for f in glob(fullpath)]:
        if f in panel.selections:
            panel.selections.remove(f)

def invert_select(panel):
    selections_old = panel.selections[:]
    panel.selections = []
    for f in panel.sorted:
        if f not in selections_old and f != os.pardir:
            panel.selections.append(f)


# misc
def show_size(panel):
    show_dirs_size(panel)


def sort(panel):
    app.show()
    sort(panel)


def file_info(panel):
    do_show_file_info(panel)


def do_something_on_file(panel):
    do_something_on_file(panel)


def special_regards(panel):
    messages.win('Special Regards',
                 '   Maite zaitut, Montse\n   T\'estimo molt, Montse')


def find_grep(panel):
    findgrep(panel)


def touch_file(panel):
    newfile = doEntry('Touch file', 'Type file name')
    if newfile == None or newfile == "":
        return
    fullfilename = os.path.join(panel.path, newfile)
    i, err = os.popen4('touch \"%s\"' % fullfilename)
    err = err.read().split(':')[-1:][0].strip()
    if err:
        app.show()
        messages.error('Touch file', '%s: %s' % (newfile, err))
    curses.curs_set(0)
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


def create_link(panel):
    otherpanel = app.get_otherpanel()
    if panel.path != otherpanel.path:
        otherfile = os.path.join(otherpanel.path,
                                 otherpanel.sorted[otherpanel.file_i])
    else:
        otherfile = otherpanel.sorted[otherpanel.file_i]
    newlink, pointto = doDoubleEntry('Create link',
                                     'Link name', '', 1, 1,
                                     'Pointing to', otherfile, 1, 1)
    if newlink == None or pointto == None:
        return
    if newlink == '':
        app.show()
        messages.error('Edit link', 'You must type new link name')
        return
    if pointto == '':
        app.show()
        messages.error('Edit link', 'You must type pointed file')
        return
    fullfilename = os.path.join(panel.path, newlink)
    ans = files.create_link(pointto, fullfilename)
    if ans:
        app.show()
        messages.error('Edit link', '%s (%s)' % (ans,
                       self.sorted[self.file_i]))
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


def edit_link(panel):
    fullfilename = os.path.join(panel.path, panel.sorted[panel.file_i])
    if not os.path.islink(fullfilename):
        return
    pointto = doEntry('Edit link', 'Link \'%s\' points to' % \
                      panel.sorted[panel.file_i],
                      os.readlink(fullfilename))
    if pointto == None or pointto == "":
        return
    if pointto != None and pointto != "" and \
       pointto != os.readlink(fullfilename):
        ans = files.modify_link(pointto, fullfilename)
        if ans:
            app.show()
            messages.error('Edit link', '%s (%s)' % (ans,
                           panel.sorted[self.file_i]))
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


def open_shell(panel):
    curses.endwin()
    os.system('cd \"%s\"; %s' % (panel.path,
                                 app.prefs.progs['shell']))
    curses.curs_set(0)
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


# main functions
def view_file(panel):
    do_view_file(panel)


def edit_file(panel):
    do_edit_file(panel)


def copy(panel):
    otherpanel = app.get_otherpanel()
    destdir = otherpanel.path + os.sep
    if len(panel.selections):
        buf = 'Copy %d items to' % len(panel.selections)
        destdir = doEntry('Copy', buf, destdir)
        if destdir:
            overwrite_all = 0
            for f in panel.selections:
                if not overwrite_all:
                    if app.prefs.confirmations['overwrite']:
                        ans = run_thread(app, 'Copying \'%s\'' % f,
                                         files.copy,
                                         panel.path, f, destdir)
                        if type(ans) == type(''):
                            app.show()
                            ans2 = messages.confirm_all('Copy', 'Overwrite \'%s\'' % ans, 1)
                            if ans2 == -1:
                                break
                            elif ans2 == 2:
                                overwrite_all = 1
                            if ans2 != 0:
                                ans = run_thread(app, 'Copying \'%s\'' % f,
                                                 files.copy,
                                                 panel.path, f,
                                                 destdir, 0)
                            else:
                                continue
                    else:
                        ans = run_thread(app, 'Copying \'%s\'' % f,
                                         files.copy,
                                         panel.path, f, destdir, 0)
                else:
                    ans = run_thread(app, 'Copying \'%s\'' % f, files.copy,
                                     panel.path, f, destdir, 0)
                if ans and ans != -100:
                    for p in app.panels:
                        p.show()
                    messages.error('Copy \'%s\'' % f, '%s (%s)' % ans)
            panel.selections = []
        else:
            return
    else:
        filename = panel.sorted[panel.file_i]
        if filename == os.pardir:
            return
        buf = 'Copy \'%s\' to' % filename
        destdir = doEntry('Copy', buf, destdir)
        if destdir:
            if app.prefs.confirmations['overwrite']:
                ans = run_thread(app, 'Copying \'%s\'' % filename,
                                 files.copy,
                                 panel.path, filename, destdir)
                if type(ans) == type(''):
                    app.show()
                    ans2 = messages.confirm('Copy',
                                            'Overwrite \'%s\'' %
                                            ans, 1)
                    if ans2 != 0 and ans2 != -1:
                        ans = run_thread(app, 'Copying \'%s\'' % filename,
                                         files.copy,
                                         panel.path, filename, destdir, 0)
                    else:
                        return
            else:
                ans = run_thread(app, 'Copying \'%s\'' % filename,
                                 files.copy,
                                 panel.path, filename, destdir, 0)
            if ans and ans != -100:
                for p in app.panels:
                    p.show()
                messages.error('Copy \'%s\'' % filename,
                               '%s (%s)' % ans)
        else:
            return
    panel.refresh_panel(panel)
    panel.refresh_panel(otherpanel)


def move(panel):
    otherpanel = app.get_otherpanel()
    destdir = otherpanel.path + os.sep
    if len(panel.selections):
        buf = 'Move %d items to' % len(panel.selections)
        destdir = doEntry('Move', buf, destdir)
        if destdir:
            overwrite_all = 0
            for f in panel.selections:
                if not overwrite_all:
                    if app.prefs.confirmations['overwrite']:
                        ans = run_thread(app, 'Moving \'%s\'' % f,
                                         files.move,
                                         panel.path, f, destdir)
                        if type(ans) == type(''):
                            app.show()
                            ans2 = messages.confirm_all('Move', 'Overwrite \'%s\'' % ans, 1)
                            if ans2 == -1:
                                break
                            elif ans2 == 2:
                                overwrite_all = 1
                            if ans2 != 0:
                                ans = run_thread(app, 'Moving \'%s\'' % f,
                                                 files.move,
                                                 panel.path, f,
                                                 destdir, 0)
                            else:
                                continue
                    else:
                        ans = run_thread(app, 'Moving \'%s\'' % f,
                                         files.move,
                                         panel.path, f, destdir, 0)
                else:
                    ans = run_thread(app, 'Moving \'%s\'' % f, files.move,
                                     panel.path, f, destdir, 0)
                if ans and ans != -100:
                    for p in app.panels:
                        p.show()
                    messages.error('Move \'%s\'' % f, '%s (%s)' % ans)
            panel.selections = []
        else:
            return
    else:
        filename = panel.sorted[panel.file_i]
        if filename == os.pardir:
            return
        buf = 'Move \'%s\' to' % filename
        destdir = doEntry('Move', buf, destdir)
        if destdir:
            if app.prefs.confirmations['overwrite']:
                ans = run_thread(app, 'Moving \'%s\'' % filename,
                                 files.move,
                                 panel.path, filename, destdir)
                if type(ans) == type(''):
                    app.show()
                    ans2 = messages.confirm('Move',
                                            'Overwrite \'%s\'' %
                                            ans, 1)
                    if ans2 != 0 and ans2 != -1:
                        ans = run_thread(app, 'Moving \'%s\'' % filename,
                                         files.move,
                                         panel.path, filename, destdir, 0)
                    else:
                        return
            else:
                ans = run_thread(app, 'Moving \'%s\'' % filename,
                                 files.move,
                                 panel.path, filename, destdir, 0)
            if ans and ans != -100:
                for p in app.panels:
                    p.show()
                messages.error('Move \'%s\'' % filename,
                               '%s (%s)' % ans)
                ans = files.move(panel.path, filename, destdir, 0)
        else:
            return
    file_i_old = panel.file_i
    pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
    panel.init_dir(panel.path)
    panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
    if file_i_old > panel.nfiles:
        panel.file_i = panel.nfiles
    else:
        panel.file_i = file_i_old
    panel.fix_limits()
    panel.refresh_panel(panel)
    panel.refresh_panel(otherpanel)


def rename(panel):
    if len(panel.selections):
        fs = panel.selections[:]
    else:
        fs = [(panel.sorted[panel.file_i])]
    for filename in fs:
        app.show()
        if filename == os.pardir:
            continue
        buf = 'Rename \'%s\' to' % filename
        newname = doEntry('Rename', buf, filename)
        if newname:
            if app.prefs.confirmations['overwrite']:
                ans = run_thread(app, 'Renaming \'%s\'' % filename,
                                 files.move,
                                 panel.path, filename, newname)
                if type(ans) == type(''):
                    app.show()
                    ans2 = messages.confirm('Rename',
                                            'Overwrite \'%s\'' %
                                            ans, 1)
                    if ans2 != 0 and ans2 != -1:
                        ans = run_thread(app, 'Renaming \'%s\'' % filename,
                                         files.move,
                                         panel.path, filename, newname, 0)
                    else:
                        continue
            else:
                ans = run_thread(app, 'Renaming \'%s\'' % filename,
                                 files.move,
                                 panel.path, filename, newname, 0)
            if ans and ans != -100:
                for p in app.panels:
                    p.show()
                messages.error('Rename \'%s\'' % filename,
                               '%s (%s)' % ans)
                ans = files.move(panel.path, filename, newname, 0)
        else:
            continue
    file_i_old = panel.file_i
    pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
    panel.init_dir(panel.path)
    panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
    if file_i_old > panel.nfiles:
        panel.file_i = panel.nfiles
    else:
        panel.file_i = file_i_old
    panel.fix_limits()
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


def make_dir(panel):
    newdir = doEntry('Make directory', 'Type directory name')
    if newdir == None or newdir == "":
        return
    ans = files.mkdir(panel.path, newdir)
    if ans:
        for p in app.panels:
            p.show()
        messages.error('Make directory',
                       '%s (%s)' % (ans, newdir))
        return
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


def delete(panel):
    if len(panel.selections):
        delete_all = 0
        for f in panel.selections:
            if f == os.pardir:
                continue
            buf = 'Delete \'%s\'' % f
            if app.prefs.confirmations['delete'] and not delete_all:
                ans2 = messages.confirm_all('Delete', buf, 1)
                if ans2 == -1:
                    break
                elif ans2 == 2:
                    delete_all = 1
                if ans2 != 0:
                    ans = run_thread(app, 'Deleting \'%s\'' % f,
                                     files.delete, panel.path, f)
                else:
                    continue
            else:
                ans = run_thread(app, 'Deleting \'%s\'' % f,
                                 files.delete, panel.path, f)
            if ans and ans != -100:
                for p in app.panels:
                    p.show()
                messages.error('Delete \'%s\'' % f, '%s (%s)' % ans)
            else:
                continue
        file_i_old = panel.file_i
        file_old = panel.sorted[panel.file_i]
        pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
        panel.init_dir(panel.path)
        panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
        try:
            panel.file_i = panel.sorted.index(file_old)
        except ValueError:
            panel.file_i = file_i_old
    else:
        filename = panel.sorted[panel.file_i]
        if filename == os.pardir:
            return
        if app.prefs.confirmations['delete']:
            ans2 = messages.confirm('Delete', 'Delete \'%s\'' %
                                    filename, 1)
            if ans2 != 0 and ans2 != -1:
                ans = run_thread(app, 'Deleting \'%s\'' % filename,
                                 files.delete, panel.path, filename)
            else:
                return
        else:
            ans = run_thread(app, 'Deleting \'%s\'' % filename,
                             files.delete, panel.path, filename)
        if ans and ans != -100:
            for p in app.panels:
                p.show()
            messages.error('Delete \'%s\'' % filename, '%s (%s)' % ans)
        file_i_old = panel.file_i
        pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
        panel.init_dir(panel.path)
        panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
        if file_i_old > panel.nfiles:
            panel.file_i = panel.nfiles
        else:
            panel.file_i = file_i_old
    panel.fix_limits()
    panel.refresh_panel(app.get_otherpanel())

# menu
def show_help(panel):
    menu = [ 'r    Readme',
             'v    Readme pyview',
             'n    News',
             't    Todo',
             'c    ChangeLog',
             'l    License' ]
    cmd = messages.MenuWin('Help Menu', menu).run()
    if cmd == -1:
        return
    cmd = cmd[0]
    curses.endwin()
    docdir = os.path.join(sys.exec_prefix, 'share/doc/lfm')
    if cmd == 'r':
        fullfilename = os.path.join(docdir, 'README')
    elif cmd == 'v':
        fullfilename = os.path.join(docdir, 'README.pyview')
    elif cmd == 'n':
        fullfilename = os.path.join(docdir, 'NEWS')
    elif cmd == 't':
        fullfilename = os.path.join(docdir, 'TODO')
    elif cmd == 'c':
        fullfilename = os.path.join(docdir, 'ChangeLog')
    elif cmd == 'l':
        fullfilename = os.path.join(docdir, 'COPYING')
    os.system('%s \"%s\"' % (app.prefs.progs['pager'], fullfilename))
    curses.curs_set(0)


def file_menu(panel):
    menu = [ '@    Do something on file(s)',
             'i    File info',
             'p    Change file permissions, owner, group',
             'g    Gzip/gunzip file(s)',
             'b    Bzip2/bunzip2 file(s)',
             'x    Uncompress .tar.gz, .tar.bz2, .tar.Z, .zip',
             'u    Uncompress .tar.gz, etc in other panel',
             'c    Compress directory to .tar.gz',
             'd    Compress directory to .tar.bz2',
             'z    Compress directory to .zip' ]
    cmd = messages.MenuWin('File Menu', menu).run()
    if cmd == -1:
        return
    cmd = cmd[0]
    if cmd == '@':
        app.show()
        do_something_on_file(panel)
    elif cmd == 'i':
        do_show_file_info(panel)
    elif cmd == 'p':
        if panel.selections:
            app.show()
            i = 0
            change_all = 0
            for file in panel.selections:
                i += 1
                if not change_all:
                    ret = messages.ChangePerms(file, panel.files[file],
                                               app, i,
                                               len(panel.selections)).run()
                    if ret == -1:
                        break
                    elif ret == 0:
                        continue
                    elif ret[3] == 1:
                        change_all = 1                            
                filename = os.path.join(panel.path, file)
                ans = files.set_perms(filename, ret[0])
                if ans:
                    app.show()
                    messages.error('Chmod', '%s (%s)' % (ans, filename))
                ans = files.set_owner_group(filename, ret[1], ret[2])
                if ans:
                    app.show()
                    messages.error('Chown', '%s (%s)' % (ans, filename))
            panel.selections = []
        else:
            file = panel.sorted[panel.file_i]
            if file == os.pardir:
                return
            app.show()
            ret = messages.ChangePerms(file, panel.files[file],
                                       app).run()
            if ret == -1:
                return
            filename = os.path.join(panel.path, file)
            ans = files.set_perms(filename, ret[0])
            if ans:
                app.show()
                messages.error('Chmod', '%s (%s)' % (ans, filename))
            ans = files.set_owner_group(filename, ret[1], ret[2])
            if ans:
                app.show()
                messages.error('Chown', '%s (%s)' % (ans, filename))
        panel.refresh_panel(panel)
        panel.refresh_panel(app.get_otherpanel())
    elif cmd == 'g':
        compress_uncompress_file(app, panel, 'gzip')
        old_file = panel.sorted[panel.file_i]
        panel.refresh_panel(panel)
        panel.file_i = panel.sorted.index(old_file)
        old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
        panel.refresh_panel(app.get_otherpanel())
        app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)
    elif cmd == 'b':
        compress_uncompress_file(app, panel, 'bzip2')
        old_file = panel.sorted[panel.file_i]
        panel.refresh_panel(panel)
        panel.file_i = panel.sorted.index(old_file)
        old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
        panel.refresh_panel(app.get_otherpanel())
        app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)
    elif cmd == 'x':
        uncompress_dir(app, panel, panel.path)
        old_file = panel.sorted[panel.file_i]
        panel.refresh_panel(panel)
        panel.file_i = panel.sorted.index(old_file)
        old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
        panel.refresh_panel(app.get_otherpanel())
        app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)
    elif cmd == 'u':
        otherpath = app.get_otherpanel().path
        uncompress_dir(app, panel, otherpath)
        old_file = panel.sorted[panel.file_i]
        panel.refresh_panel(panel)
        panel.file_i = panel.sorted.index(old_file)
        old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
        panel.refresh_panel(app.get_otherpanel())
        app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)
    elif cmd == 'c':
        compress_dir(app, panel, 'gzip')
        old_file = panel.sorted[panel.file_i]
        panel.refresh_panel(panel)
        panel.file_i = panel.sorted.index(old_file)
        old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
        panel.refresh_panel(app.get_otherpanel())
        app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)
    elif cmd == 'd':
        compress_dir(app, panel, 'bzip2')
        old_file = panel.sorted[panel.file_i]
        panel.refresh_panel(panel)
        panel.file_i = panel.sorted.index(old_file)
        old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
        panel.refresh_panel(app.get_otherpanel())
        app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)
    elif cmd == 'z':
        compress_dir(app, panel, 'zip')
        old_file = panel.sorted[panel.file_i]
        panel.refresh_panel(panel)
        panel.file_i = panel.sorted.index(old_file)
        old_file = app.get_otherpanel().sorted[app.get_otherpanel().file_i]
        panel.refresh_panel(app.get_otherpanel())
        app.get_otherpanel().file_i = app.get_otherpanel().sorted.index(old_file)


def general_menu(panel):
    menu = [ '/    Find/grep file(s)',
             '#    Show directories size',
             's    Sort files',
             't    Tree',
             'f    Show filesystems info',
             'o    Open shell',
             'c    Edit configuration',
             'a    Save configuration' ]
    cmd = messages.MenuWin('General Menu', menu).run()
    if cmd == -1:
        return
    cmd = cmd[0]
    if cmd == '/':
        app.show()
        findgrep(panel)
    elif cmd == '#':
        show_dirs_size(panel)
    elif cmd == 's':
        app.show()
        sort(panel)
    elif cmd == 't':
        if panel.vfs:
            return
        panel_i = app.panel
        app.panel = not panel_i
        panel.show()
        t = Tree(panel.path, panel.pos)
        ans = t.run()
        del(t)
        app.panel = panel_i
        if ans != -1:
            panel.init_dir(ans)
            panel.fix_limits()
    elif cmd == 'f':
        do_show_fs_info()
    elif cmd == 'o':
        curses.endwin()
        os.system('cd \"%s\"; %s' % (panel.path,
                                     app.prefs.progs['shell']))
        curses.curs_set(0)
        panel.refresh_panel(panel)
        panel.refresh_panel(app.get_otherpanel())
    elif cmd == 'c':
        app.prefs.edit(app)
        app.prefs.load()
    elif cmd == 'a':
        app.prefs.save()



# window resize
def resize_window(panel):
    app.resize()
    

# exit
def quit(panel):
    if app.prefs.confirmations['quit']:
        ans = messages.confirm('Last File Manager',
                               'Quit Last File Manager', 1)
        if ans == 1:
            return -1
    else:
        return -1

def exit(panel):  
    if app.prefs.confirmations['quit']:
        ans = messages.confirm('Last File Manager',
                               'Quit Last File Manager', 1)
        if ans == 1:
            return -2
    else:
        return -2


##################################################
##### Utils
##################################################
# bookmarks
def goto_bookmark(panel, num):
    todir = app.prefs.bookmarks[num]
    if panel.vfs:
        vfs.exit(app, panel)
    panel.init_dir(todir)
    panel.fix_limits()


# show size
def show_dirs_size(panel):
    if panel.selections:
        for f in panel.selections:
            if panel.files[f][files.FT_TYPE] != files.FTYPE_DIR and \
               panel.files[f][files.FT_TYPE] != files.FTYPE_LNK2DIR:
                continue
            file = os.path.join(panel.path, f)
            res = run_thread(app, 'Showing Directories Size',
                             files.get_fileinfo, file, 0, 1)
            if res == -100:
                break
            panel.files[f] = res
                                               
    else:
        for f in panel.files.keys():
            if f == os.pardir:
                continue
            if panel.files[f][files.FT_TYPE] != files.FTYPE_DIR and \
               panel.files[f][files.FT_TYPE] != files.FTYPE_LNK2DIR:
                continue
            file = os.path.join(panel.path, f)
            res = run_thread(app, 'Showing Directories Size',
                             files.get_fileinfo, file, 0, 1)
            if res == -100:
                break
            panel.files[f] = res


# sort
def sort(panel):
    while 1:
        ch = messages.get_a_key('Sorting mode',
                                'N(o), by (n)ame, by (s)ize, by (d)ate,\nuppercase if reversed order, Ctrl-C to quit')
        if ch in [ord('o'), ord('O')]:
            app.modes['sort'] = files.SORTTYPE_None
            break
        elif ch in [ord('n')]:
            app.modes['sort'] =  files.SORTTYPE_byName
            break
        elif ch in [ord('N')]:
            app.modes['sort'] =  files.SORTTYPE_byName_rev
            break
        elif ch in [ord('s')]:
            app.modes['sort'] = files.SORTTYPE_bySize
            break
        elif ch in [ord('S')]:
            app.modes['sort'] = files.SORTTYPE_bySize_rev
            break
        elif ch in [ord('d')]:
            app.modes['sort'] = files.SORTTYPE_byDate
            break
        elif ch in [ord('D')]:
            app.modes['sort'] = files.SORTTYPE_byDate_rev
            break
        elif ch == -1:                 # Ctrl-C
            break
    old_filename = panel.sorted[panel.file_i]
    old_selections = panel.selections[:]
    panel.init_dir(panel.path)
    panel.file_i = panel.sorted.index(old_filename)
    panel.selections = old_selections
    panel.fix_limits()

# do special view file
def do_special_view_file(panel):
    fullfilename = os.path.join(panel.path, panel.sorted[panel.file_i])
    ext = os.path.splitext(fullfilename)[1].lower()[1:]
    for typ, exts in app.prefs.filetypes.items():
        if ext in exts:
            prog = app.prefs.progs[typ]
            if prog == '':
                messages.error('Can\'t run program',
                               'Can\'t start %s files, defaulting to view' % typ)
                do_view_file(panel)
                break
            sys.stdout = sys.stderr = '/dev/null'
            curses.endwin()
            if app.prefs.options['detach_terminal_at_exec']:
                pid = os.fork()
                if pid == 0:
                    os.setsid()
                    sys.stdout = sys.stderr = '/dev/null'
                    args = [prog]
                    args.append(fullfilename)
                    pid2 = os.fork()
                    if pid2 == 0:
                        os.chdir('/')
                        # FIXME: catch errors
                        try:
                            os.execvp(args[0], args)
                        except OSError:
                            os._exit(-1)
                    else:
                        os._exit(0)
                else:
                    curses.curs_set(0)
                    sys.stdout = sys.__stdout__
                    sys.stderr = sys.__stderr__
                    break
            else:
                # programs inside same terminal as lfm should use:
                os.system('%s \"%s\"' % (prog, fullfilename))
                curses.curs_set(0)
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                break
    else:
        do_view_file(panel)
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


# do view file
def do_view_file(panel):
    fullfilename = os.path.join(panel.path, panel.sorted[panel.file_i])
    curses.endwin()
    os.system('%s \"%s\"' % (app.prefs.progs['pager'], fullfilename))
    curses.curs_set(0)


# do edit file
def do_edit_file(panel):
    curses.endwin()
    fullfilename = os.path.join(panel.path, panel.sorted[panel.file_i])
    os.system('%s \"%s\"' % (app.prefs.progs['editor'], fullfilename))
    curses.curs_set(0)
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


# do execute file
def do_do_execute_file(path, cmd):
    i, a = os.popen4('cd \"%s\"; \"%s\"; echo ZZENDZZ' % (path, cmd))
    output = ''
    while 1:
        buf = a.readline()[:-1]
        if buf == 'ZZENDZZ':
            break
        elif buf:
            output += buf + '\n'
    i.close(); a.close()
    return output


def do_execute_file(panel):
    fullfilename = os.path.join(panel.path, panel.sorted[panel.file_i])
    parms = doEntry('Execute file', 'Enter arguments')
    if parms == None:
        return
    elif parms == '':
        cmd = '%s' % fullfilename
    else:                
        cmd = '%s %s' % (fullfilename, parms)
    curses.endwin()
    err = run_thread(app, 'Executing \"%s\"' % cmd,
                     do_do_execute_file, panel.path, cmd)
    if err and err != -100:
        if app.prefs.options['show_output_after_exec']:
            curses.curs_set(0)
            for panel in app.panels:
                panel.show()
            if messages.confirm('Executing file(s)', 'Show output'):
                lst = [(l, 2) for l in err.split('\n')]
                pyview.InternalView('Output of \"%s\"' % cmd,
                                    lst, center = 0).run()
    curses.curs_set(0)
    panel.refresh_panel(panel)
    panel.refresh_panel(app.get_otherpanel())


# do something on file
### do_something_on_file does not have to run inside run_thread, either capture
### the output because it makes not possible to exec commands such as 'less', etc.
# def do_do_something_on_file(panel, cmd, filename):
#     i, a = os.popen4('cd \"%s\"; %s \"%s\"; echo ZZENDZZ' %
#                      (panel.path, cmd, filename))
#     output = ''
#     while 1:
#         buf = a.readline()[:-1]
#         if buf == 'ZZENDZZ':
#             break
#         elif buf:
#             output += buf + '\n'
#     i.close(); a.close()
#     return output


# def do_something_on_file(panel):
#     cmd = doEntry('Do something on file(s)', 'Enter command')
#     if cmd:
#         curses.endwin()
#         if len(panel.selections):
#             for f in panel.selections:
#                 err = run_thread('Executing \"%s %s\"' % (cmd, f),
#                                  do_do_something_on_file, panel, cmd, f)
#                 if err and err != -100:
#                     if app.prefs.options['show_output_after_exec']:
#                         curses.curs_set(0)
#                         for panel in app.panels:
#                             panel.show()
#                         if messages.confirm('Do something on file(s)',
#                                             'Show output'):
#                             lst = [(l, 2) for l in err.split('\n')]
#                             pyview.InternalView('Output of \"%s %s\"' %
#                                                 (cmd, f),
#                                                 lst, center = 0).run()
#             panel.selections = []
#         else:
#             filename = panel.sorted[panel.file_i]
#             err = run_thread('Executing \"%s %s\"' % (cmd, filename),
#                              do_do_something_on_file, panel, cmd, filename)
#             if err and err != -100:
#                 if app.prefs.options['show_output_after_exec']:
#                     curses.curs_set(0)
#                     for panel in app.panels:
#                         panel.show()
#                     if messages.confirm('Do something on file(s)', 'Show output'):
#                         lst = [(l, 2) for l in err.split('\n')]
#                         pyview.InternalView('Output of \"%s %s\"' %
#                                             (cmd, filename),
#                                             lst, center = 0).run()
#         curses.curs_set(0)
#         panel.refresh_panel(panel)
#         panel.refresh_panel(app.get_otherpanel())

def do_something_on_file(panel):
    cmd = doEntry('Do something on file(s)', 'Enter command')
    if cmd:
        curses.endwin()
        if len(panel.selections):
            for f in panel.selections:
                os.system('cd \"%s\"; %s \"%s\"' % (panel.path, cmd, f))
            panel.selections = []
        else:
            os.system('cd \"%s\"; %s \"%s\"' %
                      (panel.path, cmd, panel.sorted[panel.file_i]))
        curses.curs_set(0)
        panel.refresh_panel(panel)
        panel.refresh_panel(app.get_otherpanel())


# show file info
def do_show_file_info(panel):
    def show_info(panel, file):
        import stat
        from time import ctime

        fullfilename = os.path.join(panel.path, file)
        file_data = panel.files[file]
        file_data2 = os.lstat(fullfilename)
        buf = []
        user = os.environ['USER']
        username = files.get_user_fullname(user)
        so, host, ver, tmp, arch = os.uname()
        buf.append(('%s v%s executed by %s' % (LFM_NAME, VERSION, username), 5))
        buf.append(('<%s@%s> on a %s %s [%s]' % (user, host, so, ver, arch), 5))
        buf.append(('', 2))
        fileinfo = os.popen('file \"%s\"' % \
                            fullfilename).read().split(':')[1].strip()
        buf.append(('%s: %s (%s)' % (files.FILETYPES[file_data[0]][1], file,
                                     fileinfo), 6))
        if not panel.vfs:
            path = panel.path
        else:
            path = vfs.join(app, panel) + ' [%s]' % panel.base
        buf.append(('Path: %s' % path[-(curses.COLS-8):], 6))
        buf.append(('Size: %s bytes' % file_data[files.FT_SIZE], 6))
        buf.append(('Mode: %s (%4.4o)' % \
                    (files.perms2str(file_data[files.FT_PERMS]),
                     file_data[files.FT_PERMS]), 6))
        buf.append(('Links: %s' % file_data2[stat.ST_NLINK], 6))
        buf.append(('User ID: %s (%s) / Group ID: %s (%s)' % \
                    (file_data[files.FT_OWNER], file_data2[stat.ST_UID],
                     file_data[files.FT_GROUP], file_data2[stat.ST_GID]), 6))
        buf.append(('Last access: %s' % ctime(file_data2[stat.ST_ATIME]), 6))
        buf.append(('Last modification: %s' % ctime(file_data2[stat.ST_MTIME]), 6))
        buf.append(('Last change: %s' % ctime(file_data2[stat.ST_CTIME]), 6))
        buf.append(('Location: %d, %d / Inode: #%X (%Xh:%Xh)' % \
                    ((file_data2[stat.ST_DEV] >> 8) & 0x00FF,
                    file_data2[stat.ST_DEV] & 0x00FF,
                    file_data2[stat.ST_INO], file_data2[stat.ST_DEV],
                    file_data2[stat.ST_INO]), 6))
        fss = files.get_fs_info()
        fs = ['/dev', '0', '0', '0', '0%', '/', 'unknown']
        for e in fss:
            if fullfilename.find(e[5]) != -1 and (len(e[5]) > len(fs[5]) or e[5] == os.sep):
                fs = e
        buf.append(('File system: %s on %s (%s) %d%% free' % \
                    (fs[0], fs[5], fs[6], 100 - int(fs[4][:-1])), 6))
        pyview.InternalView('Information about \'%s\'' % file, buf).run()

    if panel.selections:
        for f in panel.selections:
            show_info(panel, f)
        panel.selections = []
    else:
        show_info(panel, panel.sorted[panel.file_i])


# do show filesystems info
def do_show_fs_info():
    """Show file systems info"""

    fs = files.get_fs_info()
    if type(fs) != type([]):
        app.show()
        messages.error('Show filesystems info', fs)
        return
    app.show()
    buf = []
    buf.append(('Filesystem       FS type    Total Mb     Used   Avail.  Use%  Mount point', 6))
    buf.append('-')
    for l in fs:
        buf.append(('%-15s  %-10s  %7s  %7s  %7s  %4s  %s' % \
                    (l[0], l[6], l[1], l[2], l[3], l[4], l[5]), 2))
    texts = [l[0] for l in buf]
    buf[1] = ('-' * len(max(texts)), 6)
    pyview.InternalView('Show filesystems info', buf).run()


# find and grep
def findgrep(panel):
    fs, pat = doDoubleEntry('Find files', 'Filename', '*', 1, 1,
                            'Content', '', 1, 0)
    if fs == None or fs == '':
        return
    path = os.path.dirname(fs)
    fs = os.path.basename(fs)
    if path == None or path == '':
        path = panel.path
    if path[0] != os.sep:
        path = os.path.join(panel.path, path)
    if pat:
        m = run_thread(app, 'Searching for \'%s\' in \"%s\" files' % (pat, fs),
                       files.findgrep,
                       path, fs, pat, app.prefs.progs['find'],
                       app.prefs.progs['egrep'])
        if not m:
            app.show()
            messages.error('Find/Grep', 'No files found')
            return
        elif m == -100:
            return
        elif m == -1:
            app.show()
            messages.error('Find/Grep', 'Error while creating pipe')
            return
    else:
        m = run_thread(app, 'Searching for \"%s\" files' % fs, files.find,
                       path, fs, app.prefs.progs['find'])
        if not m:
            app.show()
            messages.error('Find', 'No files found')
            return
        elif m == -100:
            return
        elif m == -1:
            app.show()
            messages.error('Find', 'Error while creating pipe')
            return        
    find_quit = 0
    par = ''
    while not find_quit:
        cmd, par = messages.FindfilesWin(m, par).run()
        if par:
            if pat:
                try:
                    line = int(par.split(':')[0])
                except ValueError:
                    line = 0
                    f = os.path.join(path, par)
                else:
                    f = os.path.join(path, par[par.find(':')+1:])
            else:
                line = 0
                f = os.path.join(path, par)
            if os.path.isdir(f):
                todir = f
                tofile = None
            else:
                todir = os.path.dirname(f)
                tofile = os.path.basename(f)
        if cmd == 0:             # goto file
            pvfs, base, vbase = panel.vfs, panel.base, panel.vbase
            panel.init_dir(todir)
            panel.vfs, panel.base, panel.vbase = pvfs, base, vbase
            if tofile:
                panel.file_i = panel.sorted.index(tofile)
            panel.fix_limits()
            find_quit = 1
        elif cmd == 1:           # panelize
            fs = []
            for f in m:
                if pat:
                    f = f[f.find(':')+1:]
                try:
                    fs.index(f)
                except ValueError:
                    fs.append(f)
                else:
                    continue
            vfs.pan_init(app, panel, fs)
            find_quit = 1
        elif cmd == 2:           # view
            if tofile:
                curses.curs_set(0)
                curses.endwin()
                os.system('%s +%d \"%s\"' %
                          (app.prefs.progs['pager'], line, f))
                curses.curs_set(0)
            else:
                messages.error('View', 'it\'s a directory',
                               todir)
        elif cmd == 3:           # edit
            if tofile:
                curses.endwin()
                if line > 0:
                    os.system('%s +%d \"%s\"' %
                              (app.prefs.progs['editor'], line, f))
                else:
                    os.system('%s \"%s\"' %
                              (app.prefs.progs['editor'], f))
                curses.curs_set(0)
                panel.refresh_panel(panel)
                panel.refresh_panel(app.get_otherpanel())
            else:
                messages.error('Edit', 'it\'s a directory',
                               todir)
        elif cmd == 4:           # do something on file
            cmd2 = doEntry('Do something on file',
                           'Enter command')
            if cmd2:
                curses.endwin()
                os.system('%s \"%s\"' % (cmd2, f))
                curses.curs_set(0)
                panel.refresh_panel(panel)
                panel.refresh_panel(app.get_otherpanel())
        else:
            find_quit = 1






#
def doEntry(title, help, path = '', with_historic = 1, with_complete = 1):
    panelpath = app.panels[app.panel].path
    while 1:
        path = messages.Entry(title, help, path, with_historic, with_complete,
                              panelpath).run()
        if type(path) != type([]):
            return path
        else:
            app.show()
            path = path.pop()


def doDoubleEntry(title, help1, path1 = '', with_historic1 = 1, with_complete1 = 1,
                  help2 = '', path2 = '', with_historic2 = 1, with_complete2 = 1):
    active_entry = 0
    panelpath1 = app.panels[app.panel].path
    panelpath2 = app.panels[app.panel].path
    while 1:
        path = messages.DoubleEntry(title, help1, path1, with_historic1,
                                    with_complete1, panelpath1,
                                    help2, path2, with_historic2,
                                    with_complete2, panelpath2,
                                    active_entry).run()
        if type(path) != type([]):
            return path
        else:
            app.show()
            active_entry = path.pop()
            path2 = path.pop()
            path1 = path.pop()


##################################################
##### Tree
##################################################
class Tree:
    """Tree class"""

    def __init__(self, path = os.sep, panelpos = 0):
        if not os.path.exists(path):
            return None
        self.__init_curses(panelpos)
        if path[-1] == os.sep and path != os.sep:
            path = path[:-1]
        self.path = path
        self.tree = self.get_tree()
        self.pos = self.__get_curpos()


    def __get_dirs(self, path):
        """return a list of dirs in path"""
        
        ds = []
        try:
            for d in os.listdir(path):
                if os.path.isdir(os.path.join(path, d)):
                    ds.append(d)
        except OSError:
            pass
        ds.sort()
        return ds


    def __get_graph(self, path):
        """return 2 dicts with tree structure"""

        tree_n = {}
        tree_dir = {}
        expanded = None
        while path:
            if path == os.sep and tree_dir.has_key(os.sep):
                break
            tree_dir[path] = (self.__get_dirs(path), expanded)
            expanded = os.path.basename(path)
            path = os.path.dirname(path)
        dir_keys = tree_dir.keys()
        dir_keys.sort()
        n = 0
        for d in dir_keys:
            tree_n[n] = d
            n += 1
        return tree_n, tree_dir


    def __get_node(self, i, tn, td, base):
        """expand branch"""

        lst2 = []
        node = tn[i]
        dirs, expanded_node = td[node]
        if not expanded_node:
            return []
        for d in dirs:
            if d == expanded_node:
                lst2.append([d, i, os.path.join(base, d)])
                lst3 = self.__get_node(i+1, tn, td, os.path.join(base, d))
                if lst3 != None:
                    lst2.extend(lst3)
            else:
                lst2.append([d, i, os.path.join(base, d)])
        return lst2


    def get_tree(self):
        """return list with tree structure"""

        tn, td = self.__get_graph(self.path)
        tree = [[os.sep, -1, os.sep]]
        tree.extend(self.__get_node(0, tn, td, os.sep))
        return tree
        

    def __get_curpos(self):
        """get position of current dir"""
        
        for i in range(len(self.tree)):
            if self.path == self.tree[i][2]:
                return i
        else:
            return -1


    def regenerate_tree(self, newpos):
        """regenerate tree when changing to a new directory"""
        
        self.path = self.tree[newpos][2]
        self.tree = self.get_tree()
        self.pos = self.__get_curpos()


    def show_tree(self, a = 0, z = -1):
        """show an ascii representation of the tree. Not used in lfm"""
        
        if z > len(self.tree) or z == -1:
            z = len(self.tree)
        for i in range(a, z):
            name, depth, fullname = self.tree[i]
            if fullname == self.path:
                name += ' <====='
            if name == os.sep:
                print ' ' + name
            else:
                print ' | ' * depth + ' +- ' + name


    # GUI functions
    def __init_curses(self, pos):
        """initialize curses stuff"""
        
        if pos == 0:      # not visible panel
            self.dims = (curses.LINES-2, 0, 0, 0)     # h, w, y, x
            return
        elif pos == 1:    # left panel -> right
            self.dims = (curses.LINES-2, int(curses.COLS/2), 1, int(curses.COLS/2))
        elif pos == 2:    # right panel -> left
            self.dims = (curses.LINES-2, int(curses.COLS/2), 1, 0)
        else:             # full panel -> right
            self.dims = (curses.LINES-2, int(curses.COLS/2), 1, int(curses.COLS/2))
        try:
            self.win_tree = curses.newwin(self.dims[0], self.dims[1], self.dims[2], self.dims[3])
        except curses.error:
            print 'Can\'t create tree window'
            sys.exit(-1)
        self.win_tree.keypad(1)
        if curses.has_colors():
            self.win_tree.attrset(curses.color_pair(2))
            self.win_tree.bkgdset(curses.color_pair(2))

        
    def show(self):
        """show tree panel"""
        
        self.win_tree.erase()
        h = curses.LINES - 4
        n = len(self.tree)
        # box
        self.win_tree.attrset(curses.color_pair(5))
        self.win_tree.box()
        self.win_tree.addstr(0, 2, ' Tree ', curses.color_pair(6) | curses.A_BOLD)
        # tree
        self.win_tree.attrset(curses.color_pair(2))
        j = 0
        a, z = int(self.pos/h) * h, (int(self.pos/h) + 1) * h
        if z > n:
            z = n
            a = z - h
            if a < 0:
                a = 0
        for i in range(a, z):
            j += 1
            name, depth, fullname = self.tree[i]
            if name == os.sep:
                self.win_tree.addstr(j, 1, ' ')
            else:
                self.win_tree.move(j, 1)
                for kk in range(depth):
                    self.win_tree.addstr(' ')
                    self.win_tree.addch(curses.ACS_VLINE)
                    self.win_tree.addstr(' ')
                self.win_tree.addstr(' ')
                if i == n - 1:
                    self.win_tree.addch(curses.ACS_LLCORNER)
                elif depth > self.tree[i+1][1]:
                    self.win_tree.addch(curses.ACS_LLCORNER)
                else:
                    self.win_tree.addch(curses.ACS_LTEE)
                self.win_tree.addch(curses.ACS_HLINE)
                self.win_tree.addstr(' ')
            w = int(curses.COLS / 2) - 2
            wd = 3 * depth + 4
            if fullname == self.path:
                self.win_tree.addstr(name[:w-wd-3], curses.color_pair(3))
                child_dirs = self.__get_dirs(self.path)
                if len(child_dirs) > 0:
                    self.win_tree.addstr(' ')
                    self.win_tree.addch(curses.ACS_HLINE)
                    self.win_tree.addch(curses.ACS_RARROW)
            else:
                self.win_tree.addstr(name[:w-wd])
        # scrollbar
        if n > h:
            nn = int(h * h / n)
            if nn == 0:
                nn = 1
            aa = int(self.pos / h) * h
            y0 = int(aa * h / n)
            if y0 < 0:
                y0 = 0
            elif y0 + nn > h:
                y0 = h - nn - 1
        else:
            y0 = 0
            nn = 0
        self.win_tree.attrset(curses.color_pair(5))
        self.win_tree.vline(y0 + 2, int(curses.COLS/2) - 1, curses.ACS_CKBOARD, nn)
        if a != 0:
            self.win_tree.vline(1, int(curses.COLS/2) - 1, '^', 1)
            if nn == 1 and (y0 + 2 == 2):
                self.win_tree.vline(3, int(curses.COLS/2) - 1, curses.ACS_CKBOARD, nn)
        if n - 1 > a + h - 1:
            self.win_tree.vline(h, int(curses.COLS/2) - 1, 'v', 1)
            if nn == 1 and (y0 + 2 == h + 1):
                self.win_tree.vline(h, int(curses.COLS/2) - 1, curses.ACS_CKBOARD, nn)
        # status
        app.win_status.erase()
        wp = curses.COLS - 8
        if len(self.path) > wp:
            path = self.path[:int(wp/2) -1] + '~' + self.path[-int(wp/2):]
        else:
            path = self.path
        app.win_status.addstr(' Path: %s' % path)
        app.win_status.refresh()


    def run(self):
        """manage keys"""
        
        while 1:
            self.show()
            chext = 0
            ch = self.win_tree.getch()

            # to avoid extra chars input
            if ch == 0x1B:
                chext = 1
                ch = self.win_tree.getch()
                ch = self.win_tree.getch()

            # cursor up
            if ch in [ord('p'), ord('P'), curses.KEY_UP]:
                if self.pos == 0:
                    continue
                if self.tree[self.pos][1] != self.tree[self.pos-1][1]:
                    continue
                newpos = self.pos - 1
            # cursor down
            elif ch in [ord('n'), ord('N'), curses.KEY_DOWN]:
                if self.pos == len(self.tree) - 1:
                    continue
                if self.tree[self.pos][1] != self.tree[self.pos+1][1]:
                    continue
                newpos = self.pos + 1
            # page previous
            elif ch in [curses.KEY_PPAGE, curses.KEY_BACKSPACE,
                        0x08, 0x10]:                         # BackSpace, Ctrl-P
                depth = self.tree[self.pos][1] 
                if self.pos - (curses.LINES-4) >= 0:
                    if depth  == self.tree[self.pos - (curses.LINES-4)][1]:
                        newpos = self.pos - (curses.LINES-4)
                    else:
                        newpos = self.pos
                        while 1:
                            if newpos - 1 < 0:
                                break
                            if self.tree[newpos-1][1] != depth:
                                break
                            newpos -= 1
                else:
                    newpos = self.pos
                    while 1:
                        if newpos - 1 < 0:
                            break
                        if self.tree[newpos-1][1] != depth:
                            break
                        newpos -= 1
            # page next
            elif ch in [curses.KEY_NPAGE, ord(' '), 0x0E]:   # Ctrl-N
                depth = self.tree[self.pos][1] 
                if self.pos + (curses.LINES-4) <= len(self.tree) - 1:
                    if depth  == self.tree[self.pos + (curses.LINES-4)][1]:
                        newpos = self.pos + (curses.LINES-4)
                    else:
                        newpos = self.pos
                        while 1:
                            if newpos + 1 == len(self.tree):
                                break
                            if self.tree[newpos+1][1] != depth:
                                break
                            newpos += 1
                else:
                    newpos = self.pos
                    while 1:
                        if newpos + 1 == len(self.tree):
                            break
                        if self.tree[newpos+1][1] != depth:
                            break
                        newpos += 1
            # home
            elif (ch in [curses.KEY_HOME, 0x001,0x16A ]) or \
                 (chext == 1) and (ch == 72):  # home
                newpos = 1
            # end
            elif (ch in [curses.KEY_END, 0x005, 0x181]) or \
                 (chext == 1) and (ch == 70):   # end
                newpos = len(self.tree) - 1
            # cursor left
            elif ch in [curses.KEY_LEFT]:
                if self.pos == 0:
                    continue
                newdepth = self.tree[self.pos][1] - 1
                for i in range(self.pos-1, -1, -1):
                    if self.tree[i][1] == newdepth:
                        break
                newpos = i
            # cursor right
            elif ch in [curses.KEY_RIGHT]:
                child_dirs = self.__get_dirs(self.path)
                if len(child_dirs) > 0:
                    self.path = os.path.join(self.path, child_dirs[0])
                    self.tree = self.get_tree()
                    self.pos = self.__get_curpos()
                continue                   
            # enter
            elif ch in [10, 13]:
                return self.path
            # quit
            elif ch in [ord('q'), ord('Q'), curses.KEY_F10, 0x03]:  # Ctrl-C
                return -1

            # else
            else:
                continue
            
            # update
            self.regenerate_tree(newpos)
