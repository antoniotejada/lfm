# -*- coding: utf-8 -*-


from os.path import dirname, basename, join, isfile, isdir

from utils import delete_bulk
from common import *


######################################################################
def get_compressed_file_engine(filename):
    for p in packagers:       # Note: tbz2 must be before bz2
        for e in p.exts:
            if filename.endswith(e):
                return p(filename)
    else:
        return None


def get_compressed_file_type(filename):
    c = get_compressed_file_engine(filename)
    return c.type if c else None


def check_compressed_vfs(filename):
    c = get_compressed_file_engine(filename)
    return c.can_vfs if c else False


class PackagerBase:
    def __init__(self, filename):
        self.path = filename
        self.dirname = dirname(self.path)
        self.filename = basename(self.path)

    @property
    def cmd_uncompress(self):
        return self.uncompress_cmd % self.path

    @property
    def cmd_compress(self):
        newfile = self.filename + self.exts[0]
        if isfile(self.path):
            if self.type in ('bz2', 'gz', 'xz', 'lz', 'lz4'):
                return self.compress_cmd % self.filename
            elif self.type in ('tbz2', 'tgz', 'txz', 'tlz', 'tlz4, ''tar'):
                return # Don't use tar, it's a file
            else:
                return self.compress_cmd % (self.filename, newfile)
        elif isdir(self.path):
            if self.type in ('bz2', 'gz', 'xz', 'lz', 'lz4'):
                return # Don't compress without tar, it's a dir
            if self.need_tar:
                return self.compress_cmd % (self.filename, newfile)
            else:
                return self.compress_cmd % (newfile, self.filename)

    def cmd_compress2(self, src, dest):
        if not dest.endswith(self.exts[0]):
            dest += self.exts[0]
        if self.need_tar:
            return self.compress2_cmd % (src, dest)
        else:
            return self.compress2_cmd % (dest, src)

    def delete_temp(self, path, from_compress, is_tmp=False):
        if is_tmp:
            tmpfile = path
        else:
            if from_compress:
                for e in self.exts:
                    if self.filename.endswith(e):
                        dirname = self.filename[:-len(e)]
                        break
                else:
                    return
                tmpfile = join(path, dirname)
            else: # from uncompress
                tmpfile = join(path, self.filename+self.exts[0])
        delete_bulk(str(tmpfile), ignore_errors=True)


class PackagerTBZ2(PackagerBase):
    type = 'tbz2'
    exts = ('.tar.bz2', '.tbz2')
    need_tar = True
    can_vfs = True
    uncompress_prog = compress_prog = SYSPROGS['bzip2']
    uncompress_cmd = uncompress_prog + ' -d \"%s\" -c | ' + SYSPROGS['tar'] + ' xfi -'
    compress_cmd = SYSPROGS['tar'] + ' cf - \"%s\" | ' + compress_prog + ' > \"%s\"'
    compress2_cmd = SYSPROGS['tar'] + ' cf - %s | ' + compress_prog + ' > \"%s\"'


class PackagerBZ2(PackagerBase):
    type = 'bz2'
    exts = ('.bz2', )
    need_tar = False
    can_vfs = False
    uncompress_prog = compress_prog = SYSPROGS['bzip2']
    uncompress_cmd = uncompress_prog + ' -d \"%s\"'
    compress_cmd = compress_prog + ' \"%s\"'
    compress2_cmd = compress_prog + ' %s'


class PackagerTGZ(PackagerBase):
    type = 'tgz'
    exts = ('.tar.gz', '.tgz', '.tar.Z')
    need_tar = True
    can_vfs = True
    uncompress_prog = compress_prog = SYSPROGS['gzip']
    uncompress_cmd = uncompress_prog + ' -d \"%s\" -c | ' + SYSPROGS['tar'] + ' xfi -'
    compress_cmd = SYSPROGS['tar'] + ' cf - \"%s\" | ' + compress_prog + ' > \"%s\"'
    compress2_cmd = SYSPROGS['tar'] + ' cf - %s | ' + compress_prog + ' > \"%s\"'


class PackagerGZ(PackagerBase):
    type = 'gz'
    exts = ('.gz', )
    need_tar = False
    can_vfs = False
    uncompress_prog = compress_prog = SYSPROGS['gzip']
    uncompress_cmd = uncompress_prog + ' -d \"%s\"'
    compress_cmd = compress_prog + ' \"%s\"'
    compress2_cmd = compress_prog + ' %s'


class PackagerTXZ(PackagerBase):
    type = 'txz'
    exts = ('.tar.xz', '.txz')
    need_tar = True
    can_vfs = True
    uncompress_prog = compress_prog = SYSPROGS['xz']
    uncompress_cmd = uncompress_prog + ' -d \"%s\" -c | ' + SYSPROGS['tar'] + ' xfi -'
    compress_cmd = SYSPROGS['tar'] + ' cf - \"%s\" | ' + compress_prog + ' > \"%s\"'
    compress2_cmd = SYSPROGS['tar'] + ' cf - %s | ' + compress_prog + ' > \"%s\"'


