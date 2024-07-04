# -*- coding: utf-8 -*-


import curses
from string import ascii_letters, digits, punctuation
from common import *


########################################################################
VALID_KEYS_1 = ascii_letters + digits + punctuation
VALID_KEYS_2 = "up down left right pageup pagedown home end del ins backspace enter spc esc tab btab".split()
VALID_KEYS_3 = ['f%d' % i for i in range(1, 25)]

tbl_kstr_kcode = [('up', curses.KEY_UP),
                  ('down', curses.KEY_DOWN),
                  ('left', curses.KEY_LEFT),
                  ('right', curses.KEY_RIGHT),
                  ('pageup', curses.KEY_PPAGE),
                  ('pagedown', curses.KEY_NPAGE),
                  ('home', curses.KEY_HOME),
                  ('end', curses.KEY_END),
                  ('del', curses.KEY_DC),
                  ('ins', curses.KEY_IC),
                  ('backspace', curses.KEY_BACKSPACE),
                  ('enter', 10),
                  ('spc', 32),
                  ('esc', 27),
                  ('tab', 9),
                  ('backtab', curses.KEY_BTAB),
                  ('S+up', curses.KEY_SR),
                  ('S+down', curses.KEY_SF),
                  ('S+left', curses.KEY_SLEFT),
                  ('S+right', curses.KEY_SRIGHT),
                  ('S+del', curses.KEY_SDC)]
kmap_str2code = dict(tbl_kstr_kcode)
kmap_code2str = dict([(it[1], it[0]) for it in tbl_kstr_kcode])

# A-up: kUP3, A-S-up: kUP4, C-up: kUP5, C-S-up: kUP6, C-A-up: kUP7 ... C-A-pagedown: kNXT7
# kUP3: 0x235, kUP4: 0x236 ... kDN3: 0x20c ... kLFT3: 0x220 ... kRIT3: 0x22c ...
# kDC3: 0x206 ... kIC3: 0x21b ... kPRV: 0x22a ... kNXT: 0x22a
tbl_mods = {'A-': 3, 'A-S-': 4, 'S-A-': 4, 'C-': 5, 'C-S-': 6, 'S-C-': 6, 'C-A-': 7, 'A-C-': 7}
#tbl_keysspecial = {'up': ('kUP', 0x235), 'down': ('kDN', 0x20c), 'left': ('kLFT', 0x220),
#                   'right': ('kRIT', 0x22f), 'del': ('kDC', 0x206), 'ins': ('kIC', 0x21b),
#                   'pageup': ('kPRV', 0x22a), 'pagedown': ('kNXT', 0x225)}
tbl_keysspecial = {'up': ('kUP', 0x236), 'down': ('kDN', 0x20d), 'left': ('kLFT', 0x221),
                   'right': ('kRIT', 0x230), 'del': ('kDC', 0x207), 'ins': ('kIC', 0x21c),
                   'pageup': ('kPRV', 0x22b), 'pagedown': ('kNXT', 0x226)}
# tbl_keysspecial = {'up': ('kUP', 0x237), 'down': ('kDN', 0x20e), 'left': ('kLFT', 0x222),
#                    'right': ('kRIT', 0x231), 'del': ('kDC', 0x208), 'ins': ('kIC', 0x21d),
#                    'pageup': ('kPRV', 0x22c), 'pagedown': ('kNXT', 0x227)}
tbl_aliases = []
for mod in tbl_mods:
    for k in tbl_keysspecial:
        pair = mod+k, tbl_keysspecial[k][1]+tbl_mods[mod]-3
        tbl_aliases.append(pair)
# S-F1: F13 ... S-F12: F24
for i in range(0, 11):
    pair = 'S-F{}'.format(i+1), curses.KEY_F1+12+i
    tbl_aliases.append(pair)
kmap_aliases_str2code = dict(tbl_aliases)
kmap_aliases_code2str = dict([(it[1], it[0]) for it in tbl_aliases])


########################################################################
def get_keycode(kstr):
    if len(kstr) == 1:
        if kstr in VALID_KEYS_1:
            return ord(kstr)
        else:
            raise ValueError
    kstr = kstr.lower()
    if kstr in kmap_aliases_str2code:
        return kmap_aliases_str2code[kstr]
    if kstr in VALID_KEYS_2:
        return kmap_str2code[kstr]
    if kstr in VALID_KEYS_3:
        return curses.KEY_F1 + int(kstr[1:]) - 1
    else:
        raise ValueError

def key_str2bin(k):
    if k in kmap_aliases_str2code:
        return (KeyModifier.none, kmap_aliases_str2code[k])
    if k.startswith('C-'):
        km = KeyModifier.control
        k = k[2:]
        if len(k) == 1:
            return (KeyModifier.none, ord(k.lower())-ord('a')+1)
    elif k.startswith('A-'):
        km = KeyModifier.alt
        k = k[2:]
    else:
        km = KeyModifier.none
    return (km, get_keycode(k))


def get_keystr(kcode):
    if kcode in kmap_code2str:
        return kmap_code2str[kcode]
    if kcode in kmap_aliases_code2str:
        return kmap_aliases_code2str[kcode]
    if kcode >= curses.KEY_F1 and kcode <= curses.KEY_F24:
        return 'f%d' % (kcode-curses.KEY_F1+1, )
    if kcode>=32 and kcode<128:
        return chr(kcode)
    return str(kcode)

def key_bin2str(k):
    km, key_code = k
    if key_code < 0x20:
        if key_code in kmap_code2str:
            return kmap_code2str[key_code]
        return 'C-' + chr(ord('a')-1+key_code)
    if km == KeyModifier.alt:
        km = 'A-'
    else:
        km = ''
    return km + get_keystr(key_code)


########################################################################
