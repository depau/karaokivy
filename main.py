#!/usr/bin/env python
# -*- coding: utf-8 -*-

# karaokivy.py
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

__version__ = "0.2~us"

APP_NAME = "Karaokivy"
APP_NAME_LONG = "Karaokivy Karaoke Player"
APP_NAME_SHORT = "karaokivy"
APP_DOMAIN = "org.karaokivy" # Stock plugins will start with this prefix
APP_VERSION = __version__
APP_AUTHORS = [{"name": "Davide Depau", "email": "me@davideddu.org", "homepage": "http://davideddu.org"}]


# FIXME: plug-ins should tell if they are able to open some file
SUPPORTED_FILES = ["*.mid", "*.midi", "*.MID", "*.MIDI", "*.kar", "*.KAR", "*.mp3"]

LABEL_TEXT = """Karaokivy"""

import sys

# Prevent Kivy from detecting our arguments
argv = sys.argv[1:]
sys.argv = sys.argv[:1]
if "--" in argv:
    index = argv.index("--")
    kivy_args = argv[index+1:]
    argv = argv[:index]

    sys.argv.extend(kivy_args)


import os, sys, argparse, misc, shutil, subprocess, time
from os.path import join, exists
from ui import *
from plugin_utils import PluginManager
from plugin_base import PluginError, PlayerError, PlayerOSError,\
                        LyricsHandlerError, LyricsHandlerOSError

import kivy

kivy.require("1.8.0")

from kivy import metrics, resources
from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.lang import Builder, BuilderException
from kivy.logger import Logger
from kivy.properties import Property, NumericProperty, BoundedNumericProperty,\
                            ObjectProperty, StringProperty, DictProperty,\
                            ListProperty, OptionProperty
from kivy.utils import platform as core_platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.bubble import Bubble, BubbleButton
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.dropdown import DropDown
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.settings import Settings, SettingsWithSidebar
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from kivy.utils import platform as core_platform
import platform as platfm

# Might be win, linux, android, macosx, ios, unknown
platform = core_platform()


if platform == "android":
    import android
    from jnius import autoclass
    Environment = autoclass("android.os.Environment")
    ContextWrapper = autoclass("android.content.ContextWrapper")

distro = None
if platform == "linux":
    with open(os.devnull, "w") as devnull:
        dpkg = subprocess.Popen(["which", "dpkg"], stdout=devnull, stderr=devnull)
        rpm = subprocess.Popen(["which", "rpm"], stdout=devnull, stderr=devnull)
        pacman = subprocess.Popen(["which", "pacman"], stdout=devnull, stderr=devnull)
        dpkg.wait()
        rpm.wait()
        pacman.wait()
        if not dpkg.poll():
            distro = "debian"
        elif not rpm.poll():
            distro = "redhat"
        elif not pacman.poll():
            distro = "arch"
        else:
            distro = "other"


curdir = os.path.dirname(os.path.realpath(__file__))
themedir = join(curdir, "themes/Default/")

def check_env():
    """
    Checks if the needed directory are available and returns True if
    it's all ok, or a string that will be shown before exiting
    """
    if platform in ("linux", "macosx"):
        if not exists(join(misc.home, ".config/karaokivy")):
            os.makedirs(join(misc.home, ".config/karaokivy"))
        if not exists(join(misc.home, ".local/share/karaokivy")):
            os.makedirs(join(misc.home, ".local/share/karaokivy"))
        return True
    elif platform == "win":
        if not exists(join(os.environ["APPDATA"], "Karaokivy")):
            os.makedirs(join(os.environ["APPDATA"], "Karaokivy"))
        return True
    elif platform == "android":
        if Environment.getExternalStorageState() != Environment.MEDIA_MOUNTED:
            return "SD Card or internal storage not found.\nMake sure there is an SD card inserted and mounted,\nor that the internal storage is mounted."
        else:
            sdcard = Environment.getExternalStorageDirectory()
            if not exists(join(sdcard, ".karaokivy")):
                os.makedirs(join(sdcard, ".karaokivy"))
            return True
    else:
        return "Your platform is not supported yet (detected platform: {0}).\nIf you think this is a bug, please contact me by filling the form in my website:\nhttp://davideddu.org/contact.php\n\nThank you.".format(platform)

