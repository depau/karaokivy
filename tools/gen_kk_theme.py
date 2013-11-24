#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gen_kk_theme.py
# Copyright (C) 2013 Davide Depau <david.dep.1996@gmail.com>
#
# Karaokivy is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Karaokivy is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.    If not, see <http://www.gnu.org/licenses/>.

# Dependencies: Kivy (to make the atlas), ImageMagick (to stack the images and get image size) and PIL (Python Imaging Library)

import os, sys, itertools, shutil, subprocess
from os.path import join, abspath, exists, isdir, basename, splitext
from tempfile import mkdtemp
from math import sqrt
from kivy.atlas import Atlas

def stack_image(bg, fg, out):
    # You need ImageMagick to stack one image onto another
    p = subprocess.Popen(["convert", bg, "-gravity", "Center", fg, "-compose", "Over", "-composite", out])
    p.wait()

def get_atlas_best_size(filenames, padding=2):
    # Thanks to
    # omnisaurusgames.com/2011/06/texture-atlas-generation-using-python/
    # for its initial implementation.
    from PIL import Image

    # open all of the images
    ims = [(f, Image.open(f)) for f in filenames]

    # sort by image area
    ims = sorted(ims, key=lambda im: im[1].size[0] * im[1].size[1],
            reverse=True)

    for size in (n ** 2 for n in itertools.count()):
        # free boxes are empty space in our output image set
        # the freebox tuple format is: outidx, x, y, w, h
        freeboxes = [(0, 0, 0, size, size)]
        numoutimages = 1

        # full boxes are areas where we have placed images in the atlas
        # the full box tuple format is: image, outidx, x, y, w, h, filename
        fullboxes = []

        broken = False

        # do the actual atlasing by sticking the largest images we can have into
        # the smallest valid free boxes
        for imageinfo in ims:
            im = imageinfo[1]
            imw, imh = im.size
            imw += padding
            imh += padding
            if imw > size or imh > size:
                #Logger.error('Atlas: image %s is larger than the atlas size!' %
                #    imageinfo[0])
                broken = True
                break

            inserted = False
            while not inserted:
                for idx, fb in enumerate(freeboxes):
                    # find the smallest free box that will contain this image
                    if fb[3] >= imw and fb[4] >= imh:
                        # we found a valid spot! Remove the current freebox, and
                        # split the leftover space into (up to) two new
                        # freeboxes
                        del freeboxes[idx]
                        if fb[3] > imw:
                            freeboxes.append((
                                fb[0], fb[1] + imw, fb[2],
                                fb[3] - imw, imh))

                        if fb[4] > imh:
                            freeboxes.append((
                                fb[0], fb[1], fb[2] + imh,
                                fb[3], fb[4] - imh))

                        # keep this sorted!
                        freeboxes = sorted(freeboxes,
                                key=lambda fb: fb[3] * fb[4])
                        fullboxes.append((im,
                            fb[0], fb[1] + padding,
                            fb[2] + padding, imw - padding,
                            imh - padding, imageinfo[0]))
                        inserted = True
                        break

                if not inserted:
                    # oh crap - there isn't room in any of our free boxes, so we
                    # have to add a new output image
                    freeboxes.append((numoutimages, 0, 0, size, size))
                    numoutimages += 1
        if numoutimages == 1 and not broken:
            return size


def hr_size(bytes):
    kb = bytes / 1024.
    if len(str(int(kb))) <= 3:
        return str(round(kb, 1)) + " KB"
    elif len(str(int(kb))) <= 6:
        return str(round(kb/1024., 1)) + " MB"
    elif len(str(int(kb))) <= 9:
        return str(round(kb/1024./1024., 1)) + " GB"
    else:
        return str(round(kb/1024./1024./1024., 1)) + " TB"


if __name__ == '__main__':
    try:
        imgdir = abspath(sys.argv[1])
    except IndexError:
        imgdir = abspath("source")
    if not exists(imgdir):
        import errno
        print "Usage: {0} [ directory ]".format(sys.argv[0])
        raise OSError(errno.ENOENT, "No such file or directory: \"{0}\"".format(imgdir))
    elif not isdir(imgdir):
        import errno
        print "Usage: {0} [ directory ]".format(sys.argv[0])
        raise OSError(errno.ENOTDIR, "Not a directory: \"{0}\"".format(imgdir))

    for i in (join(imgdir, f) for f in os.listdir(imgdir)):
        if not isdir(i) or basename(i) == "noinclude":
            continue
        atlasname = basename(i)

        print "Creating atlas", i

        tmp = mkdtemp(prefix="karaokivy-", suffix="-" + atlasname)

        # Stack images
        print "  [ ] Stacking images...",
        #print join(i, "stack")
        if exists(join(i, "stack")):
            for bg in (join(i, "stack", "bg", f) for f in os.listdir(join(i, "stack", "bg"))):
                if bg.lower().endswith(".png"):
                    for fg in (join(i, "stack", "fg", f) for f in os.listdir(join(i, "stack", "fg"))):
                        if fg.lower().endswith(".png"):
                            #print "Stacking {0} on {1} and putting the result in {2}".format(fg, bg, join(tmp, splitext(basename(fg))[0] + "_" + basename(bg)))
                            stack_image(bg, fg, join(tmp, splitext(basename(fg))[0] + "_" + basename(bg)))

        print "\r  [x] Images stacked.   "


        # Copy prefabricated images
        #print join(i, "include")
        print "  [ ] Copying included images...",
        if exists(join(i, "include")):
            for img in (join(i, "include", f) for f in os.listdir(join(i, "include"))):
                #print img
                shutil.copy(img, tmp)

        print "\r  [x] Images copied.            "

        # All done, pack everything into an atlas
        print "  [ ] Generating the atlas...",
        fnames = []
        tot_size = 0
        for i in (join(tmp, f) for f in os.listdir(tmp)):
            if i.lower().endswith(".png"):
                fnames.append(i)
                tot_size += os.stat(i).st_size
        data = Atlas.create(atlasname, fnames, get_atlas_best_size(fnames))
        if not data:
            print "\r  [!] Atlas not generated."
            continue
        else:
            fn, meta = data
            atl_size = 0
            for i in meta.keys():
                atl_size += os.stat(i).st_size
            print "\r  [x] Atlas \"{0}\" generated ({1} image{2}, {3} saved).".format(fn, len(meta), 's' if len(meta) > 1 else '', hr_size(tot_size - atl_size))

        shutil.rmtree(tmp)

    print "All done."