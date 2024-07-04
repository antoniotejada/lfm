# -*- coding: utf-8 -*-

"""actions.py

This module contains the actions to execute when keys are pressed.
"""


import os, os.path
import sys
import time
from glob import glob
import curses

from __init__ import *
import files
from utils import *
import compress
import vfs
import messages
import pyview


######################################################################
##### module variables
app = None


######################################################################
##### keys <-> actions table
keytable = {
    # movement
    ord('k'): 'cursor_up',
    ord('K'): 'cursor_up',
    curses.KEY_UP: 'cursor_up',
    ord('j'): 'cursor_down',
    ord('J'): 'cursor_down',
    curses.KEY_DOWN: 'cursor_down',
    curses.KEY_PPAGE: 'page_previous',
    curses.KEY_BACKSPACE: 'page_previous',
    0x08: 'page_previous',     # BackSpace
    0x02: 'page_previous',     # Ctrl-B
    curses.KEY_NPAGE: 'page_next',
    ord(' '): 'page_next',
    0x06: 'page_next',         # Ctrl-F
    curses.KEY_HOME: 'home',
    0x01: 'home',              # Ctrl-A
    curses.KEY_END: 'end',
    0x05: 'end',               # Ctrl-E

    # change dir
    curses.KEY_LEFT: 'cursor_left',
    curses.KEY_RIGHT: 'cursor_right',
    10: 'enter',
    13: 'enter',
    ord('g'): 'goto_dir',
    ord('G'): 'goto_dir',
    0x13: 'goto_file',         # Ctrl-S
    0x14: 'tree',              # Ctrl-T
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
    0x04: 'select_bookmark',   # Ctrl-D
    0x1C: 'select_bookmark',   # Ctrl-\
    ord('b'): 'set_bookmark',
    ord('B'): 'set_bookmark',

    # panels
    ord('\t'): 'toggle_active_pane',  # tab
    ord('.'): 'toggle_panes',
    ord(','): 'swap_panes',
    0x15: 'swap_panes',        # Ctrl-U
    ord('='): 'same_tabs',
    ord(':'): 'new_tab',
    ord('!'): 'close_tab',
    ord('<'): 'left_tab',
    ord('>'): 'right_tab',

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
    ord('@'): 'action_on_file',
    0xF1: 'special_regards',    # special regards
    ord('/'): 'find_grep',
    ord('t'): 'touch_file',
    ord('T'): 'touch_file',
    ord('l'): 'create_link',
    ord('L'): 'create_link',
    0x0C: 'edit_link',          # Ctrl-L
    0x0F: 'open_shell',         # Ctrl-O

    # main functions
    curses.KEY_F3: 'view_file',
    curses.KEY_F4: 'edit_file',
    curses.KEY_F5: 'copy',
    curses.KEY_F6: 'move',
    curses.KEY_F12: 'rename',
    curses.KEY_F7: 'make_dir',
    curses.KEY_DC: 'delete',
    curses.KEY_F8: 'delete',

    # menu
    ord('h'): 'show_help',
    ord('H'): 'show_help',
    curses.KEY_F1: 'show_help',
    curses.KEY_F2: 'file_menu',
    curses.KEY_F9: 'general_menu',

    # terminal resize:
    curses.KEY_RESIZE: 'resize_window',
    0x12: 'refresh_screen',          # Ctrl-R

    # quit & exit
    ord('q'): 'quit',
    ord('Q'): 'quit',
    curses.KEY_F10: 'quit',
    0x11: 'exit'                     # Ctrl-Q
}


def do(tab, ch):
    try:
        act = 'ret = %s(tab)'  % keytable[ch]
    except KeyError:
        curses.beep()
    else:
        exec(act)
        return ret


######################################################################
##### action functions

# movement
def cursor_up(tab):
    tab.file_i -= 1
    tab.fix_limits()

def cursor_down(tab):
    tab.file_i += 1
    tab.fix_limits()

def page_previous(tab):
    tab.file_i -= tab.pane.dims[0]
    if tab.pane.mode in (PANE_MODE_LEFT, PANE_MODE_RIGHT):
        tab.file_i += 3
    tab.fix_limits()

def page_next(tab):
    tab.file_i += tab.pane.dims[0]
    if tab.pane.mode in (PANE_MODE_LEFT, PANE_MODE_RIGHT):
        tab.file_i -= 3
    tab.fix_limits()

def home(tab):
    tab.file_i = 0
    tab.fix_limits()

def end(tab):
    tab.file_i = tab.nfiles - 1
    tab.fix_limits()


# change dir
def cursor_left(tab):
    tab.exit_dir()

def cursor_right(tab):
    enter(tab)

def enter(tab):
    filename = tab.get_file()
    vfstype = compress.check_compressed_file_type(filename)
    typ = tab.files[filename][files.FT_TYPE]
    if vfstype in ('bz2', 'gz'):
        vfstype = None
    if typ == files.FTYPE_DIR:
        tab.enter_dir(filename)
    elif typ == files.FTYPE_LNK2DIR:
        tab.init(files.get_linkpath(tab.path, filename))
    elif typ in (files.FTYPE_REG, files.FTYPE_LNK) and vfstype != None:
        vfs.init(tab, filename, vfstype)
    elif typ == files.FTYPE_EXE:
        do_execute_file(tab)
    elif typ == files.FTYPE_REG:
        do_special_view_file(tab)
    else:
        return

