# -*- coding: utf-8 -*-

# ui.py
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

import os, sys, json, mimetypes, subprocess, traceback
mimetypes.add_type("image/jpeg", ".JPG")
mimetypes.add_type("image/jpg", ".jpg")
mimetypes.add_type("image/jpeg", ".jpg")
from os.path import dirname, basename, join, exists, normpath, isdir
from chardet import detect as chardetect
from misc import repr_list
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from tempfile import mkdtemp, mktemp

from pygame import font as fonts

from kivy.adapters.listadapter import ListAdapter
from kivy.animation import Animation
from kivy.app import App
from kivy.atlas import Atlas
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty, BoundedNumericProperty,\
                            ObjectProperty, StringProperty, DictProperty,\
                            ListProperty, OptionProperty, BooleanProperty
from kivy.resources import resource_find
from kivy.utils import get_color_from_hex, platform as core_platform
from kivy.uix.actionbar import ActionButton, ActionBar, ActionView, ActionOverflow, ActionGroup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.bubble import Bubble, BubbleButton
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.filechooser import FileChooserController, FileChooserIconView, FileChooserListView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.listview import ListItemButton, ListView
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.settings import SettingItem, SettingSpacer, SettingsPanel
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

platform = core_platform()

def hide_keyboard(*args, **kwargs):
    pass

if platform == "android":
    import android
    from jnius import autoclass
    def hide_keyboard(*args, **kwargs):
        android.hide_keyboard()

def open_url(url):
    if platform == "macosx":
        subprocess.Popen(['open', url])
    elif platform == 'win':
        os.startfile(url)
    elif platform == "linux":
        subprocess.Popen(['xdg-open', url])
    elif platform == "android":
        android.open_url(url)

def open_email(email):
    if platform == "macosx":
        subprocess.Popen(['open', "mailto:" + email])
    elif platform == 'win':
        os.startfile("mailto:" + email)
    elif platform == "linux":
        subprocess.Popen(['xdg-open', "mailto:" + email])
    elif platform == "android":
        android.open_url("mailto:" + email)

# Took from Python 2.7 "user" module; Android support added
home = os.curdir                        # Default
if platform == "android":
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
    playpause = ObjectProperty(None)
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
        if self.spacers[0]:
            for i in self.spacers:
                self.remove_widget(i)
        args = [widget]
        if index: args.append(index)
        super(ToolbarSection, self).add_widget(*args)
        if self.position in ("left", "right"):
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
            self.bubble = Bubble(orientation="vertical", size=(48, 200))
            self.update_bubble_pos()
            self.bind(pos=self.update_bubble_pos)
            def on_perc(slider, value):
                slider.btn.percentage = value
            label = Label(text=self.label, size_hint_y=None, height=25)
            self.bubble.add_widget(label)
            self.slider = Slider(orientation="vertical", min=0, max=100, value=self.percentage)
            self.slider.btn = self
            self.slider.bind(value=on_perc)
            self.bubble.add_widget(self.slider)
            def on_reset(bbtn, *args, **kwargs):
                bbtn.slider.value = bbtn.reset_value
            bbtn = BubbleButton(text=self.reset_text, size_hint_y=None, height=40)
            bbtn.slider = self.slider
            bbtn.reset_value = self.reset_value
            bbtn.bind(on_release=on_reset)
            self.bubble.add_widget(bbtn)
            self.add_widget(self.bubble)
            self.icon = self.icons["close"]

    def update_icons(self, *args, **kwargs):
        if self.type == "volume":
            self.reset_value = 0
            self.reset_text = "Mute"
        else:
            self.reset_value = 50
            self.reset_text = "Reset"

        if self.percentage == 0:
                self.icon = self.icons[self.type]["none"]
        elif self.percentage > 0 and self.percentage < 33:
                self.icon = self.icons[self.type]["low"]
        elif self.percentage >= 33 and self.percentage <= 66:
                self.icon = self.icons[self.type]["medium"]
        elif self.percentage > 66 and self.percentage <= 100:
                self.icon = self.icons[self.type]["high"]

    def update_bubble_pos(self, *args):
        self.bubble.pos = (self.pos[0], self.pos[1] + 48)

