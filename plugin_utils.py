# -*- coding: utf-8 -*-

# plugin_utils.py
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

import os, sys, imp, json, re, mimetypes, misc, traceback
from os.path import dirname, basename, join, exists, normpath, isdir, splitext
from ConfigParser import NoOptionError
from kivy.app import App
from kivy.config import ConfigParser as KivyConfigParser
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.properties import NumericProperty, BoundedNumericProperty,\
                            ObjectProperty, StringProperty, DictProperty,\
                            ListProperty, OptionProperty, BooleanProperty
from kivy.utils import platform as core_platform
# Might be win, linux, android, macosx, ios, unknown
platform = core_platform()

class PluginManager(EventDispatcher):
    scope = OptionProperty("main_window", options=("main_window", "lyrics_window", "remote_control_window"))
    available_plugins = DictProperty({})
    loaded_plugins = DictProperty({})
    app_domain = StringProperty("")
    curdir = StringProperty(os.path.dirname(os.path.realpath(__file__)))
    reset_plugins = BooleanProperty(False)
    players = DictProperty([])
    lyr_providers = DictProperty([])

    def __init__(self, **kwargs):
        super(PluginManager, self).__init__(**kwargs)
        with open(join(self.curdir, "data/licenses.json"), "r") as j:
            self.licenses = json.load(j)
        self.cfg = ConfigParser()
        self.cfg.adddefaultsection("Plugins")
        self.priorities = misc.DontBotherShelf(App.get_running_app().get_config("priorities.bin"))
        self.priorities.set_default("PluginsPriority", MimeDict())
        self.priorities.set_default("PluginsDefaults", ExtDict())
        self.priorities.set_default("LyricsProvidersPriority", ExtDict())
        self.priorities.set_default("LyricsProvidersDefaults", ExtDict())

        cfg = App.get_running_app().get_config("plugins.ini")
        if self.reset_plugins:
            try:
                os.remove(cfg)
            except OSError:
                pass
        self.cfg.read(cfg)

        paths = self.get_plugins_paths()

        # Reversing the list puts the system paths (usually not writable in
        #   secure OSes) at the beginning, and user paths at the end, so that
        #   if the user updated the plugin, the updated version is loaded.
        for path in reversed(paths):
            for i in (join(path, f) for f in os.listdir(path)):
                if isdir(i):
                    if exists(join(i, "manifest.json")):
                        plugin = self.load_plugin_manifest(join(i, "manifest.json"))
                        try:
                            self.available_plugins[str(plugin.name)] += {plugin.version: plugin}
                        except KeyError:
                            self.available_plugins[str(plugin.name)] = {plugin.version: plugin}

        for plugin in self.available_plugins:
            versions = sorted(self.available_plugins[plugin].keys())
            latest = self.available_plugins[plugin][versions[-1]]
            plug = self.load_plugin(latest)

            if plug == False:
                latest.active = False
            elif type(plug) == type(str()):
                latest.errs_loading = plug
                latest.active = False
            elif type(plug) == type(os):
                self.loaded_plugins[latest.name] = {"manifest":latest, "module":plug}
                Logger.info("PluginManager: Plug-in {0} loaded".format(latest.name))
                if "player" in latest.purposes:
                    self.players[latest] = plug.get_player()
                elif "lyrics_provider" in latest.purposes:
                    self.lyr_providers[latest] = plug.get_lyr_handler()
            else:
                Logger.warning("PluginManager: Plugin {name} ({obj}) is of an unrecognised type: {type}".format(latest.name, str(plug), str(type(plug))))

    def choose_player(self, obj):
        # candidates1 = {}
        # if type(obj) == type(str()):
        #     candidates0 = {}
        #     mime = MimeType(mimetypes.guess_type(obj))
        #     for manifest in self.players:
        #         for m in manifest.player.supported_mimes:
        #             if m == mime:
        #                 candidates0[manifest] = self.players[manifest]

        #     for manifest in candidates0:
        #         p = candidates0[manifest]
        #         for ext in p.extensions():
        #             if obj.lower().endswith(ext):
        #                 candidates1[manifest] = self.players[manifest]
        # else:
        #     candidates1 = self.players

        # candidates2 = {}
        # for manifest in candidates1:
        #     p = candidates1[manifest]
        #     if p.supports(obj):
        #         candidates2[manifest] = self.players[manifest]

        # if type(obj) == type(str()):
        #     default = self.priorities["PluginsDefaults"][splitext(obj)[1]]
        #     if default:
        #         for i in candidates2:
        #             if default == i.name:
        #                 return [{manifest: i, player: candidates2[i]}]

        #################################################################

        return [{"manifest": self.players.keys()[0], "player": self.players.values()[0]}]




    def load_plugin(self, manifest):
        load = self.should_load_plugin(manifest)
        if load and type(load) == type(bool()):
            try:
                return self._load(splitext(manifest.name)[1][1:], [manifest.path])
            except ImportError, err:
                load = "[b]ImportError:[/b] {0}".format(str(err))
        if type(load) == type(str()):
            return load

        return False if load == False else None

    def _load(self, name, path):
        try:
            f, p, d = imp.find_module(name, path)
            return imp.load_module(name, f, p, d)
        finally:
            try:
                f.close()
            except NameError:
                pass
            except AttributeError:
                pass

    def load_plugin_manifest(self, man):
        with open(man, "r") as f:
            manifest = json.load(f)
        return Plugin.create_from_manifest(manifest, dirname(man), self.app_domain, self)

    def should_load_plugin(self, manifest):
        if not self.cfg.getbool("Plugins", manifest.name): # check if the plugin is disabled
            return False
        if platform not in manifest.platforms:
            return "Operating system not supported"
        for module in manifest.depends_py:
            try:
                m = imp.find_module(module)
                if m[0]:
                    m[0].close()
            except ImportError:
                return "Cannot find module \"{0}\"".format(module)
        missing = []
        not_loaded = []
        for plugin in manifest.depends_kk:
            if plugin not in self.available_plugins:
                missing += plugin
            elif not self.should_load_plugin(self.available_plugins[plugin]):
                not_loaded += plugin
        if len(missing) > 0:
            return "The following plugins are not installed: [i]{0}[/i]".format(misc.repr_list(missing))
        if len(not_loaded) > 0:
            return "The following plugins are required but cannot be loaded: [i]{0}[/i]".format(misc.repr_list(missing))

        # Both the player and the lyrics provider must run in the remote control window;
        # the lyrics will be passed to the other window in a different way
        if ("player" in manifest.purposes or "lyrics_provider" in manifest.purposes) and self.scope == "lyrics_window":
            return False
        if "ui_expansion" in manifest.purposes and self.scope not in manifest.ui_expansion.scopess:
            return False
        if "feature" in manifest.purposes and self.scope not in manifest.feature.scopes:
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
        Logger.debug("PluginManager: Toggled " + plugin)
        if state != None:
            self.cfg.setbool("Plugins", plugin, state)
        else:
            self.cfg.toggle("Plugins", plugin)

        try:
            App.get_running_app()._needsrestart = True
        except:
            pass