class Karaokivy(App):
    """Default interface for Karaokivy and base class for other interfaces.
    Inherits from kivy.app.App
    """
    use_kivy_settings = False

    icon = "atlas://data/images/logo/logo_32"
    """Icon of the application
    """

    volume = BoundedNumericProperty(50, min=0, max=100)
    """Current volume of the songs. Player plug-ins should update
    their back-ends when this value changes.
    volume is a kivy.properties.BoundedNumericProperty object
    """

    speed = BoundedNumericProperty(50, min=0, max=100)
    """Current speed of the songs. Player plug-ins should update
    their back-ends when this value changes.
    speed is a kivy.properties.BoundedNumericProperty object
    """

    pitch = BoundedNumericProperty(50, min=0, max=100)
    """Current pitch of the songs. Player plug-ins should update
    their back-ends when this value changes.
    pitch is a kivy.properties.BoundedNumericProperty object
    """

    theme = StringProperty("Default")
    themepath = StringProperty("")
    theme_plugin = DictProperty({"manifest": None, "module": None})
    plugin_scope = OptionProperty("main_window", options=("main_window", "lyrics_window", "remote_control_window"))

    state = OptionProperty("nfl", options=["nfl", "stop", "play", "pause", "busy"])
    """Playback state; it can be "nfl" (no file loaded), "stop", "play",
    "pause", "busy". Player plug-ins should listen to the changes of this property.
    state is a kivy.properties.OptionProperty object
    """

    file = StringProperty("")
    """File currently loaded.
    file is a kivy.properties.StringProperty object
    """

    curdir = curdir
    pm = ObjectProperty(None)
    """Plug-ins manager.
    pm is a kivy.properties.ObjectProperty object
    """

    karlabel = ObjectProperty(None, allownone=True)
    """Default lyrics label. Lyrics providers should NOT update its text
    directly, they will be queried for it automatically when needed.
    karlabel is a kivy.properties.ObjectProperty object
    """

    player = ObjectProperty(None, allownone=True)
    lyricsprovider = ObjectProperty(None, allownone=True)

    _needsrestart = BooleanProperty(False)

    fmthumbs = DictProperty({})
    _app_directory = None

    __events__ = ("on_load_plugin_settings",
                  "on_gui_build",
                  "on_gui_built",
                  "on_eos",
                  "on_file_opened")

    def __init__(self, cmdline=None, **kwargs):
        super(Karaokivy, self).__init__(**kwargs)
        if platform not in ("android", "ios"):
            self.settings_cls = SettingsWithSidebar

        self.cmdline = cmdline
        self.pm = PluginManager(scope=self.plugin_scope, app_domain=APP_DOMAIN,
                                curdir=curdir, reset_plugins=self.cmdline.reset_config)
        if self.cmdline.reset_config:
            try:
                os.remove(self.get_application_config)
            except OSError:
                pass

    def build(self):
        self.dispatch("on_gui_build")

        self.root = Root()

        self.karlabel = self.root.karlabel
        self.image = self.root.image
        self.tb = self.root.tb

        Config.set("graphics", "fullscreen", self.config.get("Karaokivy", "fullscreen"))
        Config.write()

        self.root.remove_widget(self.karlabel)

        self.root.volume.bind(percentage=self.setter("volume"))
        self.root.pitch.bind(percentage=self.setter("pitch"))
        self.root.speed.bind(percentage=self.setter("speed"))

        self.dispatch("on_gui_built")

        return self.root

    def build_config(self, config):
        config.app = self
        Config.app = self

        config.adddefaultsection("Karaokivy")
        config.setdefaults("Karaokivy", {
            "theme":        "Default",
            "fullscreen":   "no",
            "dual_screen":  "off",
            "bg_type":      "Color",
            "bg_image":     "",
            "bg_color":     "#000000",
            "sung_color":   "#FF0000",
            "tosing_color": "#00FF00",
            "font_family":  "sans-serif",
            "soundfont":    ""})

        self.theme = str(self.config.get("Karaokivy", "theme"))
        self.themepath = self.get_theme_path(self.theme)
        resources.resource_add_path(self.themepath)

        manifest = self.pm.load_plugin_manifest(join(self.themepath, "manifest.json"))
        plug = self.pm.load_plugin(manifest)

        self.theme_plugin = {"manifest": manifest, "module": plug}

        kv = join(self.themepath, "theme.kv")

        if os.path.exists(kv):
            self.load_kv(kv)

    def build_settings(self, settings):
        settings.register_type("color", SettingColor)
        settings.register_type("font", SettingFont)
        settings.register_type("soundfont", SettingSoundFont)
        settings.register_type("many_options", SettingManyOptions)

        with open(join(curdir, "data/appearance.json"), "r") as j:
            json = j.read()
            themes = os.listdir(join(curdir, "themes"))
            themes.sort()
            json = json.replace("#!?!?!?#", jsonize_list(themes))
            settings.add_json_panel('Appearance', self.config, data=json)
        with open(join(curdir, "data/sound.json"), "r") as json:
            settings.add_json_panel('Sound', self.config, data=json.read())

        settings.bind(on_config_change=self.on_config_change)

        plugpanel = PluginsPanel(title="Plug-ins")
        for plugin in self.pm.available_plugins.keys():
            versions = self.pm.available_plugins[plugin]
            latest = sorted(versions.keys())[-1]
            plugpanel.plugins_box.add_widget(PluginItem(manifest=self.pm.available_plugins[plugin][latest]))

        if settings.interface is not None:
            settings.interface.add_panel(plugpanel, plugpanel.title, plugpanel.uid)

        settings.bind(on_close=self.show_restart_popup)

        self.dispatch("on_load_plugin_settings", settings)

    def on_config_change(self, *args, **kwargs): # config, section, key, value):
        #print args, kwargs
        try:
            section = args[-3]
            key = args[-2]
            value = args[-1]

            if section == "graphics" and key == "fullscreen":
                self.config.set("Karaokivy", key, (value in ("auto", "yes", "1", "fake") and "auto" or "0"))
                self.config.write()
                self._needsrestart = True
            elif section == "Karaokivy" and key == "fullscreen":
                Config.set("graphics", key, value)
                Config.write()
                self._needsrestart = True
            elif section == "Karaokivy" and False:
                pass

        ######################### FIXME ##########################

        except IndexError:
            print args, kwargs

    def show_restart_popup(self, *args):
        if self._needsrestart:
            RestartPopup().open()
        self.close_settings()


    def on_load_plugin_settings(self, settings):
        """Dispatched after setting up the settings UI. Plugins that need a
        settings panel should use this event.
        """
        pass

    def on_gui_build(self):
        """Dispatched before setting up the UI. Don't add widget unless
        you add them into one of the default widgets or you are using this
        event in a theme.
        """
        pass

    def on_gui_built(self):
        """Dispatched after setting up the UI. Don't add widget unless
        you add them into one of the default widgets or you are using this
        event in a theme.
        """
        pass

    def on_eos(self):
        """Player plugins should dispatch this event after the song has
        finished or has been stopped.
        """
        try: self.root.remove_widget(self.karlabel)
        except: pass
        self.root.add_widget(self.image)
        #self.root.add_widget(self.karlabel)
        self.karlabel.text = "Karaokivy"
        #self.karlabel.font_name = font_manager.findfont("OpenComicFont", fallback_to_default=True)
        self.tb.playpause.icon = "atlas://data/images/defaulttheme/media-playback-start"

    def on_file_opened(self, file):
        """Dispatched after opening a file.
        """
        pass

    def show_file_dialog(self, *args, **kwargs):
        """Show the "open" dialog to load a new song.
        """
        print self.root.children
        content = BoxLayout(orientation="vertical")
        self.open_popup = Popup(size_hint=(.9, .9), content=content, title="Open song")
        self.chooser = KKFileChooser(filters=SUPPORTED_FILES, thumbs=self.fmthumbs)
        self.chooser.bind(thumbs=self.fmthumbs)
        content.add_widget(self.chooser)
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='OK', on_release=self.open_file)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel', on_release=self.open_popup.dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)
        self.open_popup.open()

    def open_file(self, *args, **kwargs):
        """Load a new song. Use the "filename" keyword argument,
        otherwise it will look for an open file chooser dialog and crash.
        """
        filename = kwargs["filename"] if "filename" in kwargs else None
        # Tell the plug-ins to stop the song, then tell them not to bother.
        if self.state in ("play", "pause"):
            self.state = "stop"
        self.state = "busy"
        if filename == None:
            filename = self.chooser.chooser.selection[0]
            try:
                self.open_popup.dismiss()
            except:
                pass

        if self.player:
            self.player.unload()
            
        self.player = self.choose_player(filename)(file=filename, _app=self)

        #if self.lyricsprovider:
        #    self.lyricsprovider.unload()
        #    del self.lyricsprovider

        #self.lyricsprovider = self.choose_lyr_provider(self.player.get_lyrics_filename())

        self.file = filename
        self.dispatch("on_file_opened", self.file)

    def choose_player(self, obj):
        players = self.pm.choose_player(obj)
        if len(players) > 1:
            NotImplemented
            ## FIXME
            return players[0]["player"]
        else:
            return players[0]["player"]

    def choose_lyr_provider(self, obj):
        lyr_providers = self.pm.choose_lyr_provider(obj)
        if len(lyr_providers) > 1:
            NotImplemented
            return lyr_providers[lyr_providers.keys()[0]]
        else:
            return lyr_providers[lyr_providers.keys()[0]]

    def set_playback_state(self, *args):
        self.state = self.tb.playpause.action
        if self.state == "play":
            self.tb.playpause.action = "pause"
        else:
            self.tb.playpause.action = "play"

    def open_file_error(self, exception):
        NotImplemented

    def get_theme_path(self, theme):
        """Search the default theme paths for "theme" and return it.
        It prefers local themes than system ones.
        """
        if platform == "linux":
            if exists(join(misc.home, ".local/share/karaokivy/themes", theme)):
                return join(misc.home, ".local/share/karaokivy/themes", theme)
            elif exists(join(sys.prefix, "local/share/karaokivy/themes", theme)):
                return join(sys.prefix, "local/share/karaokivy/themes", theme)
            elif exists(join(sys.prefix, "share/karaokivy/themes", theme)):
                return join(sys.prefix, "share/karaokivy/themes", theme)
            elif exists(join(curdir, "themes", theme)):
                return join(curdir, "themes", theme)
        elif platform == "win":
            if exists(join(os.environ["APPDATA"], "Karaokivy/themes", theme)):
                return join(os.environ["APPDATA"], "Karaokivy/themes", theme)
            elif exists(join(curdir, "themes", theme)):
                return join(curdir, "themes", theme)
        elif platform == "android":
            sdcard = Environment.getExternalStorageDirectory()
            if exists(join(sdcard, ".karaokivy/themes")):
                return join(sdcard, ".karaokivy/themes")
            elif exists(join(curdir, "themes", theme)):
                return join(curdir, "themes", theme)
        elif platform == "macosx":
            if exists(join(misc.home, ".karaokivy/themes")):
                return join(misc.home, ".karaokivy/themes")
            elif exists(join(curdir, "themes", theme)):
                return join(curdir, "themes", theme)
        if theme != "Default":
            try:
                p = self.get_theme_path("Default")
                return p
            except:
                return None
        else:
            return None

    @staticmethod
    def get_config(filename=""):
        """Platform-independent method to get the path for a configuration
        file. Note that the file is NOT created.
        Example:
        conf = Karaokivy.get_config("someplugin.ini")
        with open(conf, "w") as c:
            c.write("Plug-in Configuration")
        """

        if platform == 'android':
            filesdir = ContextWrapper.getFilesDir()
            try:
                # Check if it's writable, otherwise use SD card
                with open(join(filesdir, "does_not_exist"), "w") as f:
                    f.write("Hello world!")
                os.remove(join(filesdir, "does_not_exist"))

                return join(filesdir, filename)
            except OSError, IOError:
                return '/sdcard/.karaokivy/{0}'.format(filename)
        elif platform == 'ios':
            return os.path.expanduser('~/Documents/karaokivy/{0}'.format(filename))
        elif platform == 'win':
            return os.path.expanduser(join(os.environ["APPDATA"], "Karaokivy", filename))
        elif platform == "linux":
            return os.path.expanduser('~/.config/karaokivy/{0}'.format(filename))
        elif platform == "macosx":
            return os.path.expanduser("~/.karaokivy/{0}".format(filename))
        else:
            return "~/.karaokivy/{0}".format(filename)

    def get_application_config(self, defaultpath=None):
        return self.get_config("settings.ini")

    # Run when the app stops, not when the song stops!
    def on_stop(self, *args):
        for i in self.fmthumbs.values():
            os.remove(i)
        self.fmthumbs = {}

