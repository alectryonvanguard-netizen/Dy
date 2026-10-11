import os
import json
import time
import copy
import hashlib
import threading

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.graphics import (Color, Rectangle, RoundedRectangle, Ellipse, Line, Triangle,
                           PushMatrix, PopMatrix, Rotate, Scale)
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex, escape_markup

# ----------------------------------------------------------------------------
# THINGS YOU CAN CHANGE
# ----------------------------------------------------------------------------
APP_NAME = "Sam Ng"
APP_VERSION = "1.0.9"
HOME_HEADLINE = "Sam Ng is for you."      # big line on the empty home screen

TERMS_TEXT = ""      # paste your Terms and Conditions here
PRIVACY_TEXT = ""    # paste your Privacy Policy here
HELP_TEXT = ""       # paste your Help text here
ABOUT_TEXT = ""      # paste your About text here
PLACEHOLDER = "[This text has not been added yet.]"

TOP_LOWER = dp(26)       # how far the STEM / Following / For You row is pushed down
TITLE_LOWER = dp(48)     # extra push-down for the "Friends" and "Inbox" titles
NAV_RAISE = dp(22)       # how far the bottom row (Home, Friends ... photo) is raised
PROFILE_PHOTO_X = 0.5    # profile photo position: 0.0 = far left, 0.5 = centre, 1.0 = far right

# How posted photos are shown on Home:
#   "auto"    = full screen when the photo suits the screen, otherwise the whole photo is shown
#   "cover"   = always full screen (edges may be cropped)
#   "contain" = always the whole photo
FEED_MODE = "auto"
FULLSCREEN_MIN_VISIBLE = 0.55   # "auto": go full screen if at least this much of the photo stays visible

# See-through buttons on top of posts: 0.0 = invisible, 1.0 = solid dark
GLASS = 0.35

# ----------------------------------------------------------------------------
# ANDROID SUPPORT (safe on desktop too)
# ----------------------------------------------------------------------------
try:
    from jnius import autoclass, cast, PythonJavaClass, java_method
    from android import activity as android_activity
    from android.runnable import run_on_ui_thread
    ANDROID = True
except Exception:
    autoclass = None
    cast = None
    android_activity = None
    ANDROID = False
    PythonJavaClass = object

    def java_method(signature):
        def deco(func):
            return func
        return deco

    def run_on_ui_thread(func):
        return func

REQ_PICK = 9001      # video capture result
REQ_PHOTO = 9002     # system photo capture result (fallback)

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".3gp", ".m4v")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
STATE_FILE = "samng_state_v2.json"
WHITE = (1, 1, 1, 1)
MEDIA_PERMISSIONS = ["android.permission.READ_MEDIA_IMAGES", "android.permission.READ_MEDIA_VIDEO",
                     "android.permission.READ_EXTERNAL_STORAGE"]

# ----------------------------------------------------------------------------
# THEME
# ----------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg": "#04060B", "panel": "#0E131C", "card": "#0B0F17",
        "text": "#FFFFFF", "sub": "#9C9CCB", "accent": "#00E5F5",
        "accent2": "#FF286F", "on_accent": "#04060B", "line": "#1B2535",
        "glow": "#2EA8FF", "pilltext": "#D9DBF7",
        "pillfill": (0.02, 0.04, 0.09, 0.62),
    },
    "light": {
        "bg": "#F2F5FA", "panel": "#FFFFFF", "card": "#FFFFFF",
        "text": "#101522", "sub": "#5E6480", "accent": "#0099B8",
        "accent2": "#E8205F", "on_accent": "#FFFFFF", "line": "#D5DBE8",
        "glow": "#1D8FE0", "pilltext": "#1B2340",
        "pillfill": (1.0, 1.0, 1.0, 0.75),
    },
}
_mode = {"dark": True}


def T(key):
    value = THEMES["dark" if _mode["dark"] else "light"][key]
    if isinstance(value, str):
        return get_color_from_hex(value)
    return list(value)


def paint(widget, key, radius=0):
    with widget.canvas.before:
        Color(*T(key))
        shape = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
    widget.bind(pos=lambda w, v: setattr(shape, "pos", v),
                size=lambda w, v: setattr(shape, "size", v))
    return shape


def paint_rgba(widget, rgba, radius=0):
    with widget.canvas.before:
        Color(*rgba)
        shape = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
    widget.bind(pos=lambda w, v: setattr(shape, "pos", v),
                size=lambda w, v: setattr(shape, "size", v))
    return shape


def paint_bg(widget):
    paint(widget, "bg")
    if not _mode["dark"]:
        return

    def redraw(*_):
        widget.canvas.before.remove_group("fence")
        x, y = widget.pos
        w, h = widget.size
        if w <= 0 or h <= 0:
            return
        step = dp(44)
        with widget.canvas.before:
            Color(0.35, 0.5, 0.68, 0.07, group="fence")
            for k in range(-int(h / step) - 1, int(w / step) + 2):
                x0 = x + k * step
                Line(points=[x0, y, x0 + h, y + h], width=1, group="fence")
                Line(points=[x0 + h, y, x0, y + h], width=1, group="fence")

    widget.bind(pos=redraw, size=redraw)
    redraw()


# ----------------------------------------------------------------------------
# IMAGE HELPERS
# ----------------------------------------------------------------------------
def load_texture(path):
    if not path or not os.path.isfile(path):
        return None
    if os.path.splitext(path)[1].lower() not in IMAGE_EXTENSIONS:
        return None
    try:
        return CoreImage(path).texture
    except Exception:
        return None


def cover_region(tex, w, h):
    if w <= 0 or h <= 0:
        return tex
    tw, th = tex.size
    target = float(w) / float(h)
    source = float(tw) / float(th)
    if source > target:
        nw = max(1, int(th * target))
        return tex.get_region((tw - nw) // 2, 0, nw, th)
    nh = max(1, int(tw / target))
    return tex.get_region(0, (th - nh) // 2, tw, nh)


def draw_texture(x, y, w, h, tex, mode):
    """Draw a picture in a box. cover = fills it, contain = whole picture, auto = pick the better one."""
    tw, th = tex.size
    if mode == "auto":
        r_img = float(tw) / th
        r_box = float(w) / h
        visible = min(r_img / r_box, r_box / r_img)
        mode = "cover" if visible >= FULLSCREEN_MIN_VISIBLE else "contain"
    if mode == "contain":
        Color(0, 0, 0, 1)
        Rectangle(pos=(x, y), size=(w, h))
        scale = min(float(w) / tw, float(h) / th)
        dw, dh = tw * scale, th * scale
        Color(1, 1, 1, 1)
        Rectangle(texture=tex, pos=(x + (w - dw) / 2.0, y + (h - dh) / 2.0), size=(dw, dh))
    else:
        Color(1, 1, 1, 1)
        Rectangle(texture=cover_region(tex, w, h), pos=(x, y), size=(w, h))


def ago(ts):
    d = int(time.time() - ts)
    if d < 60:
        return "just now"
    if d < 3600:
        return "%dm ago" % (d // 60)
    if d < 86400:
        return "%dh ago" % (d // 3600)
    return "%dd ago" % (d // 86400)


# ----------------------------------------------------------------------------
# BASIC WIDGETS
# ----------------------------------------------------------------------------
class LLabel(Label):
    def __init__(self, **kw):
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)
        self.bind(size=lambda w, v: setattr(w, "text_size", v))


class Wrap(Label):
    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "top")
        super().__init__(**kw)
        self.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                  texture_size=lambda w, v: setattr(w, "height", v[1] + dp(6)))


class Card(BoxLayout):
    def __init__(self, bg="panel", radius=dp(16), outline=False, **kw):
        super().__init__(**kw)
        paint(self, bg, radius)
        if outline:
            glow = T("glow")
            with self.canvas.before:
                Color(glow[0], glow[1], glow[2], 0.55)
                line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, radius), width=dp(1))

            def sync(*_):
                line.rounded_rectangle = (self.x, self.y, self.width, self.height, radius)
            self.bind(pos=sync, size=sync)


class MenuCard(Card):
    def on_touch_down(self, touch):
        handled = super().on_touch_down(touch)
        return handled or self.collide_point(*touch.pos)


class NeonPill(ButtonBehavior, Label):
    def __init__(self, active=False, fg=None, translucent=False, **kw):
        super().__init__(**kw)
        self.active = active
        self.bold = True
        self.translucent = translucent
        self._fg = fg
        self.color = fg if fg is not None else (T("accent") if active else T("pilltext"))
        self.bind(pos=self.draw, size=self.draw, state=self.draw, disabled=self.draw)
        self.draw()

    def set_active(self, value):
        self.active = value
        if self._fg is None:
            self.color = T("accent") if value else T("pilltext")
        self.draw()

    def draw(self, *args):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        glow = T("glow")
        fade = 0.4 if self.disabled else 1.0
        ellipse = (float(w) / float(h)) <= 2.2
        if self.translucent:
            fill = (0.05, 0.05, 0.08, 0.55 * GLASS)
        else:
            fill = T("pillfill")
        if self.state == "down":
            fill = [fill[0], fill[1], fill[2], min(1.0, fill[3] + 0.25)]
        with self.canvas.before:
            Color(fill[0], fill[1], fill[2], fill[3])
            if ellipse:
                Ellipse(pos=(x, y), size=(w, h))
            else:
                RoundedRectangle(pos=(x, y), size=(w, h), radius=[h / 2.0])
            if self.active:
                for grow, alpha in ((dp(7), 0.08), (dp(4), 0.16), (dp(2), 0.30)):
                    Color(glow[0], glow[1], glow[2], alpha * fade * (0.6 if self.translucent else 1.0))
                    if ellipse:
                        Line(ellipse=(x - grow, y - grow, w + 2 * grow, h + 2 * grow), width=dp(2))
                    else:
                        Line(rounded_rectangle=(x - grow, y - grow, w + 2 * grow, h + 2 * grow, h / 2.0 + grow), width=dp(2))
                Color(glow[0], glow[1], glow[2], fade * (0.8 if self.translucent else 1.0))
                width = dp(1.7)
            else:
                line_alpha = (0.1 + 0.4 * GLASS) if self.translucent else 0.45
                Color(glow[0], glow[1], glow[2], line_alpha * fade)
                width = dp(1.1)
            if ellipse:
                Line(ellipse=(x, y, w, h), width=width)
            else:
                Line(rounded_rectangle=(x, y, w, h, h / 2.0), width=width)


def pill(text, primary=False, **kw):
    kw.setdefault("size_hint_y", None)
    kw.setdefault("height", dp(54))
    kw.setdefault("font_size", sp(17))
    return NeonPill(text=text, active=primary, **kw)