class Plugin(EventDispatcher):
    active = BooleanProperty(False)
    errs_loading = ObjectProperty(None, allownone=True)
    name = StringProperty("")
    title = StringProperty("")
    version = ObjectProperty(None)
    short_description = StringProperty("")
    long_description = StringProperty("")
    homepage = StringProperty("")
    authors = ListProperty([])
    platforms = ListProperty([])
    requires = ListProperty([])
    depends_kk = ListProperty([])
    depends_py = ListProperty([])
    purposes = ListProperty([])
    player = ObjectProperty(None)
    lyrics_provider = ObjectProperty(None)
    ui_expansion = ObjectProperty(None)
    feature = ObjectProperty(None)
    module = ObjectProperty(None, allownone=True)
    stock = BooleanProperty(False)
    system = BooleanProperty(False)
    path = StringProperty("")
    manager = ObjectProperty(None)
    license = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(Plugin, self).__init__(**kwargs)
        self.bind(active=self._toggle)

    def _toggle(self, *args):
        self.manager.toggle(self.name, self.active)

    @staticmethod
    def create_from_manifest(manifest, path, domain, manager):
        Logger.debug("PluginManager: Loading plug-in from \"{0}\"".format(path))
        kwargs = {}
        for i in manifest.keys():
            if not "." in i:
                if type(manifest[i]) == type(u""):
                    kwargs[str(i)] = manifest[i]
                else:
                    kwargs[str(i)] = manifest[str(i)]
        kwargs["version"] = Version(manifest["version"])
        kwargs["stock"] = manifest["name"].startswith(domain)
        kwargs["system"] = path.startswith(sys.prefix)
        kwargs["path"] = path
        kwargs["manager"] = manager
        try:
            # When license is a non-string object it should raise an exception
            manifest["license"].lower()
            kwargs["license"] = manager.licenses[manifest["license"]]
        except:
            kwargs["license"] = manifest["license"]
            if not "url" in kwargs["license"].keys():
                kwargs["license"]["url"] = None
        if not "theme" in manifest["purposes"]:
            kwargs["active"] = manager.cfg.getbool("Plugins", manifest["name"])
        if "all" in manifest["platforms"]:
            kwargs["platforms"] = ["linux", "win", "android", "macosx"]
        if "player" in manifest["purposes"]:
            kwargs["player"] = PurposePlayer(supported_mimes=[MimeType(i) for i in manifest["player.supported_mimes"]], supported_actions=manifest["player.supported_actions"], media_type=manifest["player.media_type"])
        if "lyrics_provider" in manifest["purposes"]:
            kwargs["lyrics_provider"] = PurposeLyricsProvider(supported_lrc_types=manifest["lyrics_provider.supported_lrc_types"], lyrics_type=manifest["lyrics_provider.lyrics_type"])
        if "ui_expansion" in manifest["purposes"]:
            kwargs["ui_expansion"] = PurposeUIExpansion(scopes=manifest["ui_expansion.scopes"])
        if "feature" in manifest["purposes"]:
            kwargs["feature"] = PurposeFeature(scopes=manifest["feature.scopes"])
        return Plugin(**kwargs)

