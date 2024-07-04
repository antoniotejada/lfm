# -*- coding: utf-8 -*-


import pkg_resources
from glob import glob
from tempfile import mkdtemp
from os import sep, readlink, environ, uname
from os.path import basename, dirname, exists, getsize, isdir, isfile, islink, join, pardir

import utils
from utils import public
from ui_widgets import DialogError, DialogConfirm, DialogGetKey, SelectItem, \
                       DialogEntry, DialogDoubleEntry, DialogFindGrep, TreeView, \
                       DialogPerms, DialogOwner, InternalView
from common import *


########################################################################
##### Module variables
app = None


########################################################################
##### Action dispatcher
def do(mapp, action):
    global app
    app = mapp
    log.debug('Execute: {}'.format(action))
    try:
        fn = globals()[action]
    except KeyError:
        log.warning('ERROR can\'t execute an undefined function: {}()'.format(action))
        return RET_NONE
    if not utils.is_public_api(fn):
        log.warning('ERROR: function {}() is not public API for action "{}"'.format(fn.__name__, action))
        return RET_NONE
    ret = fn()
    log.debug('Returns: {}'.format(ret))
    return ret


########################################################################
##### Cursor movement
@public
def cursor_up():
    app.pane_active.tab_active.i -= 1
    return RetCode.fix_limits, None

@public
def cursor_down():
    app.pane_active.tab_active.i += 1
    return RetCode.fix_limits, None

@public
def cursor_up10():
    app.pane_active.tab_active.i -= 10
    return RetCode.fix_limits, None

@public
def cursor_down10():
    app.pane_active.tab_active.i += 10
    return RetCode.fix_limits, None

@public
def cursor_pageup():
    app.pane_active.tab_active.i -= app.pane_active.fh
    return RetCode.fix_limits, None

@public
def cursor_pagedown():
    app.pane_active.tab_active.i += app.pane_active.fh
    return RetCode.fix_limits, None

@public
def cursor_home():
    app.pane_active.tab_active.i = 0
    return RetCode.fix_limits, None

@public
def cursor_end():
    app.pane_active.tab_active.i = app.pane_active.tab_active.n-1
    return RetCode.fix_limits, None

@public
def cursor_goto_file():
    text = DialogEntry('Go to file', 'Type part of the file name').run()
    if not text:
        return RetCode.nothing, None
    start = app.pane_active.tab_active.i + 1
    entries = app.pane_active.tab_active.fs.get_filenames(start=start)
    for e in entries:
        if e.find(text) != -1:
            app.pane_active.tab_active.i = entries.index(e) + start
            return RetCode.fix_limits, None
    return RetCode.fix_limits, None

@public
def cursor_goto_file_1char():
    start = app.pane_active.tab_active.i + 1
    entries = app.pane_active.tab_active.fs.get_filenames(start=start)
    app.win.nodelay(0)
    ch = app.win.getkey()
    app.win.nodelay(1)
    for e in entries:
        if ch == e[0]:
            app.pane_active.tab_active.i = entries.index(e) + start
            return RetCode.fix_limits, None
    return RetCode.nothing, None


########################################################################
##### Cursor movement
@public
def dir_up():
    tab = app.pane_active.tab_active
    if tab.fs.path_str == sep:
        return RetCode.nothing, None
    olddirname = tab.fs.basename
    tab.goto_folder(tab.fs.dirname)
    tab.focus_file(olddirname)
    return RetCode.full_redisplay, None

@public
def dir_enter():
    tab = app.pane_active.tab_active
    fname = tab.fs[tab.i].name
    if fname == pardir:
        return dir_up()
    ft = tab.fs[tab.i].get_type_from_ext(app.cfg.files_ext)
    if ft in ('dir', 'archive'):
        tab.goto_folder(join(tab.fs.path_str, fname))
    elif ft in ('audio', 'ebook', 'graphics', 'pdf', 'video', 'web'):
        utils.run_on_current_file(app.cfg.programs[ft], app.pane_active.tab_active.current_filename_full, True)
        return refresh()
    else:
        utils.run_on_current_file(app.cfg.programs['pager'], app.pane_active.tab_active.current_filename_full)
        return refresh()
    return RetCode.full_redisplay, None

@public
def goto():
    newdir = DialogEntry('Change directory', 'Type directory name', '',
                         history=app.history['path'][:], is_files=True).run()
    if not newdir:
        return RetCode.nothing, None
    newdir = utils.get_norm_path(newdir, app.pane_active.tab_active.dirname)
    log.debug('Chdir "{}"'.format(newdir))
    app.pane_active.tab_active.goto_folder(newdir, delete_vfs_tree=True)
    if newdir:
        app.history.append('path', newdir)
    return RetCode.full_redisplay, None

@public
def bookmark_goto():
    while True:
        key = DialogGetKey('Goto bookmark',
                           'Press 0-9 a-z to select the bookmark, Ctrl-C to quit')
        if key == -1: # Ctrl-C
            break
        elif chr(key) in BOOKMARKS_KEYS:
            log.debug('Goto bookmark in key "{}" > "{}"'.format(chr(key), app.cfg.bookmarks[chr(key)]))
            app.pane_active.tab_active.goto_folder(app.cfg.bookmarks[chr(key)], delete_vfs_tree=True)
            break
    return RetCode.full_redisplay, None