class Icon(ButtonBehavior, Widget):
    def __init__(self, kind, color=None, circle_bg=None, **kw):
        super().__init__(**kw)
        self.kind = kind
        self.icolor = color if color is not None else T("text")
        self.circle_bg = circle_bg
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        s = min(self.width, self.height)
        if s <= 0:
            return
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        if self.circle_bg is not None:
            with self.canvas.before:
                Color(*self.circle_bg)
                Ellipse(pos=(cx - s / 2, cy - s / 2), size=(s, s))
        with self.canvas.after:
            Color(*self.icolor)
            if self.kind == "search":
                r = s * 0.2
                Line(circle=(cx - r * 0.3, cy + r * 0.3, r), width=dp(1.8))
                Line(points=[cx + r * 0.6, cy - r * 0.6, cx + r * 1.6, cy - r * 1.6], width=dp(2), cap="round")
            elif self.kind == "dots":
                d = dp(4.6)
                for off in (s * 0.22, 0, -s * 0.22):
                    Ellipse(pos=(cx - d / 2, cy + off - d / 2), size=(d, d))
            elif self.kind == "back":
                Line(points=[cx + s * 0.12, cy + s * 0.26, cx - s * 0.12, cy, cx + s * 0.12, cy - s * 0.26],
                     width=dp(2.2), cap="round", joint="round")
            elif self.kind == "plus":
                a = s * 0.26
                Line(points=[cx - a, cy, cx + a, cy], width=dp(2.4), cap="round")
                Line(points=[cx, cy - a, cx, cy + a], width=dp(2.4), cap="round")
            elif self.kind == "pencil":
                a = s * 0.22
                Line(points=[cx - a, cy - a, cx + a, cy + a], width=dp(2.0), cap="round")


class TabLabel(ButtonBehavior, Label):
    def __init__(self, text, active=False, light=False, **kw):
        super().__init__(text=text, **kw)
        self.active = active
        self.light = light
        self.bold = True
        self.font_size = sp(17)
        self.set_active(active)
        self.bind(pos=self.draw, size=self.draw)

    def set_active(self, value):
        self.active = value
        if self.light:
            self.color = WHITE if value else (1, 1, 1, 0.7)
        else:
            self.color = T("text") if value else T("sub")
        self.draw()

    def draw(self, *args):
        self.canvas.after.clear()
        if not self.active or self.width <= 0:
            return
        glow = T("glow")
        cx = self.x + self.width / 2.0
        y = self.y + dp(4)
        half = min(self.width, dp(90)) * 0.32
        with self.canvas.after:
            Color(glow[0], glow[1], glow[2], 0.28)
            Line(points=[cx - half, y, cx + half, y], width=dp(4), cap="round")
            Color(*glow)
            Line(points=[cx - half, y, cx + half, y], width=dp(1.6), cap="round")


class CoverImage(ButtonBehavior, Widget):
    """Picture in a box. mode: cover | contain | auto."""

    def __init__(self, source="", fallback="panel", mode="cover", **kw):
        super().__init__(**kw)
        self.fallback = fallback
        self.mode = mode
        self._tex = load_texture(source)
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def has_image(self):
        return self._tex is not None

    def redraw(self, *args):
        self.canvas.clear()
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        with self.canvas:
            if self._tex is not None:
                draw_texture(self.x, self.y, w, h, self._tex, self.mode)
            else:
                Color(*T(self.fallback))
                Rectangle(pos=self.pos, size=self.size)


class VideoTile(ButtonBehavior, Widget):
    """Video thumbnail (or a dark tile) with a play button on top. Tap it to play the video."""

    def __init__(self, thumb="", mode="cover", **kw):
        super().__init__(**kw)
        self.mode = mode
        self._tex = load_texture(thumb)
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        cx = self.x + w / 2.0
        cy = self.y + h / 2.0
        s = min(w, h) * 0.12
        with self.canvas:
            if self._tex is not None:
                draw_texture(self.x, self.y, w, h, self._tex, self.mode)
                Color(0, 0, 0, 0.18)
                Rectangle(pos=self.pos, size=self.size)
            else:
                Color(*T("panel"))
                Rectangle(pos=self.pos, size=self.size)
            Color(0, 0, 0, 0.45)
            Ellipse(pos=(cx - s * 1.6, cy - s * 1.6), size=(s * 3.2, s * 3.2))
            Color(1, 1, 1, 0.95)
            Triangle(points=[cx - s * 0.6, cy - s, cx - s * 0.6, cy + s, cx + s * 1.0, cy])


class CircleImage(ButtonBehavior, Widget):
    def __init__(self, source="", letter="S", ring=None, **kw):
        super().__init__(**kw)
        self.ring = ring
        self._tex = load_texture(source)
        self.lbl = Label(text=(letter or "S")[:1].upper(), bold=True, color=T("on_accent"))
        self.lbl.opacity = 0 if self._tex is not None else 1
        self.add_widget(self.lbl)
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def redraw(self, *args):
        self.canvas.before.clear()
        d = min(self.width, self.height)
        if d <= 0:
            return
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        inset = dp(3) if self.ring is not None else 0
        di = d - 2 * inset
        self.lbl.pos = self.pos
        self.lbl.size = self.size
        self.lbl.font_size = max(sp(10), d * 0.42)
        with self.canvas.before:
            if self.ring is not None:
                r = self.ring
                Color(r[0], r[1], r[2], 0.22)
                Ellipse(pos=(cx - d / 2 - dp(4), cy - d / 2 - dp(4)), size=(d + dp(8), d + dp(8)))
                Color(*r)
                Line(ellipse=(cx - d / 2, cy - d / 2, d, d), width=dp(2))
            if self._tex is not None:
                Color(1, 1, 1, 1)
                Ellipse(texture=cover_region(self._tex, 1, 1), pos=(cx - di / 2, cy - di / 2), size=(di, di))
            else:
                Color(*T("accent"))
                Ellipse(pos=(cx - di / 2, cy - di / 2), size=(di, di))


def topbar(title, on_back):
    bar = BoxLayout(size_hint_y=None, height=dp(56) + TOP_LOWER, padding=(dp(8), TOP_LOWER, dp(8), dp(8)),
                    spacing=dp(8))
    back = Icon("back", size_hint=(None, 1), width=dp(40))
    back.bind(on_release=lambda *_: on_back())
    bar.add_widget(back)
    bar.add_widget(LLabel(text=title, bold=True, font_size=sp(20), color=T("text")))
    return bar


def plain_title(text):
    """Title of Friends / Inbox, pushed down from the top of the screen."""
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=TOP_LOWER + TITLE_LOWER + dp(48))
    box.add_widget(Widget())
    box.add_widget(Label(text=text, bold=True, font_size=sp(24), color=T("accent"),
                         size_hint_y=None, height=dp(48)))
    return box


def scroll_col(spacing=dp(10), padding=dp(14)):
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
    inner = BoxLayout(orientation="vertical", size_hint_y=None, spacing=spacing, padding=padding)
    inner.bind(minimum_height=inner.setter("height"))
    sv.add_widget(inner)
    return sv, inner


def field(hint, password=False, text="", height=dp(52)):
    card = Card(bg="panel", radius=dp(14), outline=True, size_hint_y=None, height=height,
                padding=(dp(14), 0))
    ti = TextInput(
        text=text, hint_text=hint, multiline=False, password=password, write_tab=False,
        background_normal="", background_active="", background_color=(0, 0, 0, 0),
        foreground_color=T("text"), hint_text_color=T("sub"), cursor_color=T("accent"),
        font_size=sp(16), padding=[0, dp(14), 0, dp(14)])
    card.add_widget(ti)
    return card, ti