def goto_dir(tab):
    todir = doEntry(tab.path, 'Go to directory', 'Type directory name')
    app.display()
    if todir == None or todir == "":
        return
    todir = os.path.join(tab.path, todir)
    if tab.vfs:
        vfs.exit(tab)
    tab.init(todir)

def goto_file(tab):
    tofile = doEntry(tab.path, 'Go to file', 'Type how file name begins')
    app.display()
    if tofile == None or tofile == "":
        return
    thefiles = tab.sorted[tab.file_i:]
    for f in thefiles:
        if f.find(tofile) == 0:
            break
    else:
        return
    tab.file_i = tab.sorted.index(f)
    tab.fix_limits()

def tree(tab):
    if tab.vfs:
        return
    app.act_pane, app.noact_pane = app.act_pane, app.noact_pane
    tab.pane.display()
    t = Tree(tab.path, tab.pane.mode)
    ans = t.run()
    del(t)
    app.act_pane, app.noact_pane = app.act_pane, app.noact_pane
    if ans != -1:
        tab.init(ans)

def bookmark_0(tab):
    goto_bookmark(tab, 0)

def bookmark_1(tab):
    goto_bookmark(tab, 1)

def bookmark_2(tab):
    goto_bookmark(tab, 2)

def bookmark_3(tab):
    goto_bookmark(tab, 3)

def bookmark_4(tab):
    goto_bookmark(tab, 4)

def bookmark_5(tab):
    goto_bookmark(tab, 5)

def bookmark_6(tab):
    goto_bookmark(tab, 6)

def bookmark_7(tab):
    goto_bookmark(tab, 7)

def bookmark_8(tab):
    goto_bookmark(tab, 8)

def bookmark_9(tab):
    goto_bookmark(tab, 9)

def select_bookmark(tab):
    ret = messages.MenuWin('Select Bookmark', app.prefs.bookmarks).run()
    if ret == -1:
        return
    if tab.vfs:
        vfs.exit(tab)
    tab.init(ret)

def set_bookmark(tab):
    if tab.vfs:
        messages.error('Set bookmark', 'Can\'t bookmark inside vfs')
        return
    while True:
        ch = messages.get_a_key('Set bookmark',
                                'Press 0-9 to save the bookmark, Ctrl-C to quit')
        if 0x30 <= ch <= 0x39:         # 0..9
            app.prefs.bookmarks[ch-0x30] = tab.path[:]
            break
        elif ch == -1:                 # Ctrl-C
            break


# panes and tabs
def toggle_active_pane(tab):
    if tab.pane.mode in (PANE_MODE_FULL, PANE_MODE_HIDDEN):
        return
    return TOGGLE_PANE

def toggle_panes(tab):
    if tab.pane.mode == PANE_MODE_FULL:
        # now => 2-panes mode
        app.lpane.mode, app.rpane.mode = PANE_MODE_LEFT, PANE_MODE_RIGHT
    else:
        # now => 1-pane mode
        app.act_pane.mode, app.noact_pane.mode = PANE_MODE_FULL, PANE_MODE_HIDDEN
    app.lpane.init_ui()
    app.rpane.init_ui()
    for tab in app.lpane.tabs + app.rpane.tabs:
        tab.fix_limits()

def swap_panes(tab):
    if tab.pane.mode == PANE_MODE_FULL:
        return
    app.lpane.mode, app.rpane.mode = app.rpane.mode, app.lpane.mode
    app.lpane.init_ui()
    app.rpane.init_ui()

def same_tabs(tab):
    othertab = app.noact_pane.act_tab
    if not tab.vfs:
        if othertab.vfs:
            vfs.exit(othertab)
        othertab.init(tab.path)
    else:
        if tab.vfs == 'pan':
            vfs.pan_copy(tab, othertab)
        else:
            vfs.copy(tab, othertab)
        pvfs, base, vbase = othertab.vfs, othertab.base, othertab.vbase
        othertab.init(base + tab.path.replace(tab.base, ''))
        othertab.vfs, othertab.base, othertab.vbase = pvfs, base, vbase

def new_tab(tab):
    if len(tab.pane.tabs) >= 4:
        messages.error('New tab', 'Can\'t create more tabs')
        return
    else:
        return TAB_NEW

def close_tab(tab):
    if len(tab.pane.tabs) == 1:
        messages.error('Close tab', 'Can\'t close last tab')
        return
    else:
        if tab.vfs:
            vfs.exit(tab)
        return TAB_CLOSE

def left_tab(tab):
    tabs = tab.pane.tabs
    idx = tabs.index(tab)
    if idx > 0:
        tab.pane.act_tab = tabs[idx-1]