@public
def bookmark_set():
    fs = app.pane_active.tab_active.fs
    if fs.vfs:
        DialogError('Cannot save a bookmark to a VFS')
        return RetCode.full_redisplay, None
    while True:
        key = DialogGetKey('Set bookmark',
                           'Press 0-9 a-z to save bookmark, Ctrl-C to quit')
        if key == -1: # Ctrl-C
            break
        elif chr(key) in BOOKMARKS_KEYS:
            log.debug('Save bookmark "{}" to key "{}"'.format(fs.path_str, chr(key)))
            app.cfg.bookmarks[chr(key)] = fs.path_str
            break
    return RetCode.full_redisplay, None

@public
def bookmark_select_fromlist():
    bmks = sorted(['{}  {}'.format(k, b) for k, b in app.cfg.bookmarks.items()])
    ret = SelectItem('Select Bookmark', bmks).run()
    if ret != -1:
        app.pane_active.tab_active.goto_folder(ret[3:], delete_vfs_tree=True)
    return RetCode.full_redisplay, None

@public
def history_select_fromlist():
    tab = app.pane_active.tab_active
    if len(tab.history) == 0:
        DialogError('No entries in history')
        return RetCode.full_redisplay, None
    ret = SelectItem('Return to', list(reversed(tab.history)), quick_key=False).run()
    if ret != -1:
        app.pane_active.tab_active.goto_folder(ret, delete_vfs_tree=True)
    return RetCode.full_redisplay, None


########################################################################
##### Panes
@public
def pane_change_focus():
    otherpane = app.pane2 if app.pane1.focus else app.pane1
    app.focus_pane(otherpane)
    return RetCode.full_redisplay, None

@public
def pane_other_tab_equal():
    path = app.pane_active.tab_active.fs.path_str
    app.pane_inactive.tab_active.goto_folder(path, delete_vfs_tree=True)
    return RetCode.full_redisplay, None

@public
def panes_swap():
    log.debug('Swap panes')
    app.pane1, app.pane2 = app.pane2, app.pane1
    app.resize()
    return RetCode.full_redisplay, None

@public
def panes_cycle_view():
    if app.pane_active.mode == PaneMode.half:
        app.pane_active.change_mode(PaneMode.full)
    else:
        app.pane_active.change_mode(PaneMode.half)
    return RetCode.full_redisplay, None

@public
def refresh():
    for tab in app.pane1.tabs + app.pane2.tabs:
        tab.reload()
        tab.refresh()
    return RetCode.full_redisplay, None

@public
def redraw_screen():
    app.clear_screen()
    return RetCode.full_redisplay, None

@public
def dotfiles_toggle():
    app.cfg.options.show_dotfiles = not app.cfg.options.show_dotfiles
    for tab in app.pane1.tabs + app.pane2.tabs:
        tab.fs.cfg.show_dotfiles = app.cfg.options.show_dotfiles
        tab.refresh()
    return RetCode.full_redisplay, None

@public
def filters_edit():
    tab = app.pane_active.tab_active
    text = DialogEntry('Edit filter', 'Type globs, separated by commas, for the files you want to hide',
                       tab.fs.cfg.filters, history=app.history['glob'][:], is_files=False).run()
    if text is None: # not "if not text"!!! because we need text='' to clear filters
        return RetCode.nothing, None
    tab.fs.cfg.filters = text
    tab.refresh()
    if text:
        app.history.append('glob', text)
    return RetCode.half_redisplay, None

@public
def sort_files():
    sorttypes = {'o': SortType.none, 'O': SortType.none,
                 'n': SortType.byName, 'N': SortType.byName,
                 'e': SortType.byName, 'E': SortType.byName,
                 's': SortType.bySize, 'S': SortType.bySize,
                 'd': SortType.byMTime, 'D': SortType.byMTime}
    while True:
        key = DialogGetKey('Sorting mode',
                           'N(o)ne, by (n)ame, by (e)xtension, by (s)ize, by (d)ate,\nuppercase to reverse order, Ctrl-C to quit')
        if key == -1: # Ctrl-C
            break
        elif chr(key) in sorttypes.keys():
            app.cfg.options.sort_type = sorttypes[chr(key)]
            app.cfg.options.sort_reverse = key<ord('Z')
            app.pane1.refresh()
            app.pane2.refresh()
            break
    return RetCode.full_redisplay, None

@public
def show_dirs_size():
    tab = app.pane_active.tab_active
    dirs = [e for e in tab.selected if e.is_dir] if tab.selected else tab.fs.dirs
    tab.selected = []
    if len(dirs) == 0:
        return RetCode.nothing, None
    log.debug('Show directories size')
    args = [(d.pfile, ) for d in dirs]
    st, rets, errs = utils.ProcessFuncLoop('Calculate directories size', utils.get_dir_size, args).run()
    if st == ProcCode.stopped:
        return RetCode.full_redisplay, None
    for d, size in zip(dirs, rets):
        if size != -1:
            tab.fs.lookup(basename(d.pfile)).update_size(size)
    return RetCode.full_redisplay, None


@public
def tab_new():
    if len(app.pane_active.tabs) >= MAX_TABS:
        DialogError('Cannot create more tabs')
    else:
        curtab = app.pane_active.tab_active
        app.pane_active.insert_new_tab(curtab.fs.path_str, curtab)
    return RetCode.full_redisplay, None

@public
def tab_close():
    if len(app.pane_active.tabs) == 1:
        DialogError('Cannot close last tab')
    else:
        app.pane_active.close_tab(app.pane_active.tab_active)
    return RetCode.full_redisplay, None

@public
def tab_left():
    tab = app.pane_active.tab_active
    idx = app.pane_active.tabs.index(tab)
    if idx == 0:
        return RetCode.nothing, None
    app.pane_active.tab_active = app.pane_active.tabs[idx-1]
    return RetCode.full_redisplay, None

