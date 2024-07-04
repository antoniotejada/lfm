#!/usr/bin/env python

from distutils.core import setup

DOC_FILES = ['COPYING', 'README', 'TODO']

setup(name = 'lfm',
      version = '0.4',
      licence = 'GPL',	# spelling error in distutils
      description = 'Last File Manager',
      author = 'Iñigo Serna',
      author_email = 'inigoserna@terra.es',
      url = '',
      py_modules = ['lfm/__init__', 'lfm/lfm', 'lfm/messages', 'lfm/files'],
      scripts = ['lfm/lfm']
      )


#  import os, os.path, sys
#  from distutils.sysconfig import get_python_lib

#  os.symlink(os.path.join(get_python_lib(), 'lfm/lfm.py'),
#             os.path.join(sys.exec_prefix, 'bin/lfm'))