def right_tab(tab):
    tabs = tab.pane.tabs
    idx = tabs.index(tab)
    if idx < len(tabs) - 1: # and idx < 3
        tab.pane.act_tab = tabs[idx+1]


# selections
def select_item(tab):
    filename = tab.get_file()
    if filename == os.pardir:
        tab.file_i += 1
        tab.fix_limits()
        return
    try:
        tab.selections.index(filename)
    except ValueError:
        tab.selections.append(filename)
    else:
        tab.selections.remove(filename)
    tab.file_i += 1
    tab.fix_limits()

def select_group(tab):
    pattern = doEntry(tab.path, 'Select group', 'Type pattern', '*')
    if pattern == None or pattern == '':
        return
    fullpath = os.path.join(tab.path, pattern)
    for f in [os.path.basename(f) for f in glob(fullpath)]:
        if f not in tab.selections:
            tab.selections.append(f)

def deselect_group(tab):
    pattern = doEntry(tab.path, 'Deselect group', 'Type pattern', '*')
    if pattern == None or pattern == '':
        return
    fullpath = os.path.join(tab.path, pattern)
    for f in [os.path.basename(f) for f in glob(fullpath)]:
        if f in tab.selections:
            tab.selections.remove(f)

def invert_select(tab):
    selections_old = tab.selections[:]
    tab.selections = [f for f in tab.sorted if f not in selections_old and \
                          f != os.pardir]

# misc
def show_size(tab):
    show_dirs_size(tab)

def sort(tab):
    do_sort(tab)

def file_info(tab):
    do_show_file_info(tab)

def action_on_file(tab):
    do_something_on_file(tab)

def special_regards(tab):
    messages.win('Special Regards',
                 '   Maite zaitut, Montse\n   T\'estimo molt, Montse')

def find_grep(tab):
    findgrep(tab)

def touch_file(tab):
    newfile = doEntry(tab.path, 'Touch file', 'Type file name')
    if newfile == None or newfile == "":
        return
    fullfilename = os.path.join(tab.path, newfile)
    i, err = os.popen4('touch \"%s\"' % get_escaped_filename(fullfilename))
    err = err.read().split(':')[-1:][0].strip()
    if err:
        messages.error('Touch file', '%s: %s' % (newfile, err))
    curses.curs_set(0)
    app.regenerate()

def create_link(tab):
    othertab = app.noact_pane.act_tab
    if tab.path != othertab.path:
        otherfile = os.path.join(othertab.path, othertab.get_file())
    else:
        otherfile = othertab.get_file()
    newlink, pointto = doDoubleEntry(tab.path, 'Create link',
                                     'Link name', '', 1, 1,
                                     'Pointing to', otherfile, 1, 1)
    if newlink == None or pointto == None:
        return
    if newlink == '':
        messages.error('Create link', 'You must type new link name')
        return
    if pointto == '':
        messages.error('Create link', 'You must type pointed file')
        return
    fullfilename = os.path.join(tab.path, newlink)
    ans = files.create_link(pointto, fullfilename)
    if ans:
        messages.error('Create link', '%s (%s)' % (ans, tab.get_file()))
    app.regenerate()

def edit_link(tab):
    fullfilename = tab.get_fullpathfile()
    if not os.path.islink(fullfilename):
        return
    pointto = doEntry(tab.path, 'Edit link', 'Link \'%s\' points to' % \
                      tab.get_file(), os.readlink(fullfilename))
    if pointto == None or pointto == "":
        return
    if pointto != None and pointto != "" and \
       pointto != os.readlink(fullfilename):
        ans = files.modify_link(pointto, fullfilename)
        if ans:
            messages.error('Edit link', '%s (%s)' % (ans, tab.getfile()))
    app.regenerate()

def open_shell(tab):
    curses.endwin()
    os.system('cd "%s"; %s' % (get_escaped_filename(tab.path),
                               app.prefs.progs['shell']))
    curses.curs_set(0)
    tab.refresh()


# main functions
def view_file(tab):
    do_view_file(tab)

def edit_file(tab):
    do_edit_file(tab)

def copy(tab):
    destdir = app.noact_pane.act_tab.path + os.sep
    if tab.selections:
        buf = 'Copy %d items to' % len(tab.selections)
        fs = tab.selections[:]
    else:
        filename = tab.get_file()
        if filename == os.pardir:
            return
        buf = 'Copy \'%s\' to' % filename
        fs = [filename]
    destdir = doEntry(tab.path, 'Copy', buf, destdir)
    if destdir:
        res = ProcessCopyMoveLoop('Copying files', files.copy,
                                  fs, tab.path, destdir).run()
    else:
        return
    tab.selections = []
    app.regenerate()

def move(tab):
    destdir = app.noact_pane.act_tab.path + os.sep
    if tab.selections:
        buf = 'Move %d items to' % len(tab.selections)
        fs = tab.selections[:]
    else:
        filename = tab.get_file()
        if filename == os.pardir:
            return
        buf = 'Move \'%s\' to' % filename
        fs = [filename]
    destdir = doEntry(tab.path, 'Move', buf, destdir)
    if destdir:
        res = ProcessCopyMoveLoop('Moving files', files.move,
                                  fs, tab.path, destdir).run()
    else:
        return
    tab.selections = []
    tab.refresh()