def hash_pw(user, pw):
    return hashlib.sha256(("samng|" + user + "|" + pw).encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------------
# STORAGE
# ----------------------------------------------------------------------------
DEFAULT_STATE = {
    "logged_in": False,
    "is_guest": False,
    "terms_accepted": False,
    "current_user": "",
    "users": {},
    "guest_profile": {"name": "Guest", "bio": "", "avatar": "", "banner": ""},
    "posts": [],
    "follows": {},
    "saved": {},
    "notifications": [],
    "settings": {"dark_mode": True, "orient_back": 3, "orient_front": 5},
}


class DataStore:
    def __init__(self, app):
        self.path = os.path.join(app.user_data_dir, STATE_FILE)

    def load(self):
        state = copy.deepcopy(DEFAULT_STATE)
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                settings = saved.pop("settings", {})
                state.update(saved)
                state["settings"].update(settings)
        except Exception:
            pass
        for p in state["posts"]:
            if "liked_by" not in p:
                p["liked_by"] = ["guest"] if p.get("liked") else []
            if not isinstance(p.get("comments"), list):
                p["comments"] = []
        return state

    def save(self, state):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass


class ThemedScreen(Screen):
    def build_ui(self):
        pass

    def rebuild(self):
        self.clear_widgets()
        self.build_ui()


# ----------------------------------------------------------------------------
# BUILT-IN VIDEO PLAYER (Android's own player: no extra video library needed,
# plays saved videos and internet links. Internet links need the INTERNET permission.)
# ----------------------------------------------------------------------------
_native = {"root": None, "video": None, "listener": None}


@run_on_ui_thread
def native_video_open(source):
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    activity = PythonActivity.mActivity
    VideoView = autoclass("android.widget.VideoView")
    MediaController = autoclass("android.widget.MediaController")
    FrameLayout = autoclass("android.widget.FrameLayout")
    Params = autoclass("android.widget.FrameLayout$LayoutParams")
    Button = autoclass("android.widget.Button")
    Gravity = autoclass("android.view.Gravity")
    Uri = autoclass("android.net.Uri")

    frame = FrameLayout(activity)
    frame.setBackgroundColor(-16777216)               # opaque black
    video = VideoView(activity)
    controller = MediaController(activity)
    controller.setAnchorView(video)
    video.setMediaController(controller)              # play / pause / seek bar
    if source.startswith("http"):
        video.setVideoURI(Uri.parse(source))
    else:
        video.setVideoPath(source)
    frame.addView(video, Params(-1, -1, Gravity.CENTER))

    try:
        listener = _CloseListener()
        close = Button(activity)
        close.setText("Close")
        close.setOnClickListener(listener)
        cparams = Params(-2, -2, Gravity.TOP | Gravity.RIGHT)
        cparams.setMargins(0, 110, 24, 0)
        frame.addView(close, cparams)
        _native["listener"] = listener
    except Exception:
        pass                                          # the Back key still closes the player

    activity.addContentView(frame, Params(-1, -1))
    video.requestFocus()
    video.start()
    _native["root"] = frame
    _native["video"] = video


@run_on_ui_thread
def native_video_close():
    frame = _native["root"]
    video = _native["video"]
    _native["root"] = None
    _native["video"] = None
    if frame is None:
        return
    try:
        if video is not None:
            video.stopPlayback()
        parent = frame.getParent()
        if parent is not None:
            cast("android.view.ViewGroup", parent).removeView(frame)
    except Exception:
        pass


if ANDROID:
    class _CloseListener(PythonJavaClass):
        __javainterfaces__ = ["android/view/View$OnClickListener"]
        __javacontext__ = "app"

        @java_method("(Landroid/view/View;)V")
        def onClick(self, view):
            native_video_close()


# ----------------------------------------------------------------------------
# BOOT / SPLASH SCREEN (logo only)
# ----------------------------------------------------------------------------
class SplashScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def build_ui(self):
        root = FloatLayout()
        paint_bg(root)
        self.add_widget(root)
        # logo.png must sit next to main.py. If it is missing you just see the plain background.
        root.add_widget(CoverImage(source="logo.png", fallback="bg", mode="contain", size_hint=(1, 1)))


# ----------------------------------------------------------------------------
# CAMERA (the "+" button): live preview, Gallery on the bottom left, shutter, flip
# ----------------------------------------------------------------------------
class CameraPreview(Widget):
    """Draws the live camera picture, full screen, with rotation / mirror / colour filter."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.cam = None
        self.angle = 0
        self.mirror = False
        self.tint = None
        self._last_size = None
        self._tick = None
        self.bind(pos=self.redraw, size=self.redraw)

    def start(self):
        if self._tick is None:
            self._tick = Clock.schedule_interval(self.tick, 1 / 30.0)

    def stop(self):
        if self._tick is not None:
            self._tick.cancel()
            self._tick = None

    def tick(self, dt):
        if self.cam is None:
            return
        tex = self.cam.texture
        size = tex.size if tex is not None else None
        if size != self._last_size:
            self.redraw()
        else:
            self.canvas.ask_update()

    def set_camera(self, cam):
        self.cam = cam
        self._last_size = None
        self.redraw()

    def set_orientation(self, index):
        self.angle = (0, 90, 180, 270)[index % 4]
        self.mirror = index >= 4
        self.redraw()

    def set_tint(self, rgba):
        self.tint = rgba
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        w, h = self.size
        if w <= 0 or h <= 0:
            return
        x, y = self.pos
        cx = x + w / 2.0
        cy = y + h / 2.0
        tex = self.cam.texture if self.cam is not None else None
        self._last_size = tex.size if tex is not None else None
        with self.canvas:
            Color(0, 0, 0, 1)
            Rectangle(pos=self.pos, size=self.size)
            if tex is not None:
                tw, th = tex.size
                quarter = self.angle in (90, 270)
                dw, dh = (th, tw) if quarter else (tw, th)
                s = max(w / float(dw), h / float(dh))
                PushMatrix()
                if self.mirror:
                    Scale(-1, 1, 1, origin=(cx, cy))
                Rotate(angle=self.angle, origin=(cx, cy))
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=(cx - tw * s / 2.0, cy - th * s / 2.0), size=(tw * s, th * s))
                PopMatrix()
            if self.tint is not None:
                Color(*self.tint)
                Rectangle(pos=self.pos, size=self.size)


class Shutter(ButtonBehavior, Widget):
    """Big round capture button. White for photo, red inside for video."""

    def __init__(self, video=False, **kw):
        super().__init__(**kw)
        self.video = video
        self.bind(pos=self.redraw, size=self.redraw, state=self.redraw)
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        d = min(self.width, self.height)
        if d <= 0:
            return
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        inner = d * (0.58 if self.state == "down" else 0.68)
        with self.canvas:
            Color(1, 1, 1, 1)
            Line(ellipse=(cx - d / 2 + dp(2), cy - d / 2 + dp(2), d - dp(4), d - dp(4)), width=dp(3.5))
            if self.video:
                Color(1.0, 0.16, 0.30, 1)
            Ellipse(pos=(cx - inner / 2, cy - inner / 2), size=(inner, inner))


FILTERS = (("Normal", None), ("Cyan", (0, 0.9, 1, 0.22)), ("Pink", (1, 0.1, 0.5, 0.22)),
           ("Mono", (0.8, 0.8, 0.8, 0.3)))


class CameraScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.mode = "photo"
        self.facing = "back"
        self.purpose = "post"
        self.cam = None
        self.build_ui()

    # ---- layout (built once; the live camera is never rebuilt) -------------
    def build_ui(self):
        app = App.get_running_app()
        root = FloatLayout()
        paint_rgba(root, (0, 0, 0, 1))
        self.add_widget(root)

        self.preview = CameraPreview(size_hint=(1, 1))
        root.add_widget(self.preview)

        self.msg = Label(text="Starting camera...", color=(1, 1, 1, 0.8), font_size=sp(15),
                         size_hint=(None, None), size=(dp(300), dp(60)),
                         pos_hint={"center_x": 0.5, "center_y": 0.55}, halign="center")
        root.add_widget(self.msg)

        self.fallback = NeonPill(text="Use phone camera app", translucent=True, font_size=sp(14),
                                 size_hint=(None, None), size=(dp(240), dp(46)),
                                 pos_hint={"center_x": 0.5, "center_y": 0.46})
        self.fallback.opacity = 0
        self.fallback.disabled = True
        self.fallback.bind(on_release=lambda *_: self.use_phone_camera())
        root.add_widget(self.fallback)

        back = Icon("back", color=WHITE, circle_bg=(0, 0, 0, 0.45), size_hint=(None, None),
                    size=(dp(42), dp(42)), pos_hint={"x": 0.04, "top": 0.965})
        back.bind(on_release=lambda *_: app.back())
        root.add_widget(back)

        rotate = NeonPill(text="Rotate", translucent=True, font_size=sp(13), size_hint=(None, None),
                          size=(dp(90), dp(38)), pos_hint={"right": 0.96, "top": 0.965})
        rotate.bind(on_release=lambda *_: self.rotate_view())
        root.add_widget(rotate)

        bottom = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=dp(8),
                           height=dp(188) + NAV_RAISE,
                           padding=(dp(14), 0, dp(14), dp(10) + NAV_RAISE), pos_hint={"x": 0, "y": 0})

        chips = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        self.chips = []
        for name, tint in FILTERS:
            chip = NeonPill(text=name, active=(tint is None), translucent=True, font_size=sp(12),
                            size_hint=(1, None), height=dp(32))
            chip.bind(on_release=lambda *_, c=chip, t=tint: self.set_filter(c, t))
            chips.add_widget(chip)
            self.chips.append(chip)
        bottom.add_widget(chips)

        self.mode_row = BoxLayout(size_hint_y=None, height=dp(36), padding=(dp(70), 0))
        self.tab_photo = TabLabel("PHOTO", active=True, light=True)
        self.tab_video = TabLabel("VIDEO", active=False, light=True)
        self.tab_photo.bind(on_release=lambda *_: self.set_mode("photo"))
        self.tab_video.bind(on_release=lambda *_: self.set_mode("video"))
        self.mode_row.add_widget(self.tab_photo)
        self.mode_row.add_widget(self.tab_video)
        bottom.add_widget(self.mode_row)

        controls = BoxLayout(size_hint_y=None, height=dp(88), spacing=dp(12))
        gallery = NeonPill(text="Gallery", translucent=True, font_size=sp(15), size_hint=(1, None),
                           height=dp(46), pos_hint={"center_y": 0.5})
        gallery.bind(on_release=lambda *_: self.open_gallery())
        self.shutter = Shutter(video=False, size_hint=(None, None), size=(dp(80), dp(80)),
                               pos_hint={"center_y": 0.5})
        self.shutter.bind(on_release=lambda *_: self.on_shutter())
        flip = NeonPill(text="Flip", translucent=True, font_size=sp(15), size_hint=(1, None),
                        height=dp(46), pos_hint={"center_y": 0.5})
        flip.bind(on_release=lambda *_: self.flip())
        controls.add_widget(gallery)
        controls.add_widget(self.shutter)
        controls.add_widget(flip)
        bottom.add_widget(controls)
        root.add_widget(bottom)

    # ---- screen events --------------------------------------------------------
    def on_pre_enter(self, *args):
        app = App.get_running_app()
        self.purpose = app.cam_purpose
        self.mode = "photo"
        self.apply_mode_ui()
        is_post = (self.purpose == "post")
        self.mode_row.height = dp(36) if is_post else 0
        self.mode_row.opacity = 1 if is_post else 0
        self.mode_row.disabled = not is_post
        self.show_message("Starting camera...", fallback=False)
        self.preview.start()
        self.ask_permission_then_start()

    def on_leave(self, *args):
        self.preview.stop()
        self.release_camera()

    # ---- camera control -----------------------------------------------------------
    def ask_permission_then_start(self):
        if ANDROID:
            try:
                from android.permissions import request_permissions, check_permission
                if not check_permission("android.permission.CAMERA"):
                    request_permissions(["android.permission.CAMERA", "android.permission.RECORD_AUDIO"],
                                        lambda perms, grants: Clock.schedule_once(lambda dt: self.start_camera(), 0.4))
                    return
            except Exception:
                pass
        self.start_camera()

    def resume(self):
        """Called after the phone's own camera/recorder closes."""
        if App.get_running_app().sm.current == "camera":
            self.ask_permission_then_start()

    def show_message(self, text, fallback):
        self.msg.text = text
        self.msg.opacity = 1 if text else 0
        self.fallback.opacity = 1 if fallback else 0
        self.fallback.disabled = not fallback

    def start_camera(self):
        self.release_camera()
        app = App.get_running_app()
        index = 1 if self.facing == "front" else 0
        cam = None
        error = ""
        try:
            from kivy.uix.camera import Camera
            for resolution in ((1280, 720), (960, 720), (640, 480)):
                try:
                    cam = Camera(index=index, resolution=resolution, play=True)
                    break
                except Exception as e:
                    error = str(e)
                    cam = None
        except Exception as e:
            error = str(e)
        if cam is None:
            self.show_message("Could not start the camera.\n" + error[:70], fallback=True)
            return
        self.cam = cam
        self.preview.set_orientation(app.state["settings"].get("orient_" + self.facing, 0))
        self.preview.set_camera(cam)
        self.show_message("", fallback=False)
        Clock.schedule_once(self.check_frames, 4.0)

    def check_frames(self, dt):
        if self.cam is not None and self.cam.texture is None:
            self.show_message("No camera picture yet.\nCheck camera permission, or use the phone camera.",
                              fallback=True)

    def release_camera(self):
        cam = self.cam
        self.cam = None
        self.preview.set_camera(None)
        if cam is None:
            return
        try:
            cam.play = False
        except Exception:
            pass
        try:
            inner = getattr(cam, "_camera", None)
            if inner is not None and hasattr(inner, "_release_camera"):
                inner._release_camera()        # lets the phone's camera app use the camera
        except Exception:
            pass

    # ---- buttons ---------------------------------------------------------------------
    def set_filter(self, chip, tint):
        for c in self.chips:
            c.set_active(c is chip)
        self.preview.set_tint(tint)

    def apply_mode_ui(self):
        self.tab_photo.set_active(self.mode == "photo")
        self.tab_video.set_active(self.mode == "video")
        self.shutter.video = (self.mode == "video")
        self.shutter.redraw()

    def set_mode(self, mode):
        self.mode = mode
        self.apply_mode_ui()

    def flip(self):
        self.facing = "front" if self.facing == "back" else "back"
        self.start_camera()

    def rotate_view(self):
        app = App.get_running_app()
        key = "orient_" + self.facing
        value = (app.state["settings"].get(key, 0) + 1) % 8
        app.state["settings"][key] = value
        app.save_state()
        self.preview.set_orientation(value)

    def open_gallery(self):
        app = App.get_running_app()
        app.open_gallery(app.gallery_callback_for(self.purpose))

    def use_phone_camera(self):
        app = App.get_running_app()
        self.release_camera()
        callback = app.gallery_callback_for(self.purpose)
        if self.mode == "video" and self.purpose == "post":
            app.record_video(self.facing == "front", callback)
        else:
            app.system_photo(self.facing == "front", callback)

    def on_shutter(self):
        app = App.get_running_app()
        if self.mode == "video" and self.purpose == "post":
            self.release_camera()
            app.record_video(self.facing == "front", app.gallery_callback_for("post"))
            return
        if self.cam is None or self.cam.texture is None:
            app.toast("The camera is not ready yet")
            return
        try:
            folder = os.path.join(app.user_data_dir, "media")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, "cam_%d.png" % int(time.time() * 1000))
            self.preview.export_to_png(path)
        except Exception as e:
            app.toast("Could not save the photo: " + str(e)[:40])
            return
        app.gallery_callback_for(self.purpose)(path)


