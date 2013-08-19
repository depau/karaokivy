# -*- coding: utf-8 -*-

# ui.py
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

import os, sys, json, mimetypes, subprocess, traceback
mimetypes.add_type("image/jpeg", ".JPG")
mimetypes.add_type("image/jpg", ".jpg")
mimetypes.add_type("image/jpeg", ".jpg")
from os.path import dirname, basename, join, exists
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from tempfile import mktemp

from pygame import font as fonts

from kivy.adapters.listadapter import ListAdapter
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.properties import NumericProperty, BoundedNumericProperty,\
						    ObjectProperty, StringProperty, DictProperty,\
						    ListProperty, OptionProperty
from kivy.resources import resource_find
from kivy.utils import get_color_from_hex
from kivy.uix.actionbar import ActionButton, ActionBar, ActionView, ActionOverflow, ActionGroup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.bubble import Bubble, BubbleButton
from kivy.uix.button import Button
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.filechooser import FileChooserController, FileChooserIconView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.listview import ListItemButton, ListView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.settings import SettingItem, SettingSpacer
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

# "opsys" is set to "android" if running on an Android Linux device,
# to "linux" if running on a generic GNU/Linux or BSD distro, to "macosx"
# if running on a Mac and to "win" if running on Windows.
opsys = "linux"

def hide_keyboard(*args, **kwargs):
    pass

try: 
    import android
    print "Running an Android device"
    android.init()
    #browser = android.AndroidBrowser()
    opsys = "android"
    def hide_keyboard(*args, **kwargs):
        android.hide_keyboard()
except ImportError:
    if sys.platform.startswith('darwin'):
        opsys = "macosx"
    elif os.name == 'nt':
        opsys = "win"
    elif os.name == "posix":
        opsys = "linux"

# Took from Python 2.7 "user" module; Android support added
home = os.curdir                        # Default
if opsys == "android":
    home = "/mnt/sdcard"
elif 'HOME' in os.environ:
    home = os.environ['HOME']
elif os.name == 'posix':
    home = os.path.expanduser("~/")
elif os.name == 'nt':                   # Contributed by Jeff Bauer
    if 'HOMEPATH' in os.environ:
        if 'HOMEDRIVE' in os.environ:
            home = os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']
        else:
            home = os.environ['HOMEPATH']


class Root(BoxLayout):
    karlabel = ObjectProperty(None)
    image = ObjectProperty(None)
    tb = ObjectProperty(None)
    volume = ObjectProperty(None)
    speed = ObjectProperty(None)
    pitch = ObjectProperty(None)

class Toolbar(BoxLayout):
    left = ObjectProperty(None)
    center = ObjectProperty(None)
    right = ObjectProperty(None)

class ToolbarSection(BoxLayout):
    position = StringProperty("")
    spacers = ListProperty([None])

    # A quick and dirty way to add new widgets between the spacers
    def add_widget(self, widget, index=None):
        print "SPACING", self.position
        if self.spacers[0]:
            for i in self.spacers:
                self.remove_widget(i)
        args = [widget]
        if index: args.append(index)
        super(ToolbarSection, self).add_widget(*args)
        if self.position in ("left", "right"):
            print "Both"
            self.spacers = [Widget()]
        if self.position == "left":
            super(ToolbarSection, self).add_widget(self.spacers[0])
        elif self.position == "right":
            super(ToolbarSection, self).add_widget(self.spacers[0], len(self.children))
        else:
            self.spacers = [Widget(), Widget()]
            super(ToolbarSection, self).add_widget(self.spacers[0])
            super(ToolbarSection, self).add_widget(self.spacers[1], len(self.children))

class ScaleLabel(Label): 
    ratio = NumericProperty(0.1)

    def __init__(self, **kwargs):
        super(ScaleLabel, self).__init__(**kwargs)
        self.bind(size=self.rescale, size_hint=self.rescale, texture_size=self.set_ratio, font_name=self.set_ratio)

        Clock.schedule_once(self.set_ratio_and_rescale, 0.7)
 
    def set_ratio_and_rescale(self, *args, **kwargs):
        self.set_ratio()
        self.rescale()

    def set_ratio(self, *args):
        try:
            if self.size[0] < self.texture_size[0] or self.size[0] - self.texture_size[0] >= 100:
                self.ratio = round(self.ratio / (float(self.texture_size[0]) / self.size[0]), 4)
        except ZeroDivisionError:
            pass

    def rescale(self, obj=None, val=None):
        self.font_size = self.size[0] * self.ratio

