
import os
import json
import time
import copy
import hashlib
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line, Triangle
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
from kivy.utils import get_color_from_hex

# ----------------------------------------------------------------------------
# TEXTS YOU CAN CHANGE
# ----------------------------------------------------------------------------
APP_NAME = "Sam Ng"
APP_VERSION = "1.0.2"
HOME_HEADLINE = "Sam Ng is for you."      # big line on the empty home screen

TERMS_TEXT = ""      # paste your Terms and Conditions here
PRIVACY_TEXT = ""    # paste your Privacy Policy here
HELP_TEXT = ""       # paste your Help text here
ABOUT_TEXT = ""      # paste your About text here
PLACEHOLDER = "[This text has not been added yet.]"

# ----------------------------------------------------------------------------
# ANDROID SUPPORT (safe on desktop too)
# ----------------------------------------------------------------------------
try:
    from jnius import autoclass
    from android import activity as android_activity
    ANDROID = True
except Exception:
    autoclass = None
    android_activity = None
    ANDROID = False

REQ_PICK = 9001

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".3gp", ".m4v")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
STATE_FILE = "samng_state_v2.json"

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
    """Paint a flat (optionally rounded) background behind a widget."""
    with widget.canvas.before:
        Color(*T(key))
        shape = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
    widget.bind(pos=lambda w, v: setattr(shape, "pos", v),
                size=lambda w, v: setattr(shape, "size", v))
    return shape


def paint_bg(widget):
    """Screen background: flat colour, plus a faint chain-link fence in dark mode."""
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
    """Centre-crop a texture so it fills a w x h box without stretching."""
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


# ----------------------------------------------------------------------------
# BASIC WIDGETS
# ----------------------------------------------------------------------------
class LLabel(Label):
    """Label that is left aligned and vertically centred inside its box."""

    def __init__(self, **kw):
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)
        self.bind(size=lambda w, v: setattr(w, "text_size", v))


class Wrap(Label):
    """Wrapping label that grows in height to fit its text."""

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
    """Card that swallows touches so taps inside it never reach the layer below."""

    def on_touch_down(self, touch):
        handled = super().on_touch_down(touch)
        return handled or self.collide_point(*touch.pos)


class NeonPill(ButtonBehavior, Label):
    """Dark oval button with a neon outline (matches the design)."""

    def __init__(self, active=False, fg=None, **kw):
        super().__init__(**kw)
        self.active = active
        self.bold = True
        self.color = fg if fg is not None else (T("accent") if active else T("pilltext"))
        self.bind(pos=self.draw, size=self.draw, state=self.draw, disabled=self.draw)
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
                    Color(glow[0], glow[1], glow[2], alpha * fade)
                    if ellipse:
                        Line(ellipse=(x - grow, y - grow, w + 2 * grow, h + 2 * grow), width=dp(2))
                    else:
                        Line(rounded_rectangle=(x - grow, y - grow, w + 2 * grow, h + 2 * grow, h / 2.0 + grow), width=dp(2))
                Color(glow[0], glow[1], glow[2], fade)
                width = dp(1.7)
            else:
                Color(glow[0], glow[1], glow[2], 0.45 * fade)
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
    """Vector icons drawn with canvas lines: search, dots, back, plus."""

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
        cx, cy = self.center
        s = min(self.size)
        if s <= 0:
            return
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


class TabLabel(ButtonBehavior, Label):
    def __init__(self, text, active=False, **kw):
        super().__init__(text=text, **kw)
        self.active = active
        self.bold = True
        self.font_size = sp(17)
        self.color = T("text") if active else T("sub")
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

    def draw(self, *args):
        self.canvas.after.clear()
        if not self.active or self.width <= 0:
            return
        glow = T("glow")
        cx = self.center_x
        y = self.y + dp(4)
        half = min(self.width, dp(90)) * 0.32
        with self.canvas.after:
            Color(glow[0], glow[1], glow[2], 0.28)
            Line(points=[cx - half, y, cx + half, y], width=dp(4), cap="round")
            Color(*glow)
            Line(points=[cx - half, y, cx + half, y], width=dp(1.6), cap="round")


class CoverImage(ButtonBehavior, Widget):
    """Picture that fills its box (centre-cropped). Shows a flat colour if empty."""

    def __init__(self, source="", fallback="panel", **kw):
        super().__init__(**kw)
        self.fallback = fallback
        self._tex = load_texture(source)
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def has_image(self):
        return self._tex is not None

    def redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        with self.canvas:
            if self._tex is not None:
                Color(1, 1, 1, 1)
                Rectangle(texture=cover_region(self._tex, self.width, self.height), pos=self.pos, size=self.size)
            else:
                Color(*T(self.fallback))
                Rectangle(pos=self.pos, size=self.size)