# ----------------------------------------------------------------------------
# GALLERY (our own: Photos | Videos, straight from the phone's pictures)
# ----------------------------------------------------------------------------
class GalleryScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.kind = "image"
        self._gen = 0
        self.cache = {"image": [], "video": []}
        self.shown = 0
        self.build_ui()

    def build_ui(self):
        app = App.get_running_app()
        root = BoxLayout(orientation="vertical")
        paint_bg(root)
        self.add_widget(root)
        root.add_widget(topbar("Gallery", app.back))

        tabs = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(30), 0))
        self.tab_photos = TabLabel("Photos", active=(self.kind == "image"))
        self.tab_videos = TabLabel("Videos", active=(self.kind == "video"))
        self.tab_photos.bind(on_release=lambda *_: self.set_kind("image"))
        self.tab_videos.bind(on_release=lambda *_: self.set_kind("video"))
        tabs.add_widget(self.tab_photos)
        tabs.add_widget(self.tab_videos)
        root.add_widget(tabs)

        self.msg = Label(text="", color=T("sub"), font_size=sp(14), size_hint_y=None, height=dp(30))
        root.add_widget(self.msg)

        self.sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.grid = GridLayout(cols=3, spacing=dp(3), padding=dp(3), size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.sv.add_widget(self.grid)
        root.add_widget(self.sv)
        self.fill(self.cache[self.kind])

    def on_pre_enter(self, *args):
        self.ask_permission_then_load()

    def on_leave(self, *args):
        self._gen += 1                      # stop any loading in the background

    def ask_permission_then_load(self):
        if not ANDROID:
            self.msg.text = "The gallery works on Android only"
            return
        try:
            from android.permissions import request_permissions, check_permission
            granted = any(check_permission(p) for p in MEDIA_PERMISSIONS)
            if not granted:
                self.msg.text = "Allow access to your photos to see your gallery"
                request_permissions(MEDIA_PERMISSIONS,
                                    lambda perms, grants: Clock.schedule_once(lambda dt: self.load(self.kind), 0.4))
                return
        except Exception:
            pass
        self.load(self.kind)

    def set_kind(self, kind):
        if kind == self.kind:
            return
        self.kind = kind
        self.tab_photos.set_active(kind == "image")
        self.tab_videos.set_active(kind == "video")
        self.fill(self.cache[kind])
        self.load(kind)

    def fill(self, items):
        self.grid.clear_widgets()
        self.shown = 0
        self.append(items)

    def append(self, items):
        app = App.get_running_app()
        for thumb, uri in items[self.shown:]:
            if self.kind == "video":
                tile = VideoTile(thumb=thumb, size_hint_y=None, height=dp(120))
            else:
                tile = CoverImage(source=thumb, size_hint_y=None, height=dp(120))
            tile.bind(on_release=lambda *_, u=uri, k=self.kind: self.pick(k, u))
            self.grid.add_widget(tile)
        self.shown = len(items)

    def load(self, kind):
        app = App.get_running_app()
        if not ANDROID:
            return
        self._gen += 1
        gen = self._gen
        self.msg.text = "Loading..."
        self.cache[kind] = []
        self.fill([])

        def finish(text):
            if gen == self._gen:
                self.msg.text = text

        def work():
            try:
                entries = app.query_media(kind)
            except Exception as e:
                Clock.schedule_once(lambda dt: finish("Can't read your gallery: " + str(e)[:40]), 0)
                return
            if not entries:
                Clock.schedule_once(lambda dt: finish("No %s found" % ("videos" if kind == "video" else "photos")), 0)
                return
            loaded = []
            for i, (mid, uri) in enumerate(entries):
                if gen != self._gen:
                    return
                loaded.append((app.media_thumb(kind, mid, uri), uri))
                if len(loaded) % 12 == 0 or i == len(entries) - 1:
                    snapshot = list(loaded)
                    Clock.schedule_once(lambda dt, s=snapshot: self.show_batch(kind, s, gen), 0)
            Clock.schedule_once(lambda dt: finish(""), 0)
        threading.Thread(target=work, daemon=True).start()

    def show_batch(self, kind, items, gen):
        if gen != self._gen or kind != self.kind:
            return
        self.cache[kind] = items
        self.append(items)

    def pick(self, kind, uri):
        app = App.get_running_app()
        callback = app.gallery_cb
        if callback is None:
            return
        self.msg.text = "Opening..."

        def work():
            path = app.copy_uri(uri)
            if path and kind == "video":
                app._thumbs[path] = app.make_thumb(path)

            def done(dt):
                self.msg.text = ""
                if path:
                    callback(path)
                else:
                    app.toast("Could not open that file")
            Clock.schedule_once(done, 0)
        threading.Thread(target=work, daemon=True).start()


# ----------------------------------------------------------------------------
# BOTTOM NAV
# ----------------------------------------------------------------------------
NAV_HEIGHT = dp(76) + NAV_RAISE


class BottomNav(BoxLayout):
    def __init__(self, active="home", translucent=False, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=NAV_HEIGHT,
                         padding=(dp(12), dp(10), dp(12), dp(10) + NAV_RAISE), spacing=dp(8), **kw)
        app = App.get_running_app()
        if translucent:
            paint_rgba(self, (0, 0, 0, 0.25 * GLASS))
        unread = app.unread_count()
        for key, label in (("home", "Home"), ("friends", "Friends"), ("create", "+"), ("inbox", "Inbox")):
            if key == "inbox" and unread:
                label = "Inbox (%d)" % unread
            p = NeonPill(text=label, active=(active == key), translucent=translucent,
                         font_size=sp(24 if key == "create" else 14),
                         size_hint=(1, None), height=dp(44), pos_hint={"center_y": 0.5})
            p.bind(on_release=lambda *_, k=key: app.nav(k))
            self.add_widget(p)
        prof = app.profile()
        glow = T("glow")
        ring = glow if active == "profile" else [glow[0], glow[1], glow[2], 0.6]
        avatar = CircleImage(source=prof.get("avatar", ""), letter=prof.get("name", "S"), ring=ring,
                             size_hint=(None, None), size=(dp(54), dp(54)), pos_hint={"center_y": 0.5})
        avatar.bind(on_release=lambda *_: app.nav("profile"))
        self.add_widget(avatar)


# ----------------------------------------------------------------------------
# ONBOARDING SCREENS
# ----------------------------------------------------------------------------
class WelcomeScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def build_ui(self):
        app = App.get_running_app()
        root = FloatLayout()
        paint_bg(root)
        self.add_widget(root)

        col = BoxLayout(orientation="vertical", size_hint=(0.8, None), height=dp(420), spacing=dp(14),
                        pos_hint={"center_x": 0.5, "center_y": 0.5})
        col.add_widget(Label(text="SAM NG", color=T("accent"), bold=True, font_size=sp(46),
                             size_hint_y=None, height=dp(90)))
        col.add_widget(Label(text="Create. Share. Discover.", color=T("sub"), font_size=sp(16),
                             size_hint_y=None, height=dp(30)))
        col.add_widget(Widget())
        login = pill("Login", primary=True)
        login.bind(on_release=lambda *_: app.go("login"))
        signup = pill("Sign up")
        signup.bind(on_release=lambda *_: app.go("signup"))
        skip = pill("Skip sign in", height=dp(48))
        skip.bind(on_release=lambda *_: app.skip_sign_in())
        col.add_widget(login)
        col.add_widget(signup)
        col.add_widget(skip)
        root.add_widget(col)


class LoginScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def build_ui(self):
        app = App.get_running_app()
        root = BoxLayout(orientation="vertical")
        paint_bg(root)
        self.add_widget(root)
        root.add_widget(topbar("Login", app.back))

        col = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(340), spacing=dp(14),
                        padding=(dp(24), dp(16)))
        col.add_widget(Label(text="Welcome back", color=T("sub"), font_size=sp(15),
                             size_hint_y=None, height=dp(28)))
        user_card, self.username = field("Username")
        pass_card, self.password = field("Password", password=True)
        col.add_widget(user_card)
        col.add_widget(pass_card)
        go = pill("Login", primary=True)
        go.bind(on_release=lambda *_: self.submit())
        col.add_widget(go)
        to_signup = pill("No account? Sign up", height=dp(48))
        to_signup.bind(on_release=lambda *_: app.go("signup"))
        col.add_widget(to_signup)
        root.add_widget(col)
        root.add_widget(Widget())

    def submit(self):
        app = App.get_running_app()
        name = self.username.text.strip()
        password = self.password.text
        if not name or not password:
            app.toast("Enter your username and password")
            return
        key = app.find_user(name)
        if key is None:
            app.toast("No account found. Please sign up first.")
            return
        if app.state["users"][key].get("pw") != hash_pw(key, password):
            app.toast("Wrong password")
            return
        app.state["current_user"] = key
        app.state["logged_in"] = True
        app.state["is_guest"] = False
        app.save_state()
        self.password.text = ""
        app.after_auth()


class SignupScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def build_ui(self):
        app = App.get_running_app()
        root = BoxLayout(orientation="vertical")
        paint_bg(root)
        self.add_widget(root)
        root.add_widget(topbar("Sign up", app.back))

        col = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(430), spacing=dp(14),
                        padding=(dp(24), dp(16)))
        col.add_widget(Label(text="Create your account", color=T("sub"), font_size=sp(15),
                             size_hint_y=None, height=dp(28)))
        u_card, self.username = field("Choose a username")
        p_card, self.password = field("Choose a password (6+ characters)", password=True)
        c_card, self.confirm = field("Repeat the password", password=True)
        col.add_widget(u_card)
        col.add_widget(p_card)
        col.add_widget(c_card)
        go = pill("Create account", primary=True)
        go.bind(on_release=lambda *_: self.submit())
        col.add_widget(go)
        to_login = pill("Already have an account? Login", height=dp(48))
        to_login.bind(on_release=lambda *_: app.go("login"))
        col.add_widget(to_login)
        root.add_widget(col)
        root.add_widget(Widget())

    def submit(self):
        app = App.get_running_app()
        name = self.username.text.strip()
        password = self.password.text
        if len(name) < 3 or " " in name:
            app.toast("Username: 3+ characters, no spaces")
            return
        if len(password) < 6:
            app.toast("Password must be 6+ characters")
            return
        if password != self.confirm.text:
            app.toast("The two passwords do not match")
            return
        if app.find_user(name) is not None:
            app.toast("That username is already taken")
            return
        key = name.lower()
        app.state["users"][key] = {
            "pw": hash_pw(key, password), "name": name, "bio": "", "avatar": "", "banner": "",
            "private": False, "allow_comments": True, "notify": True,
        }
        app.state["current_user"] = key
        app.state["logged_in"] = True
        app.state["is_guest"] = False
        app.save_state()
        self.password.text = ""
        self.confirm.text = ""
        app.toast("Account created")
        app.after_auth()


class TermsScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def build_ui(self):
        app = App.get_running_app()
        root = BoxLayout(orientation="vertical", padding=(dp(16), dp(16) + TOP_LOWER, dp(16), dp(16)),
                         spacing=dp(12))
        paint_bg(root)
        self.add_widget(root)

        root.add_widget(Label(text="Before you continue", color=T("accent"), bold=True,
                              font_size=sp(24), size_hint_y=None, height=dp(44)))

        box = Card(bg="panel", radius=dp(16), outline=True, padding=dp(6))
        sv, inner = scroll_col()
        for heading, body in (("Terms and Conditions", TERMS_TEXT), ("Privacy Policy", PRIVACY_TEXT)):
            inner.add_widget(Wrap(text=heading, bold=True, font_size=sp(18), color=T("text")))
            inner.add_widget(Wrap(text=body or PLACEHOLDER, font_size=sp(15), color=T("sub")))
        box.add_widget(sv)
        root.add_widget(box)

        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        cb = CheckBox(size_hint=(None, None), size=(dp(36), dp(36)), pos_hint={"center_y": 0.5},
                      color=T("accent"))
        row.add_widget(cb)
        row.add_widget(LLabel(text="I agree to the Terms and Conditions and the Privacy Policy",
                              color=T("text"), font_size=sp(14)))
        root.add_widget(row)

        agree = pill("Agree and continue", primary=True)
        agree.disabled = True
        agree.bind(on_release=lambda *_: app.accept_terms())
        cb.bind(active=lambda w, v: setattr(agree, "disabled", not v))
        root.add_widget(agree)

        decline = pill("Decline", height=dp(48))
        decline.bind(on_release=lambda *_: app.decline_terms())
        root.add_widget(decline)


class InfoScreen(ThemedScreen):
    def __init__(self, title, sections, **kw):
        super().__init__(**kw)
        self.title_text = title
        self.sections = sections
        self.build_ui()

    def build_ui(self):
        app = App.get_running_app()
        root = BoxLayout(orientation="vertical")
        paint_bg(root)
        self.add_widget(root)
        root.add_widget(topbar(self.title_text, app.back))
        sv, inner = scroll_col(padding=dp(16))
        for heading, body in self.sections():
            if heading:
                inner.add_widget(Wrap(text=heading, bold=True, font_size=sp(19), color=T("text")))
            inner.add_widget(Wrap(text=body or PLACEHOLDER, font_size=sp(15), color=T("sub")))
        root.add_widget(sv)


class PrivacyScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def build_ui(self):
        app = App.get_running_app()
        prof = app.profile()
        root = BoxLayout(orientation="vertical")
        paint_bg(root)
        self.add_widget(root)
        root.add_widget(topbar("Privacy settings", app.back))
        sv, inner = scroll_col(padding=dp(14))
        for label, key, default in (("Private account (only followers see my posts)", "private", False),
                                    ("Allow comments on my posts", "allow_comments", True),
                                    ("Send me inbox notifications", "notify", True)):
            row = Card(bg="panel", radius=dp(14), outline=True, size_hint_y=None, height=dp(64),
                       padding=(dp(14), 0), spacing=dp(8))
            row.add_widget(LLabel(text=label, color=T("text"), font_size=sp(15)))
            sw = Switch(active=bool(prof.get(key, default)), size_hint=(None, 1), width=dp(83))
            sw.bind(active=lambda w, v, k=key: app.set_profile_flag(k, v))
            row.add_widget(sw)
            inner.add_widget(row)
        policy = pill("Read the Privacy Policy", height=dp(50))
        policy.bind(on_release=lambda *_: app.go("legal"))
        inner.add_widget(policy)
        root.add_widget(sv)


# ----------------------------------------------------------------------------
# FULL-SCREEN FEED
# ----------------------------------------------------------------------------
class FeedPager(FloatLayout):
    def __init__(self, posts, make_page, start=0, on_change=None, **kw):
        super().__init__(**kw)
        self.posts = posts
        self.make_page = make_page
        self.on_change = on_change
        self.index = 0
        self.page = None
        self._sx = None
        self._sy = None
        self.show(start, fade=False)

    def show(self, index, fade=True):
        if not self.posts:
            return
        self.index = max(0, min(index, len(self.posts) - 1))
        if self.page is not None:
            self.remove_widget(self.page)
        self.page = self.make_page(self.posts[self.index], self)
        self.add_widget(self.page)
        if fade:
            self.page.opacity = 0
            Animation(opacity=1, duration=0.18).start(self.page)
        if self.on_change:
            self.on_change(self.index)

    def refresh_current(self):
        self.show(self.index, fade=False)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._sx, self._sy = touch.pos
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._sy is not None:
            dy = touch.y - self._sy
            dx = touch.x - self._sx
            self._sy = None
            if abs(dy) > dp(70) and abs(dy) > abs(dx) * 1.3:
                super().on_touch_up(touch)
                self.show(self.index + (1 if dy > 0 else -1))
                return True
        return super().on_touch_up(touch)


class HomeScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.tab = "foryou"
        self.search_text = ""
        self.search_open = False
        self.page_index = 0
        self.pager = None
        self.content = None
        self.ui_hidden = False
        self._last_tap_time = 0
        self.tabs_box = None
        self.nav = None
        self.build_ui()

    def on_pre_enter(self, *args):
        self.rebuild()

    def set_tab(self, key):
        self.tab = key
        self.page_index = 0
        self.rebuild()

    def toggle_search(self):
        self.search_open = not self.search_open
        self.page_index = 0
        if not self.search_open:
            self.search_text = ""
            self.rebuild()
            return
        self.rebuild()
        Clock.schedule_once(lambda dt: setattr(self.search, "focus", True), 0.15)

    def on_search(self, instance, value):
        self.search_text = value.strip().lower()
        self.page_index = 0
        self.fill_content()

    def set_index(self, index):
        self.page_index = index

    def top_height(self):
        return TOP_LOWER + dp(52) + (dp(52) if self.search_open else 0)

    def visible_posts(self):
        app = App.get_running_app()
        me = app.author_id()
        following = app.following_of(me)
        out = []
        for post in app.state["posts"]:
            author = post.get("author", "")
            tags = post.get("tags", "").lower()
            if not app.can_see(post):
                continue
            if self.tab == "following" and author not in following:
                continue
            if self.tab == "stem" and "stem" not in tags:
                continue
            if self.search_text:
                hay = (post.get("caption", "") + " " + tags + " " + author).lower()
                if self.search_text not in hay:
                    continue
            out.append(post)
        return list(reversed(out))

    def on_touch_down(self, touch):
        # double tap anywhere hides / shows the top row and the bottom row
        if self.collide_point(*touch.pos):
            now = time.time()
            if now - self._last_tap_time < 0.3:
                self._last_tap_time = 0
                self.toggle_ui_visibility()
                return True
            self._last_tap_time = now
        return super().on_touch_down(touch)

    def toggle_ui_visibility(self):
        self.ui_hidden = not self.ui_hidden
        for w in (self.tabs_box, self.nav):
            if w is None:
                continue
            Animation(opacity=0 if self.ui_hidden else 1, duration=0.25).start(w)
            w.disabled = self.ui_hidden

    def build_ui(self):
        app = App.get_running_app()
        posts = self.visible_posts()
        has_posts = bool(posts)

        root = FloatLayout()
        paint_bg(root)
        self.add_widget(root)

        self.content = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content)

        self.tabs_box = BoxLayout(orientation="vertical", size_hint=(1, None), height=self.top_height(),
                                  pos_hint={"x": 0, "top": 1})
        if has_posts:
            paint_rgba(self.tabs_box, (0, 0, 0, 0.3 * GLASS))
        self.tabs_box.add_widget(Widget(size_hint_y=None, height=TOP_LOWER))
        tabs = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(10), dp(4)), spacing=dp(2))
        for key, label in (("stem", "STEM"), ("following", "Following"), ("foryou", "For You")):
            t = TabLabel(label, active=(self.tab == key), light=has_posts)
            t.bind(on_release=lambda *_, k=key: self.set_tab(k))
            tabs.add_widget(t)
        s_btn = Icon("search", color=(WHITE if has_posts else T("sub")), size_hint=(None, 1), width=dp(38))
        s_btn.bind(on_release=lambda *_: self.toggle_search())
        tabs.add_widget(s_btn)
        self.tabs_box.add_widget(tabs)

        if self.search_open:
            row = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(12), dp(2), dp(12), dp(4)))
            card, self.search = field("Search posts, people, tags", text=self.search_text, height=dp(46))
            self.search.bind(text=self.on_search)
            row.add_widget(card)
            self.tabs_box.add_widget(row)
        root.add_widget(self.tabs_box)

        self.nav = BottomNav(active="home", translucent=has_posts)
        self.nav.size_hint = (1, None)
        self.nav.pos_hint = {"x": 0, "y": 0}
        root.add_widget(self.nav)

        if self.ui_hidden:
            self.tabs_box.opacity = 0
            self.tabs_box.disabled = True
            self.nav.opacity = 0
            self.nav.disabled = True

        self.fill_content()

    def fill_content(self):
        app = App.get_running_app()
        self.content.clear_widgets()
        posts = self.visible_posts()
        self.pager = None
        if posts:
            start = min(self.page_index, len(posts) - 1)
            self.pager = FeedPager(posts, self.make_page, start=start, on_change=self.set_index,
                                   size_hint=(1, 1))
            self.content.add_widget(self.pager)
            return

        body = BoxLayout(orientation="vertical", size_hint=(1, 1),
                         padding=(dp(16), self.top_height() + dp(16), dp(16), NAV_HEIGHT + dp(16)),
                         spacing=dp(12))

        sv, inner = scroll_col(spacing=dp(12), padding=0)
        if self.tab == "following":
            if app.state["logged_in"]:
                title, sub = "Nothing here yet", "Follow people from the Friends tab to see their posts."
            else:
                title, sub = "Nothing here yet", "Log in and follow people to see their posts here."
        elif self.tab == "stem":
            title, sub = "No STEM posts yet", "Add the tag stem when you create a post."
        elif self.search_text:
            title, sub = "No results", "Try a different search."
        else:
            title, sub = "Your feed starts here", "Tap + to add a photo or video."
        if self.tab == "foryou" and not self.search_text:
            inner.add_widget(Wrap(text=HOME_HEADLINE, bold=True, font_size=sp(34), color=T("text"),
                                  halign="center", valign="middle"))
        inner.add_widget(Widget(size_hint_y=None, height=dp(20)))
        inner.add_widget(Wrap(text=title, font_size=sp(24), color=T("sub"), halign="center"))
        inner.add_widget(Wrap(text=sub, font_size=sp(15), color=T("sub"), halign="center"))
        inner.add_widget(Widget(size_hint_y=None, height=dp(16)))

        holder = BoxLayout(size_hint_y=None, height=dp(104))
        create = NeonPill(text="[size=34sp]+[/size]\nCreate a post", markup=True, active=True, fg=T("text"),
                          font_size=sp(16), size_hint=(None, None), size=(dp(210), dp(96)))
        create.bind(on_release=lambda *_: app.open_camera("post"))
        holder.add_widget(Widget())
        holder.add_widget(create)
        holder.add_widget(Widget())
        inner.add_widget(holder)
        body.add_widget(sv)
        self.content.add_widget(body)

    def make_page(self, post, pager):
        app = App.get_running_app()
        me = app.author_id()
        page = FloatLayout()

        path = post.get("path", "")
        if post.get("kind") == "video":
            media = VideoTile(thumb=post.get("thumb", ""), mode=FEED_MODE, size_hint=(1, 1))
            media.bind(on_release=lambda *_, p=path: app.play_video(p))
        else:
            media = CoverImage(source=path, fallback="bg", mode=FEED_MODE, size_hint=(1, 1))
        page.add_widget(media)

        liked = me in post.get("liked_by", [])
        saved = app.is_saved(post)
        count_likes = len(post.get("liked_by", []))
        count_comments = len(post.get("comments", []))
        size = dp(54)
        column = BoxLayout(orientation="vertical", size_hint=(None, None),
                           size=(size, 4 * size + 3 * dp(10)), spacing=dp(10),
                           pos_hint={"right": 0.97, "center_y": 0.42})

        def action(text, active, handler):
            b = NeonPill(text=text, active=active, font_size=sp(11), size_hint=(None, None),
                         size=(size, size), translucent=True)
            b.bind(on_release=lambda *_: handler())
            column.add_widget(b)

        def do_like():
            app.toggle_like(post)
            pager.refresh_current()

        def do_save():
            app.toggle_save(post)
            pager.refresh_current()

        action("Like\n%d" % count_likes, liked, do_like)
        action("Chat\n%d" % count_comments, False,
               lambda: app.comments_dialog(post, on_change=pager.refresh_current))
        action("Saved" if saved else "Save", saved, do_save)
        action("Share", False, lambda: app.share_post(post))
        page.add_widget(column)

        author = app.profile(post.get("author"))
        info = BoxLayout(orientation="vertical", size_hint=(0.66, None), height=dp(128), spacing=dp(4),
                         padding=dp(8), pos_hint={"x": 0.03, "y": NAV_HEIGHT / max(1.0, Window.height) + 0.02})
        paint_rgba(info, (0, 0, 0, 0.5 * GLASS), dp(12))
        head = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        head.add_widget(CircleImage(source=author.get("avatar", ""), letter=author.get("name", "S"),
                                    size_hint=(None, None), size=(dp(34), dp(34))))
        head.add_widget(LLabel(text=author.get("name", "Sam Ng"), bold=True, font_size=sp(16), color=WHITE))
        info.add_widget(head)
        info.add_widget(Wrap(text=post.get("caption", ""), font_size=sp(14), color=WHITE, max_lines=3))
        tags = [t.strip() for t in post.get("tags", "").split(",") if t.strip()]
        if tags:
            info.add_widget(LLabel(text="#" + " #".join(tags), font_size=sp(13), color=T("accent"),
                                   size_hint_y=None, height=dp(20)))
        page.add_widget(info)
        return page


