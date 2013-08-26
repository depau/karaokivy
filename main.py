#!/usr/bin/env python
# -*- coding: utf-8 -*-

# karaokivy.py
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

__version__ = "0.2"

APP_NAME = "Karaokivy"
APP_NAME_SHORT = "karaokivy"
APP_DOMAIN = "org.davideddu.karaokivy"
APP_VERSION = __version__


# To be removed
SUPPORTED_FILES = ["*.mid", "*.midi", "*.MID", "*.MIDI", "*.kar", "*.KAR", "*.mp3"]

LABEL_TEXT = """Karaokivy"""

import os, sys, argparse, imp, misc, shutil, subprocess
join, exists = os.path.join, os.path.exists

from ui import *
from plugin_utils import PluginManager

import kivy
from kivy import metrics, resources
from kivy.app import App
from kivy.atlas import Atlas
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import NumericProperty, BoundedNumericProperty,\
                            ObjectProperty, StringProperty, DictProperty,\
                            ListProperty, OptionProperty
from kivy.utils import platform as core_platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.bubble import Bubble, BubbleButton
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.utils import platform as core_platform
# Might be win, linux, android, macosx, ios, unknown
platform = core_platform()


if platform == "android":
    import android
    from jnius import autoclass
    Environment = autoclass("android.os.Environment")
    ContextWrapper = autoclass("android.content.ContextWrapper")

distro = None
if platform == "linux":
    dpkg = subprocess.Popen(["which", "dpkg"])
    rpm = subprocess.Popen(["which", "rpm"])
    pacman = subprocess.Popen(["which", "pacman"])
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

# check_env
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
        return "Your platform is not supported yet (detected platform: {0}).\nIf you think this is a bug, please contact me by filling the form in my website:\nhttp://davideddu.tuxfamily.org/contact.php\n\nThank you.".format(platform)

class Karaokivy(App):
    use_kivy_settings = False
    icon = "atlas://data/images/logo/logo_32"
    volume = BoundedNumericProperty(50, min=0, max=100)
    speed = BoundedNumericProperty(50, min=0, max=100)
    pitch = BoundedNumericProperty(50, min=0, max=100)
    theme = StringProperty("Default")
    themepath = StringProperty("")
    # FIXME
    plugin_scope = OptionProperty("main_window", options=("main_window", "lyrics_window", "remote_control_window"))
    # "nfl" means "no file loaded"
    state = OptionProperty("nfl", options=["nfl", "stop", "play", "pause", "busy"])
    file = StringProperty("")
    curdir = curdir
    karlabel = ObjectProperty(None, allownone=True)
    image = ObjectProperty(None, allownone=True)
    tb = ObjectProperty(None, allownone=True)
    fmthumbs = DictProperty({})
    _app_directory = None

    __events__ = ("on_load_plugins",
                  "on_plugins_loaded",
                  "on_gui_build",
                  "on_gui_built",
                  "on_eos",
                  "on_file_opened",
                  "on_pbplay",
                  "on_pbpause",
                  "on_pbresume")

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

        kv = join(self.themepath, "theme.kv")

        if os.path.exists(kv):
            self.load_kv(kv)

    def build_settings(self, settings):
        settings.register_type("color", SettingColor)
        settings.register_type("font", SettingFont)
        settings.register_type("soundfont", SettingSoundFont)
        settings.register_type("many_options", SettingManyOptions)

        with open(join(curdir, "appearance.json"), "r") as j:
            json = j.read()
            themes = os.listdir(join(curdir, "themes"))
            themes.sort()
            json = json.replace("#!?!?!?#", jsonize_list(themes))
            settings.add_json_panel('Appearance', self.config, data=json)
        with open(join(curdir, "sound.json"), "r") as json:
            settings.add_json_panel('Sound', self.config, data=json.read())

        settings.bind(on_config_change=self.on_config_change)

        self.dispatch("on_load_plugins")

        self.pm = PluginManager(scope=self.plugin_scope, app_domain=APP_DOMAIN, curdir=curdir)

        plugpanel = PluginsPanel(title="Plug-ins")
        for plugin in self.pm.available_plugins.keys():
            plugpanel.plugins_box.add_widget(PluginItem(manifest=self.pm.available_plugins[plugin]))

        settings.add_widget(plugpanel)



    def on_config_change(self, *args, **kwargs): # config, section, key, value):
        #print args, kwargs
        try:
            section = args[-3]
            key = args[-2]
            value = args[-1]

            if section == "graphics" and key == "fullscreen":
                self.config.set("Karaokivy", key, (value in ("auto", "yes", "1", "fake") and "auto" or "0"))
                self.config.write()
            elif section == "Karaokivy" and key == "fullscreen":
                Config.set("graphics", key, value)
                Config.write()
        except IndexError:
            print args, kwargs

    def on_load_plugins(self):
        pass

    def on_plugins_loaded(self):
        pass

    def on_gui_build(self):
        pass

    def on_gui_built(self):
        pass

    def on_eos(self):
        pass

    def on_file_opened(self, file):
        pass

    def on_pbplay(self):
        pass

    # FIXME: these names cannot be used!
    def on_pbpause(self):
        pass

    def on_pbresume(self):
        pass
    # /FIXME

    def ui_playpause(self, button):
        print "play/pause"
        if self.state == "stopped":
            self.dispatch("on_pbplay")
        elif self.state == "paused":
            self.dispatch("on_pbresume")
        elif self.state == "playing":
            self.dispatch("on_pbpause")

    def open_file_dialog(self, *args, **kwargs):
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

    def on_eos(self, *args, **kwargs):
        try: self.root.remove_widget(self.karlabel)
        except: pass
        self.root.add_widget(self.image)
        #self.root.add_widget(self.karlabel)
        self.karlabel.text = "Karaokivy"
        #self.karlabel.font_name = font_manager.findfont("OpenComicFont", fallback_to_default=True)
        self.tb_playpause.icon = "atlas://data/images/defaulttheme/media-playback-start"


    def open_file(self, instance=None, value=None, file=None):
        if file == None:
            file = self.chooser.selection[0]
            try:
                self.open_popup.dismiss()
            except:
                pass
        self.file = file
        self.dispatch("on_file_opened", self.file)

    def get_theme_path(self, theme):
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
    def get_config(filename="settings.ini"):
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

    def on_stop(self, *args):
        for i in self.fmthumbs.values():
            os.remove(i)
        self.fmthumbs = {}

class FallbackApp(App):
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

def uniq(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]

def jsonize_list(seq):
    s = "["
    for i in seq:
        i = i.replace('"', r'\"')
        s += '"'
        s += i
        s += '", '
    s = s[:-2] + "]"
    return s

def get_font(font):
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Karaokivy, a free karaoke player for GNU/Linux")
    parser.add_argument("song", default=None, nargs="?", help="Song to open at startup.", metavar="/path/to/file")
    parser.add_argument("-n", "--no-autoplay", action='store_false', default=True, required=False, help="If you specify a song, this will prevent it from starting automatically, otherwise it will be ignored.", dest="autoplay")
    parser.add_argument("-r", "--reset-settings", dest="reset", default=False, action='store_true', required=False, help="Resets settings to default.")
    parser.add_argument("-V", '--version', action='version', help="Displays the current version and exits", version='{0} {1}'.format(APP_NAME, APP_VERSION))
    args = parser.parse_args()
    ret = check_env()
    if ret == True:
        Karaokivy().run()
    else:
        FallbackApp(message=ret).run()