class Purpose(EventDispatcher):
    pass

class PurposePlayer(Purpose):
    supported_mimes = ListProperty([])
    supported_actions = ListProperty([])
    media_type = OptionProperty("audio", options=["audio", "video"])

class PurposeLyricsProvider(Purpose):
    supported_lrc_types = ListProperty([])
    lyrics_type = OptionProperty("text", options=("text", "graphic"))

class PurposeUIExpansion(Purpose):
    scopes = ListProperty([])

class PurposeFeature(Purpose):
    scopes = ListProperty([])

# Clever way to compare version numbers
class Version(str):
    """Useful object to store version numbers. Unlike strings, you
    will be able to compare this kind of version numbers using Python's
    normal comparison operations.
    """
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

class MimeType(str):
    """String object tweaked to work better with MIME types. For example,
    MimeType("audio/*") == MimeType("audio/mpeg")
    will return True.
    """

    def __eq__(self, other):
        me, you = str(self), str(other)
        if "*" in me:
            return me.replace("*", "") in you
        elif "*" in you:
            return you.replace("*", "") in me
        else:
            return me == you

    def __ne__(self, other):
        me, you = str(self), str(other)
        if "*" in me:
            return not me.replace("*", "") in you
        elif "*" in you:
            return not you.replace("*", "") in me
        else:
            return me != you

class MimeDict(dict):
    def __getitem__(self, item):
        for i in self.keys():
            if item == i:
                return super(MimeDict, self).__getitem__(i)
        else:
            return None

class ExtDict(dict):
    def __getitem__(self, item):
        item = item.lower()
        if item.startswith("."):
            item = item[1:]
        for i in self.keys():
            if item == i:
                return super(ExtDict, self).__getitem__(i)
        else:
            None

    def __setitem__(self, item, value):
        item = item.lower()
        if item.startswith("."):
            item = item[1:]

        super(ExtDict, self).__setitem__(item, value)

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
        print "setbool"
        self.set(section, option, "on" if value else "off")

    def toggle(self, section, option):
        self.setbool(section, option, not self.getbool(section, option))