# ----------------------------------------------------------------------------
# FRIENDS + INBOX
# ----------------------------------------------------------------------------
class FriendsScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def on_pre_enter(self, *args):
        self.rebuild()

    def build_ui(self):
        app = App.get_running_app()
        me = app.author_id()
        root = BoxLayout(orientation="vertical")
        paint_bg(root)
        self.add_widget(root)
        root.add_widget(plain_title("Friends"))
        sv, inner = scroll_col(padding=dp(12))
        others = [(k, u) for k, u in app.state["users"].items() if k != me]
        if not others:
            inner.add_widget(Wrap(text="No other accounts yet. When someone else signs up on this phone, "
                                       "they will show up here so you can follow them.",
                                  font_size=sp(15), color=T("sub"), halign="center"))
        following = app.following_of(me)
        for key, user in others:
            row = Card(bg="panel", radius=dp(14), outline=True, size_hint_y=None, height=dp(72),
                       padding=dp(10), spacing=dp(10))
            row.add_widget(CircleImage(source=user.get("avatar", ""), letter=user.get("name", key),
                                       size_hint=(None, None), size=(dp(48), dp(48)),
                                       pos_hint={"center_y": 0.5}))
            info = BoxLayout(orientation="vertical")
            info.add_widget(LLabel(text=user.get("name", key), bold=True, font_size=sp(16), color=T("text")))
            info.add_widget(LLabel(text="@" + key, font_size=sp(13), color=T("sub")))
            row.add_widget(info)
            is_following = key in following
            btn = NeonPill(text="Following" if is_following else "Follow", active=not is_following,
                           font_size=sp(14), size_hint=(None, None), size=(dp(108), dp(42)),
                           pos_hint={"center_y": 0.5})
            btn.bind(on_release=lambda *_, k=key: (app.toggle_follow(k), self.rebuild()))
            row.add_widget(btn)
            inner.add_widget(row)
        root.add_widget(sv)
        root.add_widget(BottomNav(active="friends"))


class InboxScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def on_pre_enter(self, *args):
        self.rebuild()

    def build_ui(self):
        app = App.get_running_app()
        me = app.author_id()
        root = BoxLayout(orientation="vertical")
        paint_bg(root)
        self.add_widget(root)
        root.add_widget(plain_title("Inbox"))
        sv, inner = scroll_col(padding=dp(12))
        mine = [n for n in app.state["notifications"] if n.get("to") == me]
        if not app.state["logged_in"]:
            inner.add_widget(Wrap(text="Log in to receive notifications about likes, comments and followers.",
                                  font_size=sp(15), color=T("sub"), halign="center"))
        elif not mine:
            inner.add_widget(Wrap(text="No notifications yet.", font_size=sp(15), color=T("sub"),
                                  halign="center"))
        for n in reversed(mine):
            row = Card(bg="panel", radius=dp(14), outline=True, orientation="vertical", size_hint_y=None,
                       height=dp(70), padding=(dp(14), dp(8)))
            row.add_widget(LLabel(text=n.get("text", ""), font_size=sp(15), color=T("text")))
            row.add_widget(LLabel(text=ago(n.get("time", time.time())), font_size=sp(12), color=T("sub"),
                                  size_hint_y=None, height=dp(18)))
            inner.add_widget(row)
        if mine:
            clear = pill("Clear all", height=dp(46))
            clear.bind(on_release=lambda *_: (app.clear_notifications(), self.rebuild()))
            inner.add_widget(clear)
        root.add_widget(sv)
        app.mark_read()
        root.add_widget(BottomNav(active="inbox"))


# ----------------------------------------------------------------------------
# PROFILE (banner at the very top; it scrolls up only when you scroll the posts)
# ----------------------------------------------------------------------------
class ButtonBehaviorWidget(ButtonBehavior, Widget):
    pass


class MenuItem(ButtonBehavior, LLabel):
    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(48))
        kw.setdefault("color", T("text"))
        kw.setdefault("font_size", sp(16))
        kw.setdefault("padding_x", dp(14))
        super().__init__(**kw)


class ProfileScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.menu_layer = None
        self.show = "posts"
        self.build_ui()

    def on_pre_enter(self, *args):
        self.rebuild()

    def set_show(self, which):
        self.show = which
        self.rebuild()

    def build_ui(self):
        app = App.get_running_app()
        prof = app.profile()
        me = app.author_id()
        self.menu_layer = None

        self.layer = FloatLayout()
        self.add_widget(self.layer)
        col = BoxLayout(orientation="vertical", size_hint=(1, 1))
        paint_bg(col)
        self.layer.add_widget(col)

        sv = ScrollView(do_scroll_x=False, bar_width=dp(3), scroll_y=1)
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        content.bind(minimum_height=content.setter("height"))
        sv.add_widget(content)
        col.add_widget(sv)

        # banner sits at the very top of the content, so it only moves when the page is scrolled
        header = FloatLayout(size_hint_y=None, height=dp(210))
        banner = CoverImage(source=prof.get("banner", ""), fallback="panel", size_hint=(1, None),
                            height=dp(150), pos_hint={"x": 0, "top": 1})
        banner.bind(on_release=lambda *_: app.change_banner())
        header.add_widget(banner)
        if not banner.has_image():
            header.add_widget(Label(text="Tap to add a banner", color=T("sub"), font_size=sp(14),
                                    size_hint=(None, None), size=(dp(200), dp(30)),
                                    pos_hint={"center_x": 0.5, "top": 0.9}))

        avatar = CircleImage(source=prof.get("avatar", ""), letter=prof.get("name", "S"), ring=T("glow"),
                             size_hint=(None, None), size=(dp(104), dp(104)),
                             pos_hint={"center_x": PROFILE_PHOTO_X, "y": 0.02})
        avatar.bind(on_release=lambda *_: app.open_camera("avatar"))
        header.add_widget(avatar)
        content.add_widget(header)

        content.add_widget(Label(text=prof.get("name") or "Guest", bold=True, font_size=sp(22),
                                 color=T("text"), size_hint_y=None, height=dp(32)))
        content.add_widget(Label(text="@" + me, font_size=sp(14), color=T("sub"),
                                 size_hint_y=None, height=dp(22)))

        mine = [p for p in app.state["posts"] if p.get("author") == me]
        likes = sum(len(p.get("liked_by", [])) for p in mine)
        stats = BoxLayout(size_hint_y=None, height=dp(56))
        for number, label in ((len(app.following_of(me)), "Following"),
                              (app.followers_count(me), "Followers"), (likes, "Likes")):
            cell = BoxLayout(orientation="vertical")
            cell.add_widget(Label(text=str(number), bold=True, font_size=sp(18), color=T("text")))
            cell.add_widget(Label(text=label, font_size=sp(12), color=T("sub")))
            stats.add_widget(cell)
        content.add_widget(stats)

        content.add_widget(Wrap(text=prof.get("bio") or "No bio yet", font_size=sp(15), color=T("sub"),
                                halign="center"))

        btn_row = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(40), dp(4)))
        edit = pill("Edit profile", height=dp(44), font_size=sp(15))
        edit.bind(on_release=lambda *_: app.edit_profile_dialog())
        btn_row.add_widget(edit)
        content.add_widget(btn_row)

        switch = BoxLayout(size_hint_y=None, height=dp(40), padding=(dp(60), 0))
        for key, label in (("posts", "Posts"), ("saved", "Saved")):
            t = TabLabel(label, active=(self.show == key))
            t.bind(on_release=lambda *_, k=key: self.set_show(k))
            switch.add_widget(t)
        content.add_widget(switch)

        if self.show == "saved":
            ids = app.state["saved"].get(me, [])
            shown = [p for p in app.state["posts"] if p.get("id") in ids]
            empty_text = "Nothing saved yet"
        else:
            shown = mine
            empty_text = "No posts yet"
        if not shown:
            content.add_widget(Label(text=empty_text, color=T("sub"), font_size=sp(15),
                                     size_hint_y=None, height=dp(60)))
        else:
            grid = GridLayout(cols=3, spacing=dp(4), padding=dp(8), size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            for post in reversed(shown):
                if post.get("kind") == "video":
                    tile = VideoTile(thumb=post.get("thumb", ""), size_hint_y=None, height=dp(130))
                else:
                    tile = CoverImage(source=post.get("path", ""), size_hint_y=None, height=dp(130))
                tile.bind(on_release=lambda *_, p=post: app.view_post(p))
                grid.add_widget(tile)
            content.add_widget(grid)
        content.add_widget(Widget(size_hint_y=None, height=dp(12)))

        # pencil (left) and three dots (right) stay fixed on top of the banner
        edit_btn = Icon("pencil", color=WHITE, circle_bg=(0, 0, 0, 0.45), size_hint=(None, None),
                        size=(dp(42), dp(42)), pos_hint={"x": 0.03, "top": 0.985})
        edit_btn.bind(on_release=lambda *_: app.open_camera("avatar"))
        self.layer.add_widget(edit_btn)

        dots = Icon("dots", color=WHITE, circle_bg=(0, 0, 0, 0.45), size_hint=(None, None),
                    size=(dp(42), dp(42)), pos_hint={"right": 0.97, "top": 0.985})
        dots.bind(on_release=lambda *_: self.open_menu())
        self.layer.add_widget(dots)

    def close_menu(self):
        if self.menu_layer is None:
            return False
        self.layer.remove_widget(self.menu_layer)
        self.menu_layer = None
        return True

    def open_menu(self):
        if self.menu_layer is not None:
            self.close_menu()
            return
        app = App.get_running_app()
        layer = FloatLayout()
        catcher = ButtonBehaviorWidget()
        catcher.bind(on_release=lambda *_: self.close_menu())
        layer.add_widget(catcher)

        rows = 8
        menu = MenuCard(bg="panel", radius=dp(14), outline=True, orientation="vertical",
                        size_hint=(None, None), size=(dp(260), dp(rows * 48 + 16)), padding=dp(8),
                        pos_hint={"right": 0.97, "top": 0.93})

        def item(text, action):
            b = MenuItem(text=text)
            b.bind(on_release=lambda *_: (self.close_menu(), action()))
            menu.add_widget(b)

        item("Home", lambda: app.root_go("home"))
        item("Device permissions", app.device_permissions_dialog)

        dm = BoxLayout(size_hint_y=None, height=dp(48), padding=(dp(14), 0), spacing=dp(6))
        dm.add_widget(LLabel(text="Dark mode", color=T("text"), font_size=sp(16)))
        sw = Switch(active=_mode["dark"], size_hint=(None, 1), width=dp(83))
        sw.bind(active=lambda w, v: Clock.schedule_once(lambda dt: app.set_dark(v), 0.2))
        dm.add_widget(sw)
        menu.add_widget(dm)

        item("Privacy settings", lambda: app.go("privacy"))
        item("Help", lambda: app.go("help"))
        item("About the app", lambda: app.go("about"))
        item("Terms and Privacy Policy", lambda: app.go("legal"))
        if app.state["logged_in"]:
            item("Log out", app.log_out)
        else:
            item("Login", lambda: app.go("login"))

        layer.add_widget(menu)
        self.layer.add_widget(layer)
        self.menu_layer = layer


# ----------------------------------------------------------------------------
# APP
# ----------------------------------------------------------------------------
class SamNgApp(App):

    def save_state(self):
        self.store.save(self.state)

    def author_id(self):
        if self.state["logged_in"] and self.state["current_user"]:
            return self.state["current_user"]
        return "guest"

    def profile(self, author=None):
        author = author or self.author_id()
        users = self.state["users"]
        if author in users:
            return users[author]
        return self.state["guest_profile"]

    def display_name(self):
        return self.profile().get("name") or self.author_id()

    def authed(self):
        return self.state["logged_in"] or self.state["is_guest"]

    def find_user(self, name):
        name = name.strip().lower()
        for key in self.state["users"]:
            if key.lower() == name:
                return key
        return None

    def set_profile_flag(self, key, value):
        self.profile()[key] = bool(value)
        self.save_state()

    def following_of(self, user):
        return self.state["follows"].get(user, [])

    def followers_count(self, user):
        return sum(1 for lst in self.state["follows"].values() if user in lst)

    def toggle_follow(self, target):
        if not self.state["logged_in"]:
            self.toast("Log in to follow people")
            return
        me = self.author_id()
        lst = self.state["follows"].setdefault(me, [])
        if target in lst:
            lst.remove(target)
            self.toast("Unfollowed")
        else:
            lst.append(target)
            self.notify(target, "%s started following you" % self.display_name())
            self.toast("Following")
        self.save_state()

    def can_see(self, post):
        author = post.get("author", "")
        me = self.author_id()
        if author == me:
            return True
        if self.profile(author).get("private", False) and author not in self.following_of(me):
            return False
        return True

    def notify(self, to, text):
        users = self.state["users"]
        if to not in users or to == self.author_id():
            return
        if not users[to].get("notify", True):
            return
        self.state["notifications"].append({"to": to, "text": text, "time": time.time(), "read": False})
        self.save_state()

    def unread_count(self):
        if not self.state["logged_in"]:
            return 0
        me = self.author_id()
        return sum(1 for n in self.state["notifications"] if n.get("to") == me and not n.get("read"))

    def mark_read(self):
        me = self.author_id()
        for n in self.state["notifications"]:
            if n.get("to") == me:
                n["read"] = True
        self.save_state()

    def clear_notifications(self):
        me = self.author_id()
        self.state["notifications"] = [n for n in self.state["notifications"] if n.get("to") != me]
        self.save_state()

    def toggle_like(self, post):
        me = self.author_id()
        likers = post.setdefault("liked_by", [])
        if me in likers:
            likers.remove(me)
        else:
            likers.append(me)
            self.notify(post.get("author"), "%s liked your post" % self.display_name())
        self.save_state()

    def is_saved(self, post):
        return post.get("id") in self.state["saved"].get(self.author_id(), [])

    def toggle_save(self, post):
        lst = self.state["saved"].setdefault(self.author_id(), [])
        pid = post.get("id")
        if pid in lst:
            lst.remove(pid)
            self.toast("Removed from saved")
        else:
            lst.append(pid)
            self.toast("Saved")
        self.save_state()

    def share_post(self, post):
        text = (post.get("caption") or "Check this out") + "\nShared from " + APP_NAME
        if not ANDROID:
            self.toast("Sharing works on Android")
            return
        try:
            Intent = autoclass("android.content.Intent")
            String = autoclass("java.lang.String")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            intent = Intent()
            intent.setAction(Intent.ACTION_SEND)
            intent.putExtra(Intent.EXTRA_TEXT, cast("java.lang.CharSequence", String(text)))
            intent.setType("text/plain")
            chooser = Intent.createChooser(intent, cast("java.lang.CharSequence", String("Share via")))
            PythonActivity.mActivity.startActivity(chooser)
        except Exception as e:
            self.toast("Could not share: " + str(e)[:50])

    def comments_dialog(self, post, on_change=None):
        author = post.get("author")
        if author != self.author_id() and not self.profile(author).get("allow_comments", True):
            self.toast("Comments are turned off for this post")
            return
        mv = ModalView(size_hint=(0.94, 0.8), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.7))
        card = Card(bg="panel", radius=dp(18), outline=True, orientation="vertical", padding=dp(12), spacing=dp(8))
        card.add_widget(Label(text="Comments", bold=True, font_size=sp(20), color=T("accent"),
                              size_hint_y=None, height=dp(34)))
        sv, inner = scroll_col(spacing=dp(8), padding=dp(4))
        card.add_widget(sv)

        def fill():
            inner.clear_widgets()
            comments = post.setdefault("comments", [])
            if not comments:
                inner.add_widget(Wrap(text="No comments yet. Be the first!", font_size=sp(15),
                                      color=T("sub"), halign="center"))
            for c in comments:
                inner.add_widget(Wrap(text="[b]%s[/b]  %s" % (escape_markup(c.get("name", "")),
                                                              escape_markup(c.get("text", ""))),
                                      markup=True, font_size=sp(15), color=T("text")))
        fill()

        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        box, entry = field("Add a comment", height=dp(48))
        send = NeonPill(text="Send", active=True, font_size=sp(15), size_hint=(None, 1), width=dp(86))

        def do_send(*_):
            text = entry.text.strip()
            if not text:
                return
            name = self.display_name()
            post.setdefault("comments", []).append({"author": self.author_id(), "name": name, "text": text})
            self.notify(author, "%s commented: %s" % (name, text[:40]))
            entry.text = ""
            self.save_state()
            fill()
        send.bind(on_release=do_send)
        row.add_widget(box)
        row.add_widget(send)
        card.add_widget(row)
        close = pill("Close", height=dp(46))
        close.bind(on_release=lambda *_: mv.dismiss())
        card.add_widget(close)
        if on_change:
            mv.bind(on_dismiss=lambda *_: on_change())
        mv.add_widget(card)
        mv.open()

    # ---- build / navigation ------------------------------------------------------------
    def build(self):
        self.title = "Sam Ng"
        self.store = DataStore(self)
        self.state = self.store.load()
        _mode["dark"] = bool(self.state["settings"].get("dark_mode", True))
        Window.clearcolor = T("bg")
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass

        self.history = []
        self._pick_cb = None
        self._photo_uri = None
        self._thumbs = {}
        self.cam_purpose = "post"
        self.gallery_cb = None
        sm = ScreenManager(transition=FadeTransition(duration=0.18))
        self.sm = sm

        sm.add_widget(SplashScreen(name="splash"))
        sm.add_widget(CameraScreen(name="camera"))
        sm.add_widget(GalleryScreen(name="gallery"))
        sm.add_widget(WelcomeScreen(name="welcome"))
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(SignupScreen(name="signup"))
        sm.add_widget(TermsScreen(name="terms"))
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(FriendsScreen(name="friends"))
        sm.add_widget(InboxScreen(name="inbox"))
        sm.add_widget(ProfileScreen(name="profile"))
        sm.add_widget(PrivacyScreen(name="privacy"))
        sm.add_widget(InfoScreen("Help", lambda: [("", HELP_TEXT)], name="help"))
        sm.add_widget(InfoScreen("About the app", lambda: [(APP_NAME + "  v" + APP_VERSION, ABOUT_TEXT)], name="about"))
        sm.add_widget(InfoScreen("Terms and Privacy Policy", lambda: [("Terms and Conditions", TERMS_TEXT),
                                                                    ("Privacy Policy", PRIVACY_TEXT)], name="legal"))

        sm.current = "splash"
        Clock.schedule_once(self.finish_splash, 2.0)

        Window.bind(on_keyboard=self.on_key)
        if ANDROID:
            try:
                android_activity.bind(on_activity_result=self.on_activity_result)
            except Exception:
                pass
        return sm

    def finish_splash(self, dt):
        if self.state["terms_accepted"] and self.authed():
            self.sm.current = "home"
        else:
            self.sm.current = "welcome"

    def go(self, name):
        if self.sm.current != name:
            self.history.append(self.sm.current)
            self.sm.current = name

    def root_go(self, name):
        self.history = []
        self.sm.current = name

    def back(self):
        if _native["root"] is not None:
            native_video_close()
            return True
        prof = self.sm.get_screen("profile")
        if prof.close_menu():
            return True
        if self.history:
            self.sm.current = self.history.pop()
            return True
        if self.sm.current not in ("home", "welcome", "splash"):
            self.sm.current = "home" if (self.authed() and self.state["terms_accepted"]) else "welcome"
            return True
        self.stop()
        return True

    def on_key(self, window, key, *args):
        if key == 27:
            return self.back()
        return False

    def nav(self, name):
        if name == "create":
            self.open_camera("post")
        elif name in ("home", "profile", "friends", "inbox"):
            self.root_go(name)

    def open_camera(self, purpose="post"):
        self.cam_purpose = purpose
        self.go("camera")

    def open_gallery(self, callback):
        self.gallery_cb = callback
        self.go("gallery")

    def gallery_callback_for(self, purpose):
        """What to do with a photo / video that was just taken or picked."""
        if purpose == "avatar":
            return self.set_avatar
        return self.new_post_dialog

    def set_avatar(self, path):
        self.profile()["avatar"] = path
        self.save_state()
        self.toast("Profile photo updated")
        self.refresh_all()
        self.root_go("profile")

    def set_banner(self, path):
        self.profile()["banner"] = path
        self.save_state()
        self.toast("Banner updated")
        self.refresh_all()
        self.root_go("profile")

    def change_banner(self):
        self.open_gallery(self.set_banner)

    # ---- onboarding -----------------------------------------------------------------------
    def skip_sign_in(self):
        self.state["is_guest"] = True
        self.state["logged_in"] = False
        self.save_state()
        self.after_auth()

    def after_auth(self):
        if self.state["terms_accepted"]:
            self.root_go("home")
        else:
            self.go("terms")

    def accept_terms(self):
        self.state["terms_accepted"] = True
        self.save_state()
        self.root_go("home")

    def decline_terms(self):
        self.state["is_guest"] = False
        self.state["logged_in"] = False
        self.state["current_user"] = ""
        self.save_state()
        self.root_go("welcome")
        self.toast("You need to agree to continue")

    def log_out(self):
        self.state["logged_in"] = False
        self.state["is_guest"] = False
        self.state["current_user"] = ""
        self.save_state()
        self.root_go("welcome")
        self.toast("Logged out")

    def set_dark(self, value):
        _mode["dark"] = bool(value)
        self.state["settings"]["dark_mode"] = bool(value)
        self.save_state()
        Window.clearcolor = T("bg")
        self.refresh_all()

    def refresh_all(self):
        for screen in self.sm.screens:
            if screen.name in ("camera", "gallery"):
                continue          # keep the live camera and the loaded gallery as they are
            if hasattr(screen, "rebuild"):
                screen.rebuild()

    # ---- dialogs ------------------------------------------------------------------------------
    def device_permissions_dialog(self):
        mv = ModalView(size_hint=(0.9, None), height=dp(300), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.65))
        card = Card(bg="panel", radius=dp(18), outline=True, orientation="vertical", padding=dp(16), spacing=dp(10))
        card.add_widget(Label(text="Device permissions", bold=True, font_size=sp(20), color=T("accent"),
                              size_hint_y=None, height=dp(34)))
        card.add_widget(Wrap(text="Allow access to your camera, microphone, photos and videos so you can "
                                  "record and upload posts.", font_size=sp(15), color=T("sub")))
        card.add_widget(Widget())
        allow = pill("Allow access", primary=True, height=dp(50))
        close = pill("Not now", height=dp(46))

        def do_allow(*_):
            mv.dismiss()
            self.request_permissions()
        allow.bind(on_release=do_allow)
        close.bind(on_release=lambda *_: mv.dismiss())
        card.add_widget(allow)
        card.add_widget(close)
        mv.add_widget(card)
        mv.open()

    def request_permissions(self):
        try:
            from android.permissions import request_permissions
            request_permissions(["android.permission.CAMERA", "android.permission.RECORD_AUDIO"] + MEDIA_PERMISSIONS)
        except Exception:
            self.toast("Permissions can only be requested on Android")

    def toast(self, message):
        mv = ModalView(size_hint=(None, None), size=(dp(300), dp(56)), background="",
                       background_color=(0, 0, 0, 0), overlay_color=(0, 0, 0, 0))
        card = Card(bg="text", radius=dp(14), padding=dp(10))
        card.add_widget(Label(text=message, color=T("bg"), font_size=sp(14)))
        mv.add_widget(card)
        mv.open()
        Clock.schedule_once(lambda dt: mv.dismiss(), 1.8)

    def new_post_dialog(self, path):
        ext = os.path.splitext(path)[1].lower()
        kind = "video" if ext in VIDEO_EXTENSIONS else "image"
        thumb = self._thumbs.get(path, "")
        mv = ModalView(size_hint=(0.92, None), height=dp(500), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.7), auto_dismiss=False)
        card = Card(bg="panel", radius=dp(18), outline=True, orientation="vertical", padding=dp(14), spacing=dp(10))
        if kind == "video":
            tile = VideoTile(thumb=thumb, mode="contain", size_hint=(1, 1))
            tile.bind(on_release=lambda *_: self.play_video(path))
            card.add_widget(tile)
        else:
            card.add_widget(CoverImage(source=path, mode="contain", size_hint=(1, 1)))
        cap_card, cap = field("Write a caption")
        tag_card, tags = field("Tags, e.g. stem, travel")
        card.add_widget(cap_card)
        card.add_widget(tag_card)
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        cancel = pill("Cancel", height=dp(48))
        post = pill("Post", primary=True, height=dp(48))

        def do_post(*_):
            self.state["posts"].append({
                "id": str(int(time.time() * 1000)), "author": self.author_id(), "path": path, "kind": kind,
                "thumb": thumb, "caption": cap.text.strip() or "New post", "tags": tags.text.strip().lower(),
                "liked_by": [], "comments": [],
            })
            self.save_state()
            mv.dismiss()
            self.toast("Posted")
            self.root_go("home")
            home = self.sm.get_screen("home")
            home.tab = "foryou"
            home.page_index = 0
            home.rebuild()
        post.bind(on_release=do_post)
        cancel.bind(on_release=lambda *_: mv.dismiss())
        row.add_widget(cancel)
        row.add_widget(post)
        card.add_widget(row)
        mv.add_widget(card)
        mv.open()

    def edit_profile_dialog(self):
        prof = self.profile()
        mv = ModalView(size_hint=(0.92, None), height=dp(530), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.7), auto_dismiss=False)
        card = Card(bg="panel", radius=dp(18), outline=True, orientation="vertical", padding=dp(14), spacing=dp(10))
        card.add_widget(Label(text="Edit profile", bold=True, font_size=sp(20), color=T("accent"),
                              size_hint_y=None, height=dp(34)))
        name_card, name = field("Display name", text=prof.get("name", ""))
        bio_card, bio = field("Bio", text=prof.get("bio", ""))
        card.add_widget(name_card)
        card.add_widget(bio_card)
        photo_cam = pill("Profile photo: take with camera", height=dp(46), font_size=sp(15))
        photo_gal = pill("Profile photo: choose from gallery", height=dp(46), font_size=sp(15))
        banner = pill("Change banner", height=dp(46), font_size=sp(15))
        photo_cam.bind(on_release=lambda *_: (mv.dismiss(), self.open_camera("avatar")))
        photo_gal.bind(on_release=lambda *_: (mv.dismiss(), self.open_gallery(self.set_avatar)))
        banner.bind(on_release=lambda *_: (mv.dismiss(), self.change_banner()))
        card.add_widget(photo_cam)
        card.add_widget(photo_gal)
        card.add_widget(banner)
        card.add_widget(Widget())
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        cancel = pill("Cancel", height=dp(48))
        save = pill("Save", primary=True, height=dp(48))

        def do_save(*_):
            prof["name"] = name.text.strip() or prof.get("name", "Guest")
            prof["bio"] = bio.text.strip()
            self.save_state()
            mv.dismiss()
            self.refresh_all()
        save.bind(on_release=do_save)
        cancel.bind(on_release=lambda *_: mv.dismiss())
        row.add_widget(cancel)
        row.add_widget(save)
        card.add_widget(row)
        mv.add_widget(card)
        mv.open()

    def view_post(self, post):
        mine = post.get("author") == self.author_id()
        mv = ModalView(size_hint=(0.94, 0.82), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.75))
        card = Card(bg="panel", radius=dp(18), outline=True, orientation="vertical", padding=dp(12), spacing=dp(10))
        if post.get("kind") == "video":
            tile = VideoTile(thumb=post.get("thumb", ""), mode="contain", size_hint=(1, 1))
            tile.bind(on_release=lambda *_: self.play_video(post.get("path", "")))
            card.add_widget(tile)
        else:
            card.add_widget(CoverImage(source=post.get("path", ""), mode="contain", size_hint=(1, 1)))
        card.add_widget(Wrap(text=post.get("caption", ""), font_size=sp(15), color=T("text")))
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        second = pill("Delete" if mine else "Unsave", height=dp(48))
        close = pill("Close", primary=True, height=dp(48))

        def do_second(*_):
            if mine:
                try:
                    self.state["posts"].remove(post)
                    for f in (post.get("path", ""), post.get("thumb", "")):
                        if f and os.path.isfile(f):
                            os.remove(f)
                except Exception:
                    pass
            else:
                lst = self.state["saved"].get(self.author_id(), [])
                if post.get("id") in lst:
                    lst.remove(post["id"])
            self.save_state()
            mv.dismiss()
            self.refresh_all()
        second.bind(on_release=do_second)
        close.bind(on_release=lambda *_: mv.dismiss())
        row.add_widget(second)
        row.add_widget(close)
        card.add_widget(row)
        mv.add_widget(card)
        mv.open()

    # ---- video player ---------------
