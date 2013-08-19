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

# Dependencies: Kivy (to make the atlas) and ImageMagick (to stack the images and get image size). Kivy might also need PIL.

import os, sys, shutil, subprocess
from os.path import join, abspath, exists, isdir, basename, splitext
from tempfile import mkdtemp
from kivy.atlas import Atlas

def stack_image(bg, fg, out):
	# You need ImageMagick to stack one image onto another
	p = subprocess.Popen(["convert", bg, "-gravity", "Center", fg, "-compose", "Over", "-composite", out])
	p.wait()

def get_atlas_best_size(imgdir):
	max_size = [0, 0]
	tot_area = 0
	for i in os.listdir(imgdir):
		if i.lower().endswith(".png"):
			size = str(subprocess.check_output(["identify", "-format", r"%wx%h", join(imgdir, i)]))[:-1].split("x")
			print size
			for n in [0, 1]:
				if size[n] > max_size[n]:
					max_size[n] = size[n]
			area = size[0] * size[1]
			tot_area += area
	min_size = max_size[0] if max_size[0] > max_size[1] else max_size[1]

	stdsizes = [16, 22, 24, 32, 48, 64, 128, 192, 256, 320, 512, 1024, 2048, min_size]
	diffs = {}

	for size in stdsizes:
		if size < min_size:
			continue
		diffs[(size ** 2) - tot_area] = size
		# In some cases it's better to use more than one image
		diffs[((size ** 2) * 2) - tot_area] = size
		diffs[((size ** 2) * 3) - tot_area] = size

	best_size = diffs[sorted(diffs.keys())[0]]

	return best_size

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
		if not isdir(i) or i == "noinclude":
			continue
		atlasname = basename(i)
		tmp = mkdtemp(suffix="-kk-" + atlasname)

		# Stack images
		if exists(join(i, "stack")):
			for bg in (join(i, "stack", "bg", f) for f in os.listdir(join(i, "stack", "bg"))):
				if bg.lower().endswith(".png"):
					for fg in (join(i, "stack", "fg", f) for f in os.listdir(join(i, "stack", "fg"))):
						if fg.lower().endswith(".png"):
							stack_image(bg, fg, join(tmp, fg.splitext[0] + "_" + bg)

		# Copy prefabricated images
		if exists(join(i, "include")):
			for img in (join(i, "include", f) for f in os.listdir(join(i, "include"))):
				shutil.copy(img, tmp)

		# All done, pack everything into an atlas
		fn, meta = Atlas.create(atlasname, (join(tmp, f) for f in os.listdir(tmp), get_atlas_best_size(tmp)))
		print "Atlas \"{0}\" created ({1} image{2})".format(fn, len(meta), 's' if len(meta) > 1 else '')