class VideoTile(ButtonBehavior, Widget):
    """Dark tile with a play triangle, used for videos."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        cx, cy = self.center
        s = min(self.size) * 0.16
        with self.canvas:
            Color(*T("panel"))
            Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 0.9)
            Triangle(points=[cx - s * 0.7, cy - s, cx - s * 0.7, cy + s, cx + s * 1.1, cy])


class CircleImage(ButtonBehavior, Widget):
    """Round profile picture with an optional neon ring."""

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
        d = min(self.size)
        if d <= 0:
            return
        cx, cy = self.center
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
    bar = BoxLayout(size_hint_y=None, height=dp(56), padding=(dp(8), dp(8)), spacing=dp(8))
    back = Icon("back", size_hint=(None, 1), width=dp(40))
    back.bind(on_release=lambda *_: on_back())
    bar.add_widget(back)
    bar.add_widget(LLabel(text=title, bold=True, font_size=sp(20), color=T("text")))
    return bar


def scroll_col(spacing=dp(10), padding=dp(14)):
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
    inner = BoxLayout(orientation="vertical", size_hint_y=None, spacing=spacing, padding=padding)
    inner.bind(minimum_height=inner.setter("height"))
    sv.add_widget(inner)
    return sv, inner


def field(hint, password=False, text="", height=dp(52)):
    """Rounded input box. Returns (card, textinput)."""
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
    "settings": {
        "dark_mode": True,
        "private_account": False,
        "allow_comments": True,
        "personalized": True,
    },
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
# BOTTOM NAV (neon pills + round profile picture)
# ----------------------------------------------------------------------------
class BottomNav(BoxLayout):
    def __init__(self, active="home", **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(76),
                         padding=(dp(12), dp(10)), spacing=dp(8), **kw)
        app = App.get_running_app()
        for key, label in (("home", "Home"), ("friends", "Friends"), ("create", "Create"), ("inbox", "Inbox")):
            p = NeonPill(text=label, active=(active == key), font_size=sp(14),
                         size_hint=(1, None), height=dp(44), pos_hint={"center_y": 0.5})
            p.bind(on_release=lambda *_, k=key: app.nav(k))
            self.add_widget(p)
        prof = app.profile()
        avatar = CircleImage(source=prof.get("avatar", ""), letter=prof.get("name", "S"),
                             ring=T("glow") if active == "profile" else [T("glow")[0], T("glow")[1], T("glow")[2], 0.6],
                             size_hint=(None, None), size=(dp(54), dp(54)), pos_hint={"center_y": 0.5})
        avatar.bind(on_release=lambda *_: app.nav("profile"))
        self.add_widget(avatar)


# ----------------------------------------------------------------------------
# SCREENS
# ----------------------------------------------------------------------------
class BootScreen(ThemedScreen):
    """Booting screen loading logo.png with a 3-second progress indicator at the bottom."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def build_ui(self):
        root = FloatLayout()
        paint_bg(root)
        self.add_widget(root)

        # Center logo image matching your uploaded design file named logo.png[span_1](start_span)[span_1](end_span)
        logo_img = CoverImage(
            source="logo.png",
            size_hint=(None, None),
            size=(dp(240), dp(240)),
            pos_hint={"center_x": 0.5, "center_y": 0.55}
        )
        root.add_widget(logo_img)

        # Bottom loading bar container
        load_container = FloatLayout(
            size_hint=(0.7, None),
            height=dp(6),
            pos_hint={"center_x": 0.5, "y": 0.15}
        )
        with load_container.canvas.before:
            Color(0.15, 0.15, 0.25, 0.5)
            self.bg_bar = RoundedRectangle(pos=load_container.pos, size=load_container.size, radius=[dp(3)])
            Color(0.0, 0.9, 0.96, 1.0)
            self.fg_bar = RoundedRectangle(pos=load_container.pos, size=(0, dp(6)), radius=[dp(3)])

        def update_bar(dt):
            current_width = self.fg_bar.size[0]
            max_width = load_container.width
            if current_width < max_width:
                self.fg_bar.size = (current_width + (max_width / 30.0), dp(6))

        load_container.bind(pos=lambda w, v: setattr(self.bg_bar, 'pos', v) or setattr(self.fg_bar, 'pos', v))
        root.add_widget(load_container)

        self.progress_event = Clock.schedule_interval(update_bar, 0.1)
        Clock.schedule_once(self.finish_boot, 3.0)

    def finish_boot(self, dt):
        if hasattr(self, 'progress_event'):
            self.progress_event.cancel()
        app = App.get_running_app()
        app.transition_from_boot()


class WelcomeScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def build_ui(self):
        app = App.get_running_app()
        root = FloatLayout()
        paint_bg(root)
        self.add_widget(root)

        col = BoxLayout(orientation="vertical", size_hint=(0.8, None), height=dp(340), spacing=dp(16),
                        pos_hint={"center_x": 0.5, "center_y": 0.5})
        col.add_widget(Label(text="SAM NG", color=T("accent"), bold=True, font_size=sp(46),
                             size_hint_y=None, height=dp(90)))
        col.add_widget(Label(text="Create. Share. Discover.", color=T("sub"), font_size=sp(16),
                             size_hint_y=None, height=dp(30)))
        col.add_widget(Widget())
        login = pill("Login", primary=True)
        login.bind(on_release=lambda *_: app.go("login"))
        skip = pill("Skip sign in")
        skip.bind(on_release=lambda *_: app.skip_sign_in())
        col.add_widget(login)
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

        col = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(300), spacing=dp(14),
                        padding=(dp(24), dp(24)))
        col.add_widget(Label(text="Log in or create an account", color=T("sub"), font_size=sp(15),
                             size_hint_y=None, height=dp(28)))
        user_card, self.username = field("Username")
        pass_card, self.password = field("Password", password=True)
        col.add_widget(user_card)
        col.add_widget(pass_card)
        go = pill("Continue", primary=True)
        go.bind(on_release=lambda *_: self.submit())
        col.add_widget(go)
        root.add_widget(col)
        root.add_widget(Widget())

    def submit(self):
        app = App.get_running_app()
        username = self.username.text.strip()
        password = self.password.text
        if len(username) < 3 or len(password) < 4:
            app.toast("Username 3+ letters, password 4+ characters")
            return
        users = app.state["users"]
        if username in users:
            if users[username].get("pw") != hash_pw(username, password):
                app.toast("Wrong password")
                return
        else:
            users[username] = {"pw": hash_pw(username, password), "name": username,
                               "bio": "", "avatar": "", "banner": ""}
        app.state["current_user"] = username
        app.state["logged_in"] = True
        app.state["is_guest"] = False
        app.save_state()
        app.after_auth()


class TermsScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.build_ui()

    def build_ui(self):
        app = App.get_running_app()
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
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
    """Simple read-only text page (Help, About, Terms and Privacy)."""

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
        root = BoxLayout(orientation="vertical")
        paint_bg(root)
        self.add_widget(root)
        root.add_widget(topbar("Privacy settings", app.back))
        sv, inner = scroll_col(padding=dp(14))
        for label, key in (("Private account", "private_account"),
                           ("Allow comments on my posts", "allow_comments"),
                           ("Personalised suggestions", "personalized")):
            row = Card(bg="panel", radius=dp(14), outline=True, size_hint_y=None, height=dp(58),
                       padding=(dp(14), 0), spacing=dp(8))
            row.add_widget(LLabel(text=label, color=T("text"), font_size=sp(16)))
            sw = Switch(active=bool(app.state["settings"].get(key)), size_hint=(None, 1), width=dp(83))
            sw.bind(active=lambda w, v, k=key: app.set_setting(k, v))
            row.add_widget(sw)
            inner.add_widget(row)
        policy = pill("Read the Privacy Policy", height=dp(50))
        policy.bind(on_release=lambda *_: app.go("legal"))
        inner.add_widget(policy)
        root.add_widget(sv)


class HomeScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.tab = "foryou"
        self.search_text = ""
        self.search_open = False
        self.build_ui()

    def on_pre_enter(self, *args):
        self.rebuild()

    def set_tab(self, key):
        self.tab = key
        self.rebuild()

    def toggle_search(self):
        self.search_open = not self.search_open
        if not self.search_open:
            self.search_text = ""
            self.rebuild()
            return
        self.rebuild()
        Clock.schedule_once(lambda dt: setattr(self.search, "focus", True), 0.15)

    def on_search(self, instance, value):
        self.search_text = value.strip().lower()
        self.fill_feed()

    def build_ui(self):
        app = App.get_running_app()
        prof = app.profile()
        root = BoxLayout(orientation="vertical")
        paint_bg(root)
        self.add_widget(root)

        # --- tabs: STEM | Following | For You   (search)  (+)
        tabs = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(10), dp(4)), spacing=dp(2))
        for key, label in (("stem", "STEM"), ("following", "Following"), ("foryou", "For You")):
            t = TabLabel(label, active=(self.tab == key))
            t.bind(on_release=lambda *_, k=key: self.set_tab(k))
            tabs.add_widget(t)
        s_btn = Icon("search", color=T("sub"), size_hint=(None, 1), width=dp(38))
        s_btn.bind(on_release=lambda *_: self.toggle_search())
        p_btn = Icon("plus", color=T("accent"), size_hint=(None, 1), width=dp(38))
        p_btn.bind(on_release=lambda *_: app.open_create_menu())
        tabs.add_widget(s_btn)
        tabs.add_widget(p_btn)
        root.add_widget(tabs)

        # --- search row (only visible after tapping the search icon)
        if self.search_open:
            row = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(12), dp(2), dp(12), dp(4)))
            card, self.search = field("Search posts, people, tags", text=self.search_text, height=dp(46))
            self.search.bind(text=self.on_search)
            row.add_widget(card)
            root.add_widget(row)

        # --- banner with round avatar on the right
        banner_box = FloatLayout(size_hint_y=None, height=dp(112))
        banner = CoverImage(source=prof.get("banner", ""), fallback="panel", size_hint=(1, 1))
        banner.bind(on_release=lambda *_: app.nav("profile"))
        banner_box.add_widget(banner)
        if not banner.has_image():
            banner_box.add_widget(Label(text="Add your banner in Profile", color=T("sub"), font_size=sp(13),
                                        size_hint=(None, None), size=(dp(220), dp(30)),
                                        pos_hint={"x": 0.04, "center_y": 0.5}))
        avatar = CircleImage(source=prof.get("avatar", ""), letter=prof.get("name", "S"), ring=T("glow"),
                             size_hint=(None, None), size=(dp(84), dp(84)),
                             pos_hint={"right": 0.97, "center_y": 0.5})
        avatar.bind(on_release=lambda *_: app.nav("profile"))
        banner_box.add_widget(avatar)
        root.add_widget(banner_box)

        root.add_widget(Label(text=(prof.get("name") or APP_NAME).upper(), color=T("accent"), bold=True,
                              font_size=sp(17), size_hint_y=None, height=dp(34)))

        # --- feed
        self.scroll, self.feed = scroll_col(spacing=dp(14), padding=(dp(12), dp(8)))
        root.add_widget(self.scroll)
        root.add_widget(BottomNav(active="home"))
        self.fill_feed()

    def visible_posts(self):
        app = App.get_running_app()
        out = []
        if self.tab == "following":
            return out
        for post in app.state["posts"]:
            tags = post.get("tags", "").lower()
            if self.tab == "stem" and "stem" not in tags:
                continue
            if self.search_text:
                hay = (post.get("caption", "") + " " + tags + " " + post.get("author", "")).lower()
                if self.search_text not in hay:
                    continue
            out.append(post)
        return list(reversed(out))

    def fill_feed(self):
        app = App.get_running_app()
        self.feed.clear_widgets()
        posts = self.visible_posts()
        if posts:
            for post in posts:
                self.feed.add_widget(self.make_post_card(post))
            return

        if self.tab == "following":
            title, sub = "Nothing here yet", "Posts from people you follow will show up here."
        elif self.tab == "stem":
            title, sub = "No STEM posts yet", "Add the tag stem when you create a post."
        elif self.search_text:
            title, sub = "No results", "Try a different search."
        else:
            title, sub = "Your feed starts here", "Tap Create to add a photo or video."

        if self.tab == "foryou" and not self.search_text:
            self.feed.add_widget(Wrap(text=HOME_HEADLINE, bold=True, font_size=sp(34), color=T("text"),
                                      halign="center", valign="middle"))
        self.feed.add_widget(Widget(size_hint_y=None, height=dp(20)))
        self.feed.add_widget(Wrap(text=title, font_size=sp(24), color=T("sub"), halign="center"))
        self.feed.add_widget(Wrap(text=sub, font_size=sp(15), color=T("sub"), halign="center"))
        self.feed.add_widget(Widget(size_hint_y=None, height=dp(12)))
        holder = BoxLayout(size_hint_y=None, height=dp(100))
        create = NeonPill(text="[size=34sp]+[/size]\nCreate a post", markup=True, active=True, fg=T("text"),
                          font_size=sp(16), size_hint=(None, None), size=(dp(210), dp(96)),
                          pos_hint={"center_x": 0.5})
        create.bind(on_release=lambda *_: app.open_create_menu())
        holder.add_widget(Widget())
        holder.add_widget(create)
        holder.add_widget(Widget())
        self.feed.add_widget(holder)

    def make_post_card(self, post):
        app = App.get_running_app()
        card = Card(bg="card", radius=dp(16), outline=True, orientation="vertical", size_hint_y=None,
                    height=dp(470), padding=dp(10), spacing=dp(8))
        author = app.profile(post.get("author"))
        head = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        head.add_widget(CircleImage(source=author.get("avatar", ""), letter=author.get("name", "S"),
                                    size_hint=(None, None), size=(dp(36), dp(36))))
        head.add_widget(LLabel(text=author.get("name", "Sam Ng"), bold=True, font_size=sp(16), color=T("text")))
        card.add_widget(head)

        media = FloatLayout()
        path = post.get("path", "")
        if post.get("kind") == "video":
            tile = VideoTile(size_hint=(1, 1))
            tile.bind(on_release=lambda *_, p=path: app.play_video(p))
            media.add_widget(tile)
        else:
            media.add_widget(CoverImage(source=path, size_hint=(1, 1)))

        actions = BoxLayout(orientation="vertical", size_hint=(None, None), size=(dp(56), dp(184)),
                            pos_hint={"right": 0.99, "center_y": 0.5}, spacing=dp(8))
        like = NeonPill(text="Like\n%d" % post.get("likes", 0), active=bool(post.get("liked")),
                        font_size=sp(11), size_hint=(None, None), size=(dp(56), dp(56)))

        def toggle_like(*_):
            post["liked"] = not post.get("liked", False)
            post["likes"] = max(0, post.get("likes", 0) + (1 if post["liked"] else -1))
            app.save_state()
            self.fill_feed()
        like.bind(on_release=toggle_like)
        comment = NeonPill(text="Chat", font_size=sp(11), size_hint=(None, None), size=(dp(56), dp(56)))
        comment.bind(on_release=lambda *_: app.toast("Comments coming soon"
                                                    if app.state["settings"].get("allow_comments", True)
                                                    else "Comments are turned off"))
        share = NeonPill(text="Share", font_size=sp(11), size_hint=(None, None), size=(dp(56), dp(56)))
        share.bind(on_release=lambda *_: app.toast("Share coming soon"))
        for b in (like, comment, share):
            actions.add_widget(b)
        media.add_widget(actions)
        card.add_widget(media)

        tags = post.get("tags", "")
        caption = post.get("caption", "")
        text = caption + (("\n#" + " #".join(t.strip() for t in tags.split(",") if t.strip())) if tags else "")
        card.add_widget(Wrap(text=text, font_size=sp(15), color=T("text")))
        return card