@public
def tab_right():
    tab = app.pane_active.tab_active
    idx = app.pane_active.tabs.index(tab)
    if idx==len(app.pane_active.tabs)-1 or idx==MAX_TABS-1:
        return RetCode.nothing, None
    app.pane_active.tab_active = app.pane_active.tabs[idx+1]
    return RetCode.full_redisplay, None


########################################################################
##### Selections
@public
def select():
    tab = app.pane_active.tab_active
    if tab.i != 0: # pardir
        it = tab.fs[tab.i]
        if it is not None:
            try:
                tab.selected.index(it)
            except ValueError:
                tab.selected.append(it)
            else:
                tab.selected.remove(it)
            app.pane_active.tab_active.i += 1
            return RetCode.fix_limits, None
    return RetCode.nothing, None

@public
def select_glob():
    tab = app.pane_active.tab_active
    text = DialogEntry('Select group', 'Type pattern', '*', history=app.history['glob'][:], is_files=False).run()
    if not text:
        return RetCode.nothing, None
    for fname in glob(join(tab.dirname, text)):
        f = tab.fs.lookup(basename(fname))
        if f and f not in tab.selected:
            tab.selected.append(f)
    if text != '*':
        app.history.append('glob', text)
    return RetCode.half_redisplay, None

@public
def deselect_glob():
    tab = app.pane_active.tab_active
    text = DialogEntry('Deselect group', 'Type pattern', '*', history=app.history['glob'][:], is_files=False).run()
    if not text:
        return RetCode.nothing, None
    for fname in glob(join(tab.dirname, text)):
        f = tab.fs.lookup(basename(fname))
        if f and f in tab.selected:
            tab.selected.remove(f)
    if text != '*':
        app.history.append('glob', text)
    return RetCode.half_redisplay, None

@public
def select_invert():
    tab = app.pane_active.tab_active
    selected_old = tab.selected[:]
    tab.selected = [f for f in tab.fs if f not in selected_old and f.name != '..']
    return RetCode.half_redisplay, None


########################################################################
##### Files
@public
def rename_file():
    tab = app.pane_active.tab_active
    filename = tab.current_filename
    if filename == pardir:
        return RetCode.nothing, None
    newname = DialogEntry('Rename', 'Rename \'{}\' to'.format(filename), filename,
                          history=app.history['file'][:], is_files=True).run()
    if not newname:
        return RetCode.nothing, None
    src = tab.current_filename_full
    dest = newname if newname[0] == sep else join(tab.dirname, newname)
    if src == dest:
        DialogError('Cannot rename \'{}\'\nSource and destination are the same file'.format(filename))
        return RetCode.full_redisplay, None
    if dirname(dest) != tab.dirname:
        DialogError('Cannot rename to different directory')
        return RetCode.full_redisplay, None
    if exists(dest) and app.cfg.confirmations.overwrite:
        if not DialogConfirm('Rename file', 'Overwrite \'{}\'?'.format(newname), 0):
            return RetCode.full_redisplay, None
    log.debug('Rename file: {} -> {}'.format(src, dest))
    err = utils.rename_file(src, dest)
    if err:
        log.warning('Cannot rename: \'{}\' to \'{}\': {}'.format(filename, newname, str(err)))
        DialogError('Cannot rename: \'{}\' to \'{}\'\n{}'.format(filename, newname, str(err)))
        return RetCode.full_redisplay, None
    else:
        app.history.append('file', newname)
        return refresh()

def __copymove_helper(act):
    tab = app.pane_active.tab_active
    files = [f.pfile for f in tab.selected_or_current]
    if len(files) == 0:
        return None, None, None
    if len(files) == 1:
        subtitle = '{} \'{}\' to:'.format(act, basename(files[0]))
    else:
        subtitle = '{} {} items to:'.format(act, len(files))
    destdir = DialogEntry('{} file(s)'.format(act), subtitle, app.pane_inactive.tab_active.dirname+sep,
                          history=app.history['path'][:], is_files=True).run()
    if not destdir:
        return None, None, None
    destdir = utils.get_norm_path(destdir, tab.dirname)
    if not isdir(destdir) and len(files) > 1:
        DialogError('Cannot {0} files\nTried to {0} many items to one file name'.format(act.lower()))
        return None, None, None
    log.debug('{} file(s) to \'{}\''.format(act, destdir))
    app.history.append('path', destdir)
    basepath = tab.dirname if tab.dirname[-1]==sep else tab.dirname+sep
    return destdir, basepath, files

@public
def copy_file():
    destdir, basepath, files = __copymove_helper('Copy')
    if not destdir:
        return RetCode.full_redisplay, None
    es = utils.PathContents(files, basepath)
    args = [(f, s, e, basepath, destdir) for f, s, e in es.entries]
    st, rets, errs = utils.ProcessFuncCopyLoop('Copy file(s)', utils.copy_file, args,
                                               es.tsize, app.cfg.confirmations.overwrite).run()
    app.pane_active.tab_active.selected = []
    if st == ProcCode.stopped:
        return refresh()
    for a, res, err in zip(args, rets, errs):
        if err:
            if isinstance(err, LFMFileSkipped):
                log.warning('Copy file(s). Not overwritten: {}'.format(str(err)))
            else:
                log.warning('ERROR: {}'.format(str(err).replace('\n', ' ')))
    return refresh()

