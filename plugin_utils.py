# -*- coding: utf-8 -*-

# plugin_utils.py
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

import os, sys, json, re, misc, traceback
from os.path import dirname, basename, join, exists, normpath, isdir
from ConfigParser import NoOptionError
from kivy.app import App
from kivy.config import ConfigParser as KivyConfigParser
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, BoundedNumericProperty,\
                            ObjectProperty, StringProperty, DictProperty,\
                            ListProperty, OptionProperty, BooleanProperty
from kivy.utils import platform as core_platform
# Might be win, linux, android, macosx, ios, unknown
platform = core_platform()

class PluginManager(EventDispatcher):
    scope = OptionProperty("main_window", options=("main_window", "lyrics_window", "remote_control_window"))
    available_plugins = DictProperty({})
    running_plugins = DictProperty({})
    app_domain = StringProperty("")
    curdir = StringProperty(os.path.dirname(os.path.realpath(__file__)))

    def __init__(self, **kwargs):
        self.cfg = ConfigParser()
        self.cfg.adddefaultsection("Plugins")
        self.cfg.adddefaultsection("DefaultPlayers")
        self.cfg.adddefaultsection("DefaultLyrProviders")
        self.cfg.read(App.get_running_app().get_config("plugins.ini"))

        paths = self.get_plugins_paths()

        # Reversing the list puts the system paths (usually not writable in
        #   secure OSes) at the beginning, and user paths at the end, so that
        #   if the user updated the plugin, the user version is loaded.
        for path in reversed(paths):
            for i in (join(path, f) for f in os.listdir(path)):
                if isdir(i):
                    if exists(join(i, "manifest.json")):
                        plugin = self.load_plugin_manifest(join(i, "manifest.json"))
                        self.available_plugins[str(plugin.name)] = plugin

    def load_plugin(self, path, plugin):
        NotImplemented

    def load_plugin_manifest(self, man):
        with open(man, "r") as f:
            manifest = json.load(f)
        return Plugin.create_from_manifest(manifest, dirname(man), self.app_domain, self)

    def should_load_plugin(self, manifest):
        if False: # check if the plugin is disabled
            NotImplemented
            return False
        if platform not in manifest.platforms:
            return "Operating system not supported"
        for module in manifest.depends_py:
            try:
                imp.find_module(module)
            except ImportError:
                return "Cannot find module \"{0}\"".format(module) 
        for plugin in manifest.depends_kk:
            NotImplemented
        # Both the player and the lyrics provider must run in the remote control window;
        # the lyrics will be passed to the other window in a different way
        if ("player" in manifest.purposes or "lyrics_provider" in manifest.purposes) and self.scope == "lyrics_window":
            return False
        if "ui_expansion" in manifest.purposes and self.scope != manifest.ui_expansion.scope:
            return False
        if "feature" in manifest.purposes and self.scope != manifest.feature.scope:
            return False
        return True

    def get_plugins_paths(self):
        return self.get_plugins_paths_user() + self.get_plugins_paths_system()

    def get_plugins_paths_user(self):
        toret = []
        if platform == "linux":
            if exists(join(misc.home, ".local/share/karaokivy/plugins")):
                toret.append(join(misc.home, ".local/share/karaokivy/plugins"))
        elif platform == "win":
            if exists(join(os.environ["APPDATA"], "Karaokivy/plugins")):
                toret.append(join(os.environ["APPDATA"], "Karaokivy/plugins"))
        elif platform == "android":
            sdcard = Environment.getExternalStorageDirectory()
            if exists(join(sdcard, ".karaokivy/plugins")):
                toret.append(join(sdcard, ".karaokivy/plugins"))
        elif platform == "macosx":
            if exists(join(misc.home, ".karaokivy/plugins")):
                toret.append(join(misc.home, ".karaokivy/plugins"))
        return toret

    def get_plugins_paths_system(self):
        toret = []
        if platform == "linux":
            if exists(join(sys.prefix, "local/share/karaokivy/plugins")):
                toret.append(join(sys.prefix, "local/share/karaokivy/plugins"))
            elif exists(join(sys.prefix, "share/karaokivy/plugins")):
                toret.append(join(sys.prefix, "share/karaokivy/plugins"))
            elif exists(join(self.curdir, "plugins")):
                toret.append(join(self.curdir, "plugins"))
        elif platform == "win":
            if exists(join(self.curdir, "plugins")):
                toret.append(join(self.curdir, "plugins"))
        elif platform == "android":
            if exists(join(self.curdir, "plugins")):
                toret.append(join(self.curdir, "plugins"))
        elif platform == "macosx":
            if exists(join(self.curdir, "plugins")):
                toret.append(join(self.curdir, "plugins"))
        return toret

    def toggle(self, plugin, state=None):
        if state != None:
            self.cfg.setbool("Plugins", plugin, state)
        else:
            self.cfg.toggle("Plugins", plugin)