class ReadyActionBar(ActionBar):
    pass

class SliderButton(ActionButton):
    percentage = NumericProperty(50)
    label = StringProperty("")
    type = OptionProperty("volume", options=["volume", "pitch", "speed"])
    icons = {"volume":
                {"high":     "atlas://data/images/defaulttheme/audio-volume-high",
                 "medium":   "atlas://data/images/defaulttheme/audio-volume-medium",
                 "low":      "atlas://data/images/defaulttheme/audio-volume-low",
                 "none":     "atlas://data/images/defaulttheme/audio-volume-muted"},
             "speed":
                {"high":     "atlas://data/images/defaulttheme/speed_fast",
                 "medium":   "atlas://data/images/defaulttheme/speed_normal",
                 "low":      "atlas://data/images/defaulttheme/speed_slow",
                 "none":     "atlas://data/images/defaulttheme/speed_slow"},
             "pitch":
                {"high":     "atlas://data/images/defaulttheme/pitch_high",
                 "medium":   "atlas://data/images/defaulttheme/pitch_medium",
                 "low":      "atlas://data/images/defaulttheme/pitch_low",
                 "none":     "atlas://data/images/defaulttheme/pitch_low"},
             "close":        "atlas://data/images/defaulttheme/cancel"}


    def __init__(self, **kwargs):
        super(SliderButton, self).__init__(**kwargs)
        if self.type == "volume":
            self.reset_value = 0
            self.reset_text = "Mute"
        else:
            self.reset_value = 50
            self.reset_text = "Reset"

        App.get_running_app().bind(on_start=self.update_icons)
        self.bind(on_release=self._open)
        self.update_icons()

    def _open(self, *args, **kwargs):
        try:
            self.remove_widget(self.bubble)
            self.percentage = self.slider.value
            del self.bubble, self.slider
            self.update_icons()
        except AttributeError:
            bubble = Bubble(orientation="vertical", pos=(self.pos[0], self.pos[1] + 48), size=(48, 200))
            def on_perc(slider, value):
                slider.btn.percentage = value
            label = Label(text=self.label, size_hint_y=None, height=25)
            bubble.add_widget(label)
            self.slider = Slider(orientation="vertical", min=0, max=100, value=self.percentage)
            self.slider.btn = self
            self.slider.bind(value=on_perc)
            bubble.add_widget(self.slider)
            def on_reset(bbtn, *args, **kwargs):
                bbtn.slider.value = bbtn.reset_value
            bbtn = BubbleButton(text=self.reset_text, size_hint_y=None, height=40)
            bbtn.slider = self.slider
            bbtn.reset_value = self.reset_value
            bbtn.bind(on_release=on_reset)
            bubble.add_widget(bbtn)
            self.add_widget(bubble)
            self.bubble = bubble
            self.icon = self.icons["close"]

    def update_icons(self, *args, **kwargs):
        if self.percentage == 0:
                self.icon = self.icons[self.type]["none"]
        elif self.percentage > 0 and self.percentage < 33:
                self.icon = self.icons[self.type]["low"]
        elif self.percentage >= 33 and self.percentage <= 66:
                self.icon = self.icons[self.type]["medium"]
        elif self.percentage > 66 and self.percentage <= 100:
                self.icon = self.icons[self.type]["high"]

class DavColorPicker(ColorPicker):
    text = StringProperty("")
    def __init__(self, **kwargs):
        super(DavColorPicker, self).__init__(**kwargs)
        self.bind(hex_color=self.setter("text"))

