#!/usr/bin/env python

from distutils.core import setup

DOC_FILES = ['COPYING', 'README', 'NEWS', 'TODO', 'ChangeLog']

setup(name = 'lfm',
      version = '0.5',
      licence = 'GPL',	# spelling error in distutils
      description = 'Last File Manager',
      author = 'I�igo Serna',
      author_email = 'inigoserna@terra.es',
      url = '',
      py_modules = ['lfm/__init__', 'lfm/lfm', 'lfm/messages', 'lfm/files',
                    'lfm/preferences'],
      scripts = ['lfm/lfm'],
      data_files = [('share/doc/lfm', DOC_FILES)]
      )


#  import os, os.path, sys
#  from distutils.sysconfig import get_python_lib

#  os.symlink(os.path.join(get_python_lib(), 'lfm/lfm.py'),
#             os.path.join(sys.exec_prefix, 'bin/lfm'))
