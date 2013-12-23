#!/usr/bin/env python
# -*- coding: utf-8 -*-

# __init__.py
# Copyright (C) 2013 Davide Depau <me@davideddu.org>
#
# Karaokivy Kivy Audio Player plug-in
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

# This plug-in is part of Karaokivy's default plug-in collection.

import os, sys, errno
from os.path import abspath, exists, join, isdir
from plugin_base import AudioHandler, PlayerError, PlayerOSError
from stopwatch import Timer


from kivy.core.audio import SoundLoader
from kivy.properties import NumericProperty, BoundedNumericProperty,\
                            ObjectProperty, StringProperty, DictProperty,\
                            ListProperty, OptionProperty, BooleanProperty

class PlayerKivyAudio(AudioHandler):
    sound = ObjectProperty(None)
    pos_offset = NumericProperty(0)
    pos_timer = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super(PlayerKivyAudio, self).__init__(**kwargs)
        fn = abspath(self.file)
        if not exists(fn):
            raise PlayerOSError(errno.ENOENT, "No such file", fn)
        if isdir(fn):
            raise PlayerOSError(errno.EISDIR, "Is a directory", fn)

        self.sound = SoundLoader.load(fn)

        if not self.sound:
            raise PlayerOSError("Unknown error while loading song, check command line")

        self.bind(state=self.on_state)

    def on_state(self, *args):
        # ["nfl", "stop", "play", "pause", "busy"]
        if self.sound:
            if self.state == "play":
                pos = self.get_pos()
                print pos
                self.sound.seek(pos)
                self.sound.play()
                self.pos_timer = Timer(offset=self.pos_offset)

            elif self.state == "pause":
                self.sound.stop()
                self.pos_timer.stop()
                print self.get_pos()
                self.pos_offset = self.pos_timer.elapsed

            elif self.state == "stop":
                self.sound.stop()
                self.pos_timer.stop()
                self.pos_timer = None
                self.pos_offset = 0
        else:
            if self.state in ("play", "stop", "pause"):
                raise PlayerError("Cannot set state, no file loaded")

    def get_pos(self):
        try:
            pos = self.sound.get_pos()
            if pos < 0:
                raise Exception
            else:
                return
        except:
            try:
                return self.pos_timer.elapsed
            except:
                return 0

    def unload(self):
        try:
            self.sound.unload()
        except:
            pass

    @staticmethod
    def extensions():
        exts = []
        for i in SoundLoader._classes:
            for j in i.extensions():
                # I'm not sure if a generator is safe, as it doesn't have __getitem__
                # yield j
                exts.append(j)
        return exts

def get_player():
    return PlayerKivyAudio