@public
def move_file():
    destdir, basepath, files = __copymove_helper('Move')
    if not destdir:
        return RetCode.full_redisplay, None
    es = utils.PathContents(files, basepath)
    args = [(f, s, e, basepath, destdir) for f, s, e in es.entries]
    st, rets, errs = utils.ProcessFuncCopyLoop('Move file(s)', utils.copy_file, args,
                                               es.tsize, app.cfg.confirmations.overwrite).run()
    if st == ProcCode.stopped:
        return refresh()
    not_overwritten = list()
    for a, res, err in zip(args, rets, errs):
        if err:
            if isinstance(err, LFMFileSkipped):
                log.warning('Move file(s). Not overwritten: {}'.format(str(err)))
                not_overwritten.append(str(err))
            else:
                log.warning('ERROR: {}'.format(str(err).replace('\n', ' ')))
    es.remove_files(not_overwritten)
    args = [(f, s, e, basepath) for f, s, e in es.entries_rev] # reverse!
    st, rets, errs = utils.ProcessFuncDeleteLoop('Move file(s)', utils.delete_file, args,
                                                 es.tsize, False).run()
    app.pane_active.tab_active.selected = []
    if st == ProcCode.stopped:
        return refresh()
    for a, res, err in zip(args, rets, errs):
        if err:
            log.warning('ERROR: {}'.format(str(err).replace('\n', ' ')))
    return refresh()

@public
def move_file2():
    # alternative version using shtutil.move instead of copy & delete. Faster but less control
    destdir, basepath, files = __copymove_helper('Move')
    if not destdir:
        return RetCode.full_redisplay, None
    args, size = list(), 0
    for f in files:
        try:
            s = getsize(f)
        except OSError as err:
            s = 0
        size += s
        args.append((f, s, None, basepath, destdir))
    st, rets, errs = utils.ProcessFuncCopyLoop('Move file(s)', utils.move_file, args, size,
                                               app.cfg.confirmations.overwrite).run()
    app.pane_active.tab_active.selected = []
    if st == ProcCode.stopped:
        return refresh()
    for a, ret, err in zip(args, rets, errs):
        if err is not None:
            log.warning('ERROR: {}'.format(str(err).replace('\n', ' ')))
    return refresh()

@public
def delete_file():
    tab = app.pane_active.tab_active
    files = [f.pfile for f in tab.selected_or_current]
    if len(files) == 0:
        return RetCode.nothing, None
    log.debug('Delete file(s)')
    es = utils.PathContents(files, tab.dirname+sep)
    args = [(f, s, e, tab.dirname+sep) for f, s, e in es.entries_rev] # reverse!
    st, rets, errs = utils.ProcessFuncDeleteLoop('Delete file(s)', utils.delete_file, args,
                                                 es.tsize, app.cfg.confirmations.delete).run()
    app.pane_active.tab_active.selected = []
    if st == ProcCode.stopped:
        return refresh()
    for a, res, err in zip(args, rets, errs):
        if err:
            if isinstance(err, LFMFileSkipped):
                log.warning('Delete file(s). Not deleted: {}'.format(str(err)))
            else:
                log.warning('ERROR: {}'.format(str(err).replace('\n', ' ')))
    return refresh()

@public
def exec_on_file():
    cmd = DialogEntry('Execute command on file(s)', 'Enter command', '',
                      history=app.history['exec'][:], is_files=False).run()
    if not cmd:
        return RetCode.nothing, None
    for fsentry in app.pane_active.tab_active.selected_or_current:
        log.debug('Exec on file: {} "{}"'.format(cmd, fsentry.pfile))
        utils.run_on_current_file(cmd, fsentry.pfile)
    log.debug('Exec on file: {}'.format(cmd))
    app.pane_active.tab_active.selected = []
    app.history.append('exec', cmd)
    return refresh()

@public
def view_file():
    log.debug('View file: {}'.format(app.pane_active.tab_active.current_filename_full))
    utils.run_on_current_file(app.cfg.programs['pager'], app.pane_active.tab_active.current_filename_full)
    return refresh()

@public
def edit_file():
    log.debug('Edit file: {}'.format(app.pane_active.tab_active.current_filename_full))
    utils.run_on_current_file(app.cfg.programs['editor'], app.pane_active.tab_active.current_filename_full)
    return refresh()

@public
def make_dir():
    newdir = DialogEntry('Make directory', 'Type directory name', '',
                         history=app.history['file'][:], is_files=True).run()
    if not newdir:
        return RetCode.nothing, None
    log.debug('Make directory: {}'.format(join(app.pane_active.tab_active.dirname, newdir)))
    err = utils.make_dir(join(app.pane_active.tab_active.dirname, newdir))
    if err:
        log.warning('Cannot make directory: {}'.format(str(err)))
        DialogError('Cannot make directory\n{}'.format(str(err)))
        return RetCode.full_redisplay, None
    else:
        app.history.append('file', newdir)
        return refresh()

@public
def touch_file():
    filename = DialogEntry('Touch file', 'Type file name', '',
                           history=app.history['file'][:], is_files=True).run()
    if not filename:
        return RetCode.nothing, None
    log.debug('Touch file: {}'.format(join(app.pane_active.tab_active.dirname, filename)))
    err = utils.touch_file(join(app.pane_active.tab_active.dirname, filename))
    if err:
        log.warning('Cannot touch file: {}'.format(str(err)))
        DialogError('Cannot touch file\n{}'.format(str(err)))
        return RetCode.full_redisplay, None
    else:
        app.history.append('file', filename)
        return refresh()

