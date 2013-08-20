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

APP_NAME = "Karaokivy"
APP_NAME_SHORT = "karaokivy"
DOTTED_APP_NAME = "org.bashkaraoke.karaokivy"
APP_VERSION = "0.1"
SUPPORTED_FILES = ["*.mid", "*.midi", "*.MID", "*.MIDI", "*.kar", "*.KAR"]

LABEL_TEXT = """Karaokivy"""

import os, sys, argparse, shutil, subprocess
join, exists = os.path.join, os.path.exists

from bashkaraoke import misc

import kivy
from kivy import metrics, resources

from kivy.app import App
from kivy.atlas import Atlas
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import NumericProperty, BoundedNumericProperty,\
                            ObjectProperty, StringProperty, DictProperty,\
                            ListProperty, OptionProperty
from kivy.utils import platform as core_platform
platform = core_platform()
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

from ui import *

#try:
#    import gettext
#    gettext.bindtextdomain('bashkaraoke-gtk')
#    gettext.textdomain('bashkaraoke-gtk')
#    from gettext import gettext as _
#except:
#    # This method is defined if gettext is not available
def _(msg, arg1=None, arg2=None, arg3=None):
    return str(msg
)

class Container(object):
    pass
container = Container()

curdir = os.path.dirname(os.path.realpath(__file__))
themedir = join(curdir, "themes/Default/")

def check_env():
    if not exists(join(misc.home, ".config/karaokivy")):
        os.makedirs(join(misc.home, ".config/karaokivy"))
    if not exists(join(misc.home, ".local/share/karaokivy")):
        os.makedirs(join(misc.home, ".local/share/karaokivy"))

    #
    # if not exists(join(misc.home, ".config/bashkaraoke/")):
    #     if exists(join(misc.home, ".bashkaraoke")):
    #         shutil.move(join(misc.home, ".bashkaraoke"), join(misc.home, ".config/bashkaraoke"))
    #     else:
    #         os.mkdir(join(misc.home, ".config/bashkaraoke/"))
    # with open(join(misc.home, ".config/bashkaraoke/.pid"), "w") as pid:
    #     pid.write('BK_OUT-NOT-STARTED')
    # with open(join(misc.home, ".config/bashkaraoke/.time"), "w") as time:
    #     time.write('')
    # if not exists(join(misc.home, ".config/bashkaraoke/database.txt")):
    #     with open(join(misc.home, ".config/bashkaraoke/database.txt"), "w") as db:
    #         db.write("[Bash!Karaoke Database]\n")
    # with open(join(misc.home, ".config/bashkaraoke/database.txt"), "r") as db:
    #     global old_db
    #     old_db = not "[Bash!Karaoke Database]" in db.read()