class ProfileScreen(ThemedScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.menu_layer = None
        self.build_ui()

    def on_pre_enter(self, *args):
        self.rebuild()

    def build_ui(self):
        app = App.get_running_app()
        prof = app.profile()
        self.menu_layer = None

        self.layer = FloatLayout()
        self.add_widget(self.layer)
        col = BoxLayout(orientation="vertical", size_hint=(1, 1))
        paint_bg(col)
        self.layer.add_widget(col)

        sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        content.bind(minimum_height=content.setter("height"))
        sv.add_widget(content)
        col.add_widget(sv)
        col.add_widget(BottomNav(active="profile"))

        # banner + round photo
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
                             pos_hint={"center_x": 0.5, "y": 0.02})
        avatar.bind(on_release=lambda *_: app.change_avatar())
        header.add_widget(avatar)
        content.add_widget(header)

        content.add_widget(Label(text=prof.get("name") or "Guest", bold=True, font_size=sp(22),
                                 color=T("text"), size_hint_y=None, height=dp(32)))
        handle = app.author_id()
        content.add_widget(Label(text="@" + handle, font_size=sp(14), color=T("sub"),
                                 size_hint_y=None, height=dp(22)))

        mine = [p for p in app.state["posts"] if p.get("author") == handle]
        likes = sum(p.get("likes", 0) for p in mine)
        stats = BoxLayout(size_hint_y=None, height=dp(56))
        for number, label in ((0, "Following"), (0, "Followers"), (likes, "Likes")):
            cell = BoxLayout(orientation="vertical")
            cell.add_widget(Label(text=str(number), bold=True, font_size=sp(18), color=T("text")))
            cell.add_widget(Label(text=label, font_size=sp(12), color=T("sub")))
            stats.add_widget(cell)
        content.add_widget(stats)

        bio = prof.get("bio") or "No bio yet"
        content.add_widget(Wrap(text=bio, font_size=sp(15), color=T("sub"), halign="center"))

        btn_row = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(40), dp(4)))
        edit = pill("Edit profile", height=dp(44), font_size=sp(15))
        edit.bind(on_release=lambda *_: app.edit_profile_dialog())
        btn_row.add_widget(edit)
        content.add_widget(btn_row)

        content.add_widget(Label(text="Posts", bold=True, font_size=sp(17), color=T("accent"),
                                 size_hint_y=None, height=dp(30)))
        if not mine:
            content.add_widget(Label(text="No posts yet", color=T("sub"), font_size=sp(15),
                                     size_hint_y=None, height=dp(60)))
        else:
            grid = GridLayout(cols=3, spacing=dp(4), padding=dp(8), size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            for post in reversed(mine):
                if post.get("kind") == "video":
                    tile = VideoTile(size_hint_y=None, height=dp(130))
                else:
                    tile = CoverImage(source=post.get("path", ""), size_hint_y=None, height=dp(130))
                tile.bind(on_release=lambda *_, p=post: app.view_post(p))
                grid.add_widget(tile)
            content.add_widget(grid)
        content.add_widget(Widget(size_hint_y=None, height=dp(12)))

        # three vertical dots (top right) -> settings menu
        dots = Icon("dots", color=(1, 1, 1, 1), circle_bg=(0, 0, 0, 0.45), size_hint=(None, None),
                    size=(dp(42), dp(42)), pos_hint={"right": 0.97, "top": 0.985})
        dots.bind(on_release=lambda *_: self.open_menu())
        self.layer.add_widget(dots)

    # --- three-dot menu -----------------------------------------------------
    def menu_is_open(self):
        return self.menu_layer is not None

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

        rows = 7
        menu = MenuCard(bg="panel", radius=dp(14), outline=True, orientation="vertical",
                        size_hint=(None, None), size=(dp(260), dp(rows * 48 + 16)), padding=dp(8),
                        pos_hint={"right": 0.97, "top": 0.93})

        def item(text, action):
            b = MenuItem(text=text)
            b.bind(on_release=lambda *_: (self.close_menu(), action()))
            menu.add_widget(b)

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


class ButtonBehaviorWidget(ButtonBehavior, Widget):
    """Invisible full-screen widget that catches taps outside the menu."""


class MenuItem(ButtonBehavior, LLabel):
    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(48))
        kw.setdefault("color", T("text"))
        kw.setdefault("font_size", sp(16))
        kw.setdefault("padding_x", dp(14))
        super().__init__(**kw)