@public
def link_create():
    thistab, othertab = app.pane_active.tab_active, app.pane_inactive.tab_active
    otherfile = utils.get_relpath(join(othertab.dirname, othertab.current_filename), thistab.dirname)
    ans = DialogDoubleEntry('Create link', 'Link name', 'Pointing to', '', otherfile,
                            history1=app.history['file'][:], history2=app.history['path'][:],
                            is_files=True).run()
    if not ans:
        return RetCode.nothing, None
    newlink, pointto = ans
    if newlink == '':
        DialogError('Cannot create link\nYou must specify the name for the new link')
        return RetCode.full_redisplay, None
    if pointto == '':
        DialogError('Cannot create link\nYou must specify the file to link')
        return RetCode.full_redisplay, None
    log.debug('Create link: {} -> {}'.format(join(thistab.dirname, newlink), pointto))
    err = utils.link_create(join(thistab.dirname, newlink), pointto)
    if err:
        log.warning('Cannot create link: {}'.format(str(err)))
        DialogError('Cannot create link\n{}'.format(str(err)))
        return RetCode.full_redisplay, None
    else:
        app.history.append('file', newlink)
        return refresh()

@public
def link_edit():
    linkname = app.pane_active.tab_active.current_filename_full
    if not islink(linkname):
        return RetCode.nothing, None
    newpointto = DialogEntry('Edit link', 'Link points to', readlink(linkname),
                             history=app.history['path'][:], is_files=True).run()
    if not newpointto:
        return RetCode.nothing, None
    if newpointto == readlink(linkname):
        return RetCode.nothing, None
    log.debug('Edit link: {} -> {}'.format(linkname, newpointto))
    err = utils.link_edit(linkname, newpointto)
    if err:
        log.warning('Cannot edit link: {}'.format(str(err)))
        DialogError('Cannot edit link\n{}'.format(str(err)))
        return RetCode.full_redisplay, None
    else:
        app.history.append('path', newpointto)
        return refresh()

@public
def backup_file():
    ext = app.cfg.misc.backup_extension
    args = [(f.pfile, ext) for f in app.pane_active.tab_active.selected_or_current]
    if len(args) == 0:
        return RetCode.nothing, None
    log.debug('Backup file(s)')
    st, rets, errs = utils.ProcessFuncLoop('Create backup file(s)', utils.backup_file, args).run()
    app.pane_active.tab_active.selected = []
    if st == ProcCode.stopped:
        return refresh()
    for a, ret, err in zip(args, rets, errs):
        if err is not None:
            log.warning('ERROR: {}'.format(str(err).replace('\n', ' ')))
    return refresh()

@public
def change_perms():
    tab = app.pane_active.tab_active
    files = [f for f in tab.selected_or_current]
    if len(files) == 0:
        return RetCode.nothing, None
    log.debug('Change file permissions')
    app.pane_active.tab_active.selected = []
    for_all = False
    for i, f in enumerate(files):
        if not for_all:
            perms, recursive, for_all = DialogPerms(f.name, f.mode, i+1, len(files)).run()
            if perms == -1: # stop
                break
            elif perms == 0: # ignore file
                continue
        cmd = 'chmod {} 0{:o} "{}"'.format('-R' if recursive else '', utils.str2perms(perms), f.pfile)
        st, res, err = utils.ProcessCommand('Change file(s) permission', cmd, cmd, path=tab.dirname).run()
        if st == -100: # stopped by user
            return RetCode.full_redisplay, None
        if err:
            log.warning('Cannot "{}": {}'.format(cmd, str(err).replace('\n', ' ')))
            DialogError('Cannot "{}"\n{}'.format(cmd, str(err)))
    return refresh()

@public
def change_owner():
    tab = app.pane_active.tab_active
    files = [f for f in tab.selected_or_current]
    if len(files) == 0:
        return RetCode.nothing, None
    log.debug('Change file owner/group')
    app.pane_active.tab_active.selected = []
    for_all = False
    for i, f in enumerate(files):
        if not for_all:
            owner, group, recursive, for_all = DialogOwner(f.name, f.owner_str, f.group_str,
                                                           utils.get_owners(), utils.get_groups(),
                                                           i+1, len(files)).run()
            if owner == -1: # stop
                break
            elif owner == 0: # ignore file
                continue
        rec = '-R' if recursive else ''
        cmd = 'chown {} {} "{}"'.format(rec, owner, f.pfile)
        st, res, err = utils.ProcessCommand('Change file(s) owner', cmd, cmd, path=tab.dirname).run()
        if st == -100: # stopped by user
            return RetCode.full_redisplay, None
        if err:
            log.warning('Cannot "{}": {}'.format(cmd, str(err).replace('\n', ' ')))
            DialogError('Cannot "{}"\n{}'.format(cmd, str(err)))
        cmd = 'chgrp {} {} "{}"'.format(rec, group, f.pfile)
        st, res, err = utils.ProcessCommand('Change file(s) group', cmd, cmd, path=tab.dirname).run()
        if st == -100: # stopped by user
            return RetCode.full_redisplay, None
        if err:
            log.warning('Cannot "{}": {}'.format(cmd, str(err).replace('\n', ' ')))
            DialogError('Cannot "{}"\n{}'.format(cmd, str(err)))
    return refresh()

@public
def diff_file_with_backup():
    log.debug('Diff file with backup')
    ext = app.cfg.misc.backup_extension
    filename = app.pane_active.tab_active.current_filename_full
    if filename.endswith(ext):
        file_old, file_new = filename, filename[:-len(ext)]
    else:
        file_old, file_new = filename+ext, filename
    if not exists(file_old):
        DialogError('Cannot diff file\nBackup file does not exist')
        return RetCode.full_redisplay, None
    if not exists(file_new):
        DialogError('Cannot diff file\nOnly backup file exists')
        return RetCode.full_redisplay, None
    if not isfile(file_old) or not isfile(file_new):
        DialogError('Cannot diff file\nWe can only diff regular files')
        return RetCode.full_redisplay, None
    diff = utils.get_file_diff(file_old, file_new, app.cfg.misc.diff_type)
    if diff == '':
        DialogError('Files are identical')
        return RetCode.full_redisplay, None
    tmpfile = join(mkdtemp(), basename(file_old) + ' DIFF ' + basename(file_new))
    with open(tmpfile, 'w') as f:
        f.write(diff)
    utils.run_on_current_file(app.cfg.programs['pager'], tmpfile)
    utils.delete_bulk(tmpfile, True)
    return RetCode.full_redisplay, None

