#!/usr/bin/env python2

from distutils.core import setup

DOC_FILES = ['COPYING', 'README', 'README.pyview', 'NEWS', 'TODO', 'ChangeLog']

setup(name = 'lfm',
      version = '0.9',
      licence = 'GPL',	# spelling error in distutils
      description = 'Last File Manager',
      author = 'Iñigo Serna',
      author_email = 'inigoserna@telefonica.net',
      url = 'http://www.terra.es/personal7/inigoserna/lfm',
      py_modules = ['lfm/__init__', 'lfm/lfm', 'lfm/messages', 'lfm/files',
                    'lfm/preferences', 'lfm/pyview'],
      scripts = ['lfm/lfm', 'lfm/pyview'],
      data_files = [('share/doc/lfm', DOC_FILES)]
      )

#  import os, os.path, sys
#  from distutils.sysconfig import get_python_lib
#  os.symlink(os.path.join(get_python_lib(), 'lfm/lfm.py'),
#             os.path.join(sys.exec_prefix, 'bin/lfm'))