class Plugin(EventDispatcher):
    name = StringProperty("")
    title = StringProperty("")
    version = ObjectProperty(None)
    short_description = StringProperty("")
    long_description = StringProperty("")
    homepage = StringProperty("")
    authors = ListProperty([])
    platforms = ListProperty([])
    requires = ListProperty([])
    depends = ListProperty([])
    purposes = ListProperty([])
    player = ObjectProperty(None)
    lyrics_provider = ObjectProperty(None)
    ui_expansion = ObjectProperty(None)
    feature = ObjectProperty(None)
    module = ObjectProperty(None, allownone=True)
    stock = BooleanProperty(False)
    system = BooleanProperty(False)
    path = StringProperty("")
    active = BooleanProperty(False)
    manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(Plugin, self).__init__(**kwargs)
        self.bind(active=self._toggle)

    def _toggle(self, *args):
        self.manager.toggle(self.name, self.active)

    @staticmethod
    def create_from_manifest(manifest, path, domain, manager):
        kwargs = {}
        for i in manifest.keys():
            if not "." in i:
                if not type(manifest[i]) == type(u""):
                    kwargs[str(i)] = manifest[i]
                else:
                    kwargs[str(i)] = manifest[str(i)]
        kwargs["version"] = Version(manifest["version"])
        kwargs["stock"] = manifest["name"].startswith(domain)
        kwargs["system"] = path.startswith(sys.prefix)
        kwargs["path"] = path
        kwargs["manager"] = manager
        kwargs["active"] = manager.cfg.getbool("Plugins", manifest["name"])
        if "all" in manifest["platforms"]:
            kwargs["platforms"] = ["linux", "win", "android", "macosx"]
        if "player" in manifest["purposes"]:
            kwargs["player"] = PurposePlayer(supported_mimes=manifest["player.supported_mimes"], supported_actions=manifest["player.supported_actions"])
        if "lyrics_provider" in manifest["purposes"]:
            kwargs["lyrics_provider"] = PurposeLyricsProvider(supported_audio_mimes=manifest["lyrics_provider.supported_audio_mimes"], supported_lrc_types=manifest["lyrics_provider.supported_lrc_types"], lyrics_type=manifest["lyrics_provider.lyrics_type"])
        if "ui_expansion" in manifest["purposes"]:
            kwargs["ui_expansion"] = PurposeUIExpansion(scope=manifest["ui_expansion.scope"])
        if "feature" in manifest["purposes"]:
            kwargs["feature"] = PurposeFeature(scope=manifest["feature.scope"])
        return Plugin(**kwargs)

class PurposePlayer(EventDispatcher):
    supported_mimes = ListProperty([])
    supported_actions = ListProperty([])

class PurposeLyricsProvider(EventDispatcher):
    supported_audio_mimes = ListProperty([])
    supported_lrc_types = ListProperty([])
    lyrics_type = OptionProperty("text", options=("text", "graphic"))

class PurposeUIExpansion(EventDispatcher):
    scope = ListProperty([])

class PurposeFeature(EventDispatcher):
    scope = ListProperty([])

# Clever way to compare version numbers
class Version(str):
    # I use a lot of try/except because an exception in an object
    #     like this is not acceptable, expecially when comparing.
    #     Kivy uses to compare properties with non-string objects
    #     like None, and it should not make the app crash.
    def __lt__(self, other):
        try:
            me, you = self.get_floats(other)
            if type(other) == type(self):
                return me < you
            else:
                return NotImplemented
        except:
            print "EXCEPTION IN Version.__lt__ (self = \"{0}\", other = \"{1}\")".format(str(self), str(other))
            traceback.print_exc()

    def __le__(self, other):
        try:
            me, you = self.get_floats(other)
            if type(other) == type(self):
                return me <= you
            else:
                return NotImplemented
        except:
            print "EXCEPTION IN Version.__le__ (self = \"{0}\", other = \"{1}\")".format(str(self), str(other))
            traceback.print_exc()

    def __eq__(self, other):
        try:
            me, you = self.get_floats(other)
            if type(other) == type(self):
                return me == you
            else:
                return NotImplemented
        except:
            print "EXCEPTION IN Version.__eq__ (self = \"{0}\", other = \"{1}\")".format(str(self), str(other))
            traceback.print_exc()

    def __ne__(self, other):
        try:
            me, you = self.get_floats(other)
            if type(other) == type(self):
                return me != you
            else:
                return NotImplemented
        except:
            print "EXCEPTION IN Version.__ne__ (self = \"{0}\", other = \"{1}\")".format(str(self), str(other))
            traceback.print_exc()

    def __gt__(self, other):
        try:
            me, you = self.get_floats(other)
            if type(other) == type(self):
                return me > you
            else:
                return NotImplemented
        except:
            print "EXCEPTION IN Version.__gt__ (self = \"{0}\", other = \"{1}\")".format(str(self), str(other))
            traceback.print_exc()

    def __ge__(self, other):
        try:
            me, you = self.get_floats(other)
            if type(other) == type(self):
                return me >= you
            else:
                return NotImplemented
        except:
            print "EXCEPTION IN Version.__ge__ (self = \"{0}\", other = \"{1}\")".format(str(self), str(other))
            traceback.print_exc()

    def get_floats(self, other):
        try:
            me = float("0." + "".join(re.findall(r"\d", self)))
            you = other != None and float("0." + "".join(re.findall(r"\d", other))) or None

            return me, you
        except:
            print "EXCEPTION IN Version.get_floats (self = \"{0}\", other = \"{1}\")".format(str(self), str(other))
            traceback.print_exc()
            return None

class ConfigParser(KivyConfigParser):
    def __init__(self, *args, **kwargs):
        KivyConfigParser.__init__(self, *args, **kwargs)
        self.getboolean = self.getbool

    def get(self, section, option):
        try:
            return KivyConfigParser.get(self, section, option)
        except NoOptionError:
            self.set(section, option, "off")
            return "off"

    def getbool(self, section, option):
        try:
            return KivyConfigParser.getboolean(self, section, option)
        except NoOptionError:
            self.set(section, option, "off")
            return False

    def set(self, *args, **kwargs):
        KivyConfigParser.set(self, *args, **kwargs)
        self.write()

    def setbool(self, section, option, value):
        self.set(section, option, "on" if value else "off")

    def toggle(self, section, option):
        self.setbool(section, option, not self.getbool(section, option))