@public
def show_file_info():
    log.debug('Show file information')
    tab = app.pane_active.tab_active
    f = tab.current
    lst = []
    user = environ['USER']
    username = utils.get_user_fullname(user)
    so, host, ver, tmp, arch = uname()
    color = 'view_green_on_black'
    lst.append(('{} v{} executed by {}'.format(LFM_NAME, VERSION, username), color))
    lst.append(('<{}@{}> on {} {} [{}]'.format(user, host, so, ver, arch), color))
    lst.append(('', color))
    color = 'view_red_on_black'
    fileinfo = utils.get_file_info(f.pfile)
    lst.append(('{}: {} ({})'.format(FILETYPES[f.type][1], f.name, fileinfo), color))
    lst.append(('Path: {}'.format(tab.fs.path_str), color))
    lst.append(('Size: {} bytes'.format(f.size), color))
    lst.append(('Mode: {} ({:o})'.format(f.mode_str, f.mode), color))
    lst.append(('Links: {}'.format(f.stat.st_nlink), color))
    lst.append(('User ID: {} ({}) / Group ID: {} ({})'.format(f.owner_str, f.owner, f.group_str, f.group), color))
    lst.append(('Last access: {}'.format(utils.time2str_full(f.stat.st_atime)), color))
    lst.append(('Last modification: {}'.format(utils.time2str_full(f.mtime)), color))
    lst.append(('Last change: {}'.format(utils.time2str_full(f.stat.st_ctime)), color))
    dev = f.stat.st_dev
    lst.append(('Location: {}, {} / Inode: #{:X} ({:X}h:{:X}h)'.format(
        (dev>>8) & 0x00FF, dev & 0x00FF, f.stat.st_ino, dev, f.stat.st_ino), color))
    filename = tab.fs.path_str if tab.fs.vfs else f.pfile
    mountpoint, device, fstype = utils.get_mountpoint_for_file(filename)
    lst.append(('File system: {} on {} ({})'.format(device, mountpoint, fstype), color))
    InternalView('Information about \'{}\''.format(f.name), lst).run()
    return refresh()

@public
def show_filesystems_info():
    log.debug('Show filesystems information')
    try:
        buf = utils.get_filesystems_info()
    except OSError as err:
        DialogError('Cannot show filesystems info:\n{}'.format(err))
        return RetCode.full_redisplay, None
    lbuf = buf.strip().split('\n')
    hdr = lbuf[0].strip()
    lst = [(hdr, 'view_red_on_black'), ('-'*len(hdr), 'view_red_on_black')]
    for l in lbuf[1:]:
        lst.append((l.strip(), 'view_white_on_black'))
    InternalView('Show filesystems info', lst).run()
    return refresh()


########################################################################
##### Un/compress
def do_uncompress_dir(destdir):
    args = [(f.pfile, destdir) for f in app.pane_active.tab_active.selected_or_current]
    if len(args) == 0:
        return RetCode.nothing, None
    log.debug('Uncompress file(s) to \'{}\''.format(destdir))
    app.pane_active.tab_active.selected = []
    st, rets, errs = utils.ProcessFuncLoop('Uncompress file(s)', utils.uncompress_dir, args).run()
    if st == ProcCode.stopped:
        return refresh()
    for a, res, err in zip(args, rets, errs):
        if err:
            log.warning('ERROR: {}'.format(str(err).replace('\n', ' ')))
    return refresh()

@public
def uncompress_dir():
    return do_uncompress_dir(app.pane_active.tab_active.dirname)

@public
def uncompress_dir_other_pane():
    return do_uncompress_dir(app.pane_inactive.tab_active.dirname)

@public
def compress_dir():
    dirs = [d.pfile for d in app.pane_active.tab_active.selected_or_current] # if d.is_dir
    if len(dirs) == 0:
        return RetCode.nothing, None
    compress_fmts = {'g': 'tgz', 'b': 'tbz2', 'x': 'txz', 'l': 'tlz', '4': 'tlz4',
                     't': 'tar', 'z': 'zip', 'r': 'rar', '7': '7z'}
    while True:
        ch = DialogGetKey('Compress directory to...',
                          '.tar.(g)z, .tar.(b)z2, .tar.(x)z, .tar.(l)z,\n.tar.lz(4), .(t)ar, .(z)ip, .(r)ar, .(7)z\n\n'
                          '                Ctrl-C to quit')
        if ch == -1: # Ctrl-C
            return RetCode.full_redisplay, None
        elif chr(ch) in compress_fmts.keys():
            typ = compress_fmts[chr(ch)]
            break
    args = [(d, typ) for d in dirs]
    log.debug('Compress dir(s)')
    app.pane_active.tab_active.selected = []
    st, rets, errs = utils.ProcessFuncLoop('Compress dir(s)', utils.compress_dir, args).run()
    if st == ProcCode.stopped:
        return refresh()
    for a, res, err in zip(args, rets, errs):
        if err:
            log.warning('ERROR: {}'.format(str(err).replace('\n', ' ')))
    return refresh()