def rename(tab):
    if tab.selections:
        fs = tab.selections[:]
    else:
        filename = tab.get_file()
        if filename == os.pardir:
            return
        fs = [filename]
    res = ProcessRenameLoop('Renaming files', files.move, fs, tab.path).run()
    tab.selections = []
    tab.refresh()
    app.regenerate()

def make_dir(tab):
    newdir = doEntry(tab.path, 'Make directory', 'Type directory name')
    if newdir == None or newdir == '':
        return
    ans = files.mkdir(tab.path, newdir)
    if ans:
        messages.error('Make directory',
                       '%s (%s)' % (ans, newdir))
        return
    app.regenerate()

def delete(tab):
    if tab.selections:
        fs = tab.selections[:]
    else:
        filename = tab.get_file()
        if filename == os.pardir:
            return
        fs = [filename]
    res = ProcessDeleteLoop('Deleting files', files.delete, fs, tab.path).run()
    tab.selections = []
    tab.refresh()


# menu
def show_help(tab):
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
        docfile = 'README'
    elif cmd == 'v':
        docfile = 'README.pyview'
    elif cmd == 'n':
        docfile = 'NEWS'
    elif cmd == 't':
        docfile = 'TODO'
    elif cmd == 'c':
        docfile = 'ChangeLog'
    elif cmd == 'l':
        docfile = 'COPYING'
    fullfilename = os.path.join(docdir, docfile)
    os.system('%s \"%s\"' % (app.prefs.progs['pager'], fullfilename))
    curses.curs_set(0)

def file_menu(tab):
    menu = [ '@    Do something on file(s)',
             'i    File info',
             'p    Change file permissions, owner, group',
             'g    Gzip/gunzip file(s)',
             'b    Bzip2/bunzip2 file(s)',
             'x    Uncompress .tar.gz, .tar.bz2, .zip, .rar',
             'u    Uncompress .tar.gz, etc in other panel',
             'c    Compress directory to .tar.gz',
             'd    Compress directory to .tar.bz2',
             'z    Compress directory to .zip',
             'r    Compress directory to .rar' ]
    cmd = messages.MenuWin('File Menu', menu).run()
    if cmd == -1:
        return
    app.display()
    cmd = cmd[0]
    if cmd == '@':
        do_something_on_file(tab)
    elif cmd == 'i':
        do_show_file_info(tab)
    elif cmd == 'p':
        do_change_perms(tab)
    elif cmd == 'g':
        compress_uncompress_file(tab, 'gz')
    elif cmd == 'b':
        compress_uncompress_file(tab, 'bz2')
    elif cmd == 'x':
        uncompress_dir(tab, tab.path)
    elif cmd == 'u':
        uncompress_dir(tab, app.noact_pane.act_tab.path)
    elif cmd == 'c':
        compress_dir(tab, 'tgz')
    elif cmd == 'd':
        compress_dir(tab, 'tbz2')
    elif cmd == 'z':
        compress_dir(tab, 'zip')
    elif cmd == 'r':
        compress_dir(tab, 'rar')
    app.regenerate()


def general_menu(tab):
    menu = [ '/    Find/grep file(s)',
             '#    Show directories size',
             's    Sort files',
             't    Tree',
             'f    Show filesystems info',
             'o    Open shell',
             'c    Edit configuration',
             'r    Regenerate programs' ]
    cmd = messages.MenuWin('General Menu', menu).run()
    if cmd == -1:
        return
    app.display()
    cmd = cmd[0]
    if cmd == '/':
        findgrep(tab)
    elif cmd == '#':
        show_dirs_size(tab)
    elif cmd == 's':
        do_sort(tab)
    elif cmd == 't':
        tree(tab)
    elif cmd == 'f':
        do_show_fs_info()
    elif cmd == 'o':
        open_shell(tab)
    elif cmd == 'c':
        curses.endwin()
        os.system('%s \"%s\"' % (app.prefs.progs['editor'], app.prefs.file))
        curses.curs_set(0)
        app.prefs.load()
    elif cmd == 'r':
        app.prefs.check_progs()
        app.prefs.save()
        app.prefs.load()
        messages.win('Regenerate programs', '          OK')


# window resize
def resize_window(tab):
    app.resize()


#refresh screen
def refresh_screen(tab):
    app.regenerate()


# exit
def quit(tab):
    if app.prefs.confirmations['quit']:
        ans = messages.confirm('Last File Manager',
                               'Quit Last File Manager', 1)
        if ans == 1:
            return -1
    else:
        return -1

def exit(tab):
    if app.prefs.confirmations['quit']:
        ans = messages.confirm('Last File Manager',
                               'Quit Last File Manager', 1)
        if ans == 1:
            return -2
    else:
        return -2


######################################################################
##### Utils
# bookmarks
def goto_bookmark(tab, num):
    todir = app.prefs.bookmarks[num]
    if tab.vfs:
        vfs.exit(tab)
    tab.init(todir)