# ----------------------------------------------------------------------------
# APP
# ----------------------------------------------------------------------------
class SamNgApp(App):
    # ---- state ------------------------------------------------------------
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

    def authed(self):
        return self.state["logged_in"] or self.state["is_guest"]

    # ---- build ------------------------------------------------------------
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
        sm = ScreenManager(transition=FadeTransition(duration=0.18))
        self.sm = sm
        
        # Register screens including BootScreen
        sm.add_widget(BootScreen(name="boot"))
        sm.add_widget(WelcomeScreen(name="welcome"))
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(TermsScreen(name="terms"))
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(ProfileScreen(name="profile"))
        sm.add_widget(PrivacyScreen(name="privacy"))
        sm.add_widget(InfoScreen("Help", lambda: [("", HELP_TEXT)], name="help"))
        sm.add_widget(InfoScreen("About the app", lambda: [(APP_NAME + "  v" + APP_VERSION, ABOUT_TEXT)], name="about"))
        sm.add_widget(InfoScreen("Terms and Privacy Policy", lambda: [("Terms and Conditions", TERMS_TEXT),
                                                                    ("Privacy Policy", PRIVACY_TEXT)], name="legal"))

        sm.current = "boot"

        Window.bind(on_keyboard=self.on_key)
        if ANDROID:
            try:
                android_activity.bind(on_activity_result=self.on_activity_result)
            except Exception:
                pass
        return sm

    def transition_from_boot(self):
        if self.state["terms_accepted"] and self.authed():
            self.root_go("home")
        else:
            self.root_go("welcome")

    # ---- navigation -------------------------------------------------------
    def go(self, name):
        if self.sm.current != name:
            self.history.append(self.sm.current)
            self.sm.current = name

    def root_go(self, name):
        self.history = []
        self.sm.current = name

    def back(self):
        prof = self.sm.get_screen("profile")
        if prof.close_menu():
            return True
        if self.history:
            self.sm.current = self.history.pop()
            return True
        if self.sm.current not in ("home", "welcome", "boot"):
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
            self.open_create_menu()
        elif name in ("home", "profile"):
            self.root_go(name)
        else:
            self.toast("%s coming soon" % name.capitalize())

    # ---- onboarding -------------------------------------------------------
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
        self.save_state()
        self.root_go("welcome")
        self.toast("You need to agree to continue")

    def log_out(self):
        self.state["logged_in"] = False
        self.state["is_guest"] = False
        self.state["current_user"] = ""
        self.save_state()
        self.root_go("welcome")

    # ---- settings ---------------------------------------------------------
    def set_setting(self, key, value):
        self.state["settings"][key] = bool(value)
        self.save_state()

    def set_dark(self, value):
        _mode["dark"] = bool(value)
        self.state["settings"]["dark_mode"] = bool(value)
        self.save_state()
        Window.clearcolor = T("bg")
        self.refresh_all()

    def refresh_all(self):
        for screen in self.sm.screens:
            if hasattr(screen, "rebuild"):
                screen.rebuild()

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
            request_permissions([
                "android.permission.CAMERA",
                "android.permission.RECORD_AUDIO",
                "android.permission.READ_MEDIA_IMAGES",
                "android.permission.READ_MEDIA_VIDEO",
                "android.permission.READ_EXTERNAL_STORAGE",
            ])
        except Exception:
            self.toast("Permissions can only be requested on Android")

    # ---- popups -----------------------------------------------------------
    def toast(self, message):
        mv = ModalView(size_hint=(None, None), size=(dp(300), dp(56)), background="",
                       background_color=(0, 0, 0, 0), overlay_color=(0, 0, 0, 0))
        card = Card(bg="text", radius=dp(14), padding=dp(10))
        card.add_widget(Label(text=message, color=T("bg"), font_size=sp(14)))
        mv.add_widget(card)
        mv.open()
        Clock.schedule_once(lambda dt: mv.dismiss(), 1.6)

    def open_create_menu(self):
        mv = ModalView(size_hint=(0.9, None), height=dp(380), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.65))
        card = Card(bg="panel", radius=dp(18), outline=True, orientation="vertical", padding=dp(16), spacing=dp(10))
        card.add_widget(Label(text="Create new post", bold=True, font_size=sp(20), color=T("accent"),
                              size_hint_y=None, height=dp(36)))
        for text, kind in (("Choose a photo", "image"), ("Choose a video", "video"), ("Record a video", "record")):
            b = pill(text, height=dp(52))
            b.bind(on_release=lambda *_, k=kind: (mv.dismiss(), self.pick_media(k, self.new_post_dialog)))
            card.add_widget(b)
        cancel = pill("Cancel", height=dp(48))
        cancel.bind(on_release=lambda *_: mv.dismiss())
        card.add_widget(cancel)
        mv.add_widget(card)
        mv.open()

    def new_post_dialog(self, path):
        ext = os.path.splitext(path)[1].lower()
        kind = "video" if ext in VIDEO_EXTENSIONS else "image"
        mv = ModalView(size_hint=(0.92, None), height=dp(480), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.7), auto_dismiss=False)
        card = Card(bg="panel", radius=dp(18), outline=True, orientation="vertical", padding=dp(14), spacing=dp(10))
        if kind == "video":
            card.add_widget(VideoTile(size_hint=(1, 1)))
        else:
            card.add_widget(CoverImage(source=path, size_hint=(1, 1)))
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
                "caption": cap.text.strip() or "New post", "tags": tags.text.strip().lower(),
                "likes": 0, "liked": False,
            })
            self.save_state()
            mv.dismiss()
            self.toast("Posted")
            self.root_go("home")
            self.sm.get_screen("home").rebuild()
        post.bind(on_release=do_post)
        cancel.bind(on_release=lambda *_: mv.dismiss())
        row.add_widget(cancel)
        row.add_widget(post)
        card.add_widget(row)
        mv.add_widget(card)
        mv.open()

    def edit_profile_dialog(self):
        prof = self.profile()
        mv = ModalView(size_hint=(0.92, None), height=dp(470), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.7), auto_dismiss=False)
        card = Card(bg="panel", radius=dp(18), outline=True, orientation="vertical", padding=dp(14), spacing=dp(10))
        card.add_widget(Label(text="Edit profile", bold=True, font_size=sp(20), color=T("accent"),
                              size_hint_y=None, height=dp(34)))
        name_card, name = field("Display name", text=prof.get("name", ""))
        bio_card, bio = field("Bio", text=prof.get("bio", ""))
        card.add_widget(name_card)
        card.add_widget(bio_card)
        photo = pill("Change profile photo", height=dp(48))
        banner = pill("Change banner", height=dp(48))
        photo.bind(on_release=lambda *_: (mv.dismiss(), self.change_avatar()))
        banner.bind(on_release=lambda *_: (mv.dismiss(), self.change_banner()))
        card.add_widget(photo)
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

    def change_avatar(self):
        def done(path):
            self.profile()["avatar"] = path
            self.save_state()
            self.refresh_all()
        self.pick_media("image", done)

    def change_banner(self):
        def done(path):
            self.profile()["banner"] = path
            self.save_state()
            self.refresh_all()
        self.pick_media("image", done)

    def view_post(self, post):
        mv = ModalView(size_hint=(0.94, 0.82), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.75))
        card = Card(bg="panel", radius=dp(18), outline=True, orientation="vertical", padding=dp(12), spacing=dp(10))
        if post.get("kind") == "video":
            tile = VideoTile(size_hint=(1, 1))
            tile.bind(on_release=lambda *_: self.play_video(post.get("path", "")))
            card.add_widget(tile)
        else:
            card.add_widget(CoverImage(source=post.get("path", ""), size_hint=(1, 1)))
        card.add_widget(Wrap(text=post.get("caption", ""), font_size=sp(15), color=T("text")))
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        delete = pill("Delete", height=dp(48))
        close = pill("Close", primary=True, height=dp(48))

        def do_delete(*_):
            try:
                self.state["posts"].remove(post)
                if os.path.isfile(post.get("path", "")):
                    os.remove(post["path"])
            except Exception:
                pass
            self.save_state()
            mv.dismiss()
            self.refresh_all()
        delete.bind(on_release=do_delete)
        close.bind(on_release=lambda *_: mv.dismiss())
        row.add_widget(delete)
        row.add_widget(close)
        card.add_widget(row)
        mv.add_widget(card)
        mv.open()

    def play_video(self, path):
        mv = ModalView(size_hint=(1, 1), background="", background_color=(0, 0, 0, 1), auto_dismiss=False)
        box = FloatLayout()
        player = None
        try:
            from kivy.uix.video import Video
            player = Video(source=path, state="play", options={"eos": "loop"})
            box.add_widget(player)
        except Exception:
            box.add_widget(Label(text="Video playback is not available", color=(1, 1, 1, 1)))
        close = NeonPill(text="Close", active=True, font_size=sp(16), size_hint=(None, None),
                         size=(dp(110), dp(46)), pos_hint={"right": 0.96, "top": 0.97})

        def do_close(*_):
            try:
                if player is not None:
                    player.state = "stop"
                    player.unload()
            except Exception:
                pass
            mv.dismiss()
        close.bind(on_release=do_close)
        box.add_widget(close)
        mv.add_widget(box)
        mv.open()

    # ---- picking media on Android ------------------------------------------
    def pick_media(self, kind, callback):
        if not ANDROID:
            self.toast("Picking media works on Android only")
            return
        try:
            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            if kind == "record":
                MediaStore = autoclass("android.provider.MediaStore")
                intent = Intent(MediaStore.ACTION_VIDEO_CAPTURE)
            else:
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType("video/*" if kind == "video" else "image/*")
                intent.addCategory(Intent.CATEGORY_OPENABLE)
            self._pick_cb = callback
            PythonActivity.mActivity.startActivityForResult(intent, REQ_PICK)
        except Exception as e:
            self.toast("Could not open picker: " + str(e)[:60])

    def on_activity_result(self, request_code, result_code, intent):
        if request_code != REQ_PICK:
            return
        callback = self._pick_cb
        self._pick_cb = None
        try:
            if result_code != -1 or intent is None or callback is None:  # -1 == RESULT_OK
                return
            uri = intent.getData()
            if uri is None:
                return

            def work():
                path = self.copy_uri(uri)
                if path:
                    Clock.schedule_once(lambda dt: callback(path), 0)
                else:
                    Clock.schedule_once(lambda dt: self.toast("Could not read that file"), 0)
            threading.Thread(target=work, daemon=True).start()
        except Exception:
            pass

    def copy_uri(self, uri):
        """Copy a content:// URI into the app's private folder and return the path."""
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            resolver = PythonActivity.mActivity.getContentResolver()
            mime = resolver.getType(uri) or ""
            ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif",
                       "video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm",
                       "video/3gpp": ".3gp", "video/x-matroska": ".mkv"}
            ext = ext_map.get(mime, ".mp4" if mime.startswith("video") else ".jpg")
            folder = os.path.join(self.user_data_dir, "media")
            os.makedirs(folder, exist_ok=True)
            dest = os.path.join(folder, "m_%d%s" % (int(time.time() * 1000), ext))

            # Method A: buffered read loop
            ok = False
            stream = resolver.openInputStream(uri)
            if stream is None:
                return None
            try:
                buf = bytearray(65536)
                first = True
                with open(dest, "wb") as out:
                    while True:
                        n = stream.read(buf)
                        if n is None or n <= 0:
                            break
                        chunk = bytes(buf[:n])
                        if first:
                            first = False
                            if not any(chunk):      # buffer never filled: method A unsupported
                                raise RuntimeError("buffer not filled")
                        out.write(chunk)
                ok = os.path.getsize(dest) > 0
            except Exception:
                ok = False
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

            # Method B: let Android copy it (API 29+)
            if not ok:
                stream = resolver.openInputStream(uri)
                FileOutputStream = autoclass("java.io.FileOutputStream")
                FileUtils = autoclass("android.os.FileUtils")
                fos = FileOutputStream(dest)
                FileUtils.copy(stream, fos)
                fos.close()
                stream.close()
                ok = os.path.getsize(dest) > 0
            return dest if ok else None
        except Exception:
            return None


if __name__ == "__main__":
    SamNgApp().run()