class FallbackApp(App):
    """This app will be used when the default one couldn't be
    used for example when the there isn't any SD card/internal
    storage mounted on Android, or if the platform is not supported.
    """

    message = StringProperty("")
    def build(self):
        root = BoxLayout(orientation="vertical")
        content = BoxLayout(orientation="vertical")
        label = Label(text=self.message, halign="center")
        btn = Button(text="Exit", size_hint_y=None, height="40dp", on_release=self.stop)
        content.add_widget(label)
        content.add_widget(btn)
        self.popup = Popup(size_hint=(.8, .5), title="Karaokivy", content=content, on_dismiss=self.stop)
        Clock.schedule_once(self.popup.open)
        return root

class ReportErrorApp(App):
    """This app will be executed when an exception occurs in the program,
    in order to allow the user to report it to the developers.
    """
    exception = StringProperty("")
    exc_info = ListProperty([])

    def build(self):
        root = BoxLayout(orientation="vertical")
        content = BoxLayout(orientation="vertical")
        label = Label(text="Please insert some details that will be reported to the developers\n(e.g. what were you doing when the problem occurred)", size_hint_y=None)
        self.entry = TextInput(text="(optional)", focus=True)
        self.entry.select_all()

        box1 = BoxLayout(orientation="horizontal", size_hint_y=None, height="30dp", spacing="20dp")
        self.restart = CheckBox(active=(platform not in ("android", "ios")), disabled=platform in ("android", "ios"), size_hint=(None, None), size=("50dp", "30dp"))
        box1.add_widget(self.restart)
        box1.add_widget(Label(text="Restart application", size_hint_x=None, size_hint_y=None, height="30dp"))
        box1.add_widget(Widget())

        box2 = BoxLayout(orientation="horizontal", size_hint_y=None, height="30dp", spacing="20dp")
        self.no_plugins = CheckBox(active=False, size_hint=(None, None), size=("50dp", "30dp"))
        box2.add_widget(self.no_plugins)
        box2.add_widget(Label(text="Disable all plug-ins", size_hint_x=None, size_hint_y=None, height="30dp"))
        box2.add_widget(Widget())

        box4 = BoxLayout(orientation="horizontal", size_hint_y=None, height="30dp", spacing="20dp")
        self.reset_settings = CheckBox(active=False, size_hint=(None, None), size=("50dp", "30dp"))
        box4.add_widget(self.reset_settings)
        box4.add_widget(Label(text="Reset settings", size_hint_x=None, size_hint_y=None, height="30dp"))
        box4.add_widget(Widget())

        box3 = BoxLayout(orientation="horizontal", size_hint_y=None, height="50dp")
        report_btn = Button(text="Report", size_hint_y=None, height="40dp", on_release=self.report)
        exit_btn = Button(text="Don't report", size_hint_y=None, height="40dp", on_release=self.quit)
        box3.add_widget(exit_btn)
        box3.add_widget(report_btn)

        content.add_widget(label)
        content.add_widget(self.entry)
        content.add_widget(box1)
        content.add_widget(box2)
        content.add_widget(box4)
        content.add_widget(box3)

        self.popup = Popup(size_hint=(.8, .8), title="An problem has occurred", content=content, on_dismiss=self.stop)
        Clock.schedule_once(self.popup.open)
        return root

    def report(self, *args):
        report = ""
        report += self.entry.text.replace("(optional)", "") + "\n\n---\n\n"
        report += "**Application:** {0}\n".format(APP_NAME)
        report += "**Version:** {0}\n".format(APP_VERSION)
        report += "**Platform:** {0}\n".format(platform)
        report += "**Distro:** {0}\n".format(platfm.dist())
        report += "**OS release:** {0}\n".format(platfm.release())
        if platform == "macosx":
            report += "**Mac version:** {0}\n".format(platfm.mac_ver)
        if platform == "win":
            report += "**Win32 version:** {0}\n".format(platfm.win32_ver())
        report += "**Uname:** {0}\n".format(platfm.uname())
        report += "**Python version:** {0}\n".format(platfm.python_version())
        report += "**Python branch:** {0}\n".format(platfm.python_branch())        
        report += "**Python revision:** {0}\n".format(platfm.python_revision())
        report += "**Python build:** {0}\n".format(platfm.python_build())
        report += "**Python implementation:** {0}\n".format(platfm.python_implementation())
        report += "**Python compiler:** {0}\n".format(platfm.python_compiler())
        report += "**Kivy version:** {0}\n".format(kivy.__version__)
        report += "**Prefix:** {0}\n".format(sys.prefix)
        report += "\n\n---\n\n<pre>\n"
        report += self.exception
        report += "</pre>"

        exc = traceback.format_exception_only(*self.exc_info[0:2])[0].split(":")[0]
        last = traceback.format_tb(self.exc_info[-1])[-1].replace("  File", "file").split("\n")[0].replace(misc.home, "~")

        title = "{exception} in {file}".format(exception=exc, file=last)

        from urllib import quote

        open_url("https://github.com/Davideddu/Karaokivy/issues/new?title={title}&body={body}&labels=bug".format(title=quote(title), body=quote(report)))

        self.quit()

    def quit(self, *args):
        if self.restart.active:
            args = [sys.executable, sys.argv[0]]
            if self.no_plugins.active:
                args.append("--disable-plugins")
            if self.reset_settings.active:
                args.append("--reset-settings")
            print args
            os.execlp(sys.executable, *args)
            print args
        else:
            self.dispatch("on_stop")
            sys.exit()


