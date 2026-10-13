# pik D main.py
# Production release with Boot/Welcome screen, Auth/Login screen, continuous scrolling & 7-day trash bin.
# Features:
# 1. Native Android Photo/Video Picker (ACTION_PICK_IMAGES / SAF) that pops up without exiting app.
# 2. Fixed video playback: MediaMetadataRetriever thumbnail extraction + robust local video caching (no white static blank).
# 3. Automatic horizontal vs vertical orientation detection for photos & videos.
# 4. Real icons: Heart (♥) for Like, Bookmark (🔖) for Save, Chat Bubble (💬) for Comment, and Real House (🏠), Friends (👥), Mail (✉) in Bottom Nav.
# 5. Expanded Settings: Autoplay, Colors, AMOLED Mode, 7-Day Trash Bin Manager, Search History Cleaner, Cache Cleaner, Help & Privacy.

import os
import json
import time
import shutil
import hashlib

from kivy.app import App
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.graphics import (Color, RoundedRectangle, Rectangle, Line, Ellipse,
                           StencilPush, StencilUse, StencilUnUse, StencilPop)
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.video import Video
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.switch import Switch
from kivy.uix.filechooser import FileChooserListView

try:
    from plyer import filechooser, camera, permissions
except Exception:
    filechooser = None
    camera = None
    permissions = None

try:
    from jnius import autoclass
    from jnius import cast
except Exception:
    autoclass = None
    cast = None

APP_NAME = "pik D"
BG = "#000000"
PANEL = "#141424"
WHITE = "#FFFFFF"
GREY = "#A0A0B2"
CYAN = "#00F5E9"
PINK = "#FF286F"
PURPLE = "#965CFF"
BLUE = "#3B82F6"
YELLOW = "#FFC857"
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".3gp", ".m4v")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
ALL_MEDIA = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

SEVEN_DAYS_SEC = 7 * 24 * 3600
THIRTY_DAYS_SEC = 30 * 24 * 3600


def rgba(value):
    return get_color_from_hex(value)


def unique_accent(path):
    palette = ["#00F5E9", "#FF286F", "#965CFF", "#FFC857",
               "#53F28B", "#FF7A30", "#3B82F6", "#F05BFF"]
    key = os.path.basename(path or "post").encode("utf-8", "ignore")
    number = int(hashlib.md5(key).hexdigest()[:8], 16)
    return palette[number % len(palette)]


class CleanNavButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)


class TextTabButton(Button):
    def __init__(self, is_active=False, active_color=CYAN, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.is_active = is_active
        self.active_color = active_color
        self.bold = True
        self.font_size = "14sp"
        self.color = rgba(self.active_color if self.is_active else GREY)


class RoundedInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_active = ""
        self.background_color = (0, 0, 0, 0)
        self.padding = (dp(12), dp(12))
        self.foreground_color = rgba(WHITE)
        self.hint_text_color = rgba(GREY)
        self.cursor_color = rgba(CYAN)
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*rgba(PANEL))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(15)] * 4)
            Color(*rgba("#343440"))
            Line(rounded_rectangle=(self.x, self.y, self.width,
                                    self.height, dp(15)), width=1)


class NeonButton(Button):
    def __init__(self, fill=PANEL, outline=CYAN, radius=18, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.fill_hex = fill
        self.outline_hex = outline
        self.radius_dp = radius
        self.bind(pos=self.redraw, size=self.redraw, state=self.redraw)
        self.redraw()

    def redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            fill = rgba(self.fill_hex) if self.fill_hex else (0, 0, 0, 0)
            alpha = 0.88 if self.state == "down" else 0.72
            if self.fill_hex:
                Color(fill[0], fill[1], fill[2], alpha)
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[dp(self.radius_dp)] * 4)
            if self.outline_hex:
                Color(*rgba(self.outline_hex))
                Line(rounded_rectangle=(self.x, self.y, self.width,
                                        self.height, dp(self.radius_dp)),
                     width=1.1)


class RoundedClip(FloatLayout):
    """Clip child widgets to a rounded rectangle."""
    def __init__(self, radius=18, **kwargs):
        super().__init__(**kwargs)
        self.radius_dp = radius
        with self.canvas.before:
            StencilPush()
            self._clip_shape = RoundedRectangle(pos=self.pos, size=self.size,
                                                radius=[dp(radius)] * 4)
            StencilUse()
        with self.canvas.after:
            StencilUnUse()
            StencilPop()
        self.bind(pos=self._update_clip, size=self._update_clip)

    def _update_clip(self, *_):
        self._clip_shape.pos = self.pos
        self._clip_shape.size = self.size
        self._clip_shape.radius = [dp(self.radius_dp)] * 4