class SettingColor(SettingItem):
    popup = ObjectProperty(None, allownone=True)
    textinput = ObjectProperty(None)
    rect = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(SettingColor, self).__init__(**kwargs)
        # with self.rect.canvas:
        #     Color(*get_color_from_hex(self.value))
        #     Rectangle(size=(50, 30))

        self.bind(value=self.on_value)
        #self.bind(pos=self.rect.setter("pos"))

    def on_value(self, *args):
        color = get_color_from_hex(self.value)
        self.rect.background_color = color
        self.rect.text = self.value
        avg = (color[0] + color[1] + color[2]) / 3
        self.rect.color = [0, 0, 0, 1] if avg > 0.5 else [1, 1, 1, 1]
        print avg


    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _dismiss(self, *args):
        if self.popup:
            self.popup.dismiss()
        self.popup = None

    def _validate(self, instance):
        self._dismiss()
        value = self.textinput.hex_color
        if len(value) == 9:
            value = value[:-2]
        self.value = value

        # with self.rect.canvas:
        #     Color(*get_color_from_hex(self.value))
        #     Rectangle(size=(50, 30))

    def _create_popup(self, instance):
        # create popup layout

        content = BoxLayout(orientation='vertical', spacing='5dp')
        self.popup = popup = Popup(title=self.title,
            content=content, size_hint=(.8, .8))#, size_hint=(None, None), size=('400dp', '250dp'))

        # create the textinput used for numeric input
        self.textinput = textinput = DavColorPicker(hex_color=str(self.value), size_hint_y=1)
        self.textinput = textinput

        # construct the content, widget are used as a spacer
        #content.add_widget(Widget())
        content.add_widget(textinput)
        #content.add_widget(Widget())
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='OK')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

class SettingFont(SettingItem):
    popup = ObjectProperty(None, allownone=True)
    textinput = ObjectProperty(None)
    label = ObjectProperty(None)

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _dismiss(self, *largs):
        if self.popup:
            self.popup.dismiss()
        self.popup = None

    def _validate(self, instance):
        self._dismiss()
        self.value = self.textinput.font
        self.label.text = self.value

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing='5dp')
        self.popup = popup = Popup(title=self.title,
            content=content, size_hint=(.8, .8))#, size_hint=(None, None), size=('400dp', '250dp'))

        # create the textinput used for numeric input
        self.textinput = textinput = FontChooser(font=str(self.value), size_hint_y=1)
        self.textinput = textinput

        # construct the content, widget are used as a spacer
        content.add_widget(textinput)
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='OK')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

class SettingSoundFont(SettingItem):
    popup = ObjectProperty(None, allownone=True)
    textinput = ObjectProperty(None)

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _dismiss(self, *largs):
        if self.textinput:
            self.textinput.focus = False
        if self.popup:
            self.popup.dismiss()
        self.popup = None

    def _validate(self, instance):
        self._dismiss()
        value = self.textinput.selection

        if not value:
            return

        self.value = os.path.realpath(value[0])

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing=5)
        self.popup = popup = Popup(title=self.title,
            content=content, size_hint=(None, None), size=(400, 400))

        # create the filechooser
        self.textinput = textinput = FileChooserListView(path=str(self.value),
                                                         size_hint=(1, 1),
                                                         dirselect=False, filters=["*.sf2"])
        textinput.bind(on_path=self._validate)
        self.textinput = textinput

        # construct the content
        content.add_widget(textinput)
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='OK')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

class SettingManyOptions(SettingItem):
    options = ListProperty([])
    popup = ObjectProperty(None, allownone=True)
    selected = StringProperty("")

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _validate(self, instance, value=None):
        self.value = self.selected
        self.popup.dismiss()

    def _set_option(self, instance):
        self.selected = instance.text

    def _create_popup(self, instance):
        # create the popup
        content = BoxLayout(orientation='vertical', spacing='5dp')
        box = GridLayout(cols=1, spacing="5dp")
        box.bind(minimum_height=box.setter('height'))
        self.popup = popup = Popup(content=content,
            title=self.title, size_hint=(None, 1), width='400dp')
        #popup.height = len(self.options) * dp(55) + dp(150)

        # add all the options
        content.add_widget(Widget(size_hint_y=None, height=1))
        uid = str(self.uid)
        for option in self.options:
            state = 'down' if option == self.value else 'normal'
            btn = ToggleButton(text=option, state=state, group=uid)
            btn.bind(on_release=self._set_option)
            box.add_widget(btn)
        #box.height = metrics.dp(35) * len(self.options)

        scroll = ScrollView(pos_hint={'center_x': .5, 'center_y': .5}, do_scroll_x=False, size_hint=(1, 1))
        scroll.add_widget(box)
        content.add_widget(scroll)
        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='OK')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self.popup.dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # and open the popup !
        popup.open()