class Karaokivy(App):
    use_kivy_settings = False
    icon = "atlas://data/images/logo/logo_32"
    volume = BoundedNumericProperty(50, min=0, max=100)
    speed = BoundedNumericProperty(50, min=0, max=100)
    pitch = BoundedNumericProperty(50, min=0, max=100)
    theme = StringProperty("Default")
    themepath = StringProperty("")
    # "nfl" means no file loaded
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
        self.root = Root()

        self.karlabel = self.root.karlabel
        self.image = self.root.image
        self.tb = self.root.tb

        Config.set("graphics", "fullscreen", self.config.get("Karaokivy", "fullscreen"))
        Config.write()

        self.dispatch("on_gui_build")

        self.root.remove_widget(self.karlabel)

        self.root.volume.bind(percentage=self.setter("volume"))
        self.root.pitch.bind(percentage=self.setter("pitch"))
        self.root.speed.bind(percentage=self.setter("speed"))

        # self.menu_button = Button(background_normal="atlas://data/images/defaulttheme/menu_normal", background_down="atlas://data/images/defaulttheme/menu_down", size_hint=(None, None), size=(40, 40), pos_hint={"right":0.5})
        # self.menu = DropDown(auto_width=False, width="100dp", dismiss_on_select=True)
        # self.menu.add_widget(Button(text="Open...", on_release=self.open_file_dialog, size_hint_y=None, height=40))
        # self.menu.add_widget(Button(text="Settings", on_release=self.open_settings, size_hint_y=None, height=40))
        # self.menu.add_widget(Button(text="Exit", on_release=self.stop, size_hint_y=None, height=40))
        
        # self.menu_button.bind(on_release=self.menu.open)

        #self.tb.right.add_widget(self.menu_button)

        #self.tb.right.anchor_x = "right"

        self.dispatch("on_gui_built")

        return self.root

    def build_config(self, config):
        config.app = self
        Config.app = self

        config.adddefaultsection("Karaokivy")
        config.adddefaultsection("BashKaraoke")
        config.setdefaults("Karaokivy", {
            "theme":        "Default",
            "fullscreen":   "no",
            "bg_type":      "Color",
            "bg_image":     "",
            "sung_color":   "#FF0000",
            "tosing_color": "#00FF00",
            "midi_player":  "Bash!Karaoke"})
        config.setdefaults("BashKaraoke", {
            "font_family":  "sans-serif",
            "background":   "#000000",
            "foreground_1": "green",
            "foreground_2": "red",
            "soundfont":    "",
            "supermode":    "auto",
            "use_gtk":      "false",
            "use_gsw":      "false",
            "use_buc":      "false",
            "extract_way":  "internal",
            "error_correction_chars": "0",
            "columns":      "24",
            "rows":         "3",
            "LANG":         "en_US.UTF-8",
            "char_encoding": "ISO-8859-1",
            "delimiter":    "______________________________________________",
            "karaoke_window": "true",
            "levels_window": "true",
            "channels_window": "false",
            "spectrogram_window": "false"})

        self.theme = str(self.config.get("Karaokivy", "theme"))
        self.themepath = self.get_theme_path(self.theme)
        resources.resource_add_path(self.themepath)

        kv = join(self.themepath, "theme.kv")

        if os.path.exists(kv):
            self.load_kv(kv)

        self.dispatch("on_load_plugins")

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
        with open(join(curdir, "bashkaraoke.json"), "r") as j:
            json = j.read()
            locales = str(subprocess.check_output(["locale", "-a"])).split("\n")[:-1]
            json = json.replace("#!?!?!?#", jsonize_list(locales))
            settings.add_json_panel('Advanced', self.config, data=json)

        settings.bind(on_config_change=self.on_config_change)

    def on_config_change(self, settings, config, section, key, value):
        if section == "graphics" and key == "fullscreen":
            config.app.config.set("Karaokivy", key, (value in ("auto", "yes", "1", "fake") and "auto" or "0"))
            config.app.config.write()
        elif section == "Karaokivy" and key == "fullscreen":
            Config.set("graphics", key, value)
            Config.write()
        elif section == "Karaokivy" and key == "theme":
            with open(join(os.path.dirname(self.get_application_config()), "theme"), "w") as theme:
                theme.write(value)

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

    def ui_previous(self, button):
        print "Previous"

    def ui_next(self, button):
        print "Next :)"

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
        self.karlabel.text = ""
        #self.karlabel.font_name = font_manager.findfont("OpenComicFont", fallback_to_default=True)
        self.tb_playpause.background_normal = "atlas://data/images/defaulttheme/play_normal"
        self.tb_playpause.background_down = "atlas://data/images/defaulttheme/play_down"


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
        if exists(join(misc.home, ".local/share/karaokivy/themes", theme)):
            return join(misc.home, ".local/share/karaokivy/themes", theme)
        elif exists(join(sys.prefix, "share/karaokivy/themes", theme)):
            return join(sys.prefix, "share/karaokivy/themes", theme)
        elif exists(join(sys.prefix, "local/share/karaokivy/themes", theme)):
            return join(sys.prefix, "local/share/karaokivy/themes", theme)
        else:
            try:
                p = self.get_theme_path("Default")
                return p
            except:
                return None

    def get_application_config(self, defaultpath='%(appdir)s/%(appname)s.ini'):
        if platform == 'android':
            defaultpath = '/sdcard/.%(appname)s.ini'
        elif platform == 'ios':
            defaultpath = '~/Documents/%(appname)s.ini'
        elif platform == 'win':
            defaultpath = join(os.environ["APPDATA"], "Karaokivy", "karaokivy.ini")
        else:
            defaultpath = '~/.config/karaokivy/settings.ini'
        return os.path.expanduser(defaultpath) % {'appname': "karaokivy", 'appdir': self.directory}

    def on_stop(self, *args):
        for i in self.fmthumbs.values():
            os.remove(i)
        self.fmthumbs = {}

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
    check_env()
    Karaokivy().run()