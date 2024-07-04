# -*- coding: utf-8 -*-

"""compress.py

This module contains un/compress classes.
"""


import os, os.path
from __init__ import sysprogs
import files


######################################################################
def check_compressed_file(filename):
    for p in packagers:       # Note: tbz2 must be before bz2
        for e in p.exts:
            if filename.endswith(e):
                return p(filename)
    else:
        return None


def check_compressed_file_type(filename):
    c = check_compressed_file(filename)
    if c:
        return c.type
    else:
        return None


class PackagerBase:
    def __init__(self, filename):
        while filename[-1] == os.sep:
            filename = filename[:-1]
        self.fullname = filename
        self.dirname = os.path.dirname(filename)
        self.filename = os.path.basename(filename)

    def build_uncompress_cmd(self):
        return self.uncompress_cmd % self.fullname

    def build_compress_cmd(self):
        newfile = self.filename + self.exts[0]
        if os.path.isfile(self.fullname):
            if self.type in ('bz2', 'gz'):
                return self.compress_cmd % self.filename
            elif self.type in ('tbz2', 'tgz'):
                return # Don't use tar, it's a file
            else:
                return self.compress_cmd % (self.filename, newfile)
        elif os.path.isdir(self.fullname):
            if self.type in ('bz2', 'gz'):
                return # Don't compress without tar, it's a dir
            if self.need_tar:
                return self.compress_cmd % (self.filename, newfile)
            else:
                return self.compress_cmd % (newfile, self.filename)

    def build_compressXXX_cmd(self, src, dest):
        if not dest.endswith(self.exts[0]):
            dest += self.exts[0]
        if self.need_tar:
            return self.compressXXX_cmd % (src, dest)
        else:
            return self.compressXXX_cmd % (dest, src)

    def delete_uncompress_temp(self, path, is_tmp = False):
        if is_tmp:
            tmpfile = path
        else:
            for e in self.exts:
                if self.filename.endswith(e):
                    dirname = self.filename[:-len(e)]
                    break
            else:
                return
            tmpfile = os.path.join(path, dirname)
        try:
            files.do_delete(tmpfile)
        except OSError:
            pass

    def delete_compress_temp(self, path, is_tmp = False):
        if is_tmp:
            tmpfile = path
        else:
            tmpfile = os.path.join(path, self.filename + self.exts[0])
        try:
            files.do_delete(tmpfile)
        except OSError:
            pass


class PackagerTBZ2(PackagerBase):
    type = 'tbz2'
    exts = ('.tar.bz2', '.tbz2')
    need_tar = True
    uncompress_prog = compress_prog = sysprogs['bzip2']
    uncompress_cmd = uncompress_prog + ' -d \"%s\" -c | ' + sysprogs['tar'] + ' xfi -'
    compress_cmd = sysprogs['tar'] + ' cf - \"%s\" | ' + compress_prog + ' > \"%s\"'
    compressXXX_cmd = sysprogs['tar'] + ' cf - %s | ' + compress_prog + ' > \"%s\"'


class PackagerBZ2(PackagerBase):
    type = 'bz2'
    exts = ('.bz2', )
    need_tar = False
    uncompress_prog = compress_prog = sysprogs['bzip2']
    uncompress_cmd = uncompress_prog + ' -d \"%s\"'
    compress_cmd = compress_prog + ' \"%s\"'
    compressXXX_cmd = compress_prog + ' %s'


class PackagerTGZ(PackagerBase):
    type = 'tgz'
    exts = ('.tar.gz', '.tgz', '.tar.Z')
    need_tar = True
    uncompress_prog = compress_prog = sysprogs['gzip']
    uncompress_cmd = uncompress_prog + ' -d \"%s\" -c | ' + sysprogs['tar'] + ' xfi -'
    compress_cmd = sysprogs['tar'] + ' cf - \"%s\" | ' + compress_prog + ' > \"%s\"'
    compressXXX_cmd = sysprogs['tar'] + ' cf - %s | ' + compress_prog + ' > \"%s\"'


class PackagerGZ(PackagerBase):
    type = 'gz'
    exts = ('.gz', )
    need_tar = False
    uncompress_prog = compress_prog = sysprogs['gzip']
    uncompress_cmd = uncompress_prog + ' -d \"%s\"'
    compress_cmd = compress_prog + ' \"%s\"'
    compressXXX_cmd = compress_prog + ' %s'


class PackagerZIP(PackagerBase):
    type = 'zip'
    exts = ('.zip', )
    need_tar = False
    uncompress_prog = sysprogs['unzip']
    uncompress_cmd = uncompress_prog + ' -q \"%s\"'
    compress_prog = sysprogs['zip']
    compress_cmd = compress_prog + ' -qr \"%s\" \"%s\"'
    compressXXX_cmd = compress_prog + ' -qr \"%s\" %s'


class PackagerRAR(PackagerBase):
    type = 'rar'
    exts = ('.rar', )
    need_tar = False
    uncompress_prog = compress_prog = sysprogs['rar']
    uncompress_cmd = uncompress_prog + ' x \"%s\"'
    compress_cmd = compress_prog + ' a \"%s\" \"%s\"'
    compressXXX_cmd = compress_prog + ' a \"%s\" %s'


packagers = ( PackagerTBZ2, PackagerBZ2,
              PackagerTGZ, PackagerGZ,
              PackagerZIP, PackagerRAR )

packagers_by_type = { 'tbz2': PackagerTBZ2,
                      'bz2': PackagerBZ2,
                      'tgz': PackagerTGZ,
                      'gz': PackagerGZ,
                      'zip': PackagerZIP,
                      'rar': PackagerRAR }


######################################################################