class FontChooser(BoxLayout):
    font = StringProperty("")
    text = font
    def __init__(self, **kwargs):
        super(FontChooser, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.fonts = sorted(map(str, fonts.get_fonts()))

        data = [{'text': str(i), 'is_selected': i == self.font} for i in self.fonts]

        args_converter = lambda row_index, rec: {'text': rec['text'],
                                                 'size_hint_y': None,
                                                 'height': 25}

        self.list_adapter = ListAdapter(data=data, args_converter=args_converter, cls=ListItemButton, selection_mode='single', allow_empty_selection=False)
        self.list_view = ListView(adapter=self.list_adapter)
        self.list_adapter.bind(selection=self.on_font_select)

        self.label = Label(text="The quick brown fox jumps over the brown lazy dog. 0123456789", font_size="30dp", halign="center", size_hint_y=None)
        self.label.font_name = fonts.match_font(self.list_adapter.selection[0].text)
        self.label.bind(size=self.label.setter("text_size"))
        self.font = self.list_adapter.selection[0].text

        self.add_widget(self.list_view)
        self.add_widget(self.label)          

    def on_font_select(self, instance, value):
        self.font = value[0].text
        self.label.font_name = fonts.match_font(value[0].text)

class MultiActionButton(ActionButton):
    action = StringProperty("")

class FileChooserArtView(FileChooserController):
    '''Implementation of :class:`FileChooserController` using an icon view.
    '''
    _ENTRY_TEMPLATE = 'FileThumbEntry'
    thumbs = DictProperty({})
    scrollview = ObjectProperty(None)

    def get_image(self, ctx):
        to_return = None
        if ctx.isdir:
            to_return = 'atlas://data/images/defaulttheme/filechooser_folder'
        else:
            try:
                try:
                    mime = mimetypes.guess_type(ctx.name)[0]
                except TypeError:
                    mime = ""
                if not mime:
                    mime = ""

                if ctx.path in self.thumbs.keys():
                    to_return = self.thumbs[ctx.path]
                elif mime == "audio/mpeg":
                    try:
                        audio = ID3(ctx.path)
                        art = audio.getall("APIC")
                        pix = None
                        if len(art) == 1:
                            pix = art[0]
                        elif len(art) > 1:
                            for pic in art:
                                if pic.type == 3:
                                    pix = pic
                        if not pix:
                            # This would raise an exception if no image is present,
                            # and the default one would be returned
                            pix = art[0]
                        ext = mimetypes.guess_extension(pix.mime)
                        image = mktemp() + ext if ext != ".jpe" else ".jpg"
                        with open(image, "w") as img:
                            img.write(pix.data)
                        to_return = image
                        self.thumbs[ctx.path] = image
                    except:
                        traceback.print_exc()
                        to_return = 'atlas://data/images/mimetypes/audio_mpeg'
                elif mime == "audio/flac":
                    try:
                        audio = FLAC(ctx.path)
                        art = audio.pictures
                        pix = None
                        if len(art) == 1:
                            pix = art[0]
                        elif len(art) > 1:
                            for pic in art:
                                if pic.type == 3:
                                    pix = pic
                        if not pix:
                            # This would raise an exception if no image is present,
                            # and the default one would be returned
                            pix = art[0]
                        image = mktemp() + mimetypes.guess_extension(pix.mime)
                        with open(image, "w") as img:
                            img.write(pix.data)
                        to_return = image
                        self.thumbs[ctx.path] = image
                    except:
                        traceback.print_exc()
                        to_return = 'atlas://data/images/mimetypes/audio_flac'
                elif "video/" in mime:
                    data = None
                    print "ffmpeg:", exec_exists("ffmpeg"), "- avconv:", exec_exists("avconv")
                    if exec_exists("avconv"):
                        data = subprocess.Popen(['avconv', '-i', ctx.path, '-an', '-vcodec', 'png', '-vframes', '1', '-ss', '00:00:01', '-y', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
                    elif exec_exists("ffmpeg"):
                        data = subprocess.Popen(['ffmpeg', '-i', ctx.path, '-an', '-vcodec', 'png', '-vframes', '1', '-ss', '00:00:01', '-y', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
                    if data:
                        image = mktemp() + ".png"
                        with open(image, "w") as img:
                            img.write(data)
                        to_return = image
                        self.thumbs[ctx.path] = image
                    else:
                        uri = 'atlas://data/images/mimetypes/{0}'.format(mime.replace("/", "_").replace("-", "_"))
                        if atlas_texture_exists(uri):
                            to_return =  uri
                        else:
                            to_return = 'atlas://data/images/defaulttheme/filechooser_file'
                elif "image/" in mime and ("jpeg" in mime or "jpg" in mime or "gif" in mime or "png" in mime) and not ctx.name.endswith(".jpe"):
                    to_return = ctx.path
                else:
                    uri = 'atlas://data/images/mimetypes/{0}'.format(mime.replace("/", "_").replace("-", "_"))
                    if atlas_texture_exists(uri):
                        to_return = uri
                    else:
                        to_return = 'atlas://data/images/defaulttheme/filechooser_file'
            except:
                print "EXCEPTION IN get_image"
                traceback.print_exc()
                to_return = 'atlas://data/images/defaulttheme/filechooser_file'

        return to_return

    def gen_label(self, ctx):
        size = ctx.get_nice_size()
        t = ""
        try:
            t = os.path.splitext(ctx.name)[1][1:].upper()
        except IndexError:
            pass
        if ctx.name.endswith(".tar.gz"):
            t = "TAR.GZ"
        if ctx.name.endswith(".tar.bz2"):
            t = "TAR.BZ2"
        if t == "":
            label = size
        else:
            label = size + " - " + t
        return label

class KKFileChooser(BoxLayout):
    filename = StringProperty("")
    chooser = ObjectProperty(None, allownone=True)
    path = StringProperty(home)
    thumbs = DictProperty({})

    def __init__(self, **kwargs):
        super(KKFileChooser, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = "5dp"
        self.chooser = FileChooserArtView(path=self.path, thumbs=self.thumbs)
        self.chooser.bind(selection=self.on_file_select, path=self.setter("path"), thumbs=self.setter("thumbs"))
        self.fileentry = TextInput(size_hint_y=None, height="30dp", text=self.filename, multiline=False)
        self.fileentry.bind(text=self.setter("filename"))
        # self.davbar = BoxLayout(orientation="horizontal", size_hint_y=None, height="45dp", spacing="5dp")
        # self.levelup = Button(on_press=hide_keyboard, on_release=self.on_levelup, height=40, width=40, size_hint=(None, None), background_normal="atlas://data/images/defaulttheme/levelup_normal", background_down="atlas://data/images/defaulttheme/levelup_down")
        # self.edit = Button(on_press=hide_keyboard, on_release=self.on_edit, height=40, width=40, size_hint=(None, None), background_normal="atlas://data/images/defaulttheme/edit_normal", background_down="atlas://data/images/defaulttheme/edit_down")
        # self.newdir = Button(on_press=hide_keyboard, on_release=self.on_newdir, height=40, width=40, size_hint=(None, None), background_normal="atlas://data/images/defaulttheme/newdir_normal", background_down="atlas://data/images/defaulttheme/newdir_down")
        # self.davbar.add_widget(self.levelup)
        # self.davbar.add_widget(self.edit)

        # scroll = ScrollView(pos_hint={'center_x': .5, 'center_y': .42}, do_scroll_y=False, size_hint=(1, 1))
        # self.navbar = GridLayout(cols=1, orientation="horizontal", spacing=5, padding=[5, 0, 0, 0])
        # self.navbar.bind(minimum_width=self.navbar.setter('width'))
        # scroll.add_widget(self.navbar)

        # self.davbar.add_widget(scroll)
        # self.davbar.add_widget(self.newdir)

        self.davbar = ReadyActionBar()
        self.actionview = self.davbar.actview
        self.levelup = ActionButton(on_press=hide_keyboard, on_release=self.on_levelup, icon="atlas://data/images/defaulttheme/levelup", text="One level up")
        self.edit = ActionButton(on_press=hide_keyboard, on_release=self.on_edit, icon="atlas://data/images/defaulttheme/edit", text="Edit path")
        self.newdir = ActionButton(on_press=hide_keyboard, on_release=self.on_newdir, icon="atlas://data/images/defaulttheme/newdir", text="New folder")
        self.pathgroup = ActionGroup(text="Path")
        self.actionview.add_widget(self.levelup)
        self.actionview.add_widget(self.newdir)
        self.actionview.add_widget(self.edit)
        self.actionview.add_widget(self.pathgroup)

        self.chooser.bind(path=self.on_path)
        self.on_path(None, self.path)

        self.add_widget(self.davbar)
        self.add_widget(self.fileentry)
        self.add_widget(self.chooser)

    def on_path(self, instance, path):
        print "ONPATH"
        splitpath = os.path.abspath(path).split(os.sep)
        self.pathgroup.clear_widgets()
        if splitpath[0] == "":
            splitpath[0] = os.sep
        print splitpath

        for i in splitpath:
            if i != "":
                btn = ActionButton(text=i, on_press=hide_keyboard, on_release=self.navigate)
                btn.path = os.path.normpath(os.sep.join(splitpath[:splitpath.index(i)+1]))
                self.pathgroup.add_widget(btn)

    def on_levelup(self, *args):
        #print "levelup", os.sep.join(self.chooser.path.split(os.sep)[:-1]), self.chooser.path
        newpath = os.sep.join(self.chooser.path.split(os.sep)[:-1])
        if newpath == "":
            newpath = os.sep
        self.chooser.path = newpath

    def on_edit(self, *args):
        content = BoxLayout(orientation="vertical", spacing="5dp")
        self.popup = Popup(size_hint=(.5, .3), content=content, title="Insert custom path")
        buttonbox = BoxLayout(orientation="horizontal", spacing="5dp", height=45)
        ok = Button(text="OK", on_press=hide_keyboard, on_release=self.cd, height=40, size_hint_y=None)
        cancel = Button(text="Cancel", on_press=hide_keyboard, on_release=self.popup.dismiss, height=40, size_hint_y=None)
        buttonbox.add_widget(ok)
        buttonbox.add_widget(cancel)
        self.direntry = TextInput(height=30, size_hint_y=None, on_text_validate=self.cd, multiline=False)
        content.add_widget(Widget())
        content.add_widget(self.direntry)
        content.add_widget(Widget())
        content.add_widget(buttonbox)
        self.popup.open()

    def on_newdir(self, *args):
        content = BoxLayout(orientation="vertical", spacing="5dp")
        self.popup = Popup(size_hint=(.5, .3), content=content, title="New folder")
        buttonbox = BoxLayout(orientation="horizontal", spacing="5dp", height=45)
        ok = Button(text="OK", on_press=hide_keyboard, on_release=self.mkdir, height=40, size_hint_y=None)
        cancel = Button(text="Cancel", on_press=hide_keyboard, on_release=self.popup.dismiss, height=40, size_hint_y=None)
        buttonbox.add_widget(ok)
        buttonbox.add_widget(cancel)
        self.direntry = TextInput(height=30, size_hint_y=None, on_text_validate=self.mkdir, multiline=False)
        content.add_widget(Widget())
        content.add_widget(self.direntry)
        content.add_widget(Widget())
        content.add_widget(buttonbox)
        self.popup.open()

    def mkdir(self, *args):
        #print "mkdir", join(self.chooser.path, self.direntry.text)
        os.mkdir(join(self.chooser.path, self.direntry.text))
        # This should make the view refresh
        self.chooser.path = os.sep + self.chooser.path[:]
        self.popup.dismiss()

    def cd(self, *args):
        if exists(self.direntry.text):
            self.chooser.path = self.direntry.text
            self.popup.dismiss()
        else:
            global oldcolor, restore_color
            oldcolor = self.direntry.selection_color[:]
            self.direntry.selection_color = [1, 0.08627450980392157, 0.08627450980392157, 0.5]
            self.direntry.select_all()
            def restore_color(instance, value):
                global oldcolor, restore_color
                instance.selection_color = oldcolor
                instance.unbind(selection=restore_color)
            self.direntry.bind(selection=restore_color)

    def navigate(self, button):
        #print "navigate", button.path
        self.chooser.path = button.path

    def on_file_select(self, instance, selection):
        try:
            self.fileentry.text = selection and os.path.basename(selection[0]) or ""
        except:
            self.fileentry.text = ""
        try:
            self.filename = selection[0]
        except IndexError:
            pass

def exec_exists(bin):
    try:
        p = subprocess.check_output(["which", bin])
        return True
    except subprocess.CalledProcessError:
        return False
    except:
        print "EXCEPTION IN get_atlas_textures"
        
        traceback.print_exc()
        return False

def get_atlas_textures(atlas):
    try:
        with open(atlas, "r") as a:
            atl = json.load(a)
        textures = []
        for i in atl.keys():
            for j in atl[i].keys():
                textures.append(str(j))
        return textures
    except:
        print "EXCEPTION IN get_atlas_textures"
        
        traceback.print_exc()

def atlas_texture_exists(uri):
    try:
        textures = get_atlas_textures(resource_find(dirname(uri).replace("atlas://", "") + ".atlas"))
        return basename(uri) in textures
    except OSError:
        return False
    except:
        print "EXCEPTION IN atlas_texture_exists"
        
        traceback.print_exc()