class BootScreen(Screen):
    """Welcome / Splash Screen"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = FloatLayout()
        self.add_widget(root)
        with root.canvas.before:
            Color(*rgba(BG))
            rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, v: setattr(rect, "pos", v),
                  size=lambda w, v: setattr(rect, "size", v))

        if os.path.isfile("logo.png"):
            logo = Image(source="logo.png", size_hint=(None, None), size=(dp(150), dp(150)),
                         pos_hint={"center_x": .5, "center_y": .61})
            root.add_widget(logo)
        else:
            root.add_widget(Label(text="[b]pik D[/b]", markup=True, color=rgba(CYAN),
                                  font_size="46sp", size_hint=(1, .3),
                                  pos_hint={"center_x": .5, "center_y": .61}))

        root.add_widget(Label(text="YOUR WORLD. YOUR SPACE.",
                              color=rgba(PURPLE), font_size="12sp",
                              size_hint=(1, .05),
                              pos_hint={"center_x": .5, "center_y": .40}))
        self.progress = 0
        Clock.schedule_interval(self.advance, .035)

    def advance(self, dt):
        self.progress += 2
        if self.progress >= 100:
            Clock.unschedule(self.advance)
            app = App.get_running_app()
            home = self.manager.get_screen("home")
            app.is_logged_in = bool(home.is_logged_in)
            app.username = home.username
            self.manager.current = "home" if home.is_logged_in else "auth"
            return False


class AuthScreen(Screen):
    """Login / Authentication Screen"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = FloatLayout()
        with root.canvas.before:
            Color(*rgba(BG))
            rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, v: setattr(rect, "pos", v), size=lambda w, v: setattr(rect, "size", v))
        self.add_widget(root)

        box = BoxLayout(orientation="vertical", spacing=dp(14), size_hint=(0.85, None), height=dp(360),
                        pos_hint={"center_x": .5, "center_y": .5})

        box.add_widget(Label(text="Welcome to pik D", color=rgba(CYAN), font_size="22sp", bold=True, size_hint_y=None, height=dp(36)))
        box.add_widget(Label(text="Log in or create an account to start sharing.", color=rgba(GREY), font_size="13sp", size_hint_y=None, height=dp(24)))

        self.user_input = RoundedInput(hint_text="Username or Email", multiline=False, size_hint_y=None, height=dp(48))
        self.pass_input = RoundedInput(hint_text="Password", password=True, multiline=False, size_hint_y=None, height=dp(48))

        box.add_widget(self.user_input)
        box.add_widget(self.pass_input)

        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        login_btn = NeonButton(text="Log In", outline=CYAN, color=rgba(CYAN))
        signup_btn = NeonButton(text="Sign Up", outline=PURPLE, color=rgba(WHITE))

        login_btn.bind(on_release=self.handle_login)
        signup_btn.bind(on_release=self.handle_signup)

        btn_row.add_widget(login_btn)
        btn_row.add_widget(signup_btn)
        box.add_widget(btn_row)

        skip_btn = NeonButton(text="Skip for now", outline="#343440", color=rgba(GREY),
                              size_hint_y=None, height=dp(42))
        skip_btn.bind(on_release=self.skip_auth)
        box.add_widget(skip_btn)
        root.add_widget(box)

    def skip_auth(self, *_):
        app = App.get_running_app()
        home = self.manager.get_screen("home")
        home.is_logged_in = False
        app.is_logged_in = False
        if not home.username:
            home.username = "guest"
        self.manager.current = "home"
        home.show_feed()

    def _finish_auth(self, username):
        app = App.get_running_app()
        home = self.manager.get_screen("home")
        clean_username = username.strip().lstrip("@").replace(" ", "")[:30]
        if not clean_username:
            home.message("Username required", "Enter a username to continue.")
            return False
        try:
            if os.path.isfile(home.account_lock_file):
                with open(home.account_lock_file, "r", encoding="utf-8") as f:
                    locked = json.load(f).get("username", "")
                if locked and clean_username.casefold() != locked.casefold():
                    home.message("One account on this device", f"This pik D installation is locked to @{locked}. Log in with that account instead.")
                    return False
            else:
                os.makedirs(home.data_dir, exist_ok=True)
                with open(home.account_lock_file, "w", encoding="utf-8") as f:
                    json.dump({"username": clean_username}, f)
        except Exception as error:
            home.message("Account setting", "Could not save the one-account setting: " + str(error))
            return False
        home.username = clean_username
        home.is_logged_in = True
        app.username = clean_username
        app.is_logged_in = True
        home._save_data()
        self.manager.current = "home"
        return True

    def handle_login(self, *_):
        u = self.user_input.text.strip()
        p = self.pass_input.text.strip()
        if not u or not p:
            self.user_input.hint_text = "Please enter credentials!"
            return
        self._finish_auth(u)

    def handle_signup(self, *_):
        u = self.user_input.text.strip()
        p = self.pass_input.text.strip()
        if not u or not p:
            self.user_input.hint_text = "Provide username & password!"
            return
        app = App.get_running_app()
        if self._finish_auth(u):
            self.manager.get_screen("home").message("Account Created", f"Successfully registered as @{app.username}")


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        self.data_dir = app.user_data_dir
        self.state_file = os.path.join(self.data_dir, "samng_data.json")
        self.account_lock_file = os.path.join(self.data_dir, "samng_account_lock.json")
        self.ai_messages = []
        self.inbox_notifications = []
        self.friends = []
        self.posts = []
        self.drafts = []
        self.private_posts = []
        self.deleted_posts = {}
        self.post_captions = {}
        self.post_documents = {}
        self.post_thumbnails = {}
        self.post_orientation = {}  # "horizontal" or "vertical"
        self.comments = {}
        self.saved = set()
        self.liked = set()
        self.search_history = ["pik D trends", "tutorial video", "kivy design", "cyber visuals"]
        self.secret_codes = {"*#7266#": "pik D Engine v1.0", "*#0007#": "Debug Overlay Activated"}
        self.active_page = "Home"
        self.inbox_return_page = "Home"
        self.active_tab = "For You"
        self.profile_tab = "Posts"
        self.profile_name = "pik D"
        self.username = app.username or "samng"
        self.bio = "Creator"
        self.profile_picture = ""
        self.banner_picture = ""
        self.banner_opacity = .72
        self.profile_bg_picture = ""
        self.profile_bg_opacity = .50
        self.dark_mode = True
        self.autoplay = True
        self.show_post_colours = True
        self.amoled_mode = True
        self.high_quality = True
        self.display_mode = "name"
        self.last_name_change = 0
        self.last_username_change = 0
        self.is_logged_in = app.is_logged_in

        # Setup Android Activity & Native Photo Picker Callback
        self._native_picker_callback = None
        self._native_picker_request_code = 4820
        if autoclass:
            try:
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                self._android_activity = PythonActivity.mActivity
                self._android_activity.bind(on_activity_result=self._on_android_activity_result)
            except Exception:
                self._android_activity = None
        else:
            self._android_activity = None

        self._load_data()
        self.clean_expired_trash()

        self.root = BoxLayout(orientation="vertical", spacing=0,
                              padding=(dp(0), dp(28), dp(0), dp(44)))
        self.add_widget(self.root)

        # Top Bar
        self.topbar = BoxLayout(size_hint_y=None, height=dp(65),
                                padding=(dp(8), dp(12), dp(8), dp(4)), spacing=dp(4))
        self.root.add_widget(self.topbar)
        self.top_tab_buttons = {}

        for tab in ("STEM", "Following", "For You"):
            b = TextTabButton(text=tab, is_active=(tab == "For You"), active_color=CYAN)
            b.bind(on_release=lambda btn, t=tab: self.change_tab(t))
            b.color = rgba(WHITE)
            b.bold = True
            b.font_size = "16sp"
            self.topbar.add_widget(b)
            self.top_tab_buttons[tab] = b

        search_btn = CleanNavButton(text="Search", size_hint_x=None, width=dp(65),
                                    font_size="14sp", color=rgba(PURPLE), bold=True)
        search_btn.bind(on_release=self.activate_search_mode)
        self.topbar.add_widget(search_btn)

        # Search Bar Overlay
        self.search_bar_top = BoxLayout(size_hint_y=None, height=dp(0), opacity=0, disabled=True,
                                        padding=(dp(8), dp(8)), spacing=dp(6))
        search_back = CleanNavButton(text="<", size_hint_x=None, width=dp(40),
                                     font_size="22sp", color=rgba(CYAN), bold=True)
        search_back.bind(on_release=self.deactivate_search_mode)
        self.search_bar_top.add_widget(search_back)

        self.search_input_field = RoundedInput(hint_text="Search or enter secret code...", multiline=False)
        self.search_input_field.bind(text=self.on_search_text_change)
        self.search_bar_top.add_widget(self.search_input_field)

        mic_btn = CleanNavButton(text="🎤", size_hint_x=None, width=dp(40),
                                 font_size="18sp", color=rgba(WHITE))
        mic_btn.bind(on_release=self.start_voice_search)
        self.search_bar_top.add_widget(mic_btn)
        self.root.add_widget(self.search_bar_top)

        # Content area
        self.content = BoxLayout(orientation="vertical", spacing=0)
        self.root.add_widget(self.content)

        # Bottom Navigation Bar with REAL ICONS (House, People, Plus, Mail, Avatar)
        self.nav_wrapper = BoxLayout(size_hint_y=None, height=dp(82),
                                     padding=(dp(0), dp(2), dp(0), dp(2)))
        self.nav = BoxLayout(size_hint=(1, 1), padding=(dp(4), dp(2)), spacing=dp(0))
        self.nav_wrapper.add_widget(self.nav)
        self.root.add_widget(self.nav_wrapper)
        self.nav_buttons = {}

        nav_items = [
            ("Home", "🏠\nHome"),
            ("Friends", "👥\nFriends"),
            ("Create", "+"),
            ("Inbox", "✉\nInbox"),
            ("Profile", "avatar")
        ]

        for name, label in nav_items:
            if name == "Profile":
                b = CleanNavButton(size_hint_x=1)
                self.update_nav_avatar(b)
            else:
                is_create = (name == "Create")
                b = CleanNavButton(text=label, font_size="12sp" if not is_create else "28sp",
                                   color=rgba(WHITE), bold=True, size_hint_x=1)
            b.bind(on_release=lambda btn, n=name: self.navigate(n))
            self.nav.add_widget(b)
            self.nav_buttons[name] = b

        self.show_feed()

    def update_nav_avatar(self, button):
        button.clear_widgets()
        avatar_box = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, 1))
        with button.canvas.before:
            Color(*rgba(PURPLE))
            avatar_ring = Ellipse(pos=(0, 0), size=(dp(36), dp(36)))
        button.bind(pos=lambda w, v: setattr(avatar_ring, "pos",
                                             (w.x + (w.width - dp(36)) / 2,
                                              w.y + (w.height - dp(36)) / 2)))
        button.bind(size=lambda w, v: setattr(avatar_ring, "pos",
                                              (w.x + (w.width - dp(36)) / 2,
                                               w.y + (w.height - dp(36)) / 2)))
        circle = self._round_avatar(self.profile_picture, self.profile_name[:1].upper() or "P", 30, CYAN)
        avatar_box.add_widget(circle)
        button.add_widget(avatar_box)

    def _load_data(self):
        try:
            if os.path.isfile(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.posts = [p for p in data.get("posts", []) if os.path.isfile(p) or p.startswith("document:")]
                self.drafts = [p for p in data.get("drafts", []) if os.path.isfile(p)]
                self.private_posts = [p for p in data.get("private_posts", []) if os.path.isfile(p)]
                self.deleted_posts = data.get("deleted_posts", {})
                self.comments = data.get("comments", {})
                self.post_captions = data.get("post_captions", {})
                self.post_documents = data.get("post_documents", {})
                self.post_thumbnails = data.get("post_thumbnails", {})
                self.post_orientation = data.get("post_orientation", {})
                self.saved = set(data.get("saved", []))
                self.liked = set(data.get("liked", []))
                self.search_history = data.get("search_history", self.search_history)
                self.profile_name = data.get("profile_name", self.profile_name)
                self.username = data.get("username", self.username)
                self.bio = data.get("bio", self.bio)
                self.profile_picture = data.get("profile_picture", "")
                self.banner_picture = data.get("banner_picture", "")
                self.banner_opacity = float(data.get("banner_opacity", .72))
                self.profile_bg_picture = data.get("profile_bg_picture", "")
                self.profile_bg_opacity = float(data.get("profile_bg_opacity", .50))
                self.dark_mode = bool(data.get("dark_mode", True))
                self.autoplay = bool(data.get("autoplay", True))
                self.show_post_colours = bool(data.get("show_post_colours", True))
                self.amoled_mode = bool(data.get("amoled_mode", True))
                self.high_quality = bool(data.get("high_quality", True))
                self.display_mode = data.get("display_mode", "name")
                self.last_name_change = data.get("last_name_change", 0)
                self.last_username_change = data.get("last_username_change", 0)
                self.is_logged_in = bool(data.get("is_logged_in", False))
                self.ai_messages = data.get("ai_messages", [])
                self.inbox_notifications = data.get("inbox_notifications", [])
                self.friends = data.get("friends", [])
        except Exception:
            pass

    def _save_data(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            data = {
                "posts": self.posts, "drafts": self.drafts, "private_posts": self.private_posts,
                "deleted_posts": self.deleted_posts, "comments": self.comments,
                "post_captions": self.post_captions, "post_documents": self.post_documents,
                "post_thumbnails": self.post_thumbnails, "post_orientation": self.post_orientation,
                "saved": list(self.saved), "liked": list(self.liked), "search_history": self.search_history,
                "profile_name": self.profile_name, "username": self.username,
                "bio": self.bio, "profile_picture": self.profile_picture,
                "banner_picture": self.banner_picture, "banner_opacity": self.banner_opacity,
                "profile_bg_picture": self.profile_bg_picture, "profile_bg_opacity": self.profile_bg_opacity,
                "dark_mode": self.dark_mode, "autoplay": self.autoplay,
                "show_post_colours": self.show_post_colours, "amoled_mode": self.amoled_mode,
                "high_quality": self.high_quality, "display_mode": self.display_mode,
                "last_name_change": self.last_name_change, "last_username_change": self.last_username_change,
                "is_logged_in": self.is_logged_in, "ai_messages": self.ai_messages,
                "inbox_notifications": self.inbox_notifications, "friends": self.friends,
            }
            temp_file = self.state_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, self.state_file)
        except Exception:
            pass

    def clean_expired_trash(self):
        now = time.time()
        to_remove = []
        for path, ts in list(self.deleted_posts.items()):
            if now - ts >= SEVEN_DAYS_SEC:
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                to_remove.append(path)
        for path in to_remove:
            del self.deleted_posts[path]
        if to_remove:
            self._save_data()

    def delete_post(self, path):
        if path in self.posts:
            self.posts.remove(path)
        self.deleted_posts[path] = time.time()
        self._save_data()
        self.message("Post Removed", "Moved to Trash Bin. It will be permanently deleted after 7 days.")
        self.show_feed()

    def clear_content(self):
        self.content.clear_widgets()

    def page_title(self, title, accent=CYAN, back_to="Home"):
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8), padding=(dp(4), dp(2)))
        back = CleanNavButton(text="< Back", size_hint_x=None, width=dp(60),
                              font_size="14sp", color=rgba(accent), bold=True)
        back.bind(on_release=lambda *_: self.navigate(back_to))
        row.add_widget(back)
        row.add_widget(Label(text=title, color=rgba(accent), font_size="19sp", bold=True, halign="left"))
        self.content.add_widget(row)

    def activate_search_mode(self, *_):
        self.topbar.height = 0
        self.topbar.opacity = 0
        self.topbar.disabled = True
        self.nav_wrapper.height = 0
        self.nav_wrapper.opacity = 0
        self.nav_wrapper.disabled = True
        self.search_bar_top.height = dp(58)
        self.search_bar_top.opacity = 1
        self.search_bar_top.disabled = False
        self.show_search_suggestions()

    def deactivate_search_mode(self, *_):
        self.search_bar_top.height = 0
        self.search_bar_top.opacity = 0
        self.search_bar_top.disabled = True
        self.topbar.height = dp(65)
        self.topbar.opacity = 1
        self.topbar.disabled = False
        self.nav_wrapper.height = dp(82)
        self.nav_wrapper.opacity = 1
        self.nav_wrapper.disabled = False
        self.show_feed()

    def start_voice_search(self, *_):
        if self._android_activity is None or autoclass is None:
            self.message("Voice Search", "Voice search requires Android speech recognition.")
            return
        try:
            Intent = autoclass("android.content.Intent")
            RecognizerIntent = autoclass("android.speech.RecognizerIntent")
            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak your search")
            self._android_activity.startActivityForResult(intent, self._native_picker_request_code + 2)
        except Exception:
            self.message("Voice Search", "Microphone speech service unavailable.")

    def on_search_text_change(self, instance, value):
        if value in self.secret_codes:
            self.message("Secret Code Activated", self.secret_codes[value])
            return
        self.show_search_suggestions(value)

    def show_search_suggestions(self, query=""):
        self.clear_content()
        sc = ScrollView(do_scroll_x=False)
        stack = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(12))
        stack.bind(minimum_height=stack.setter("height"))
        stack.add_widget(Label(text="[b]Search History & Suggestions[/b]", markup=True, color=rgba(CYAN), size_hint_y=None, height=dp(30), halign="left"))
        filtered = [s for s in self.search_history if not query or query.lower() in s.lower()]
        if not filtered:
            filtered = ["pik D community", "trending videos", "creator tips"]
        for item in filtered:
            b = NeonButton(text=item, size_hint_y=None, height=dp(42), outline="#343440", color=rgba(WHITE), radius=12)
            b.bind(on_release=lambda _, q=item: self.execute_search(q))
            stack.add_widget(b)
        sc.add_widget(stack)
        self.content.add_widget(sc)

    def execute_search(self, query):
        if query not in self.search_history:
            self.search_history.insert(0, query)
            self._save_data()
        self.deactivate_search_mode()
        self.message("Search Result", f"Showing cached results for: {query}")

    def show_feed(self):
        self.active_page = "Home"
        self.clear_content()
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        stack = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(20), padding=(dp(0), dp(4)))
        stack.bind(minimum_height=stack.setter("height"))
        if not self.posts:
            empty = FloatLayout(size_hint_y=None, height=Window.height - dp(130))
            empty.add_widget(Label(text="Your feed starts here\n\nTap + Create to add a photo or video.",
                                   color=rgba(GREY), halign="center",
                                   pos_hint={"center_x": .5, "center_y": .57}))
            create = NeonButton(text="+ Create a post", size_hint=(.75, None),
                                height=dp(48), outline=CYAN, color=rgba(CYAN),
                                pos_hint={"center_x": .5, "y": .28})
            create.bind(on_release=lambda *_: self.pick_media())
            empty.add_widget(create)
            stack.add_widget(empty)
        else:
            for path in reversed(self.posts):
                if path.startswith("document:") or os.path.isfile(path):
                    stack.add_widget(self.make_post_card(path))
        scroll.add_widget(stack)
        self.content.add_widget(scroll)

    def make_post_card(self, path):
        accent = unique_accent(path) if self.show_post_colours else CYAN
        card = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        card.bind(minimum_height=card.setter("height"))

        # Header
        header_box = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(12), dp(2)), spacing=dp(8))
        avatar = FloatLayout(size_hint_x=None, width=dp(36))
        if self.profile_picture and os.path.isfile(self.profile_picture):
            avatar.add_widget(Image(source=self.profile_picture, allow_stretch=True, keep_ratio=False,
                                    size_hint=(None, None), size=(dp(34), dp(34)),
                                    pos_hint={"center_x": .5, "center_y": .5}))
        else:
            avatar.add_widget(self._round_avatar("", self.profile_name[:1].upper() or "P", 34, accent))
        header_box.add_widget(avatar)

        header_label = self.profile_name if self.display_mode == "name" else f"@{self.username}"
        title_box = BoxLayout(orientation="vertical", spacing=0)
        title_box.add_widget(Label(text=header_label, color=rgba(WHITE),
                                   bold=True, font_size="15sp", halign="left", valign="middle"))
        header_box.add_widget(title_box)

        menu = CleanNavButton(text="...", size_hint_x=None, width=dp(30),
                              font_size="18sp", color=rgba(WHITE), bold=True)
        menu.bind(on_release=lambda *_: self.post_options(path))
        header_box.add_widget(menu)
        card.add_widget(header_box)

        # Media Container with Horizontal vs Vertical dynamic sizing
        media_holder = FloatLayout(size_hint_y=None)
        orientation = self.post_orientation.get(path, "vertical")

        if path.startswith("document:"):
            media_holder.height = dp(160)
            doc_name = self.post_documents.get(path, "Attached Document")
            media_holder.add_widget(Label(text=f"📄 [b]{doc_name}[/b]", markup=True, color=rgba(CYAN), halign="center", pos_hint={"center_x": .5, "center_y": .5}))
        else:
            ext = os.path.splitext(path)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                # Video handling with robust preview frame to prevent white static blank
                if orientation == "horizontal":
                    media_holder.height = dp(240)
                else:
                    media_holder.height = dp(380)

                thumb = self.post_thumbnails.get(path, "")
                if thumb and os.path.isfile(thumb):
                    img = Image(source=thumb, allow_stretch=True, keep_ratio=True,
                                size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
                    media_holder.add_widget(img)

                try:
                    video = Video(source=path, state="play" if self.autoplay else "pause",
                                  options={"eos": "loop"}, allow_stretch=True, keep_ratio=True,
                                  size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
                    media_holder.add_widget(video)
                except Exception:
                    pass

                # Play/Pause badge overlay
                play_badge = NeonButton(text="▶", fill=BG, outline=CYAN, radius=16,
                                        size_hint=(None, None), size=(dp(44), dp(44)),
                                        pos_hint={"center_x": .5, "center_y": .5})
                def toggle_vid(*_):
                    try:
                        if hasattr(video, "state"):
                            video.state = "pause" if video.state == "play" else "play"
                    except Exception:
                        pass
                play_badge.bind(on_release=toggle_vid)
                media_holder.add_widget(play_badge)

            else:
                # Photo handling with horizontal vs vertical detection
                if orientation == "horizontal":
                    media_holder.height = dp(230)
                else:
                    media_holder.height = dp(360)

                img = Image(source=path, allow_stretch=True, keep_ratio=True,
                            size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
                media_holder.add_widget(img)

        # Right Action Rail with REAL ICONS: Heart (♥), Chat Bubble (💬), Share (↗), Bookmark (🔖)
        rail = BoxLayout(orientation="vertical", size_hint=(None, 0.52), width=dp(56),
                         spacing=dp(6), pos_hint={"right": 0.98, "y": 0.04})
        liked_now = path in self.liked
        saved_now = path in self.saved
        like_count = (1 if liked_now else 0)

        # Heart Icon for Like
        rail_like = NeonButton(text=f"♥\n{like_count}", font_size="14sp",
                               fill=PANEL, outline=PINK if liked_now else "#343440",
                               color=rgba(PINK if liked_now else WHITE), radius=12)

        # Messaging Bubble for Comment
        rail_comment = NeonButton(text=f"💬\n{len(self.comments.get(path, []))}", font_size="12sp",
                                  fill=PANEL, outline=accent, color=rgba(WHITE), radius=12)

        # Share Icon
        rail_share = NeonButton(text="↗\nShare", font_size="10sp",
                                fill=PANEL, outline=accent, color=rgba(accent), radius=12)

        # Bookmark Icon for Save
        rail_save = NeonButton(text="🔖\nSaved" if saved_now else "🔖\nSave", font_size="10sp",
                                fill=PANEL, outline=PURPLE if saved_now else "#343440",
                                color=rgba(PURPLE if saved_now else WHITE), radius=12)

        rail_like.bind(on_release=lambda *_: self.protected_action(lambda: self.toggle_like(path)))
        rail_comment.bind(on_release=lambda *_: self.protected_action(lambda: self.comment_dialog(path)))
        rail_share.bind(on_release=lambda *_: self.share_options(path))
        rail_save.bind(on_release=lambda *_: self.toggle_save(path))

        for action_button in (rail_like, rail_comment, rail_share, rail_save):
            rail.add_widget(action_button)
        media_holder.add_widget(rail)
        card.add_widget(media_holder)

        # Caption
        caption_text = self.post_captions.get(path, "")
        if caption_text:
            words = caption_text.split()
            desc_container = BoxLayout(orientation="vertical", size_hint_y=None,
                                       padding=(dp(12), dp(2)), spacing=dp(2))
            desc_container.bind(minimum_height=desc_container.setter("height"))
            if len(words) > 6:
                short_text = " ".join(words[:6]) + "..."
                lbl = Label(text=short_text, color=rgba(WHITE), font_size="13sp",
                            size_hint_y=None, height=dp(22), halign="left", valign="middle")
                more_btn = Button(text="more", color=rgba(CYAN), size_hint=(None, None),
                                  size=(dp(50), dp(20)), font_size="12sp", bold=True,
                                  background_normal="", background_color=(0, 0, 0, 0))
                def expand_desc(instance, full=caption_text, container=desc_container):
                    container.clear_widgets()
                    full_lbl = Label(text=full, color=rgba(WHITE), font_size="13sp",
                                     size_hint_y=None, height=dp(max(24, 20 * (full.count("\n") + 1))),
                                     halign="left", valign="middle")
                    container.add_widget(full_lbl)
                more_btn.bind(on_release=expand_desc)
                desc_row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(4))
                desc_row.add_widget(lbl)
                desc_row.add_widget(more_btn)
                desc_container.add_widget(desc_row)
            else:
                desc_container.add_widget(Label(text=caption_text, color=rgba(WHITE), font_size="13sp",
                                                size_hint_y=None, height=dp(22), halign="left", valign="middle"))
            card.add_widget(desc_container)

        return card

    def post_options(self, path):
        popup = Popup(title="Post Options", size_hint=(.88, None), height=dp(220))
        layout = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        del_btn = NeonButton(text="Delete Post (7-Day Trash)", outline=PINK, color=rgba(PINK))
        share_btn = NeonButton(text="Share File", outline=CYAN, color=rgba(CYAN))
        close_btn = NeonButton(text="Cancel", outline="#343440", color=rgba(WHITE))
        del_btn.bind(on_release=lambda *_: (popup.dismiss(), self.delete_post(path)))
        share_btn.bind(on_release=lambda *_: (popup.dismiss(), self.share_options(path)))
        close_btn.bind(on_release=popup.dismiss)
        layout.add_widget(del_btn)
        layout.add_widget(share_btn)
        layout.add_widget(close_btn)
        popup.content = layout
        popup.open()

    def protected_action(self, action):
        if self.is_logged_in:
            action()
        else:
            self.manager.current = "auth"

    def navigate(self, name):
        previous_page = self.active_page
        if name == "Inbox" and previous_page != "Inbox":
            self.inbox_return_page = previous_page or "Home"
        self.active_page = name

        hide_navigation = name in ("Inbox", "Friends", "Create", "Profile")
        self.topbar.height = 0 if hide_navigation else dp(65)
        self.topbar.opacity = 0 if hide_navigation else 1
        self.topbar.disabled = hide_navigation

        if hide_navigation:
            self.nav_wrapper.height = 0
            self.nav_wrapper.opacity = 0
            self.nav_wrapper.disabled = True
        else:
            self.nav_wrapper.height = dp(82)
            self.nav_wrapper.opacity = 1
            self.nav_wrapper.disabled = False

        for key, button in self.nav_buttons.items():
            if key == "Profile":
                continue
            button.color = rgba(WHITE if key == name else GREY)

        if name == "Home":
            self.show_feed()
        elif name == "Create":
            self.pick_media()
        elif name == "Profile":
            self.show_profile()
        elif name == "Friends":
            self.show_friends()
        elif name == "Inbox":
            self.show_inbox()

    def show_friends(self):
        self.active_page = "Friends"
        self.clear_content()
        self.page_title("FRIENDS", PURPLE, back_to="Home")
        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(10))
        body.bind(minimum_height=body.setter("height"))
        body.add_widget(self._ai_profile_row())
        body.add_widget(Label(text="FRIENDS · People you follow who follow you back", color=rgba(GREY),
                              font_size="12sp", size_hint_y=None, height=dp(34), halign="left", valign="middle"))
        if not self.friends:
            body.add_widget(Label(text="No mutual friends yet.", color=rgba(GREY),
                                  size_hint_y=None, height=dp(54), halign="center", valign="middle"))
        scroll.add_widget(body)
        self.content.add_widget(scroll)

    def _round_avatar(self, path="", letter="P", size=54, accent=CYAN):
        avatar = Widget(size_hint=(None, None), size=(dp(size), dp(size)))
        try:
            if path and os.path.isfile(path):
                texture = CoreImage(path).texture
                with avatar.canvas:
                    Color(1, 1, 1, 1)
                    shape = Ellipse(pos=avatar.pos, size=avatar.size, texture=texture)
            else:
                with avatar.canvas:
                    Color(*rgba(PANEL))
                    shape = Ellipse(pos=avatar.pos, size=avatar.size)
                avatar.add_widget(Label(text=letter or "P", color=rgba(accent), bold=True,
                                        font_size=f"{int(size * .42)}sp",
                                        pos_hint={"center_x": .5, "center_y": .5}))
            avatar.bind(pos=lambda w, v: setattr(shape, "pos", v),
                        size=lambda w, v: setattr(shape, "size", v))
        except Exception:
            pass
        return avatar

    def _ai_profile_row(self):
        row = BoxLayout(size_hint_y=None, height=dp(82), spacing=dp(12), padding=(dp(8), dp(8)))
        avatar = self._round_avatar("", "Q", 58, PURPLE)
        details = BoxLayout(orientation="vertical", spacing=dp(2))
        details.add_widget(Label(text="QYRONEX AI", color=rgba(WHITE), bold=True, font_size="16sp", halign="left", valign="middle"))
        details.add_widget(Label(text="AI assistant · Tap to chat", color=rgba(CYAN), font_size="12sp", halign="left", valign="middle"))
        open_btn = NeonButton(text="Chat", size_hint=(None, None), size=(dp(72), dp(40)), outline=PURPLE, color=rgba(WHITE))
        open_btn.bind(on_release=lambda *_: self.open_ai_chat())
        row.add_widget(avatar); row.add_widget(details); row.add_widget(open_btn)
        return row

    def show_inbox(self):
        self.active_page = "Inbox"
        self.clear_content()
        self.page_title("INBOX", PINK, back_to=self.inbox_return_page)
        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(10))
        body.bind(minimum_height=body.setter("height"))
        body.add_widget(self._ai_profile_row())
        for item in reversed(self.inbox_notifications):
            if isinstance(item, dict):
                row = BoxLayout(size_hint_y=None, height=dp(66), spacing=dp(10), padding=(dp(8), dp(5)))
                details = BoxLayout(orientation="vertical", spacing=dp(2))
                details.add_widget(Label(text=item.get("title", "Notice"), color=rgba(WHITE), bold=True, halign="left"))
                details.add_widget(Label(text=item.get("detail", ""), color=rgba(GREY), font_size="12sp", halign="left"))
                row.add_widget(details)
                body.add_widget(row)
        if not self.inbox_notifications:
            body.add_widget(Label(text="No activity yet. Likes, messages and alerts appear here.",
                                  color=rgba(GREY), size_hint_y=None, height=dp(76), halign="center"))
        scroll.add_widget(body)
        self.content.add_widget(scroll)

    def open_ai_chat(self, *_):
        self.active_page = "AI Chat"
        self.clear_content()
        chat_root = BoxLayout(orientation="vertical", spacing=dp(6), padding=(dp(8), dp(4), dp(8), dp(6)))
        header = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        back = CleanNavButton(text="< Back", size_hint_x=None, width=dp(68), color=rgba(CYAN), bold=True)
        back.bind(on_release=lambda *_: self.navigate("Inbox"))
        header.add_widget(back)
        header.add_widget(self._round_avatar("", "Q", 40, PURPLE))
        names = BoxLayout(orientation="vertical", spacing=0)
        names.add_widget(Label(text="QYRONEX AI", color=rgba(WHITE), bold=True, halign="left", valign="middle"))
        names.add_widget(Label(text="AI assistant", color=rgba(CYAN), font_size="11sp", halign="left", valign="middle"))
        header.add_widget(names)
        chat_root.add_widget(header)

        history_scroll = ScrollView(do_scroll_x=False)
        history = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=(dp(4), dp(8)))
        history.bind(minimum_height=history.setter("height"))

        def add_bubble(sender, message):
            bubble = BoxLayout(orientation="vertical", size_hint=(.92, None), padding=dp(10), spacing=dp(2))
            bubble.bind(minimum_height=bubble.setter("height"))
            with bubble.canvas.before:
                Color(*rgba(PANEL if sender == "QYRONEX AI" else "#173B43"))
                bg = RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[dp(15)] * 4)
            bubble.bind(pos=lambda w, v: setattr(bg, "pos", v), size=lambda w, v: setattr(bg, "size", v))
            bubble.add_widget(Label(text=f"[b]{sender}[/b]", markup=True, color=rgba(CYAN if sender == "QYRONEX AI" else WHITE), size_hint_y=None, height=dp(20), halign="left"))
            text_label = Label(text=message, color=rgba(WHITE), halign="left", valign="top", size_hint_y=None)
            text_label.bind(width=lambda w, v: setattr(w, "text_size", (max(1, v), None)), texture_size=lambda w, v: setattr(w, "height", v[1] + dp(4)))
            bubble.add_widget(text_label)
            align = AnchorLayout(anchor_x="left" if sender == "QYRONEX AI" else "right", size_hint_y=None)
            align.add_widget(bubble)
            bubble.bind(height=lambda w, v: setattr(align, "height", v))
            history.add_widget(align)

        if not self.ai_messages:
            self.ai_messages.append({"sender": "QYRONEX AI", "text": "Hi! I'm QYRONEX AI. Your personal creative & coding co-pilot in pik D."})
            self._save_data()

        for item in self.ai_messages[-100:]:
            add_bubble(item.get("sender", "QYRONEX AI"), item.get("text", ""))

        history_scroll.add_widget(history)
        chat_root.add_widget(history_scroll)

        composer = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(6), padding=(0, dp(2)))
        entry = RoundedInput(hint_text="Message QYRONEX AI…", multiline=False, size_hint_x=1)
        send = NeonButton(text="➤", size_hint_x=None, width=dp(54), outline=CYAN, color=rgba(CYAN), radius=16)
        composer.add_widget(entry); composer.add_widget(send)
        chat_root.add_widget(composer)
        self.content.add_widget(chat_root)

        def send_message(*_):
            value = entry.text.strip()
            if not value:
                return
            reply = self._local_ai_reply(value)
            self.ai_messages.append({"sender": self.username or "You", "text": value})
            self.ai_messages.append({"sender": "QYRONEX AI", "text": reply})
            self.ai_messages = self.ai_messages[-200:]
            self._save_data()
            add_bubble(self.username or "You", value)
            add_bubble("QYRONEX AI", reply)
            entry.text = ""
            Clock.schedule_once(lambda dt: setattr(history_scroll, "scroll_y", 0), .08)

        send.bind(on_release=send_message)
        entry.bind(on_text_validate=send_message)

    def _local_ai_reply(self, message):
        text = message.lower()
        if any(w in text for w in ("hello", "hi", "hey", "habari")):
            return "Hello! 👋 I'm QYRONEX AI. Tell me what you'd like to work on."
        if any(w in text for w in ("code", "python", "kivy", "android")):
            return "I can help troubleshoot code! pik D is now updated with the latest in-app photo picker, horizontal/vertical media rendering, and smooth video playback."
        if any(w in text for w in ("video", "blank", "static", "picker")):
            return "Videos are now saved directly to app storage and frame thumbnails are generated to ensure zero white blank screens!"
        return "I received your message. I am ready to help you create, explore STEM posts, or customize pik D."

    def change_tab(self, tab):
        self.active_tab = tab
        for t_name, btn in self.top_tab_buttons.items():
            btn.is_active = (t_name == tab)
            btn.color = rgba(WHITE)
            btn.bold = True
            btn.font_size = "16sp"
        if tab == "For You":
            self.show_feed()
        elif tab == "Following":
            self.simple_page("FOLLOWING", "Posts from creators you follow.", PURPLE)
        else:
            self.simple_page("STEM", "Science • Technology • Engineering • Mathematics", CYAN)

    def simple_page(self, title, message, accent, back_to="Home"):
        self.clear_content()
        self.page_title(title, accent, back_to=back_to)
        self.content.add_widget(Label(text=message, color=rgba(GREY), halign="center", valign="top"))

    # =========================================================================
    # LATEST ANDROID IN-APP POPUP PICKER + HORIZONTAL/VERTICAL + VIDEO FIX
    # =========================================================================
    def pick_media(self, *_):
        """Show bottom sheet for media uploads."""
        sheet = ModalView(size_hint=(1, None), height=dp(244),
                          pos_hint={"x": 0, "y": 0},
                          background="", background_color=(0, 0, 0, 0),
                          overlay_color=(0, 0, 0, .58), auto_dismiss=True)
        panel = BoxLayout(orientation="vertical", spacing=dp(8), padding=(dp(14), dp(14), dp(14), dp(12)))
        with panel.canvas.before:
            Color(*rgba(PANEL))
            panel._sheet_bg = RoundedRectangle(pos=panel.pos, size=panel.size, radius=[dp(22), dp(22), 0, 0])
        panel.bind(pos=lambda w, v: setattr(w._sheet_bg, "pos", v), size=lambda w, v: setattr(w._sheet_bg, "size", v))

        heading = Label(text="Add to pik D", color=rgba(WHITE), bold=True,
                        font_size="17sp", size_hint_y=None, height=dp(28), halign="left")
        panel.add_widget(heading)

        for label, kind in (("Add Photos", "photo"), ("Add Video", "video"), ("Add Document", "document")):
            b = NeonButton(text=label, size_hint_y=None, height=dp(46),
                           outline=CYAN if kind == "photo" else (PURPLE if kind == "video" else PINK),
                           color=rgba(WHITE), radius=14)
            b.bind(on_release=lambda _btn, k=kind: (sheet.dismiss(), self.open_in_app_picker(k)))
            panel.add_widget(b)
        sheet.add_widget(panel)
        sheet.open()

    def open_in_app_picker(self, kind="photo", callback=None):
        """
        Launches Android's latest Photo Picker (ACTION_PICK_IMAGES) or SAF
        which pops up directly over the app without exiting it!
        """
        self._native_picker_callback = callback or (lambda sel: self.file_selected(sel, kind))

        if self._android_activity and autoclass:
            try:
                Intent = autoclass("android.content.Intent")
                if kind == "document":
                    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                    intent.addCategory(Intent.CATEGORY_OPENABLE)
                    intent.setType("*/*")
                elif kind == "video":
                    # Android 13+ Photo Picker for Video (pops up bottom sheet in-app)
                    intent = Intent("android.provider.action.PICK_IMAGES")
                    intent.setType("video/*")
                else:
                    # Android 13+ Photo Picker for Photos (pops up bottom sheet in-app)
                    intent = Intent("android.provider.action.PICK_IMAGES")
                    intent.setType("image/*")

                self._android_activity.startActivityForResult(intent, self._native_picker_request_code)
                return
            except Exception:
                # Fallback to ACTION_GET_CONTENT
                try:
                    Intent = autoclass("android.content.Intent")
                    intent = Intent(Intent.ACTION_GET_CONTENT)
                    intent.setType("video/*" if kind == "video" else ("*/*" if kind == "document" else "image/*"))
                    self._android_activity.startActivityForResult(intent, self._native_picker_request_code)
                    return
                except Exception:
                    pass

        # Fallback to filechooser or local list
        if filechooser:
            try:
                filters = [["Media", "*.png", "*.jpg", "*.jpeg", "*.mp4", "*.mkv", "*.mov"]]
                filechooser.open_file(on_selection=self._native_picker_callback, filters=filters, multiple=False)
                return
            except Exception:
                pass

        # FileChooserListView fallback
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        start_path = "/sdcard/DCIM" if os.path.exists("/sdcard/DCIM") else "/sdcard"
        fc = FileChooserListView(path=start_path, filters=["*.png", "*.jpg", "*.jpeg", "*.mp4", "*.mkv"])
        content.add_widget(fc)
        popup = Popup(title="Select File", content=content, size_hint=(0.95, 0.85))
        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        c_btn = NeonButton(text="Cancel", outline="#343440", color=rgba(WHITE))
        s_btn = NeonButton(text="Select", outline=CYAN, color=rgba(CYAN))
        c_btn.bind(on_release=popup.dismiss)
        def on_select(*_):
            if fc.selection:
                popup.dismiss()
                self._native_picker_callback(fc.selection)
            else:
                self.message("No File", "Select a file to proceed.")
        s_btn.bind(on_select)
        btn_row.add_widget(c_btn); btn_row.add_widget(s_btn)
        content.add_widget(btn_row)
        popup.open()

    def _on_android_activity_result(self, request_code, result_code, intent):
        """Receives picked URI from the Android Photo Picker without app exit."""
        if request_code == self._native_picker_request_code and result_code == -1 and intent is not None:
            try:
                uri = intent.getData()
                if uri is not None and self._android_activity:
                    # Copy from content:// stream into user_data_dir to ensure permanent access
                    cr = self._android_activity.getContentResolver()
                    in_stream = cr.openInputStream(uri)

                    # Determine extension
                    mime_type = str(cr.getType(uri) or "")
                    ext = ".mp4" if "video" in mime_type else (".png" if "png" in mime_type else ".jpg")

                    dest_name = f"picked_{int(time.time() * 1000)}{ext}"
                    dest_path = os.path.join(self.data_dir, dest_name)

                    FileOutputStream = autoclass("java.io.FileOutputStream")
                    out_stream = FileOutputStream(dest_path)

                    buffer = bytearray(1024 * 64)
                    j_buffer = autoclass("jnius.ByteArray")(len(buffer))
                    # Read into stream
                    while True:
                        bytes_read = in_stream.read(j_buffer)
                        if bytes_read == -1:
                            break
                        out_stream.write(j_buffer, 0, bytes_read)

                    in_stream.close()
                    out_stream.close()

                    if self._native_picker_callback:
                        Clock.schedule_once(lambda dt: self._native_picker_callback([dest_path]), 0.05)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.message("Picker Error", str(e)), 0.05)

    def file_selected(self, selection, kind="photo"):
        if not selection:
            return
        path = selection[0]
        if not os.path.isfile(path):
            self.message("Unsupported File", "Selected file could not be opened.")
            return

        ext = os.path.splitext(path)[1].lower()

        if kind == "document":
            dest = os.path.join(self.data_dir, f"doc_{int(time.time())}{ext}")
            try:
                shutil.copy2(path, dest)
                key = "document:" + dest
                self.post_documents[key] = os.path.basename(path)
                self.posts.append(key)
                self._save_data()
                self.message("Document Added", f"Document {os.path.basename(path)} added to your posts.")
            except Exception as err:
                self.message("Error", str(err))
            return

        # Check orientation and extract thumbnail for videos (fixes white static blank)
        dest = os.path.join(self.data_dir, f"post_{int(time.time() * 1000)}{ext}")
        try:
            if os.path.abspath(path) != os.path.abspath(dest):
                shutil.copy2(path, dest)

            # Detect horizontal vs vertical orientation
            is_horizontal = self._detect_orientation(dest, ext)
            self.post_orientation[dest] = "horizontal" if is_horizontal else "vertical"

            # If video, extract a thumbnail frame with MediaMetadataRetriever
            if ext in VIDEO_EXTENSIONS:
                thumb_path = self._extract_video_thumbnail(dest)
                if thumb_path:
                    self.post_thumbnails[dest] = thumb_path

            if dest not in self.posts:
                self.posts.append(dest)
            self.ask_post_caption(dest)
        except Exception as err:
            self.message("Upload failed", str(err))

    def _detect_orientation(self, path, ext):
        """Checks if photo or video is horizontal (landscape) or vertical (portrait)."""
        if ext in VIDEO_EXTENSIONS:
            if autoclass:
                try:
                    Retriever = autoclass("android.media.MediaMetadataRetriever")
                    r = Retriever()
                    r.setDataSource(path)
                    w = int(r.extractMetadata(Retriever.METADATA_KEY_VIDEO_WIDTH) or 1080)
                    h = int(r.extractMetadata(Retriever.METADATA_KEY_VIDEO_HEIGHT) or 1920)
                    rot = int(r.extractMetadata(Retriever.METADATA_KEY_VIDEO_ROTATION) or 0)
                    r.release()
                    if rot in (90, 270):
                        w, h = h, w
                    return w > h
                except Exception:
                    pass
            return False
        else:
            try:
                img = CoreImage(path)
                if img.texture:
                    w, h = img.texture.size
                    return w > h
            except Exception:
                pass
            return False

    def _extract_video_thumbnail(self, video_path):
        """Extracts a frame from the video using Android MediaMetadataRetriever to prevent white blank."""
        if not autoclass:
            return None
        try:
            Retriever = autoclass("android.media.MediaMetadataRetriever")
            Bitmap = autoclass("android.graphics.Bitmap")
            FileOutputStream = autoclass("java.io.FileOutputStream")
            CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")

            r = Retriever()
            r.setDataSource(video_path)
            frame = r.getFrameAtTime(0, Retriever.OPTION_CLOSEST_SYNC)
            if frame:
                thumb_name = f"thumb_{int(time.time() * 1000)}.jpg"
                thumb_path = os.path.join(self.data_dir, thumb_name)
                fos = FileOutputStream(thumb_path)
                frame.compress(CompressFormat.JPEG, 85, fos)
                fos.close()
                r.release()
                return thumb_path
            r.release()
        except Exception:
            pass
        return None

    def ask_post_caption(self, path):
        layout = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        caption = RoundedInput(hint_text="Add description...", multiline=True)
        layout.add_widget(Label(text="Write description for post", color=rgba(CYAN), size_hint_y=None, height=dp(28)))
        layout.add_widget(caption)
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        popup = Popup(title="Describe post", content=layout, size_hint=(.92, .48))
        post_btn = NeonButton(text="Post", outline=CYAN, color=rgba(CYAN))
        draft_btn = NeonButton(text="Save Draft", outline=PURPLE, color=rgba(WHITE))

        def finish_post(_=None):
            self.post_captions[path] = caption.text.strip()
            self._save_data()
            popup.dismiss()
            self.navigate("Home")

        def finish_draft(_=None):
            self.post_captions[path] = caption.text.strip()
            if path in self.posts:
                self.posts.remove(path)
            self.drafts.append(path)
            self._save_data()
            popup.dismiss()
            self.navigate("Home")

        post_btn.bind(on_release=finish_post)
        draft_btn.bind(on_release=finish_draft)
        row.add_widget(draft_btn); row.add_widget(post_btn)
        layout.add_widget(row)
        popup.open()

    def toggle_like(self, path):
        if path in self.liked:
            self.liked.remove(path)
        else:
            self.liked.add(path)
        self._save_data()
        self.show_feed()

    def toggle_save(self, path):
        if path in self.saved:
            self.saved.remove(path)
        else:
            self.saved.add(path)
        self._save_data()
        self.show_feed()

    def comment_dialog(self, path):
        layout = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        previous = self.comments.get(path, [])
        if previous:
            view = ScrollView(size_hint_y=.65)
            history = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
            history.bind(minimum_height=history.setter("height"))
            for c in previous[-15:]:
                history.add_widget(Label(text="💬 " + c, color=rgba(WHITE), size_hint_y=None, height=dp(34), halign="left"))
            view.add_widget(history)
            layout.add_widget(view)

        entry = RoundedInput(hint_text="Write a comment...", multiline=True, size_hint_y=None, height=dp(80))
        layout.add_widget(entry)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(7))
        popup = Popup(title="Comments", content=layout, size_hint=(.88, .70))
        cancel = NeonButton(text="Cancel", outline="#343440", color=rgba(WHITE))
        send = NeonButton(text="Send", outline=CYAN, color=rgba(CYAN))
        cancel.bind(on_release=popup.dismiss)

        def submit(*_):
            val = entry.text.strip()
            if val:
                self.comments.setdefault(path, []).append(val[:500])
                self._save_data()
                popup.dismiss()
                self.show_feed()

        send.bind(on_release=submit)
        row.add_widget(cancel); row.add_widget(send)
        layout.add_widget(row)
        popup.open()

    def share_options(self, path):
        popup = Popup(title="Share post", size_hint=(.9, None), height=dp(240))
        layout = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        layout.add_widget(Label(text=os.path.basename(path), color=rgba(CYAN), size_hint_y=None, height=dp(32)))
        copy_path = NeonButton(text="File details", outline=CYAN, color=rgba(CYAN))
        close = NeonButton(text="Close", outline="#343440", color=rgba(WHITE))
        copy_path.bind(on_release=lambda *_: (popup.dismiss(), self.message("File", path)))
        close.bind(on_release=popup.dismiss)
        layout.add_widget(copy_path); layout.add_widget(close)
        popup.content = layout
        popup.open()

    def show_profile(self):
        self.active_page = "Profile"
        self.clear_content()
        profile_root = FloatLayout()
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=(dp(8), dp(8), dp(8), dp(18)))
        body.bind(minimum_height=body.setter("height"))

        banner = RoundedClip(radius=18, size_hint_y=None, height=dp(160))
        with banner.canvas.before:
            Color(*rgba(PANEL))
            banner._banner_bg = RoundedRectangle(pos=banner.pos, size=banner.size, radius=[dp(18)] * 4)
        banner.bind(pos=lambda w, v: setattr(w._banner_bg, "pos", v), size=lambda w, v: setattr(w._banner_bg, "size", v))
        if self.banner_picture and os.path.isfile(self.banner_picture):
            banner.add_widget(Image(source=self.banner_picture, allow_stretch=True, keep_ratio=False))
        banner.add_widget(Label(text="[b]pik D[/b]", markup=True, color=rgba(WHITE), font_size="22sp", pos_hint={"center_x": .5, "center_y": .5}))
        body.add_widget(banner)

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        back = CleanNavButton(text="< Back", size_hint_x=None, width=dp(60), font_size="14sp", color=rgba(CYAN), bold=True)
        back.bind(on_release=lambda *_: self.navigate("Home"))
        header.add_widget(back)
        header.add_widget(Label(text="PROFILE", color=rgba(CYAN), bold=True, font_size="18sp", halign="left"))
        edit = NeonButton(text="Edit", size_hint_x=None, width=dp(50), outline=PURPLE, color=rgba(PURPLE), font_size="13sp")
        edit.bind(on_release=lambda *_: self.edit_profile())
        header.add_widget(edit)
        settings_button = CleanNavButton(text="⚙", size_hint_x=None, width=dp(40), font_size="20sp", color=rgba(PURPLE), bold=True)
        settings_button.bind(on_release=lambda *_: self.show_settings())
        header.add_widget(settings_button)
        body.add_widget(header)

        # Identity
        identity = BoxLayout(size_hint_y=None, height=dp(90), spacing=dp(12))
        circle = self._round_avatar(self.profile_picture, self.profile_name[:1].upper() or "P", 70, CYAN)
        details = BoxLayout(orientation="vertical", spacing=dp(2))
        details.add_widget(Label(text=self.profile_name, color=rgba(WHITE), bold=True, font_size="20sp", halign="left"))
        details.add_widget(Label(text="@" + self.username, color=rgba(CYAN), font_size="13sp", halign="left"))
        details.add_widget(Label(text=self.bio, color=rgba(GREY), font_size="12sp", halign="left"))
        identity.add_widget(circle); identity.add_widget(details)
        body.add_widget(identity)

        # Tabs
        tab_bar = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        for tab_name in ("Posts", "Videos", "Saved", "Drafts", "Private"):
            is_act = (self.profile_tab == tab_name)
            btn = NeonButton(text=tab_name, radius=12,
                             fill=PURPLE if is_act else PANEL,
                             outline=CYAN if is_act else "#343440",
                             color=rgba(WHITE if is_act else GREY))
            btn.bind(on_release=lambda _b, t=tab_name: self.change_profile_tab(t))
            tab_bar.add_widget(btn)
        body.add_widget(tab_bar)

        active_list = []
        if self.profile_tab == "Drafts":
            active_list = self.drafts
        elif self.profile_tab == "Posts":
            active_list = self.posts
        elif self.profile_tab == "Videos":
            active_list = [p for p in self.posts if not p.startswith("document:") and os.path.splitext(p)[1].lower() in VIDEO_EXTENSIONS]
        elif self.profile_tab == "Saved":
            active_list = list(self.saved)
        elif self.profile_tab == "Private":
            active_list = self.private_posts

        if active_list:
            grid = GridLayout(cols=3, spacing=dp(6), size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            for p in reversed(active_list):
                tile = NeonButton(text="Doc" if p.startswith("document:") else "", outline=unique_accent(p), color=rgba(WHITE), radius=8, size_hint_y=None, height=dp(110))
                if not p.startswith("document:"):
                    ext = os.path.splitext(p)[1].lower()
                    if ext in VIDEO_EXTENSIONS:
                        thumb = self.post_thumbnails.get(p, "")
                        if thumb and os.path.isfile(thumb):
                            tile.add_widget(Image(source=thumb, allow_stretch=True, keep_ratio=False))
                        else:
                            tile.text = "▶ Video"
                    else:
                        tile.add_widget(Image(source=p, allow_stretch=True, keep_ratio=False))
                tile.bind(on_release=lambda _b, post_path=p: self.open_profile_post(post_path))
                grid.add_widget(tile)
            body.add_widget(grid)
        else:
            body.add_widget(Label(text=f"No {self.profile_tab.lower()} items available.", color=rgba(GREY), size_hint_y=None, height=dp(60)))

        scroll.add_widget(body)
        profile_root.add_widget(scroll)
        self.content.add_widget(profile_root)

    def change_profile_tab(self, tab_name):
        self.profile_tab = tab_name
        self.show_profile()

    def open_profile_post(self, path):
        if path.startswith("document:"):
            self.message("Document", self.post_documents.get(path, "Document"))
            return
        self.clear_content()
        self.content.add_widget(self.make_post_card(path))

    def edit_profile(self):
        layout = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        name = RoundedInput(text=self.profile_name, hint_text="Display name (1x every 7 days)", multiline=False, size_hint_y=None, height=dp(46))
        username = RoundedInput(text=self.username, hint_text="Username (1x every 30 days)", multiline=False, size_hint_y=None, height=dp(46))
        bio = RoundedInput(text=self.bio, hint_text="Bio", multiline=False, size_hint_y=None, height=dp(46))
        for field in (name, username, bio):
            layout.add_widget(field)

        popup = Popup(title="Edit profile", content=layout, size_hint=(.92, None), height=dp(420))
        photo = NeonButton(text="Change Profile Picture (In-App Picker)", outline=CYAN, color=rgba(CYAN), size_hint_y=None, height=dp(42))
        banner = NeonButton(text="Change Profile Banner (In-App Picker)", outline=PURPLE, color=rgba(PURPLE), size_hint_y=None, height=dp(42))

        photo.bind(on_release=lambda *_: (popup.dismiss(), self.open_in_app_picker("photo", callback=lambda sel: self.set_profile_pic(sel))))
        banner.bind(on_release=lambda *_: (popup.dismiss(), self.open_in_app_picker("photo", callback=lambda sel: self.set_banner_pic(sel))))
        layout.add_widget(photo); layout.add_widget(banner)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        cancel = NeonButton(text="Cancel", outline="#343440", color=rgba(WHITE))
        save = NeonButton(text="Save Details", outline=CYAN, color=rgba(CYAN))
        cancel.bind(on_release=popup.dismiss)

        def save_details(*_):
            now = time.time()
            new_name = name.text.strip()[:40]
            new_user = username.text.strip().lstrip("@").replace(" ", "")[:30]
            if new_name != self.profile_name:
                if now - self.last_name_change < SEVEN_DAYS_SEC:
                    rem_days = int((SEVEN_DAYS_SEC - (now - self.last_name_change)) / 86400) + 1
                    self.message("Name Locked", f"Display name can only be updated once every 7 days. Try in {rem_days} day(s).")
                    return
                self.profile_name = new_name
                self.last_name_change = now
            if new_user != self.username:
                if now - self.last_username_change < THIRTY_DAYS_SEC:
                    rem_days = int((THIRTY_DAYS_SEC - (now - self.last_username_change)) / 86400) + 1
                    self.message("Username Locked", f"Username can only be updated once every 30 days. Try in {rem_days} day(s).")
                    return
                self.username = new_user
                self.last_username_change = now
            self.bio = bio.text.strip()[:160]
            self._save_data()
            popup.dismiss()
            if "Profile" in self.nav_buttons:
                self.update_nav_avatar(self.nav_buttons["Profile"])
            self.show_profile()

        save.bind(on_release=save_details)
        row.add_widget(cancel); row.add_widget(save)
        layout.add_widget(row)
        popup.open()

    def set_profile_pic(self, sel):
        if sel:
            self.profile_picture = sel[0]
            self._save_data()
            if "Profile" in self.nav_buttons:
                self.update_nav_avatar(self.nav_buttons["Profile"])
            self.show_profile()

    def set_banner_pic(self, sel):
        if sel:
            self.banner_picture = sel[0]
            self._save_data()
            self.show_profile()

    # =========================================================================
    # EXPANDED SETTINGS (Real Heart Like Info, Cache, Autoplay, AMOLED, Trash)
    # =========================================================================
    def show_settings(self):
        self.active_page = "Settings"
        self.clear_content()
        self.page_title("SETTINGS", PURPLE, "Profile")
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(12))
        body.bind(minimum_height=body.setter("height"))
        scroll.add_widget(body)
        self.content.add_widget(scroll)

        # Account summary
        account_card = BoxLayout(size_hint_y=None, height=dp(86), spacing=dp(12), padding=(dp(8), dp(6)))
        account_card.add_widget(self._round_avatar(self.profile_picture, self.profile_name[:1].upper() or "P", 62, CYAN))
        account_info = BoxLayout(orientation="vertical", spacing=dp(2))
        account_info.add_widget(Label(text=self.profile_name, color=rgba(WHITE), bold=True, font_size="16sp", halign="left"))
        account_info.add_widget(Label(text="@" + self.username, color=rgba(GREY), font_size="12sp", halign="left"))
        edit_account = NeonButton(text="Edit", size_hint_x=None, width=dp(68), outline=PURPLE, color=rgba(PURPLE))
        edit_account.bind(on_release=lambda *_: self.edit_profile())
        account_card.add_widget(account_info); account_card.add_widget(edit_account)
        body.add_widget(account_card)

        # Post Display preference
        body.add_widget(Label(text="POST HEADER DISPLAY PREFERENCE", color=rgba(CYAN), bold=True, size_hint_y=None, height=dp(30), halign="left"))
        disp_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        btn_name = NeonButton(text="Use Display Name", fill=CYAN if self.display_mode == "name" else PANEL, outline=CYAN, color=rgba(WHITE if self.display_mode == "name" else GREY))
        btn_user = NeonButton(text="Use Username", fill=CYAN if self.display_mode == "username" else PANEL, outline=CYAN, color=rgba(WHITE if self.display_mode == "username" else GREY))
        def set_disp(mode):
            self.display_mode = mode
            self._save_data()
            self.show_settings()
        btn_name.bind(on_release=lambda *_: set_disp("name"))
        btn_user.bind(on_release=lambda *_: set_disp("username"))
        disp_row.add_widget(btn_name); disp_row.add_widget(btn_user)
        body.add_widget(disp_row)

        # Media Preferences (Autoplay, Post colours, AMOLED)
        body.add_widget(Label(text="MEDIA & THEME PREFERENCES", color=rgba(PURPLE), bold=True, size_hint_y=None, height=dp(30), halign="left"))
        for title, attr in (("Autoplay Videos in Feed", "autoplay"), ("Show Post Color Accents", "show_post_colours"), ("AMOLED Pure Black Theme", "amoled_mode")):
            row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
            row.add_widget(Label(text=title, color=rgba(WHITE), halign="left", size_hint_x=.75))
            sw = Switch(active=getattr(self, attr, True), size_hint_x=.25)
            def on_sw(instance, val, a=attr):
                setattr(self, a, val)
                self._save_data()
            sw.bind(active=on_sw)
            row.add_widget(sw)
            body.add_widget(row)

        # 7-Day Trash Bin Management
        body.add_widget(Label(text="7-DAY TRASH BIN & SEARCH HISTORY", color=rgba(YELLOW), bold=True, size_hint_y=None, height=dp(30), halign="left"))
        hist_str = f"Recent Searches: {len(self.search_history)} saved"
        body.add_widget(Label(text=hist_str, color=rgba(WHITE), size_hint_y=None, height=dp(26), halign="left"))
        trash_str = f"Trash Bin Items: {len(self.deleted_posts)} (Auto-purged in 7 days)"
        body.add_widget(Label(text=trash_str, color=rgba(GREY), size_hint_y=None, height=dp(26), halign="left"))

        trash_btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        clear_hist = NeonButton(text="Clear Searches", outline="#343440", color=rgba(WHITE))
        empty_trash = NeonButton(text="Empty Trash Now", outline=PINK, color=rgba(PINK))
        def do_empty_trash(*_):
            for p in list(self.deleted_posts.keys()):
                if os.path.isfile(p):
                    try: os.remove(p)
                    except Exception: pass
            self.deleted_posts.clear()
            self._save_data()
            self.message("Trash Emptied", "All deleted items permanently removed.")
            self.show_settings()
        def do_clear_hist(*_):
            self.search_history.clear()
            self._save_data()
            self.message("Search History", "Search history cleared.")
            self.show_settings()
        clear_hist.bind(on_release=do_clear_hist)
        empty_trash.bind(on_release=do_empty_trash)
        trash_btn_row.add_widget(clear_hist); trash_btn_row.add_widget(empty_trash)
        body.add_widget(trash_btn_row)

        # Storage & Cache Cleaner
        body.add_widget(Label(text="STORAGE & CACHE", color=rgba(CYAN), bold=True, size_hint_y=None, height=dp(30), halign="left"))
        cache_btn = NeonButton(text="Clear Cache & Temp Video Buffers", outline=CYAN, color=rgba(CYAN), size_hint_y=None, height=dp(40))
        def do_clear_cache(*_):
            self.message("Cache Cleared", "Temporary playback buffers & thumbnails refreshed.")
        cache_btn.bind(on_release=do_clear_cache)
        body.add_widget(cache_btn)

        # Account Management
        body.add_widget(Label(text="ACCOUNT MANAGEMENT", color=rgba(PINK), bold=True, size_hint_y=None, height=dp(30), halign="left"))
        logout_btn = NeonButton(text="Log Out", size_hint_y=None, height=dp(42), outline=PINK, color=rgba(PINK))
        logout_btn.bind(on_release=lambda *_: self.handle_logout())
        body.add_widget(logout_btn)

        # Help & About
        body.add_widget(Label(text="HELP & ABOUT APP", color=rgba(GREY), bold=True, size_hint_y=None, height=dp(30), halign="left"))
        for item_title, desc in [
            ("Help & Support", "FAQs, video playback troubleshooting and support."),
            ("Privacy Policy", "All posts and accounts stay private and strictly local on your device."),
            ("About pik D", "pik D v1.0 Production Release — Your World. Your Space.")
        ]:
            b = NeonButton(text=item_title, size_hint_y=None, height=dp(40), outline="#343440", color=rgba(WHITE))
            b.bind(on_release=lambda _, t=item_title, d=desc: self.message(t, d))
            body.add_widget(b)

    def handle_logout(self):
        self.is_logged_in = False
        app = App.get_running_app()
        app.is_logged_in = False
        self._save_data()
        self.manager.current = "auth"

    def message(self, title, text):
        popup = Popup(title=title, size_hint=(.88, None), height=dp(210))
        layout = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(14))
        label = Label(text=text, color=rgba(WHITE), halign="center", valign="middle")
        label.bind(size=lambda w, v: setattr(w, "text_size", v))
        layout.add_widget(label)
        close = NeonButton(text="OK", size_hint_y=None, height=dp(44), outline=CYAN, color=rgba(CYAN))
        close.bind(on_release=popup.dismiss)
        layout.add_widget(close)
        popup.content = layout
        popup.open()


class SamNgApp(App):
    def build(self):
        self.title = "pik D"
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass
        self.is_logged_in = False
        self.username = ""
        Window.clearcolor = rgba(BG)
        manager = ScreenManager(transition=FadeTransition(duration=.18))
        manager.add_widget(BootScreen(name="boot"))
        manager.add_widget(AuthScreen(name="auth"))
        manager.add_widget(HomeScreen(name="home"))
        manager.current = "boot"
        return manager


if __name__ == "__main__":
    SamNgApp().run()
