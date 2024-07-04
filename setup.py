#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

from distutils.core import setup
import sys

DOC_FILES = ['COPYING', 'README', 'README.pyview', 'NEWS', 'TODO', 'ChangeLog']


classifiers = ["Development Status :: 4 - Beta",
               "Environment :: Console :: Curses",
               "Intended Audience :: End Users/Desktop",
               "License :: OSI Approved :: GNU General Public License (GPL)",
               "Programming Language :: Python",
               "Natural Language :: English",
               "Operating System :: POSIX",
               "Operating System :: Unix",
               "Topic :: Desktop Environment :: File Managers",
               "Topic :: System :: Filesystems",
               "Topic :: System :: Shells",
               "Topic :: System :: System Shells"
              ]


if sys.version_info >= (2, 3):
    addargs = {"classifiers": classifiers}
else:
    addargs = {}
   

setup(name = 'lfm',
      version = '0.91',
      license = 'GPL',
      description = 'Last File Manager',
      author = 'Iñigo Serna',
      author_email = 'inigoserna@terra.es',
      url = 'http://www.terra.es/personal7/inigoserna/lfm',
      py_modules = ['lfm/__init__', 'lfm/lfm', 'lfm/messages', 'lfm/files',
                    'lfm/actions', 'lfm/utils', 'lfm/vfs',
                    'lfm/preferences', 'lfm/pyview'],
      scripts = ['lfm/lfm', 'lfm/pyview'],
      data_files = [('share/doc/lfm', DOC_FILES)]
#      **addargs
     )


#  import os, os.path, sys
#  from distutils.sysconfig import get_python_lib
#  os.symlink(os.path.join(get_python_lib(), 'lfm/lfm.py'),
#             os.path.join(sys.exec_prefix, 'bin/lfm'))
