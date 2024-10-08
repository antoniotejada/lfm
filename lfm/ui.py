# -*- coding: utf-8 -*-


import errno
import curses
from os import getuid, pardir, statvfs
from os.path import basename, dirname, exists, join, split
from datetime import datetime

from preferences import Config, load_colortheme, load_keys, History
from folders import new_folder, is_delete_oldfs
from utils import num2str, size2str, length, text2wrap, get_realpath, run_in_background, run_shell, ProcessCommand
from ui_widgets import display_scrollbar, DialogError, DialogConfirm, EntryLine, InternalView
from key_defs import key_bin2str
from actions import do
from common import *


########################################################################
##### Definitions and module variables
colors_table = {'black': curses.COLOR_BLACK,
                'blue': curses.COLOR_BLUE,
                'cyan': curses.COLOR_CYAN,
                'green': curses.COLOR_GREEN,
                'magenta': curses.COLOR_MAGENTA,
                'red': curses.COLOR_RED,
                'white': curses.COLOR_WHITE,
                'yellow': curses.COLOR_YELLOW}

##### Module variables
app, cfg = None, None


########################################################################
##### Main window
class UI:
    def __init__(self, cfg, win, paths1, paths2):
        log.debug('Create UI')
        self.cfg = cfg
        self.win = win
        self.w = self.h = 0
        self.CLR = dict()
        self.init_curses()
        self.init_panes(paths1, paths2)
        self.statusbar = StatusBar(self)
        self.cli = PowerCLI(self)
        self.resize()

        # Restoring saved state may put the focused file outside the display,
        # call fix_limits to put the focus in view (otherwise curses will crash
        # trying to addstr outside the screen).
        # This needs to be done after the app has been initialized and resized
        # so all the necessary variables (eg app, .fh) are available

        for pane in [self.pane1, self.pane2]:
            for tab in pane.tabs:
                # The code at resize does this too
                try:
                    tab.fix_limits()
                except AttributeError:
                    pass
             
    def init_curses(self):
        curses.cbreak()
        curses.raw()
        self.win.leaveok(1)
        self.win.keypad(1)
        curses.curs_set(0)
        self.init_colors()
        self.init_keys()
        self.init_history()
        # HACK: ugly hack to inject main app in that module
        import ui_widgets
        ui_widgets.app = self

    def init_colors(self):
        if curses.has_colors():
            try:
                colors = load_colortheme()
            except FileNotFoundError:
                raise
            for i, col in enumerate(colors.keys()):
                fg, bg = colors[col]
                light = fg.endswith('*')
                fg = fg[:-1] if fg.endswith('*') else fg
                bg = bg[:-1] if bg.endswith('*') else bg
                color_fg, color_bg = colors_table[fg], colors_table[bg]
                curses.init_pair(i+1, color_fg, color_bg)
                self.CLR[col] = curses.color_pair(i+1)
                if light:
                    self.CLR[col] = self.CLR[col] | curses.A_BOLD
        else:
            for col in COLOR_ITEMS:
                self.CLR[col] = curses.color_pair(0)

    def init_keys(self):
        try:
            self.keys = load_keys()
        except FileNotFoundError:
            raise

    def init_history(self):
        self.history = History()
        if self.cfg.options.save_history_at_exit:
            try:
                self.history.load()
            except Exception as e:
                return

    def init_panes(self, paths1, paths2):
        # XXX Missing honoring paths1 and paths2 over stored configuration if
        #     not default?
        log.debug("init_panes %s %s", paths1, paths2)
        
        # Note that restoring the panel configuration needs to be robust to
        # paths or focused/selected files no longer existing, that's the reason
        # why names are stored instead of indices
        if cfg.options.save_panel_state_at_exit and (len(cfg.options.panel_state) != 0):
            # The configuration writer stores a json.dumps, and the loader does
            # exec("{} = {}".format(field, value), of that dumps converts json
            # to a Python dict because the json dumps is compatible with Python
            # dict, so no need to json.loads
            panel_state = cfg.options.panel_state
            panes = []
            for pane_config in panel_state["panels"]:
                log.debug("Restoring pane %s", pane_config)
                paths = [tab["path"] for tab in pane_config["tabs"]]

                # Do a two-step creation in case any of the paths doesn't exist
                # the exception can be trapped and left with default path
                pane = Pane(self, ["."] * len(paths))

                for path, tab in zip(paths, pane.tabs):
                    log.debug("Restoring path %r", path)
                    try:
                        tab.goto_folder(path)
                    except:
                        # XXX Needs to skip initialization below
                        log.warning("Cannot restore path %r, using . instead", path)
                
                # Make the proper tab active
                pane.tab_active = pane.tabs[pane_config["active_tab"]]

                for tab, tab_config in zip(pane.tabs, pane_config["tabs"]):
                    log.debug("Restoring tab %s", tab_config)
                    # focus_file can't be called because it calls fix_limits()
                    # which requires app.pane_active but app hasn't been
                    # set yet
                    i = tab.fs.pos(tab_config["focused_file"])
                    if i != -1:
                        log.debug("Restoring focus %d:%r", i, tab_config["focused_file"])
                        # This crashes when i is out of the screen, needs to
                        # force a redraw
                        # XXX Disabled for now 
                        # tab.i = i

                    for filename in tab_config["selected_files"]:
                        f = tab.fs.lookup(filename)
                        if f:
                            log.debug("Restoring selection %r", filename)
                            tab.selected.append(f)

                    # History is on the second revision of the config, ignore
                    # if not present
                    if ("history_mru" in tab_config):
                        log.debug("Restoring history %r", tab_config["history"])
                        tab.history = tab_config["history"]
                        tab.next_history_index = tab_config["next_history_index"]
                        log.debug("Restoring history_mru %r", tab_config["history_mru"])
                        tab.history_mru = tab_config["history_mru"]
                        
                panes.append(pane)

            self.pane1, self.pane2 = panes
            self.focus_pane(panes[panel_state["active_panel"]])
            
        else:
            self.pane1 = Pane(self, paths1)
            self.pane2 = Pane(self, paths2)
            self.focus_pane(self.pane1)


    def focus_pane(self, pane):
        pane.focus = True
        otherpane = self.pane2 if pane==self.pane1 else self.pane1
        otherpane.focus = False

    @property
    def pane_active(self):
        return self.pane1 if self.pane1.focus else self.pane2

    @property
    def pane_inactive(self):
        return self.pane2 if self.pane1.focus else self.pane1

    def resize(self):
        h, w = self.win.getmaxyx()
        log.debug('Resize UI: w={}, h={}'.format(w, h))
        self.h, self.w = h, w
        if w == 0 or h == 2:
            return
        if w < MIN_COLUMNS:
            raise LFMTerminalTooNarrow
        self.win.resize(self.h, self.w)
        if self.pane1.mode == PaneMode.full:
            self.pane1.resize(0, 0, h-1, w)
        elif self.pane1.mode == PaneMode.hidden:
            self.pane1.resize(0, 0, h-1, w)
        else:
            self.pane1.resize(0, 0, h-1, w//2)
        if self.pane2.mode == PaneMode.full:
            self.pane2.resize(0, 0, h-1, w)
        elif self.pane2.mode == PaneMode.hidden:
            self.pane2.resize(0, 0, h-1, w)
        else:
            self.pane2.resize(0, w//2, h-1, w//2)
        self.statusbar.resize(h-1, w)
        self.cli.resize(h-1, w)
        self.display()

    def clear_screen(self):
        log.debug('Clear screen')
        self.pane1.clear()
        self.pane2.clear()
        self.statusbar.clear()
        curses.doupdate()

    def display(self):
        log.debug('Display UI')
        self.pane1.display()
        self.pane2.display()
        self.display_statusbar_or_powercli()
        self.win.noutrefresh()
        curses.doupdate()

    def display_half(self):
        log.debug('Display half UI')
        self.pane_active.display()
        self.display_statusbar_or_powercli()
        self.win.noutrefresh()
        curses.doupdate()

    def display_statusbar_or_powercli(self):
        if self.cli.visible:
            self.cli.display()
        else:
            self.statusbar.display()

    def run(self):
        self.display()
        while True:
            ret, extra = self.get_key()
            if ret == RetCode.quit_chdir:
                return extra
            elif ret == RetCode.quit_nochdir:
                return None
            elif ret == RetCode.fix_limits:
                self.pane_active.tab_active.fix_limits()
                self.display_half()
            elif ret == RetCode.full_redisplay:
                self.display()
            elif ret == RetCode.half_redisplay:
                self.display_half()

    def get_key(self):
        self.win.nodelay(False)
        km = KeyModifier.none
        key = self.win.getch()
        log.debug("First key received %d", key)
        if key == 27: # Esc or Alt
            km = KeyModifier.alt
            self.win.nodelay(True)
            key = self.win.getch()
            log.debug("Second key received %d", key)
            if key == -1: # Esc
                km, key = KeyModifier.none, 27
        if key == curses.KEY_RESIZE:
            self.resize()
            return RetCode.full_redisplay, None
        key_str = key_bin2str((km, key))
        action = self.keys[(km, key)] if (km, key) in self.keys else None
        log.debug('Key pressed: {0} [{1:#x}] => {2} => {3} -> {4}'
                      .format(curses.keyname(key), key, str((km, key)), key_str, action if action else '<undefined>'))
        return do(self, action) if action else (RetCode.nothing, None)


########################################################################
##### Pane
class Pane:
    def __init__(self, ui, paths):
        log.debug('Create Pane')
        self.ui = ui
        self.mode = PaneMode.half
        self.focus = False
        self.tabs = [Tab(p) for p in paths[:MAX_TABS]]
        self.tab_active = self.tabs[0]
        # ui
        try:
            self.win_tabs = curses.newwin(1, 1, 0, 0)
            self.win = curses.newwin(10, 10, 0, 0)
        except curses.error:
            raise
        self.win.bkgd(self.ui.CLR['pane_inactive'])

    def resize(self, y0, x0, h, w):
        log.debug('Resize Pane: x0={}, y0={}, w={}, h={}'.format(x0, y0, h, w))
        self.x0, self.y0 = x0, y0
        self.w, self.h = w, h
        self.fh = h-4 if self.mode==PaneMode.half else h-1
        self.win_tabs.resize(2, w)
        self.win_tabs.mvwin(y0, x0)
        self.win.resize(h-1, w)
        self.win.mvwin(y0+1, x0)
        try:
            for tab in self.tabs:
                tab.fix_limits()
        except AttributeError:
            pass

    def clear(self):
        self.win.erase()
        self.win_tabs.erase()
        self.win.noutrefresh()
        self.win_tabs.noutrefresh()

    def display(self):
        log.debug('Display Pane')
        if self.mode == PaneMode.hidden:
            return
        tab = self.tab_active
        CLR = self.ui.CLR
        # tabs
        self.win_tabs.erase()
        self.win_tabs.addstr(0, 0, ' '*self.w, CLR['header'])
        wtab = self.w // MAX_TABS
        for i, t in enumerate(self.tabs):
            pathname = '/' if t.fs.basename=='' else t.fs.basename
            buf = '[' + text2wrap(pathname, wtab-2, start_pct=.5) + ']'
            self.win_tabs.addstr(0, wtab*i, buf, CLR['tab_active' if t==tab else 'tab_inactive'])

        # Current tab filesystem size
        filename = tab.fs.base_filename if tab.fs.vfs else tab.fs.path_str
        filesystem_info = statvfs(filename)
        free_bytes = filesystem_info.f_bavail * filesystem_info.f_frsize
        total_bytes = filesystem_info.f_blocks * filesystem_info.f_frsize
        buf = " {} of {} free".format(size2str(free_bytes), size2str(total_bytes))
        self.win_tabs.addstr(0, wtab*(len(self.tabs)), buf, CLR['tab_active'])

        # contens:
        self.win.erase()
        if self.mode == PaneMode.half:
            self.__display_panehalf(tab, CLR)
        elif self.mode == PaneMode.full:
            self.__display_panefull(tab, CLR)
        # refresh
        self.win_tabs.noutrefresh()
        self.win.noutrefresh()

    def __decorate_header(self, tab, header, sort_type):
        # XXX Missing decorations for extension, path
        # XXX Missing decorator in full pane
        up_arrow = "\u2191"
        down_arrow = "\u2193"
        prefix = ""
        if (tab.fs.cfg.sort_type == sort_type):
            prefix = down_arrow if (tab.fs.cfg.sort_reverse) else up_arrow

        return prefix + header

    def __display_panehalf(self, tab, CLR):
        if self.focus:
            attr, attr_path = CLR['pane_active'], CLR['pane_header_path']
        else:
            attr, attr_path = CLR['pane_inactive'], CLR['pane_inactive']
        self.win.attrset(attr)
        # box
        self.win.box()
        self.win.addstr(0, 2, text2wrap(tab.fs.path_str, self.w-5, start_pct=.33, fill=False), attr_path)
        col2 = self.w - 14 # sep between size and date: w - len(mtime) - 2x borders
        col1 = col2 - 8    # sep between filename and size: col2 - len(size) - 1x border
        self.win.addstr(1, 1, self.__decorate_header(tab, 'Name', SortType.byName).center(col1-2)[:col1-2], CLR['pane_header_titles'])
        self.win.addstr(1, col1+2, self.__decorate_header(tab, 'Size', SortType.bySize), CLR['pane_header_titles'])
        self.win.addstr(1, col2+5, self.__decorate_header(tab, 'Date', SortType.byMTime), CLR['pane_header_titles'])
        if tab.fs.cfg.show_dotfiles:
            self.win.addstr(0, self.w-3, '·', attr)
        if tab.fs.cfg.filters:
            self.win.addstr(0, self.w-2, 'f', attr)
        # files
        fmt = [('type', 1), ('name', col1-2), ('sep', 1), ('size', 7), ('sep', 1), ('mtime', 12)]
        for i in range(self.h-4):
            if i+tab.a >= len(tab.fs):
                break
            f = tab.fs[tab.a+i]
            if self.focus and tab.i == tab.a+i:
                attr = 'cursor_selected' if f in tab.selected else 'cursor'
            else:
                attr = 'selected_files' if f in tab.selected else 'files_' + f.get_type_from_ext(self.ui.cfg.files_ext)
            self.win.addstr(2+i, 1, f.format(fmt), CLR[attr])
        # vertical separators
        self.win.vline(1, col1, curses.ACS_VLINE, self.h-3)
        self.win.vline(1, col2, curses.ACS_VLINE, self.h-3)
        if self.focus:
            self.win.vline(tab.i-tab.a+2, col1, curses.ACS_VLINE, 1, CLR['cursor'])
            self.win.vline(tab.i-tab.a+2, col2, curses.ACS_VLINE, 1, CLR['cursor'])
        # scrollbar
        display_scrollbar(self.win, 2, self.w-1, self.h-4, len(tab.fs), tab.i, tab.a)

    def __display_panefull(self, tab, CLR):
        self.win.attrset(CLR['pane_inactive'])
        # files
        col = self.w - 64 # 1x border
        fmt = [('type', 1), ('mode', 9), ('sep', 2), ('owner', 10), ('sep', 2), ('group', 10), ('sep', 2),
               ('size', 7), ('sep', 2), ('mtime2', 16), ('sep', 2), ('name', col)]
        for i in range(self.h-1):
            if i+tab.a >= len(tab.fs):
                break
            f = tab.fs[tab.a+i]
            if tab.i == tab.a+i:
                attr = 'cursor_selected' if f in tab.selected else 'cursor'
            else:
                attr = 'selected_files' if f in tab.selected else 'files_' + f.get_type_from_ext(self.ui.cfg.files_ext)
            self.win.addstr(i, 0, f.format(fmt, sep=' '), CLR[attr])
        # scrollbar
        display_scrollbar(self.win, 0, self.w-1, self.h-1, len(tab.fs), tab.i, tab.a)

    def change_mode(self, newmode):
        otherpane = self.ui.pane2 if self==self.ui.pane1 else self.ui.pane1
        if self.mode == PaneMode.full:
            otherpane.mode = PaneMode.half
        if newmode == PaneMode.full:
            otherpane.mode = PaneMode.hidden
        self.mode = newmode
        self.ui.resize()

    def refresh(self):
        for tab in self.tabs:
            tab.refresh()

    def insert_new_tab(self, path, lefttab):
        newtab = Tab(path)
        self.tabs.insert(self.tabs.index(lefttab)+1, newtab)
        self.tab_active = newtab

    def close_tab(self, tab):
        idx = self.tabs.index(tab)
        tab.close()
        self.tabs.remove(tab)
        self.tab_active = self.tabs[idx-1]


########################################################################
##### Tab
class Tab:
    def __init__(self, path):
        self.fs = None
        self.history = []
        self.history_mru = []
        self.next_history_index = 0
        self.goto_folder(path)

    def __check_rebuild(self):
        if self.fs.vfs:
            rebuild = 1 if app.cfg.options.rebuild_vfs is True else 0
            if app.cfg.confirmations.ask_rebuild_vfs:
                rebuild = DialogConfirm('Rebuild vfs file', self.fs.base_filename, rebuild)
            return rebuild==1
        else:
            return False

    def close(self):
        self.fs.exit(all_levels=True, rebuild=self.__check_rebuild())

    def goto_history(self, entry_i):
        if (0 <= entry_i < len(self.history)):
            self.next_history_index = entry_i
            self.goto_folder(self.history[self.next_history_index], delete_vfs_tree=True)
            
            # If the next history entry is a file in this directory, focus on
            # that file.
            if (self.next_history_index < len(self.history)):
                d, b = split(self.history[self.next_history_index])
                if (self.fs.path_str == d):
                    self.focus_file(b)

    def goto_folder(self, path, delete_vfs_tree=False, files=None):
        """Called when chdir to a new path"""
        oldfs = self.fs
        try:
            if files: # search vfs
                self.fs = new_folder(path, self.fs, files=files)
            else:
                rebuild = self.__check_rebuild() if is_delete_oldfs(path, self.fs) else False
                self.fs = new_folder(path, self.fs, rebuild_if_exit=rebuild)
            self.fs.cfg.filters = oldfs.cfg.filters if oldfs else ''
        except PermissionError as e:
            log.warning('ERROR: cannot enter in {}: {}'.format(path, str(e)))
            app.display()
            DialogError('Cannot chdir {}\n{}'.format(path, str(e).split(':', 1)[0]))
            return
        except UserWarning as e:
            log.warning('ERROR: cannot enter in {}: {}'.format(path, str(e)))
            app.display()
            DialogError('Cannot chdir {}\n{}'.format(path, str(e)))
            return
        except FileNotFoundError:
            log.warning('ERROR: cannot enter in {}: invalid directory?'.format(path))
            app.display()
            DialogError('Cannot chdir {}\nInvalid directory?'.format(path))
            return
        if delete_vfs_tree:
            oldfs.exit(all_levels=True)
        self.a = self.i = 0
        self.selected = []
        self.refresh(first=True)
        newpath = self.fs.path_str
        if newpath and VFS_STRING not in newpath:
            # Append to MRU
            try:
                self.history_mru.remove(newpath)
            except ValueError: 
                pass
            self.history_mru.append(newpath)
            # The history index points to the next entry to be filled in, if the
            # entry is the same this means it's navigating the history,
            # otherwise it's creating new history
            if (self.next_history_index < len(self.history)):
                if (self.history[self.next_history_index] != newpath):
                    # Trim the history
                    self.history = self.history[:self.next_history_index]
                    self.history.append(newpath)
            else:
                self.history.append(newpath)
            self.next_history_index += 1
            
            # Only keep the HISTORY_MAX last entries
            self.next_history_index -= max(0, (len(self.history) - HISTORY_MAX))
            self.history = self.history[-HISTORY_MAX:]
            self.history_mru = self.history_mru[-HISTORY_MAX:]

    def reload(self):
        """Called when contents have changed"""
        try:
            self.fs.load()
        except OSError as err:
            if err.errno == errno.ENOENT: # dir deleted?
                pardir = self.fs.pdir
                while not exists(pardir):
                    pardir = dirname(pardir)
                self.goto_folder(pardir)
        self.refresh()

    def refresh(self, first=False):
        """Called when config or filters have changed"""
        if not first:
            oldi = self.i
            oldf = self.fs[self.i].name
            oldselected = [f.name for f in self.selected]
        self.fs.cfg.fill_with_app(cfg)
        self.fs.refresh()
        self.n = len(self.fs)
        i = 0 if first else self.fs.pos(oldf)
        self.i = oldi if i==-1 else i
        self.a = divmod(self.i, self.n)[0] * self.n
        if not first:
            self.fix_limits()
            self.selected = list(filter(None, [self.fs.lookup(f) for f in oldselected]))

    def fix_limits(self):
        self.i = max(0, min(self.i, self.n-1))
        self.a = int(self.i//app.pane_active.fh * app.pane_active.fh)

    def focus_file(self, filename):
        log.debug("focus_file %r %s", filename, self.fs.get_filenames)
        i = self.fs.pos(filename)
        if i != -1:
            self.i = i
            self.fix_limits()

    @property
    def dirname(self):
        return self.fs.pdir

    @property
    def current_filename(self):
        return self.fs[self.i].name

    @property
    def current_filename_full(self):
        return join(self.fs.pdir, self.fs[self.i].name)

    @property
    def current(self):
        return self.fs[self.i]

    @property
    def selected_or_current(self):
        if len(self.selected) == 0:
            cur = self.fs[self.i]
            return list() if cur.name==pardir else [cur]
        else:
            return self.selected

    @property
    def selected_or_current2(self):
        return self.selected if self.selected else [self.fs[self.i]]


########################################################################
##### Statusbar
class StatusBar:
    def __init__(self, ui):
        log.debug('Create StatusBar')
        self.ui = ui
        try:
            self.win = curses.newwin(1, 10, 1, 0)
        except curses.error:
            raise
        self.win.bkgd(self.ui.CLR['statusbar'])

    def resize(self, y0, w):
        log.debug('Resize StatusBar: y0={}, w={}'.format(y0, w))
        self.y0, self.w = y0, w
        self.win.resize(1, w)
        self.win.mvwin(y0, 0)

    def clear(self):
        self.win.erase()
        self.win.noutrefresh()

    def display(self):
        log.debug('Display StatusBar')
        self.win.erase()
        tab = self.ui.pane_active.tab_active
        # XXX Ignore dirs in sice calculation unless they have been resolved?
        dir_size = sum([f.size for f in tab.fs])
        if len(tab.selected) > 0:
            if self.w >= 45:
                size = sum([f.size for f in tab.selected])
                self.win.addstr('    %s / %s in %d / %d files' % (size2str(size), size2str(dir_size), len(tab.selected), tab.n))
        else:
            if self.w >= 80:
                s = 'File: %4d of %-4d %s' % (tab.i+1, tab.n, size2str(dir_size))
                if tab.fs.cfg.filters:
                    s+= '  [%d filtered]' % tab.fs.nfiltered
                self.win.addstr(s)
                filename = text2wrap(get_realpath(tab), self.w-20-len(s), fill=False)
                self.win.addstr(0, len(s)+4, 'Path: ' + filename)
        if self.w > 10:
            try:
                self.win.addstr(0, self.w-8, 'F1=Help')
            except:
                pass
        self.win.refresh()

    def show_message(self, text):
        self.win.erase()
        self.win.addstr(0, 1, text2wrap(text, self.w-2, fill=False))
        self.win.refresh()


########################################################################
##### PowerCLI
class PowerCLI:
    RUN_NORMAL, RUN_BACKGROUND, RUN_NEEDCURSESWIN = range(3)

    def __init__(self, ui):
        log.debug('Create PowerCLI')
        self.ui = ui
        self.visible = self.running = False
        try:
            self.win = curses.newwin(1, 10, 1, 0)
        except curses.error:
            raise
        self.win.bkgd(self.ui.CLR['powercli_text'])
        self.entry, self.text, self.pos = None, '', 0

    def toggle(self):
        if self.visible:
            self.visible = self.running = False
        else:
            self.visible, self.running = True, False

    def resize(self, y0, w):
        log.debug('Resize PowerCLI: y0={}, w={}'.format(y0, w))
        self.y0, self.w = y0, w
        self.win.resize(1, w)
        self.win.mvwin(y0, 0)

    def display(self):
        if self.running:
            return
        log.debug('Display PowerCLI')
        tab = self.ui.pane_active.tab_active
        self.win.erase()
        path = text2wrap(tab.fs.path_str, self.ui.w//6, start_pct=0, fill=False)
        prompt = '[{}]{} '.format(path, '#' if getuid()==0 else '$')
        lprompt = length(prompt)
        self.win.addstr(0, 0, prompt, self.ui.CLR['powercli_prompt'])
        self.win.noutrefresh()
        curses.curs_set(1)
        self.running = True
        self.entry = EntryLine(self, self.w-lprompt, self.y0, lprompt, self.text,
                               history=self.ui.history['cli'][:], is_files=True, cli=True)
        self.entry.pos = self.pos
        self.entry.show()
        ans = self.entry.manage_keys()
        if ans == -1:           # Ctrl-C
            cmd, self.text, self.pos = None, '', 0
        elif ans == -2:           # Ctrl-X
            cmd, self.text, self.pos = None, self.entry.text, self.entry.pos
        elif ans == 10:         # return
            cmd, self.text, self.pos = self.entry.text.strip(), '', 0
            if cmd:
                self.execute(cmd)
        else:
            raise ValueError
        curses.curs_set(0)
        self.visible = False
        self.ui.display()

    def execute(self, cmd):
        self.ui.history.append('cli', cmd)
        log.debug('PowerCLI Execute: |{}|'.format(cmd))
        selected = [f for f in self.ui.pane_active.tab_active.selected_or_current2]
        if cmd[-1] == '&':
            mode, cmd = PowerCLI.RUN_BACKGROUND, cmd[:-1].strip()
        elif cmd[-1] == '$':
            mode, cmd = PowerCLI.RUN_NEEDCURSESWIN, cmd[:-1].strip()
        else:
            mode = PowerCLI.RUN_NORMAL
        for f in selected:
            try:
                cmd2 = self.__replace_cli(cmd, f)
            except Exception as err:
                log.warning('Cannot execute PowerCLI command: {}\n{}'.format(cmd2, str(err)))
                DialogError('Cannot execute PowerCLI command:\n  {}\n\n{}'.format(cmd2, str(err)))
            else:
                if self.__run(cmd2, self.ui.pane_active.tab_active.dirname, mode) == -1:
                    self.ui.display()
                    if DialogConfirm('Error running PowerCLI', 'Do you want to stop now?') == 1:
                        break
        self.ui.pane_active.tab_active.selected = []

    def __replace_cli(self, cmd, f):
        # prepare variables
        tab = self.ui.pane_active.tab_active
        filename = f.name
        cur_directory = tab.dirname
        other_directory = self.ui.pane_inactive.tab_active.dirname
        fullpath = f.pfile
        filename_noext = f.name_noext
        ext = f.ext
        all_selected = [s.name for s in tab.selected]
        all_files = [elm for elm in tab.fs.get_filenames() if elm is not pardir]
        try:
            selection_idx = all_selected.index(filename)+1
        except ValueError:
            selection_idx = 0
        tm = datetime.fromtimestamp(f.mtime)
        ta = datetime.fromtimestamp(f.stat.st_atime)
        tc = datetime.fromtimestamp(f.stat.st_ctime)
        tnow = datetime.now()
        dm = tm.date()
        da = ta.date()
        dc = tc.date()
        dnow = tnow.date()
        # conversion table
        lcls = {'f': filename, 'v': filename, 'F': fullpath,
                'E': filename_noext, 'e': ext,
                'p': cur_directory, 'o': other_directory,
                's': all_selected, 'a': all_files, 'i': selection_idx,
                'dm': dm, 'da': da, 'dc': dc, 'dn': dnow,
                'tm': tm, 'ta': ta, 'tc': tc, 'tn': tnow}
        for k, bmk in self.ui.cfg.bookmarks.items():
            lcls['b{}'.format(k)] = bmk
        # and replace, first python code, and then variables
        cmd = self.__replace_python(cmd, lcls)
        cmd = self.__replace_variables(cmd, lcls)
        return cmd

    def __replace_python(self, cmd, lcls):
        lcls = dict([('__lfm_{}'.format(k), v) for k, v in lcls.items()])
        # get chunks
        chunks, st = {}, 0
        while True:
            i = cmd.find('{', st)
            if i == -1:
                break
            j = cmd.find('}', i+1)
            if j == -1:
                raise SyntaxError('{ at %d position has not ending }' % i)
            else:
                chunks[(i+1, j)] = cmd[i+1:j].replace('$', '__lfm_')
                st = j + 1
        # evaluate
        if chunks == {}:
            return cmd
        buf, st = '', 0
        for i, j in sorted(chunks.keys()):
            buf += cmd[st:i-1]
            try:
                translated = eval(chunks[(i, j)], {}, lcls)
            except Exception as err:
                raise SyntaxError(str(err).replace('__lfm_', '$'))
            buf += translated
            st = j+1
        buf += cmd[st:]
        return buf

    def __replace_variables(self, cmd, lcls):
        for k, v in lcls.items():
            if k in ('i', ):
                cmd = cmd.replace('${}'.format(k), str(v))
            elif k in ('dm', 'da', 'dc', 'dn', 'tm', 'ta', 'tc', 'tn'):
                cmd = cmd.replace('${}'.format(k), str(v).split('.')[0])
            elif k in ('s', 'a'):
                cmd = cmd.replace('${}'.format(k), ' '.join(['"{}"'.format(f) for f in v]))
            else:
                cmd = cmd.replace('${}'.format(k), v)
        return cmd

    def __run(self, cmd, path, mode):
        curses.curs_set(0)
        if mode == PowerCLI.RUN_NEEDCURSESWIN:
            run_shell(cmd, path)
            st, msg, err = 0, '', ''
        elif mode == PowerCLI.RUN_BACKGROUND:
            run_in_background(cmd, path)
            st, msg, err = 0, '', ''
        else: # PowerCLI.RUN_NORMAL
            st, msg, err = ProcessCommand('Executing PowerCLI', cmd, cmd, path).run()
        if err:
            log.warning('Error running PowerCLI command: {}\n{}'.format(cmd, str(err)))
            DialogError('Error running PowerCLI command:\n  {}\n\n{}'.format(cmd, str(err)))
        if st != -100 and msg:
            if self.ui.cfg.options.show_output_after_exec:
                if DialogConfirm('Executing PowerCLI', 'Show output?', 1) == 1:
                    lst = [(l, 'view_white_on_black') for l in msg.split('\n')]
                    InternalView('Output of: {}'.format(cmd), lst, center=False).run()
        return st

########################################################################
##### Main
def init_config(use_wide_chars):
    global cfg
    cfg = Config()
    cfg.load()
    # HACK: ugly hack to inject option in that module
    import utils
    utils.use_wide_chars = True if use_wide_chars else cfg.options.use_wide_chars
    log.info('Support wide chars: {}'.format(utils.use_wide_chars))
    return cfg


def launch_ui(win, path1, path2, use_wide_chars):
    global app
    cfg = init_config(use_wide_chars)
    try:
        app = UI(cfg, win, [path1], [path2])
        ret = app.run()
    except LFMTerminalTooNarrow as e:
        DialogError('Terminal too narrow to show contents.\nIt should have {} columns at mininum.'.format(MIN_COLUMNS))
        return None
    if app.cfg.options.save_configuration_at_exit:
        try:
            if app.cfg.options.save_panel_state_at_exit:
                state = {
                    'active_panel': 0 if (app.pane_active == app.pane1) else 1,
                    'panels' : []
                }
                # Store pane configuration, always store filenames instead of
                # indices since files can be deleted from the directory across
                # invocations and storing filenames makes restoring more robust
                for pane in [app.pane1, app.pane2]:
                    panel_state = {
                        'tabs': [],
                        'active_tab': pane.tabs.index(pane.tab_active),
                    }
                    for tab in pane.tabs:
                        # If it's a VFS 
                        # - set the path as the parent of the archive
                        # - focus on the archive
                        # - ignore selected files
                        # XXX Support VFS better? Is there enough infrastructure
                        #     plumbed at inint time to uncompress it? but it can
                        #     take a long time to uncompress, increasing startup
                        #     time? 
                        tab_state = {
                            'path' : dirname(tab.fs.base_filename) if tab.fs.vfs else tab.fs.path_str,
                            'focused_file' : basename(tab.fs.base_filename) if tab.fs.vfs else tab.fs[tab.i].name,
                            'selected_files' : [] if tab.fs.vfs else [fs.name for fs in tab.selected],
                            'history' : tab.history,
                            'history_mru' : tab.history_mru,
                            'next_history_index' : tab.next_history_index,
                        }
                        panel_state["tabs"].append(tab_state)
                    state["panels"].append(panel_state)
                import json
                app.cfg.options.panel_state = json.dumps(state)
            else:
                app.cfg.options.panel_state = {}

            log.debug(app.cfg.options.panel_state)
            app.cfg.save()
        except Exception as e:
            DialogError('Cannot save configuration file\n{}'.format(str(e)))
    if app.cfg.options.save_history_at_exit:
        try:
            app.history.save()
        except Exception as e:
            DialogError('Cannot save history file\n{}'.format(str(e)))
    return ret


def run_app(path1, path2, use_wide_chars):
    return curses.wrapper(launch_ui, path1, path2, use_wide_chars)


########################################################################