def uniq(seq):
    """Removes all the duplicates in seq and returns a new list.
    """

    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]

def jsonize_list(seq):
    return json.dumps(seq)
    
    # s = "["
    # for i in seq:
    #     i = i.replace('"', r'\"')
    #     s += '"'
    #     s += i
    #     s += '", '
    # s = s[:-2] + "]"
    # return s

def get_font(font):
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Karaokivy, a free open-source karaoke player", epilog="If you want to pass an argument directly to Kivy, please put \"--\" before Kivy arguments. Example: \"karaokivy -nf mysong.mp3 -- -f\". To get the list of Kivy arguments, use \"-- --help\".")
    parser.add_argument("song", default=None, nargs="?", help="Song to open at startup.", metavar="/path/to/file")
    parser.add_argument("-n", "--no-autoplay", action='store_false', default=True, required=False, help="If you specify a song, this will prevent it from starting automatically.", dest="autoplay")
    parser.add_argument("-r", "--reset-settings", dest="reset_config", default=False, action='store_true', required=False, help="Resets the settings to their default values.")
    parser.add_argument("-d", "--disable-plugins", dest="disable_plugins", default=False, action='store_true', required=False, help="Don't load any plug-in for this session (you won't be able to play anything")
    parser.add_argument("-V", '--version', action='version', help="Displays the current version and exits", version='{0} {1}'.format(APP_NAME, APP_VERSION))
    args = parser.parse_args(argv)
    ret = check_env()
    if ret == True:
        #try:
            Karaokivy(cmdline=args).run()
        #except:
        #    exc_info = sys.exc_info()
        #    exception = traceback.format_exc()
        #    ReportErrorApp(exception=exception, exc_info=exc_info).run()
    else:
        FallbackApp(message=ret).run()
