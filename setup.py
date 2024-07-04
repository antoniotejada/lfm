#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""lfm v3.1 - (C) 2001-17, by Iñigo Serna <inigoserna@gmail.com>

'Last File Manager' is a powerful file manager for UNIX console.
It has a curses interface and it's written in Python version 3.4+.
Released under GNU Public License, read COPYING file for more details.
"""


import os
from distutils.core import setup
from os.path import join
from sys import argv, exit, prefix, version_info


DOC_FILES = ['COPYING', 'README', 'NEWS', 'TODO']
CONFIG_FILES = ['etc/lfm-default.keys', 'etc/lfm-default.theme']
MAN_FILES = ['lfm.1']

classifiers = """\
Development Status :: 5 - Production/Stable
Environment :: Console :: Curses
Intended Audience :: End Users/Desktop
Intended Audience :: System Administrators
License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)
Natural Language :: English
Operating System :: POSIX
Operating System :: Unix
Programming Language :: Python :: 3
Topic :: Desktop Environment :: File Managers
Topic :: System :: Filesystems
Topic :: System :: Shells
Topic :: System :: System Shells
Topic :: Utilities
"""

print(__doc__)

# check python version
ver = (version_info.major, version_info.minor)
if ver < (3, 4):
    print('ERROR: Python 3.4 or higher is required to run lfm.')
    exit(-1)

# to avoid bug in pip 7.x. See https://bitbucket.org/pypa/wheel/issues/92
if 'bdist_wheel' in argv:
    raise RuntimeError("This setup.py does not support wheels")

import shutil
try:
    try:
        os.mkdir('lfm/doc')
        for f in DOC_FILES:
            shutil.copy2(f, 'lfm/doc')
        os.symlink('../etc', 'lfm/etc')
    except:
        pass
    setup(name='lfm',
          version='3.1',
          description=__doc__.split("\n")[2],
          long_description='\n'.join(__doc__.split("\n")[2:]).strip(),
          author='Iñigo Serna',
          author_email='inigoserna@gmail.com',
          url='https://inigo.katxi.org/devel/lfm',
          platforms='POSIX',
          keywords=['file manager shell cli'],
          classifiers=filter(None, classifiers.split("\n")),
          license='GPL3+',
          packages=['lfm'],
          scripts=['lfm/lfm'],
          data_files=[(join(prefix, 'share/man/man1'), MAN_FILES)],
          package_data={'': CONFIG_FILES + [join('doc', f) for f in DOC_FILES]},
    )
finally:
    shutil.rmtree('lfm/doc')
    try:
        os.unlink('lfm/etc')
    except IsADirectoryError:
        pass