class PackagerXZ(PackagerBase):
    type = 'xz'
    exts = ('.xz', )
    need_tar = False
    can_vfs = False
    uncompress_prog = compress_prog = SYSPROGS['xz']
    uncompress_cmd = uncompress_prog + ' -d \"%s\"'
    compress_cmd = compress_prog + ' \"%s\"'
    compress2_cmd = compress_prog + ' %s'


class PackagerTLZ(PackagerBase):
    type = 'tlz'
    exts = ('.tar.lz', '.tlz')
    need_tar = True
    can_vfs = True
    uncompress_prog = compress_prog = SYSPROGS['lzip']
    uncompress_cmd = uncompress_prog + ' -d \"%s\" -c | ' + SYSPROGS['tar'] + ' xfi -'
    compress_cmd = SYSPROGS['tar'] + ' cf - \"%s\" | ' + compress_prog + ' > \"%s\"'
    compress2_cmd = SYSPROGS['tar'] + ' cf - %s | ' + compress_prog + ' > \"%s\"'


class PackagerLZ(PackagerBase):
    type = 'lz'
    exts = ('.lz', )
    need_tar = False
    can_vfs = False
    uncompress_prog = compress_prog = SYSPROGS['lzip']
    uncompress_cmd = uncompress_prog + ' -d \"%s\"'
    compress_cmd = compress_prog + ' \"%s\"'
    compress2_cmd = compress_prog + ' %s'


class PackagerTLZ4(PackagerBase):
    type = 'tlz4'
    exts = ('.tar.lz4', '.tlz4')
    need_tar = True
    can_vfs = True
    uncompress_prog = compress_prog = SYSPROGS['lz4']
    uncompress_cmd = uncompress_prog + ' -q -d \"%s\" -c | ' + SYSPROGS['tar'] + ' xfi -'
    compress_cmd = SYSPROGS['tar'] + ' cf - \"%s\" | ' + compress_prog + ' -9 -q > \"%s\"'
    compress2_cmd = SYSPROGS['tar'] + ' cf - %s | ' + compress_prog + ' -9 -q > \"%s\"'


class PackagerLZ4(PackagerBase):
    type = 'lz4'
    exts = ('.lz4', )
    need_tar = False
    can_vfs = False
    uncompress_prog = compress_prog = SYSPROGS['lz4']
    uncompress_cmd = uncompress_prog + ' --rm -m -q -d \"%s\"'
    compress_cmd = compress_prog + ' --rm -m -q \"%s\"'
    compress2_cmd = compress_prog + ' --rm -m -q %s'


class PackagerTAR(PackagerBase):
    type = 'tar'
    exts = ('.tar', )
    need_tar = False
    can_vfs = True
    uncompress_prog = compress_prog = SYSPROGS['tar']
    uncompress_cmd = uncompress_prog + ' xf \"%s\"'
    compress_cmd = compress_prog + ' cf \"%s\" \"%s\"'
    compress2_cmd = compress_prog + ' cf \"%s\" %s'


class PackagerZIP(PackagerBase):
    type = 'zip'
    exts = ('.zip', '.jar', '.apk')
    need_tar = False
    can_vfs = True
    uncompress_prog = SYSPROGS['unzip']
    uncompress_cmd = uncompress_prog + ' -o -q \"%s\"'
    compress_prog = SYSPROGS['zip']
    compress_cmd = compress_prog + ' -qr \"%s\" \"%s\"'
    compress2_cmd = compress_prog + ' -qr \"%s\" %s'


class PackagerRAR(PackagerBase):
    type = 'rar'
    exts = ('.rar', )
    need_tar = False
    can_vfs = True
    uncompress_prog = compress_prog = SYSPROGS['rar']
    uncompress_cmd = uncompress_prog + ' x \"%s\"'
    compress_cmd = compress_prog + ' a \"%s\" \"%s\"'
    compress2_cmd = compress_prog + ' a \"%s\" %s'


class Packager7Z(PackagerBase):
    type = '7z'
    exts = ('.7z', )
    need_tar = False
    can_vfs = True
    uncompress_prog = SYSPROGS['7z']
    uncompress_cmd = uncompress_prog + ' x \"%s\"'
    compress_prog = SYSPROGS['7z']
    compress_cmd = compress_prog + ' a \"%s\" \"%s\"'
    compress2_cmd = compress_prog + ' a \"%s\" %s'


######################################################################
packagers = (PackagerTBZ2, PackagerBZ2,
             PackagerTGZ, PackagerGZ,
             PackagerTXZ, PackagerXZ,
             PackagerTLZ, PackagerLZ,
             PackagerTLZ4, PackagerLZ4,
             PackagerTAR, PackagerZIP,
             PackagerRAR, Packager7Z)

packagers_by_type = {'tbz2': PackagerTBZ2,
                     'bz2': PackagerBZ2,
                     'tgz': PackagerTGZ,
                     'gz': PackagerGZ,
                     'txz': PackagerTXZ,
                     'xz': PackagerXZ,
                     'tlz': PackagerTLZ,
                     'lz': PackagerLZ,
                     'tlz4': PackagerTLZ4,
                     'lz4': PackagerLZ4,
                     'tar': PackagerTAR,
                     'zip': PackagerZIP,
                     'rar': PackagerRAR,
                     '7z': Packager7Z}


######################################################################