@public
def compress_uncompress_file():
    files = [f.pfile for f in app.pane_active.tab_active.selected_or_current] # if f.is_dir
    if len(files) == 0:
        return RetCode.nothing, None
    compress_fmts = {'g': 'gz', 'b': 'bz2', 'x': 'xz', 'l': 'lz', '4': 'lz4'}
    while True:
        ch = DialogGetKey('Un/Compress file(s)',
                          '(g)zip, (b)zip2, (x)z, (l)z, lz(4)\n\n'
                          '   Ctrl-C to quit')
        if ch == -1: # Ctrl-C
            return RetCode.full_redisplay, None
        elif chr(ch) in compress_fmts.keys():
            typ = compress_fmts[chr(ch)]
            break
    args = [(f, typ) for f in files]
    log.debug('Compress or Uncompress file(s)')
    app.pane_active.tab_active.selected = []
    st, rets, errs = utils.ProcessFuncLoop('Compress dir(s)', utils.compress_uncompress_file, args).run()
    if st == ProcCode.stopped:
        return refresh()
    for a, res, err in zip(args, rets, errs):
        if err:
            log.warning('ERROR: {}'.format(str(err).replace('\n', ' ')))
    return refresh()


########################################################################
##### General
@public
def find_grep():
    ans = DialogDoubleEntry('Find files', 'Filename', 'Content', '*', '',
                            history1=app.history['find'][:], history2=app.history['grep'][:],
                            is_files=False).run()
    if ans is None or not ans[0]:
        return RetCode.nothing, None
    fs, pat = ans
    tab = app.pane_active.tab_active
    path = tab.dirname if tab.dirname[-1]==sep else tab.dirname+sep
    if pat:
        log.debug('Find "{}" files with "{}" in {}'.format(fs, pat, path))
        # 1. find . -type f -iname "*.py" -exec grep -EHni PATTERN {} \;
        #    the slowest, 10x
        # 2. find . -type f -iname "*py" -print0 | xargs --null -0 grep -EHni PATTERN
        #    maybe the best choice
        # 3. grep -EHni PATTERN `find . -type f -iname "*.py"`
        #    don't like the `
        # 4. grep -REHni PATTERN --include "*.py" .
        #    the fastest, but maybe they wouldn't work on some old UNIX because of -R, --include
        cmd = '{} -R{}Hn{} "{}" --include "{}"'.format(SYSPROGS['grep'],
                                                       'E' if app.cfg.options.grep_regex else '',
                                                       'i' if app.cfg.options.grep_ignorecase else '',
                                                       pat, fs)
        st, res, err = utils.ProcessCommand('Find files', 'Searching for "{}" in files with "{}" in their name'.format(pat, fs),
                                            cmd, path=path).run()
        if st == -100: # stopped by user
            return RetCode.full_redisplay, None
        if err:
            log.warning('Cannot grep "{}" in "{}" files: {}'.format(pat, fs, str(err).replace('\n', ' ')))
            DialogError('Cannot grep "{}" in "{}" files\n{}'.format(pat, fs, str(err)))
            return RetCode.full_redisplay, None
        app.history.append('find', fs)
        app.history.append('grep', pat)
        if not res.strip():
            DialogError('Did not find "{}" in any file with "{}" in name'.format(pat, fs))
            return RetCode.full_redisplay, None
        entries = sorted([f.strip() for f in res.split('\n') if f.strip()])
        title, entry = 'Find "{}" pattern in "{}" files'.format(pat, fs), ''
    else:
        log.debug('Find "{}" files in {}'.format(fs, path))
        cmd = '{} "{}" -{}name "{}" -print'.format(SYSPROGS['find'], path,
                                                   'i' if app.cfg.options.find_ignorecase else '', fs)
        st, res, err = utils.ProcessCommand('Find files', 'Searching for files with "{}" in their name'.format(fs),
                                            cmd, path=path).run()
        if st == -100: # stopped by user
            return RetCode.full_redisplay, None
        if err:
            log.warning('Cannot find "{}" files: {}'.format(fs, str(err).replace('\n', ' ')))
            DialogError('Cannot find "{}" files\n{}'.format(fs, str(err)))
            return RetCode.full_redisplay, None
        app.history.append('find', fs)
        if not res.strip():
            DialogError('Did not find any file with "{}" in name'.format(fs))
            return RetCode.full_redisplay, None
        entries = sorted([f.strip().replace(path, '') for f in res.split('\n') if f.strip() and f!=path])
        title, entry = 'Find "{}" files'.format(fs), ''
    # common
    while True:
        ans, entry = DialogFindGrep(title, entries, entry).run()
        if pat:
            try:
                filename, lineno, _ = entry.split(':', 2)
            except ValueError: # entry = "-1 - Binary file .hg/store/data/lfm/utils.py.i matches"
                filename = entry
                if filename.startswith('Binary file'):
                    filename = filename[11:]
                if filename.endswith('matches'):
                    filename = filename[:-7]
                filename, lineno = filename.strip(), 0
        else:
            filename = entry
        pfilename = join(path, filename)
        if ans == 0:             # goto file
            tab.goto_folder(join(tab.fs.path_str, dirname(filename)))
            tab.i = tab.fs.pos(basename(filename))
            tab.fix_limits()
            return RetCode.full_redisplay, None
        elif ans == 1:           # panelize
            files = list()
            for f in entries:
                if f.startswith('Binary file'):
                    f = f[11:]
                if f.endswith('matches'):
                    f = f[:-7]
                f = f.split(':', 1)[0].strip() # FIXME: won't work if filename contains ':' chars
                if f not in files:
                    files.append(f)
            tab.goto_folder(tab.fs.path_str, files=files)
            return RetCode.full_redisplay, None
        elif ans == 2:           # view
            cmd = app.cfg.programs['pager']
            cmd = '{} +{}'.format(cmd, lineno) if pat else cmd
            utils.run_on_current_file(cmd, pfilename)
        elif ans == 3:           # edit
            cmd = app.cfg.programs['editor']
            cmd = '{} +{}'.format(cmd, lineno) if pat else cmd
            utils.run_on_current_file(cmd, pfilename)
        elif ans == 4:           # do something on file
            cmd = DialogEntry('Execute command on file(s)', 'Enter command', '',
                              history=app.history['exec'][:], is_files=False).run()
            if not cmd:
                continue
            app.history.append('exec', cmd)
            utils.run_on_current_file(cmd, pfilename)
        else:
            return refresh()

