#!/usr/bin/env python
# -*- coding: utf-8 -*-

# plugin_base.py
# Copyright (C) 2013 Davide Depau <me@davideddu.org>
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

from os.path import splitext

from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, BoundedNumericProperty,\
                            ObjectProperty, StringProperty, DictProperty,\
                            ListProperty, OptionProperty, BooleanProperty,\
                            AliasProperty

class PluginHandler(EventDispatcher):
    """Base class for all the objects returned by the plug-ins..
    """

    _app = ObjectProperty(None)
    """It will be automatically filled by Karaokivy with the running App instance.
    """

    pass

class FileHandler(PluginHandler):
    """Base class for all the objects returned by plug-ins that
    handle files (like players or lyrics providers)-
    """

    file = ObjectProperty(None)
    """The file that will be used by the handler. Check object documentation
    to see what types are accepted - string containing a path, file-like
    object, etc.
    """

    supported_mimes = ListProperty([])
    """List containing all the MIME types supported by the program. Please be
    as generic as possible (not too much), as if the file's mimetype doesn't
    match one of the mimes here, the plug-in will be skipped.
    Defaults to [].
    """

    @staticmethod
    def extensions():
        return []

    @staticmethod
    def supports(obj):
        if type(obj) == type(str()):
            for ext in FileHandler.extensions():
                if obj.lower().endswith(ext.lower()):
                    return True
        return False

    def unload(self):
        """Unloads the open file from memory when it's not needed any more.
        By default it doesn't do anything. Override it with your custom method.
        """
        pass


class ActiveLyricsHandler(FileHandler):
    """Base class for the standard lyrics handlers that cannot store in
    memory the lyrics but have to look for them at every iteration.
    """
    lyrics = ListProperty([NotImplemented, NotImplemented, NotImplemented])
    """Update this property with the lyrics at current time (in milliseconds).
    Returned object should be a list/tuple like this:
    [lyrics, time, next_time]
    lyrics is a string containing the part of the song that should be sung,
    time is the timestamp of that part of song (obviously not the time
    passed to the method), next_time is the timestamp of the following piece
    of song. Not abailable information (except the lyrics) can be replaced by
    NotImplemented.
    """

    time = NumericProperty(0)
    """Karaokivy will update this property with the current time.
    """

class PassiveLyricsHandler(FileHandler):
    """Base class for the standard lyrics handlers that can store the
    lyrics in memory (like LRC readers).
    """

    time = NumericProperty(0)
    """Karaokivy will update this property with the current time.
    """

    _lyrics = StringProperty("")

    def __get_lyrics(self, time=None):
        """Override this method and program it to return the lyrics at the
        specified time ( in milliseconds). Returned object should be a
        list/tuple like this:
        [lyrics, time, next_time]
        lyrics is a string containing the part of the song that should be sung,
        time is the timestamp of that part of song (obviously not the time
        passed to the method), next_time is the timestamp of the following piece
        of song, or NotImplemented.
        By default it returns (self._lyrics, NotImplemented, NotImplemented).
        """
        if not time:
            time = self.time
        return self._lyrics, NotImplemented, NotImplemented

    def __set_lyrics(self, value):
        self._lyrics = value

    lyrics = AliasProperty(__get_lyrics, __set_lyrics)
    """lyrics is an AliasProperty. When reading it, it will return
    [lyrics, time, next_time] (see PassiveLyricsHandler.__get_lyrics 
    documentation). Example:
    >>> print mylyricshandler.lyrics
    ("Lyrics text", NotImplemented, NotImplemented)

    Remember that it's an alias property, and it does not contain
    anything. Its value is generated on the fly by __get_lyrics.
    When setting it you'll be setting the _lyrics property instead,
    that is a StringProperty. That means that if you do something like
    this, it will raise ValueError:
    >>> mylyricshandler.lyrics = ["some string", NotImplemented, NotImplemented]
     Traceback (most recent call last):
       [...]
     ValueError: mylyricshandler._lyrics accepts only str
    """

class StreamHandler(FileHandler):
    """Base class for all the handlers that handle streams.
    """

    state = OptionProperty("nfl", options=["nfl", "stop", "play", "pause", "busy"])

    def __init__(self, **kwargs):
        super(StreamHandler, self).__init__(**kwargs)

        self._app.bind(state=self.setter("state"))
        self.bind(state=self._app.setter("state"))

    def get_pos(self):
        return -1

class VideoHandler(StreamHandler):
    """Base class for all the handlers that show a video.
    """
    pass

class AudioHandler(StreamHandler):
    """Base class for all the handlers that play an audio file.
    """
    pass


class PluginError(Exception):
    pass

class PlayerError(PluginError):
    pass

class PlayerOSError(OSError, PlayerError):
    pass

class LyricsHandlerError(PluginError):
    pass

class LyricsHandlerOSError(OSError, LyricsHandlerError):
    pass