# show size
def do_show_dirs_size(filename, path):
    return files.get_fileinfo(os.path.join(path, filename), False, True)

def show_dirs_size(tab):
    if tab.selections:
        lst = tab.selections
    else:
        lst = tab.files.keys()
    dirs = [d for d in lst if tab.files[d][files.FT_TYPE] in \
                (files.FTYPE_DIR, files.FTYPE_LNK2DIR) and d != os.pardir]
    res = ProcessDirSizeLoop('Calculate Directories Size',
                             do_show_dirs_size, dirs, tab.path).run()
    if res != None and type(res) == type([]) and len(res):
        for i, d in enumerate(dirs):
            try:
                tab.files[d] = res[i]
            except IndexError: # if stopped by user len(res) < len(dirs)
                pass


# sort
def do_sort(tab):
    options = app.prefs.options
    while True:
        ch = messages.get_a_key('Sorting mode',
                                'N(o), by (n)ame, by (s)ize, by (d)ate,\nuppercase if reversed order, Ctrl-C to quit')
        if ch in (ord('o'), ord('O')):
            options['sort'] = files.SORTTYPE_None
            break
        elif ch == ord('n'):
            options['sort'] =  files.SORTTYPE_byName
            break
        elif ch == ord('N'):
            options['sort'] =  files.SORTTYPE_byName_rev
            break
        elif ch == ord('s'):
            options['sort'] = files.SORTTYPE_bySize
            break
        elif ch == ord('S'):
            options['sort'] = files.SORTTYPE_bySize_rev
            break
        elif ch == ord('d'):
            options['sort'] = files.SORTTYPE_byDate
            break
        elif ch == ord('D'):
            options['sort'] = files.SORTTYPE_byDate_rev
            break
        elif ch == -1:                 # Ctrl-C
            break
    old_filename = tab.get_file()
    old_selections = tab.selections[:]
    tab.init(tab.path)
    tab.file_i = tab.sorted.index(old_filename)
    tab.fix_limits()
    tab.selections = old_selections


# do special view file
def do_special_view_file(tab):
    fullfilename = tab.get_fullpathfile()
    ext = os.path.splitext(fullfilename)[1].lower()[1:]
    for typ, exts in app.prefs.filetypes.items():
        if ext in exts:
            prog = app.prefs.progs[typ]
            if prog == '':
                messages.error('Can\'t run program',
                               'Can\'t start %s files, defaulting to view' % typ)
                do_view_file(tab)
                break
            sys.stdout = sys.stderr = '/dev/null'
            curses.endwin()
            if app.prefs.options['detach_terminal_at_exec']:
                run_dettached(prog, get_escaped_filename(fullfilename))
                curses.curs_set(0)
                break
            else:
                # programs inside same terminal as lfm should use:
                cmd = get_escaped_command(prog, fullfilename)
                os.system(cmd)
                curses.curs_set(0)
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                break
    else:
        do_view_file(tab)
    app.regenerate()


# do view file
def do_view_file(tab):
    run_on_current_file('pager', tab)


# do edit file
def do_edit_file(tab):
    run_on_current_file('editor', tab)
    app.regenerate()


# do execute file
def do_execute_file(tab):
    filename = tab.get_file()
    parms = doEntry(tab.path, 'Execute file', 'Enter arguments')
    if parms == None:
        return
    elif parms == '':
        cmd = get_escaped_filename(filename)
    else:
        cmd = '%s \"%s\"' % (get_escaped_filename(filename), parms)
    curses.endwin()
    st, msg = ProcessFunc('Executing file', filename,
                          run_shell, cmd, tab.path, True).run()
    if st == -1:
        messages.error('Executing file', msg)
    if st != -100 and msg != None:
        if app.prefs.options['show_output_after_exec']:
            curses.curs_set(0)
            if messages.confirm('Executing file', 'Show output'):
                lst = [(l, 2) for l in msg.split('\n')]
                pyview.InternalView('Output of "%s"' % cmd,
                                    lst, center = 0).run()
    curses.curs_set(0)
    tab.refresh()


# do something on file
def do_something_on_file(tab):
    cmd = doEntry(tab.path, 'Do something on file(s)', 'Enter command')
    if cmd:
        curses.endwin()
        if len(tab.selections):
            for f in tab.selections:
                cmd = get_escaped_command(cmd, f)
                os.system('cd \"%s\"; %s' % (tab.path, cmd))
            tab.selections = []
        else:
            cmd = get_escaped_command(cmd, tab.sorted[tab.file_i])
            os.system('cd \"%s\"; %s' % (tab.path, cmd))
        curses.curs_set(0)
        tab.refresh()