@public
def show_tree():
    tab = app.pane_active.tab_active
    log.debug('Tree in "{}"'.format(tab.dirname))
    res = TreeView(tab.dirname).run()
    if res != -1:
        tab.goto_folder(res)
    return RetCode.full_redisplay, None

@public
def main_menu():
    menu = ['/    Find/grep file(s)',
            '#    Show directories size',
            's    Sort files',
            't    Tree',
            'f    Show filesystems info',
            'o    Open shell',
            'c    Edit configuration',
            'k    Edit keys',
            'e    Edit theme',
            'h    Delete history']
    ret = SelectItem('Main Menu', menu, min_height=True).run()
    if ret != -1:
        ch = ret[0]
        if ch == '/':
            return find_grep()
        elif ch == '#':
            return show_dirs_size()
        elif ch == 's':
            return sort_files()
        elif ch == 't':
            return show_tree()
        elif ch == 'f':
            return show_filesystems_info()
        elif ch == 'o':
            return open_shell()
        elif ch == 'c':
            utils.run_on_current_file(app.cfg.programs['editor'], CONFIG_FILE)
            from ui import init_config
            app.cfg = init_config(False)
            return refresh()
        elif ch == 'k':
            utils.run_on_current_file(app.cfg.programs['editor'], KEYS_FILE)
            app.init_keys()
            return refresh()
        elif ch == 'e':
            utils.run_on_current_file(app.cfg.programs['editor'], THEME_FILE)
            app.init_colors()
            return refresh()
        elif ch == 'h':
            try:
                app.history.delete()
            except Exception as e:
                DialogError('Cannot save history file\n{}'.format(str(e)))
            return RetCode.nothing, None
        return RetCode.nothing, None
    else:
        return RetCode.nothing, None

@public
def file_menu():
    menu = ['@    Exec on file',
            'i    File info',
            'p    Change file permissions',
            'o    Change file owner and/or group',
            'a    Backup file(s)',
            'd    Diff file with backup',
            # 'l    Folder comparation',
            # 'y    Folder synchronization',
            'z    Compress/uncompress file(s)…',
            'x    Uncompress file',
            'u    Uncompress file in other panel',
            'c    Compress directory to format…']
    ret = SelectItem('File Menu', menu, min_height=True).run()
    if ret != -1:
        ch = ret[0]
        if ch == '@':
            return exec_on_file()
        elif ch == 'i':
            return show_file_info()
        elif ch == 'p':
            return change_perms()
        elif ch == 'o':
            return change_owner()
        elif ch == 'a':
            return backup_file()
        elif ch == 'd':
            return diff_file_with_backup()
        elif ch == 'l':
            pass
        elif ch == 'y':
            pass
        elif ch == 'z':
            return compress_uncompress_file()
        elif ch == 'x':
            return uncompress_dir()
        elif ch == 'u':
            return uncompress_dir_other_pane()
        elif ch == 'c':
            return compress_dir()
        return RetCode.nothing, None
    else:
        return RetCode.nothing, None

@public
def help_menu():
    menu = ['r    Readme',
            'n    News',
            't    Todo',
            'l    License',
            'k    Key bindings']
    ret = SelectItem('Help Menu', menu, min_height=True).run()
    if ret != -1:
        if ret[0] == 'k':
            from preferences import dump_keys_to_file
            dump_keys_to_file(app.keys)
            filename = DUMP_KEYS_FILE
            utils.run_on_current_file(app.cfg.programs['pager'], filename)
        else:
            docfile = {'r': 'README', 'n': 'NEWS', 't': 'TODO', 'l': 'COPYING'}.get(ret[0])
            try:
                filename = pkg_resources.resource_filename('lfm', 'doc/' + docfile)
                utils.run_on_current_file(app.cfg.programs['pager'], filename)
            except NotImplementedError:
                buf = str(pkg_resources.resource_string('lfm', 'doc/' + docfile), 'UTF-8')
                InternalView(docfile, [(l, 'view_white_on_black') for l in buf.splitlines()], center=False).run()
        return refresh()
    else:
        return RetCode.nothing, None

@public
def toggle_powercli():
    app.cli.toggle()
    app.display_statusbar_or_powercli()
    return refresh()

@public
def open_shell():
    utils.run_shell(app.cfg.programs['shell'], app.pane_active.tab_active.dirname)
    return refresh()

@public
def quit_chdir():
    return do_quit(chdir=True)

@public
def quit_nochdir():
    return do_quit(chdir=False)

def do_quit(chdir=True):
    if app.cfg.confirmations.quit:
        ch = DialogConfirm('Last File Manager', 'Quit Last File Manager?', 1)
        if ch == 0:
            return RetCode.full_redisplay, None
    fs = app.pane_active.tab_active.fs
    path = dirname(fs.base) if fs.vfs else fs.pdir
    for tab in app.pane1.tabs + app.pane2.tabs:
        tab.close()
    return RetCode.quit_chdir if chdir else RetCode.quit_nochdir, path


########################################################################