class AnimTabbedPanel(TabbedPanel):

    #override tab switching method to animate on tab switch
    def switch_to(self, header):
        anim = Animation(opacity=0, d=.24, t='in_out_quad')

        def start_anim(_anim, child, in_complete, *lt):
            _anim.start(child)

        def _on_complete(*lt):
            if header.content:
                header.content.opacity = 0
                anim = Animation(opacity=1, d=.43, t='in_out_quad')
                start_anim(anim, header.content, True)
            super(AnimTabbedPanel, self).switch_to(header)

        anim.bind(on_complete = _on_complete)
        if self.current_tab.content:
            start_anim(anim, self.current_tab.content, False)
        else:
            _on_complete()

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
        self.textinput = textinput = FileChooserListView(size_hint=(1, 1),
                                                         dirselect=False, filters=["*.sf2"])
        if str(self.value) not in ("", "None"):
            self.textinput.path = os.path.dirname(str(self.value))

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
    '''Implementation of :class:`FileChooserController` using an icon view with thumbnails.
    '''
    _ENTRY_TEMPLATE = 'FileThumbEntry'

    thumbdir = StringProperty(mkdtemp(prefix="kivy-", suffix="-thumbs"))
    """Custom directory for the thumbnails. By default it uses tempfile to
    generate it randomly.
    """

    showthumbs = NumericProperty(-1)
    """Thumbnail limit. If set to a number > 0, it will show the thumbnails
    only if the directory doesn't contain more files or directories. If set
    to 0 it won't show any thumbnail. If set to a number < 0 it will always
    show the thumbnails, regardless of how many items the current directory
    contains.
    By default it is set to -1, so it will show all the thumbnails.
    """

    thumbsize = NumericProperty(dp(64))
    """The size of the thumbnails. It defaults to 64dp.
    """

    _thumbs = DictProperty({})
    scrollview = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(FileChooserArtView, self).__init__(**kwargs)
        if not exists(self.thumbdir):
            os.mkdir(self.thumbdir)

    def _get_image(self, ctx):
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

                if ctx.path in self._thumbs.keys():
                    to_return = self._thumbs[ctx.path]
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
                        image = join(self.thumbdir, mktemp()) + ext if ext != ".jpe" else ".jpg"
                        with open(image, "w") as img:
                            img.write(pix.data)
                        to_return = image
                        self._thumbs[ctx.path] = image
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
                        image = join(self.thumbdir, mktemp()) + mimetypes.guess_extension(pix.mime)
                        with open(image, "w") as img:
                            img.write(pix.data)
                        to_return = image
                        self._thumbs[ctx.path] = image
                    except:
                        traceback.print_exc()
                        to_return = 'atlas://data/images/mimetypes/audio_flac'
                elif "video/" in mime:
                    data = None
                    #print "ffmpeg:", exec_exists("ffmpeg"), "- avconv:", exec_exists("avconv")
                    if exec_exists("avconv"):
                        data = subprocess.Popen(['avconv', '-i', ctx.path, '-an', '-vcodec', 'png', '-vframes', '1', '-ss', '00:00:01', '-y', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
                    elif exec_exists("ffmpeg"):
                        data = subprocess.Popen(['ffmpeg', '-i', ctx.path, '-an', '-vcodec', 'png', '-vframes', '1', '-ss', '00:00:01', '-y', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
                    if data:
                        image = join(self.thumbdir, mktemp()) + ".png"
                        with open(image, "w") as img:
                            img.write(data)
                        to_return = image
                        self._thumbs[ctx.path] = image
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

    def _gen_label(self, ctx):
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
        
    def _unicode_noerrs(self, string):
        if not string:
            return u""
        if type(string) == type(unicode()):
            return string
        try:
            return unicode(string, encoding=chardetect(string)["encoding"])
        except:
            raise UnicodeWarning("EXCEPTION IN FileChooserThumbView._unicode_noerrs skipped.\nThis means that file list might not contain all the files that are really present in the directory.\nThis was the exception:")
            traceback.print_exc()
            return u""


class KKFileChooser(BoxLayout):
    filename = StringProperty("")
    chooser = ObjectProperty(None, allownone=True)
    path = StringProperty(home)
    thumbs = DictProperty({})

    def __init__(self, **kwargs):
        super(KKFileChooser, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = "5dp"
        self.chooser = FileChooserArtView(path=self.path, _thumbs=self.thumbs)
        self.chooser.bind(selection=self.on_file_select, path=self.setter("path"), _thumbs=self.setter("thumbs"))
        self.fileentry = TextInput(size_hint_y=None, height="30dp", text=self.filename, multiline=False)
        self.fileentry.bind(text=self.setter("filename"))

        self.gen_actionbar()

        self.chooser.bind(path=self.on_path)
        self.on_path(None, self.path)

        self.add_widget(self.fileentry)
        self.add_widget(self.chooser)


    def gen_actionbar(self):
        self.davbar = ReadyActionBar()
        self.actionview = self.davbar.actview
        self.levelup = ActionButton(on_press=hide_keyboard, on_release=self.on_levelup, icon="atlas://data/images/defaulttheme/levelup", text="One level up")
        self.edit = ActionButton(on_press=hide_keyboard, on_release=self.on_edit, icon="atlas://data/images/defaulttheme/edit", text="Edit path")
        self.newdir = ActionButton(on_press=hide_keyboard, on_release=self.on_newdir, icon="atlas://data/images/defaulttheme/newdir", text="New folder")
        self.actionview.add_widget(self.levelup)
        self.actionview.add_widget(self.newdir)
        self.actionview.add_widget(self.edit)
        self.add_widget(self.davbar, len(self.children))

    def on_path(self, instance, path):
        #print "ONPATH"
        try:
            self.remove_widget(self.davbar)
        except:
            pass
        self.gen_actionbar()

        self.pathgroup = ActionGroup(text="Path")
        self.actionview.add_widget(self.pathgroup)

        seq = os.path.abspath(normpath(path)).split(os.sep)
        splitpath = []

        if platform != "win":
            splitpath.append("/")

        for i in seq:
            if i != "":
                splitpath.append(i)

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
        self.direrror = Label(markup=True, text="")
        self.direntry = TextInput(height=30, size_hint_y=None, on_text_validate=self.cd, multiline=False, focus=True)
        content.add_widget(self.direrror)
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
        self.direrror = Label(markup=True, text="")
        self.direntry = TextInput(height=30, size_hint_y=None, on_text_validate=self.mkdir, multiline=False, focus=True)
        content.add_widget(self.direrror)
        content.add_widget(self.direntry)
        content.add_widget(Widget())
        content.add_widget(buttonbox)
        self.popup.open()

    def mkdir(self, *args):
        #print "mkdir", join(self.chooser.path, self.direntry.text)
        try:
            os.mkdir(join(self.chooser.path, self.direntry.text))
            # This should make the view refresh
            self.chooser.path = os.sep + self.chooser.path[:]
            self.popup.dismiss()
        except OSError, error:
            self.direrror.text = str(error)

    def cd(self, *args):
        if exists(self.direntry.text) and isdir(self.direntry.text):
            self.chooser.path = self.direntry.text
            self.popup.dismiss()
        else:
            self.direrror.text = "The path doesn't exist"

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

class PluginsPanel(BoxLayout):
    title = StringProperty("Plug-ins")
    plugins_box = ObjectProperty(None)
    defaults_box = ObjectProperty(None)

    def install_plugin(self, *args):
        NotImplemented

    def download_plugin(self, *args):
        NotImplemented

class PluginItem(FloatLayout):
    title = StringProperty('<No title set>')
    desc = StringProperty("")
    disabled = BooleanProperty(False)
    stock = BooleanProperty(False)
    manifest = ObjectProperty(None)
    selected_alpha = NumericProperty(0)
    logo = StringProperty("")
    _box = ObjectProperty(None)

    __events__ = ('on_release',)

    def __init__(self, **kwargs):
        super(PluginItem, self).__init__(**kwargs)
        self.bind(disabled=self.toggle)
        self.titlebak = self.title[:]
        p = join(self.manifest.path, "logo/32.png")
        if exists(p):
            self.logo = p

    def add_widget(self, *largs):
        if self.content is None:
            return super(PluginItem, self).add_widget(*largs)
        return self.content.add_widget(*largs)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return
        if self.disabled:
            return
        touch.grab(self)
        self.selected_alpha = 1
        return super(PluginItem, self).on_touch_down(touch)

    def toggle(self, *args):
        if self.disabled:
            self.title = "[i]" + self.titlebak + " (disabled)[/i]"
        else:
            self.title = self.titlebak

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.dispatch('on_release')
            Animation(selected_alpha=0, d=.25, t='out_quad').start(self)
            return True
        return super(PluginItem, self).on_touch_up(touch)

    def on_release(self, *args):
        # create popup layout
        self.popup = PluginPopup(manifest=self.manifest, disabled=self.disabled, logo=self.logo)
        self.popup.bind(disabled=self.setter("disabled"))
        self.bind(disabled=self.popup.setter("disabled"))

        # all done, open the popup !
        self.popup.open()

class PluginPopup(ModalView):
    title_size = NumericProperty('20sp')
    title_color = ListProperty([1, 1, 1, 1])
    separator_color = ListProperty([47 / 255., 167 / 255., 212 / 255., 1.])
    separator_height = NumericProperty('2dp')
    manifest = ObjectProperty(None)
    plugin_disabled = BooleanProperty(False)
    infolabel = ObjectProperty(None)
    logo = StringProperty("")
    screenshot = ObjectProperty(None)
    switch = ObjectProperty(None)

    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint', (.9, .9))
        super(PluginPopup, self).__init__(**kwargs)

        self.switch.active = self.manifest.active
        self.switch.bind(active=self.manifest.setter("active"))
        self.switch.disabled = bool(self.manifest.errs_loading)

        def repr_purposes(seq):
            toret = ""
            dic = {"player":          "Player",
                   "lyrics_provider": "Lyrics provider",
                   "ui_expansion":    "Interface expansion",
                   "feature":         "New feature"}
            for i in seq:
                try:
                    toret += dic[i] + ", "
                except KeyError:
                    pass
            return toret[:-2]

        def repr_optional(manifest):
            toret = ""
            if "player" in manifest.purposes:
                toret += "[b]Supported audio MIME types:[/b] {0}\n".format(repr_list(manifest.player.supported_mimes))
            if "lyrics_provider" in manifest.purposes:
                toret += "[b]Supported audio MIME types for lyrics:[/b] {0}\n".format(repr_list(manifest.lyrics_provider.supported_audio_mimes))
                toret += "[b]Supported lyrics format:[/b] {0}\n".format(repr_list(manifest.lyrics_provider.supported_lrc_types))
            return toret + "\n"


        def repr_authors(seq):
            toret = ""
            for i in seq:
                if "homepage" in i.keys() and "email" in i.keys():
                    toret += "    - [b]" + i["name"] + "[/b] ([ref=email{0}]e-mail[/ref], [ref=homepage{0}]homepage[/ref])\n".format(seq.index(i))
                elif "homepage" in i.keys():
                    toret += "    - [b]" + i["name"] + "[/b] ([ref=homepage{0}]homepage[/ref])\n".format(seq.index(i))
                elif "email" in i.keys():
                    toret += "    - [b]" + i["name"] + "[/b] ([ref=email{0}]e-mail[/ref])\n".format(seq.index(i))
                else:
                    toret += "    - [b]" + i["name"] + "[/b]\n"

            return toret[:-1]

        self.infolabel.text = """{manifest.long_description}
{error}

[ref=homepage]Homepage[/ref]

[b]Name:[/b] {manifest.name}
[b]Version:[/b] {manifest.version}
[b]Required plugins:[/b] {depends_kk}
[b]Required Python modules:[/b] {depends_py}
[b]Purpose{0}:[/b] {purposes}
{optional}
[b]Authors:[/b]
{authors}

[b]License:[/b] [ref=license]{license_name}[/ref] ({license_type}){license_text}
""".format(
            "s" if len(self.manifest.purposes) > 1 else "",
            manifest=self.manifest,
            depends_kk=repr_list(self.manifest.depends_kk == [] and ["None"] or self.manifest.depends_kk),
            depends_py=repr_list(self.manifest.depends_py == [] and ["None"] or self.manifest.depends_py),
            purposes=repr_purposes(self.manifest.purposes),
            authors=repr_authors(self.manifest.authors),
            optional=repr_optional(self.manifest),
            error=self.manifest.errs_loading or "",
            license_name=self.manifest.license["name"],
            license_type=self.manifest.license["type"],
            license_text="" if not self.manifest.license["text"] else "\n\n" + self.manifest.license["text"]
            )

        self.infolabel.bind(on_ref_press=self.on_ref)

    def on_ref(self, instance, value):
        if value == "homepage":
            open_url(self.manifest.homepage)
        elif "email" in value:
            index = int(value.replace("email", ""))
            open_email(self.manifest.authors[index]["email"])
        elif "homepage" in value:
            index = int(value.replace("homepage", ""))
            open_url(self.manifest.authors[index]["homepage"])
        elif "license" in value:
            try:
                open_url(self.manifest.license["url"])
            except:
                pass

    def on_touch_down(self, touch):
        if self.disabled and self.collide_point(*touch.pos):
            return True
        return super(PluginPopup, self).on_touch_down(touch)


class RestartPopup(Popup):
    """Popup that asks the user if he wants to restart the app
    after making thanges that require restart. Users might also
    just exit.
    """

    def __init__(self, **kwargs):
        self.label = """Karaokivy needs restart to apply some of the settings you changed.
If you don't, some plug-ins may not be enabled/disabled, or something might not work as expected."""

        if platform in ("android", "ios"):
            self.label += """\n\nNote: it seems that you're using Android/iOS; restarting will probably not work. If it just exits, restart the app manually. Thank you."""

        super(RestartPopup, self).__init__(**kwargs)

    def do_nothing(self, *args):
        """Closes the popup and the settings UI without restarting.
        """
        self.dismiss()
        App.get_running_app().close_settings()

    def restart_app(self, *args):
        """Restarts the current program or exits if it's not possible.
        Note: this function does not return. Any cleanup action (like
        saving data) must be done before calling this function.
        """

        try:
            python = sys.executable
            os.execl(python, python, * sys.argv)
        except:
            sys.exit("Failed to restart, exiting normally.")

class PluginSelector(ModalView):
    title = StringProperty("")
    content = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(PluginSelector, self).__init__(**kwargs)
        panel = PluginsPanel(self.title)
        self.bind(title=panel.setter("title"))
        box = BoxLayout(orientation="horizontal")
        self.add_widget(box)
        self.content = panel
        once = Button(size_hint)


    def add_widget(self, *largs):
        if len(self.children) == 0:
            return super(PluginSelector, self).add_widget(*largs)
        return self.content.add_widget(*largs)

class PluginToggleItem(PluginItem):
    group = ObjectProperty(None)
    radio = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(PluginToggleItem, self).__init__(**kwargs)
        self.radio = CheckBox(group=self.group)
        self._box.add_widget(self.radio)