# show file info
def do_show_file_info(tab):
    def show_info(tab, file):
        import stat
        from time import ctime

        fullfilename = os.path.join(tab.path, file)
        file_data = tab.files[file]
        file_data2 = os.lstat(fullfilename)
        buf = []
        user = os.environ['USER']
        username = files.get_user_fullname(user)
        so, host, ver, tmp, arch = os.uname()
        buf.append(('%s v%s executed by %s' % (LFM_NAME, VERSION, username), 5))
        buf.append(('<%s@%s> on a %s %s [%s]' % (user, host, so, ver, arch), 5))
        buf.append(('', 2))
        cmd = get_escaped_command('file', fullfilename)
        fileinfo = os.popen(cmd).read().split(':')[1].strip()
        buf.append(('%s: %s (%s)' % (files.FILETYPES[file_data[0]][1], file,
                                     fileinfo), 6))
        if not tab.vfs:
            path = tab.path
        else:
            path = vfs.join(tab) + ' [%s]' % tab.base
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
        fs = ['/', '0', '0', '0', '0%', '/', 'unknown']
        for e in fss:
            if fullfilename.find(e[5]) != -1 and (len(e[5]) > len(fs[5]) or e[5] == os.sep):
                fs = e
        buf.append(('File system: %s on %s (%s) %d%% free' % \
                    (fs[0], fs[5], fs[6], 100 - int(fs[4][:-1])), 6))
        pyview.InternalView('Information about \'%s\'' % file, buf).run()

    if tab.selections:
        for f in tab.selections:
            show_info(tab, f)
        tab.selections = []
    else:
        show_info(tab, tab.sorted[tab.file_i])


# change permissions
def __do_change_perms(filename, ret):
    ans = files.set_perms(filename, ret[0])
    if ans:
        messages.error('Chmod', '%s (%s)' % (ans, filename))
    ans = files.set_owner_group(filename, ret[1], ret[2])
    if ans:
        messages.error('Chown', '%s (%s)' % (ans, filename))

def do_change_perms(tab):
    if tab.selections:
        change_all = 0
        for i, f in enumerate(tab.selections):
            if not change_all:
                ret = messages.ChangePerms(f, tab.files[f], i+1,
                                           len(tab.selections)).run()
                if ret == -1:
                    break
                elif ret == 0:
                    continue
                elif ret[3] == 1:
                    change_all = 1
            filename = os.path.join(tab.path, f)
            __do_change_perms(filename, ret)
        tab.selections = []
    else:
        filename = tab.get_file()
        if filename == os.pardir:
            return
        ret = messages.ChangePerms(filename, tab.files[filename]).run()
        if ret == -1:
            return
        filename = os.path.join(tab.path, filename)
        __do_change_perms(filename, ret)
    app.regenerate()


# do show filesystems info
def do_show_fs_info():
    """Show file systems info"""

    fs = files.get_fs_info()
    if type(fs) != type([]):
        messages.error('Show filesystems info', fs)
        return
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
def findgrep(tab):
    # ask data
    fs, pat = doDoubleEntry(tab.path, 'Find files', 'Filename', '*', 1, 1,
                            'Content', '', 1, 0)
    if fs == None or fs == '':
        return
    path = os.path.dirname(fs)
    fs = os.path.basename(fs)
    if path == None or path == '':
        path = tab.path
    if path[0] != os.sep:
        path = os.path.join(tab.path, path)
    if pat: # findgrep
        st, m = do_findgrep(path, fs, pat)
        search_type = 'Find/Grep'
    else: # find
        st, m = do_find(path, fs)
        search_type = 'Find'
    # check returned value
    if st < 0: # error
        if st == -100: # stopped by user
            return
        else: # some other error
            app.display()
            messages.error(search_type, m)
            return
    if not m or m == []:
        app.display()
        messages.error(search_type, 'No files found')
        return
    # show matches
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
            pvfs, base, vbase = tab.vfs, tab.base, tab.vbase
            tab.init(todir)
            tab.vfs, tab.base, tab.vbase = pvfs, base, vbase
            if tofile:
                tab.file_i = tab.sorted.index(tofile)
            find_quit = 1
        elif cmd == 1:           # panelize
            if pat:
                fs = [f[f.find(':')+1:] for f in m if fs.count(f) == 0]
            else:
                fs = [f for f in m if fs.count(f) == 0]
            vfs.pan_init(tab, fs)
            find_quit = 1
        elif cmd == 2:           # view
            if tofile:
                curses.curs_set(0)
                curses.endwin()
                os.system('%s +%d \"%s\"' %  (app.prefs.progs['pager'],
                                              line,  get_escaped_filename(f)))
                curses.curs_set(0)
            else:
                messages.error('View', 'it\'s a directory',
                               todir)
        elif cmd == 3:           # edit
            if tofile:
                curses.endwin()
                if line > 0:
                    os.system('%s +%d \"%s\"' % (app.prefs.progs['editor'],
                                                 line, get_escaped_filename(f)))
                else:
                    os.system('%s \"%s\"' % (app.prefs.progs['editor'],
                                             get_escaped_filename(f)))
                curses.curs_set(0)
                app.regenerate()
            else:
                messages.error('Edit', 'it\'s a directory', todir)
        elif cmd == 4:           # do something on file
            cmd2 = doEntry(tab.path, 'Do something on file', 'Enter command')
            if cmd2:
                curses.endwin()
                os.system('%s \"%s\"' % (cmd2, get_escaped_filename(f)))
                curses.curs_set(0)
                app.regenerate()
        else:
            find_quit = 1


# entries
def doEntry(tabpath, title, help, path = '', with_historic = True,
            with_complete = True):
    while True:
        path = messages.Entry(title, help, path, with_historic, with_complete,
                              tabpath).run()
        if type(path) == type([]):
            path = path.pop()
        else:
            return path


def doDoubleEntry(tabpath, title, help1, path1 = '',
                  with_historic1 = True, with_complete1 = True,
                  help2 = '', path2 = '',
                  with_historic2 = True, with_complete2 = True):
    active_entry = 0
    tabpath1 = tabpath2 = tabpath
    while True:
        path = messages.DoubleEntry(title, help1, path1, with_historic1,
                                    with_complete1, tabpath1,
                                    help2, path2, with_historic2,
                                    with_complete2, tabpath2,
                                    active_entry).run()
        if type(path) != type([]):
            return path
        else:
            active_entry = path.pop()
            path2 = path.pop()
            path1 = path.pop()


######################################################################
##### Tree
class Tree:
    """Tree class"""

    def __init__(self, path = os.sep, panemode = 0):
        if not os.path.exists(path):
            raise ValueError, 'path does not exist'
        self.panemode = panemode
        self.__init_ui()
        if path[-1] == os.sep and path != os.sep:
            path = path[:-1]
        self.path = path
        self.tree = self.get_tree()
        self.pos = self.__get_curpos()


    def __get_dirs(self, path):
        """return a list of dirs in path"""

        ds = []
        try:
            ds = [d for d in os.listdir(path) \
                      if os.path.isdir(os.path.join(path, d))]
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
        for n, d in enumerate(dir_keys):
            tree_n[n] = d
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

        for i in xrange(len(self.tree)):
            if self.path == self.tree[i][2]:
                return i
        else:
            return -1


    def regenerate_tree(self, newpos):
        """regenerate tree when changing to a new directory"""

        self.path = self.tree[newpos][2]
        self.tree = self.get_tree()
        self.pos = self.__get_curpos()


    def show_tree(self, a=0, z=-1):
        """show an ascii representation of the tree. Not used in lfm"""

        if z > len(self.tree) or z == -1:
            z = len(self.tree)
        for i in xrange(a, z):
            name, depth, fullname = self.tree[i]
            if fullname == self.path:
                name += ' <====='
            if name == os.sep:
                print ' ' + name
            else:
                print ' | ' * depth + ' +- ' + name


    # GUI functions
    def __init_ui(self):
        """initialize curses stuff"""

        self.__calculate_dims()
        try:
            self.win = curses.newwin(*self.dims)
        except curses.error:
            print 'Can\'t create tree window'
            sys.exit(-1)
        self.win.keypad(1)
        if curses.has_colors():
            self.win.bkgd(curses.color_pair(2))


    def __calculate_dims(self):
        if self.panemode == PANE_MODE_LEFT:
            self.dims = (app.maxh-2, int(app.maxw/2), 1, int(app.maxw/2))
        elif self.panemode in (PANE_MODE_RIGHT, PANE_MODE_FULL):
            self.dims = (app.maxh-2, int(app.maxw/2), 1, 0)
        else: # PANE_MODE_HIDDEN:
            self.dims = (app.maxh-2, 0, 0, 0)     # h, w, y, x
            return


    def display(self):
        """show tree panel"""

        self.win.erase()
        h = app.maxh - 4
        n = len(self.tree)
        # box
        self.win.attrset(curses.color_pair(5))
        self.win.box()
        self.win.addstr(0, 2, ' Tree ', curses.color_pair(6) | curses.A_BOLD)
        # tree
        self.win.attrset(curses.color_pair(2))
        j = 0
        a = int(self.pos/h) * h
        z = (int(self.pos/h) + 1) * h
        if z > n:
            a = max(n-h, 0); z = n
        for i in xrange(a, z):
            j += 1
            name, depth, fullname = self.tree[i]
            if name == os.sep:
                self.win.addstr(j, 1, ' ')
            else:
                self.win.move(j, 1)
                for kk in xrange(depth):
                    self.win.addstr(' ')
                    self.win.addch(curses.ACS_VLINE)
                    self.win.addstr(' ')
                self.win.addstr(' ')
                if i == n - 1:
                    self.win.addch(curses.ACS_LLCORNER)
                elif depth > self.tree[i+1][1]:
                    self.win.addch(curses.ACS_LLCORNER)
                else:
                    self.win.addch(curses.ACS_LTEE)
                self.win.addch(curses.ACS_HLINE)
                self.win.addstr(' ')
            w = int(app.maxw / 2) - 2
            wd = 3 * depth + 4
            if fullname == self.path:
                self.win.addstr(name[:w-wd-3], curses.color_pair(3))
                child_dirs = self.__get_dirs(self.path)
                if len(child_dirs) > 0:
                    self.win.addstr(' ')
                    self.win.addch(curses.ACS_HLINE)
                    self.win.addch(curses.ACS_RARROW)
            else:
                self.win.addstr(name[:w-wd])
        # scrollbar
        if n > h:
            nn = max(int(h*h/n), 1)
            y0 = min(max(int(int(self.pos/h)*h*h/n), 0), h-nn)
        else:
            y0 = nn = 0
        self.win.attrset(curses.color_pair(5))
        self.win.vline(y0 + 2, int(app.maxw/2) - 1, curses.ACS_CKBOARD, nn)
        if a != 0:
            self.win.vline(1, int(app.maxw/2) - 1, '^', 1)
            if nn == 1 and (y0 + 2 == 2):
                self.win.vline(3, int(app.maxw/2) - 1, curses.ACS_CKBOARD, nn)
        if n - 1 > a + h - 1:
            self.win.vline(h, int(app.maxw/2) - 1, 'v', 1)
            if nn == 1 and (y0 + 2 == h + 1):
                self.win.vline(h, int(app.maxw/2) - 1, curses.ACS_CKBOARD, nn)
        # status
        app.statusbar.win.erase()
        wp = app.maxw - 8
        if len(self.path) > wp:
            path = self.path[:int(wp/2) -1] + '~' + self.path[-int(wp/2):]
        else:
            path = self.path
        app.statusbar.win.addstr(' Path: %s' % path)
        app.statusbar.win.refresh()


    def run(self):
        """manage keys"""

        while True:
            self.display()
            chext = 0
            ch = self.win.getch()

            # to avoid extra chars input
            if ch == 0x1B:
                chext = 1
                ch = self.win.getch()
                ch = self.win.getch()

            # cursor up
            if ch in (ord('k'), ord('K'), curses.KEY_UP):
                if self.pos == 0:
                    continue
                if self.tree[self.pos][1] != self.tree[self.pos-1][1]:
                    continue
                newpos = self.pos - 1
            # cursor down
            elif ch in (ord('j'), ord('j'), curses.KEY_DOWN):
                if self.pos == len(self.tree) - 1:
                    continue
                if self.tree[self.pos][1] != self.tree[self.pos+1][1]:
                    continue
                newpos = self.pos + 1
            # page previous
            elif ch in (curses.KEY_PPAGE, curses.KEY_BACKSPACE,
                        0x08, 0x02):                         # BackSpace, Ctrl-B
                depth = self.tree[self.pos][1]
                if self.pos - (app.maxh-4) >= 0:
                    if depth  == self.tree[self.pos - (app.maxh-4)][1]:
                        newpos = self.pos - (app.maxh-4)
                    else:
                        newpos = self.pos
                        while 1:
                            if newpos - 1 < 0 or self.tree[newpos-1][1] != depth:
                                break
                            newpos -= 1
                else:
                    newpos = self.pos
                    while 1:
                        if newpos - 1 < 0 or self.tree[newpos-1][1] != depth:
                            break
                        newpos -= 1
            # page next
            elif ch in (curses.KEY_NPAGE, ord(' '), 0x06):   # Ctrl-F
                depth = self.tree[self.pos][1]
                if self.pos + (app.maxh-4) <= len(self.tree) - 1:
                    if depth  == self.tree[self.pos + (app.maxh-4)][1]:
                        newpos = self.pos + (app.maxh-4)
                    else:
                        newpos = self.pos
                        while 1:
                            if newpos + 1 == len(self.tree) or \
                                    self.tree[newpos+1][1] != depth:
                                break
                            newpos += 1
                else:
                    newpos = self.pos
                    while 1:
                        if newpos + 1 == len(self.tree) or \
                                self.tree[newpos+1][1] != depth:
                            break
                        newpos += 1
            # home
            elif (ch in (curses.KEY_HOME, 0x01)) or \
                 (chext == 1) and (ch == 72):  # home
                newpos = 1
            # end
            elif (ch in (curses.KEY_END, 0x05)) or \
                 (chext == 1) and (ch == 70):   # end
                newpos = len(self.tree) - 1
            # cursor left
            elif ch == curses.KEY_LEFT:
                if self.pos == 0:
                    continue
                newdepth = self.tree[self.pos][1] - 1
                for i in xrange(self.pos-1, -1, -1):
                    if self.tree[i][1] == newdepth:
                        break
                newpos = i
            # cursor right
            elif ch == curses.KEY_RIGHT:
                child_dirs = self.__get_dirs(self.path)
                if len(child_dirs) > 0:
                    self.path = os.path.join(self.path, child_dirs[0])
                    self.tree = self.get_tree()
                    self.pos = self.__get_curpos()
                continue
            # enter
            elif ch in (10, 13):
                return self.path
            # resize
            elif ch == curses.KEY_RESIZE:
                curses.doupdate()
                app.resize()
                self.__calculate_dims()
                self.win.resize(self.dims[0], self.dims[1])
                self.win.mvwin(self.dims[2], self.dims[3])
                continue
            # quit
            elif ch in (ord('q'), ord('Q'), curses.KEY_F10, 0x03):  # Ctrl-C
                return -1

            # else
            else:
                continue

            # update
            self.regenerate_tree(newpos)


######################################################################
