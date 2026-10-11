# SAM NG — Kivy main.py
# Production release with Boot/Welcome screen, Auth/Login screen, continuous scrolling & 7-day trash bin.
# Minimal repair: preserve the supplied app structure and UI; fix login/signup state and data saving.

import os
import json
import time
import shutil
import hashlib
import threading
import urllib.request
import urllib.error

# NEXOVARA AI CONFIGURATION: paste your Gemini API key between the quotes.
# For local testing only. Never publish a real API key in a public GitHub repository.
NEXOVARA_API_KEY = "PASTE_YOUR_GEMINI_API_KEY_HERE"
NEXOVARA_MODEL = "gemini-2.5-flash"
NEXOVARA_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

from kivy.app import App
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line, Ellipse
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
from kivy.uix.slider import Slider
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
    from jnius import jarray
except Exception:
    autoclass = None
    jarray = None

APP_NAME = "SAM NG"
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

PRIVACY_POLICY = """SAM NG — PRIVACY POLICY
Last updated: 11 October 2026

1. About SAM NG
SAM NG is currently a local prototype social app. Login and sign-up in this version are demonstrations stored on this device and are not verified by a secure online account service.

2. Information the app handles
Depending on the features you use, SAM NG may store a username, profile information, app settings, captions, posts, drafts, comments, likes, saved items, search history, and media or documents you choose to import. The app uses Android's system picker so you choose individual photos or videos rather than granting access to your entire photo library.

3. How information is used
This prototype uses locally stored information to show your profile, posts, settings, drafts, comments, saved items, search history, and trash-bin entries. Imported media is copied into the app's private storage so it can be displayed later.

4. Uploading and sharing
This prototype does not upload posts to a SAM NG server. Online publishing, cloud synchronisation, real friend messaging, and server-based account services are not connected. If those services are added, this policy must be updated to explain what is sent, to whom, and why before public release.

5. Permissions and your choices
Android may ask for permission when you use a feature such as the camera. When selecting media, you can cancel without choosing anything. You can review or change app permissions in Android Settings. You can delete content within the app where deletion controls are provided. Uninstalling the app normally removes its private app data, but exported or separately shared copies may remain elsewhere.

6. Storage and security
Imported files and app data are kept in the app's private storage on this device. Protect your device with its screen lock. No app can guarantee absolute security. Items in the app's trash feature may remain until they are permanently removed by the app.

7. Children and personal information
Do not post personal information or content you do not have permission to share. Because online accounts and online publishing are not connected in this prototype, it does not currently operate an online social service through a SAM NG server.

8. Contact and policy updates
A public release should include a monitored developer contact email and a stable public URL for this policy. This policy must be updated if SAM NG adds online accounts, server uploads, analytics, advertising, or other data-processing services.

Important: This policy describes the current local prototype only. The developer must review it against the final app and any services actually connected before publishing it."""

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
            logo = Image(source="logo.png", size_hint=(None, None), size=(dp(120), dp(120)),
                         pos_hint={"center_x": .5, "center_y": .56})
            root.add_widget(logo)
        else:
            root.add_widget(Label(text="[b]SAM NG[/b]", markup=True, color=rgba(CYAN),
                                  font_size="40sp", size_hint=(1, .3),
                                  pos_hint={"center_x": .5, "center_y": .56}))

        root.add_widget(Label(text="YOUR WORLD. YOUR SPACE.",
                              color=rgba(PURPLE), font_size="12sp",
                              size_hint=(1, .05),
                              pos_hint={"center_x": .5, "center_y": .37}))
        self.progress = 0
        Clock.schedule_interval(self.advance, .035)

    def advance(self, dt):
        self.progress += 2
        if self.progress >= 100:
            Clock.unschedule(self.advance)
            app = App.get_running_app()
            # Use the persisted HomeScreen login state as the source of truth.
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

        box = BoxLayout(orientation="vertical", spacing=dp(20), size_hint=(0.86, None), height=dp(410),
                        pos_hint={"center_x": .5, "center_y": .5})

        box.add_widget(Label(text="Welcome to SAM NG", color=rgba(CYAN), font_size="22sp", bold=True, size_hint_y=None, height=dp(36)))
        box.add_widget(Label(text="Log in or create an account to start sharing.", color=rgba(GREY), font_size="13sp", size_hint_y=None, height=dp(24)))

        self.user_input = RoundedInput(hint_text="Username or Email", multiline=False, size_hint_y=None, height=dp(48))
        self.pass_input = RoundedInput(hint_text="Password", password=True, multiline=False, size_hint_y=None, height=dp(48))

        box.add_widget(self.user_input)
        box.add_widget(Widget(size_hint_y=None, height=dp(6)))
        box.add_widget(self.pass_input)
        box.add_widget(Widget(size_hint_y=None, height=dp(4)))

        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        login_btn = NeonButton(text="Log In", outline=CYAN, color=rgba(CYAN))
        signup_btn = NeonButton(text="Sign Up", outline=PURPLE, color=rgba(WHITE))

        login_btn.bind(on_release=self.handle_login)
        signup_btn.bind(on_release=self.handle_signup)

        btn_row.add_widget(login_btn)
        btn_row.add_widget(signup_btn)
        box.add_widget(btn_row)
        root.add_widget(box)

    def _finish_auth(self, username):
        """Synchronize app and HomeScreen state and save through the correct object."""
        app = App.get_running_app()
        home = self.manager.get_screen("home")
        clean_username = username.replace(" ", "")
        home.username = clean_username
        home.is_logged_in = True
        app.username = clean_username
        app.is_logged_in = True
        home._save_data()
        self.manager.current = "home"

    def handle_login(self, *_):
        u = self.user_input.text.strip()
        p = self.pass_input.text.strip()
        if not u or not p:
            self.user_input.hint_text = "Please enter credentials!"
            return
        # This app currently uses local profile state rather than a remote auth service.
        self._finish_auth(u)

    def handle_signup(self, *_):
        u = self.user_input.text.strip()
        p = self.pass_input.text.strip()
        if not u or not p:
            self.user_input.hint_text = "Provide username & password!"
            return
        app = App.get_running_app()
        self._finish_auth(u)
        self.manager.get_screen("home").message("Account Created", f"Successfully registered as @{app.username}")


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        self.data_dir = app.user_data_dir
        self.state_file = os.path.join(self.data_dir, "samng_data.json")
        self._native_picker_callback = None
        self._native_picker_kind = "media"
        self._native_picker_request_code = 4817
        self._native_camera_photo_request_code = 4818
        self._native_camera_video_request_code = 4819
        if autoclass:
            try:
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                self._android_activity = PythonActivity.mActivity
                self._android_activity.bind(on_activity_result=self._on_native_picker_result)
            except Exception:
                self._android_activity = None
        else:
            self._android_activity = None
        self.posts = []
        self.drafts = []
        self.private_posts = []
        self.deleted_posts = {}
        self.post_captions = {}
        self.post_documents = {}
        self.comments = {}
        self.saved = set()
        self.liked = set()
        self.search_history = ["samng trends", "tutorial video", "kivy design"]
        self.ai_chat_history = []
        self.ai_waiting = False
        self.secret_codes = {"*#7266#": "SAM NG Engine v0.8", "*#0007#": "Debug Overlay Activated"}
        self.active_page = "Home"
        self.inbox_return_page = "Home"
        self.active_tab = "For You"
        self.profile_tab = "Posts"
        self.profile_name = "Sam Ng"
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
        self.display_mode = "name"
        self.last_name_change = 0
        self.last_username_change = 0
        self.is_logged_in = app.is_logged_in
        self._load_data()
        self.clean_expired_trash()

        self.root = BoxLayout(orientation="vertical", spacing=0)
        self.add_widget(self.root)

        self.topbar = BoxLayout(size_hint_y=None, height=dp(65),
                                padding=(dp(8), dp(12), dp(8), dp(4)), spacing=dp(4))
        self.root.add_widget(self.topbar)
        self.top_tab_buttons = {}

        for tab in ("STEM", "Following", "For You"):
            b = TextTabButton(text=tab, is_active=(tab == "For You"), active_color=CYAN)
            b.bind(on_release=lambda btn, t=tab: self.change_tab(t))
            self.topbar.add_widget(b)
            self.top_tab_buttons[tab] = b

        search_btn = CleanNavButton(text="Search", size_hint_x=None, width=dp(65),
                                    font_size="14sp", color=rgba(PURPLE), bold=True)
        search_btn.bind(on_release=self.activate_search_mode)
        self.topbar.add_widget(search_btn)

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
        mic_btn.bind(on_release=lambda *_: self.message("Voice Search", "Voice input active..."))
        self.search_bar_top.add_widget(mic_btn)

        self.root.add_widget(self.search_bar_top)

        self.content = BoxLayout(orientation="vertical", spacing=0)
        self.root.add_widget(self.content)

        self.nav_wrapper = BoxLayout(size_hint_y=None, height=dp(65), padding=(dp(0), dp(0), dp(0), dp(8)))
        self.nav = BoxLayout(size_hint=(1, 1), padding=(dp(4), dp(2)), spacing=dp(0))
        self.nav_wrapper.add_widget(self.nav)
        self.root.add_widget(self.nav_wrapper)
        self.nav_buttons = {}

        nav_items = [
            ("Home", "Home"),
            ("Friends", "Friends"),
            ("Create", "+"),
            ("Inbox", "Inbox"),
            ("Profile", "avatar")
        ]

        for name, label in nav_items:
            if name == "Profile":
                b = CleanNavButton(size_hint_x=1)
                self.update_nav_avatar(b)
            else:
                b = CleanNavButton(text=label, font_size="15sp" if name != "Create" else "26sp",
                                   color=rgba(WHITE), bold=True, size_hint_x=1)
            b.bind(on_release=lambda btn, n=name: self.navigate(n))
            self.nav.add_widget(b)
            self.nav_buttons[name] = b

        self.show_feed()

    def update_nav_avatar(self, button):
        button.clear_widgets()
        avatar_box = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, 1))

        # Give the avatar a clearly visible, fixed-size area inside its nav button.
        with button.canvas.before:
            Color(*rgba(PURPLE))
            avatar_ring = Ellipse(pos=(0, 0), size=(dp(36), dp(36)))
        button.bind(pos=lambda w, v: setattr(avatar_ring, "pos",
                                             (w.x + (w.width - dp(36)) / 2,
                                              w.y + (w.height - dp(36)) / 2)))
        button.bind(size=lambda w, v: setattr(avatar_ring, "pos",
                                              (w.x + (w.width - dp(36)) / 2,
                                               w.y + (w.height - dp(36)) / 2)))
        if self.profile_picture and os.path.isfile(self.profile_picture):
            avatar_img = Image(source=self.profile_picture, allow_stretch=True, keep_ratio=False,
                               size_hint=(None, None), size=(dp(30), dp(30)))
            avatar_box.add_widget(avatar_img)
        else:
            lbl = Label(text=self.profile_name[:1].upper() or "S", color=rgba(CYAN), bold=True,
                        font_size="16sp", size_hint=(None, None), size=(dp(30), dp(30)))
            avatar_box.add_widget(lbl)

        button.add_widget(avatar_box)

    def _load_data(self):
        try:
            if os.path.isfile(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.posts = [p for p in data.get("posts", []) if os.path.isfile(p)]
                self.drafts = [p for p in data.get("drafts", []) if os.path.isfile(p)]
                self.private_posts = [p for p in data.get("private_posts", []) if os.path.isfile(p)]
                self.deleted_posts = data.get("deleted_posts", {})
                self.comments = data.get("comments", {})
                self.post_captions = data.get("post_captions", {})
                self.post_documents = data.get("post_documents", {})
                self.saved = set(data.get("saved", []))
                self.liked = set(data.get("liked", []))
                self.search_history = data.get("search_history", self.search_history)
                self.ai_chat_history = data.get("ai_chat_history", [])
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
                self.display_mode = data.get("display_mode", "name")
                self.last_name_change = data.get("last_name_change", 0)
                self.last_username_change = data.get("last_username_change", 0)
                self.is_logged_in = bool(data.get("is_logged_in", False))
        except Exception:
            pass

    def _save_data(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            data = {
                "posts": self.posts, "drafts": self.drafts, "private_posts": self.private_posts,
                "deleted_posts": self.deleted_posts, "comments": self.comments,
                "post_captions": self.post_captions, "post_documents": self.post_documents,
                "saved": list(self.saved), "liked": list(self.liked), "search_history": self.search_history,
                "ai_chat_history": self.ai_chat_history,
                "profile_name": self.profile_name, "username": self.username,
                "bio": self.bio, "profile_picture": self.profile_picture,
                "banner_picture": self.banner_picture, "banner_opacity": self.banner_opacity,
                "profile_bg_picture": self.profile_bg_picture, "profile_bg_opacity": self.profile_bg_opacity,
                "dark_mode": self.dark_mode, "autoplay": self.autoplay,
                "show_post_colours": self.show_post_colours, "display_mode": self.display_mode,
                "last_name_change": self.last_name_change, "last_username_change": self.last_username_change,
                "is_logged_in": self.is_logged_in,
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
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8),
                        padding=(dp(4), dp(2)))
        back = CleanNavButton(text="< Back", size_hint_x=None, width=dp(60),
                              font_size="14sp", color=rgba(accent), bold=True)
        back.bind(on_release=lambda *_: self.navigate(back_to))
        row.add_widget(back)
        row.add_widget(Label(text=title, color=rgba(accent),
                             font_size="19sp", bold=True, halign="left"))
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
        self.nav_wrapper.height = dp(65)
        self.nav_wrapper.opacity = 1
        self.nav_wrapper.disabled = False
        self.show_feed()

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
            filtered = ["samng community", "trending videos", "creator tips"]
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
                if os.path.isfile(path):
                    stack.add_widget(self.make_post_card(path))
        scroll.add_widget(stack)
        self.content.add_widget(scroll)

    def make_post_card(self, path):
        accent = unique_accent(path) if self.show_post_colours else CYAN
        card = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        card.bind(minimum_height=card.setter("height"))
        ext = os.path.splitext(path)[1].lower()
        header_box = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(12), dp(2)), spacing=dp(8))
        avatar = FloatLayout(size_hint_x=None, width=dp(36))
        if self.profile_picture and os.path.isfile(self.profile_picture):
            avatar.add_widget(Image(source=self.profile_picture, allow_stretch=True, keep_ratio=False,
                                    size_hint=(None, None), size=(dp(34), dp(34)),
                                    pos_hint={"center_x": .5, "center_y": .5}))
        else:
            lbl = Label(text=self.profile_name[:1].upper() or "S", color=rgba(CYAN), bold=True,
                        font_size="16sp", pos_hint={"center_x": .5, "center_y": .5})
            avatar.add_widget(lbl)
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

        media_holder = FloatLayout(size_hint_y=None)
        try:
            if ext in VIDEO_EXTENSIONS:
                media = Video(source=path, state="play" if self.autoplay else "pause",
                              options={"eos": "loop"}, allow_stretch=True, keep_ratio=True,
                              size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
                media_holder.height = dp(380)
            else:
                media = Image(source=path, allow_stretch=True, keep_ratio=True,
                              size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
                if media.texture:
                    w, h = media.texture.size
                    aspect = h / float(w) if w > 0 else 1.0
                    calc_h = Window.width * aspect
                    media_holder.height = max(dp(220), min(calc_h, Window.height - dp(160)))
                else:
                    media_holder.height = dp(320)
            media_holder.add_widget(media)
        except Exception:
            media_holder.height = dp(200)
            media_holder.add_widget(Label(text="Video/Media loading error.", color=rgba(PINK)))

        rail = BoxLayout(orientation="vertical", size_hint=(None, 0.5), width=dp(56),
                         spacing=dp(6), pos_hint={"right": 0.98, "y": 0.05})
        liked_now = path in self.liked
        saved_now = path in self.saved
        like_count = (1 if liked_now else 0) + len(self.posts) % 5
        rail_like = NeonButton(text=f"Like\n{like_count}", font_size="11sp",
                               fill=PANEL, outline=BLUE if liked_now else PINK,
                               color=rgba(BLUE if liked_now else WHITE), radius=12)
        rail_comment = NeonButton(text=f"Chat\n{len(self.comments.get(path, []))}", font_size="11sp",
                                  fill=PANEL, outline=accent, color=rgba(WHITE), radius=12)
        rail_share = NeonButton(text="Share", font_size="11sp",
                                fill=PANEL, outline=accent, color=rgba(accent), radius=12)
        rail_save = NeonButton(text="Saved" if saved_now else "Save", font_size="11sp",
                                fill=PANEL, outline=PURPLE, color=rgba(PURPLE), radius=12)
        rail_like.bind(on_release=lambda *_: self.protected_action(lambda: self.toggle_like(path)))
        rail_comment.bind(on_release=lambda *_: self.protected_action(lambda: self.comment_dialog(path)))
        rail_share.bind(on_release=lambda *_: self.share_options(path))
        rail_save.bind(on_release=lambda *_: self.toggle_save(path))
        for action_button in (rail_like, rail_comment, rail_share, rail_save):
            rail.add_widget(action_button)
        media_holder.add_widget(rail)
        card.add_widget(media_holder)

        caption_text = self.post_captions.get(path, "")
        if caption_text:
            words = caption_text.split()
            desc_container = BoxLayout(orientation="vertical", size_hint_y=None,
                                       padding=(dp(12), dp(2)), spacing=dp(2))
            desc_container.bind(minimum_height=desc_container.setter("height"))
            if len(words) > 5:
                short_text = " ".join(words[:5]) + "..."
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
        del_btn = NeonButton(text="Delete Post", outline=PINK, color=rgba(PINK))
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

        # Inbox, Friends, and Create are immersive pages: hide both navigation
        # bars while these destinations are active.
        is_inbox = (name == "Inbox")
        is_profile = (name == "Profile")
        hide_navigation = name in ("Inbox", "Friends", "Create", "Profile")
        self.topbar.height = 0 if hide_navigation else dp(65)
        self.topbar.opacity = 0 if hide_navigation else 1
        self.topbar.disabled = hide_navigation

        if hide_navigation:
            self.nav_wrapper.height = 0
            self.nav_wrapper.opacity = 0
            self.nav_wrapper.disabled = True
        else:
            # Keep the bottom avatar visible on the profile page.
            self.nav_wrapper.height = dp(65)
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
            self.show_ai_friend()
        elif name == "Inbox":
            self.simple_page("INBOX", "Messages and comments appear here.", PINK,
                             back_to=self.inbox_return_page)

    def show_ai_friend(self, *_):
        """Permanent Nexovara AI friend and chat screen inside SAM NG."""
        self.active_page = "Friends"
        self.clear_content()
        self.page_title("AI", PURPLE, back_to="Home")

        outer = BoxLayout(orientation="vertical", spacing=dp(8), padding=(dp(10), dp(4), dp(10), dp(10)))
        self.content.add_widget(outer)

        intro = Label(
            text="AI  •  Your SAM NG assistant",
            color=rgba(GREY), font_size="12sp", size_hint_y=None, height=dp(34),
            halign="center", valign="middle")
        intro.bind(size=lambda w, v: setattr(w, "text_size", v))
        outer.add_widget(intro)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2), size_hint=(1, 1))
        self.ai_chat_stack = BoxLayout(orientation="vertical", size_hint_y=None,
                                       spacing=dp(8), padding=(dp(2), dp(6)))
        self.ai_chat_stack.bind(minimum_height=self.ai_chat_stack.setter("height"))
        scroll.add_widget(self.ai_chat_stack)
        outer.add_widget(scroll)
        self.ai_chat_scroll = scroll

        if not self.ai_chat_history:
            self._add_ai_bubble("AI", "Hi! I'm AI, your friend in SAM NG. Ask me about the app or general questions.")
        else:
            for item in self.ai_chat_history[-80:]:
                self._add_ai_bubble(item.get("role", "Nexovara AI"), item.get("text", ""), save=False)

        composer = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52), spacing=dp(7))
        self.ai_input = TextInput(
            hint_text="Message AI...", multiline=False, size_hint_x=1,
            background_normal="", background_active="", background_color=rgba(PANEL),
            foreground_color=rgba(WHITE), cursor_color=rgba(CYAN), padding=(dp(12), dp(14)))
        self.ai_input.bind(on_text_validate=self.send_ai_message)
        send = NeonButton(text="Send", size_hint_x=None, width=dp(76), outline=CYAN,
                          color=rgba(CYAN), radius=14)
        send.bind(on_release=self.send_ai_message)
        composer.add_widget(self.ai_input)
        composer.add_widget(send)
        outer.add_widget(composer)

        privacy = Label(
            text="Privacy: messages sent to the AI provider may be processed to generate replies. Do not send passwords or highly sensitive information.",
            color=rgba(GREY), font_size="10sp", size_hint_y=None, height=dp(32),
            halign="center", valign="middle")
        privacy.bind(size=lambda w, v: setattr(w, "text_size", v))
        outer.add_widget(privacy)
        Clock.schedule_once(lambda *_: setattr(scroll, "scroll_y", 0), .15)

    def _add_ai_bubble(self, role, text, save=True):
        is_user = str(role).lower() in ("user", "you")
        row = BoxLayout(orientation="horizontal", size_hint_y=None, spacing=dp(7),
                        size_hint_x=1, height=dp(54))
        row.bind(minimum_height=row.setter("height"))
        avatar = Label(text="S" if is_user else "AI", color=rgba(WHITE), bold=True,
                       font_size="12sp", size_hint=(None, None), size=(dp(36), dp(36)))
        with avatar.canvas.before:
            Color(*rgba(CYAN if is_user else PURPLE))
            avatar_bg = Ellipse(pos=avatar.pos, size=avatar.size)
        avatar.bind(pos=lambda w, v: setattr(avatar_bg, "pos", v))
        avatar.bind(size=lambda w, v: setattr(avatar_bg, "size", v))
        bubble = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp(10), spacing=dp(3))
        bubble.bind(minimum_height=bubble.setter("height"))
        title = Label(text="You" if is_user else "AI", color=rgba(CYAN if is_user else PURPLE),
                      bold=True, font_size="12sp", size_hint_y=None, height=dp(20), halign="left", valign="middle")
        title.bind(size=lambda w, v: setattr(w, "text_size", v))
        body = Label(text=str(text), color=rgba(WHITE), font_size="14sp", size_hint_y=None,
                     halign="left", valign="top")
        body.bind(width=lambda w, v: setattr(w, "text_size", (max(dp(80), v-dp(12)), None)))
        body.bind(texture_size=lambda w, v: setattr(w, "height", v[1] + dp(8)))
        with bubble.canvas.before:
            Color(*rgba("#20202D" if is_user else "#171725"))
            bg = RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[dp(12)])
        bubble.bind(pos=lambda w, v: setattr(bg, "pos", v))
        bubble.bind(size=lambda w, v: setattr(bg, "size", v))
        bubble.add_widget(title)
        bubble.add_widget(body)
        row.add_widget(avatar)
        row.add_widget(bubble)
        # Keep the AI/user profile badge and message grouped as one chat row.
        row.height = max(dp(48), bubble.height)
        self.ai_chat_stack.add_widget(row)
        if save:
            self.ai_chat_history.append({"role": "user" if is_user else "AI", "text": str(text)})
            self.ai_chat_history = self.ai_chat_history[-160:]
            self._save_data()
        if hasattr(self, "ai_chat_scroll"):
            Clock.schedule_once(lambda *_: setattr(self.ai_chat_scroll, "scroll_y", 0), .1)

    def send_ai_message(self, *_):
        if self.ai_waiting:
            return
        if not hasattr(self, "ai_input"):
            return
        prompt = self.ai_input.text.strip()
        if not prompt:
            return
        self.ai_input.text = ""
        self._add_ai_bubble("You", prompt)
        if not NEXOVARA_API_KEY or NEXOVARA_API_KEY == "PASTE_YOUR_GEMINI_API_KEY_HERE":
            self._add_ai_bubble("AI", "Add your Gemini API key in main.py at NEXOVARA_API_KEY near the top, then restart SAM NG.")
            return
        self.ai_waiting = True
        self._add_ai_bubble("AI", "AI is typing…")
        # Use a background thread so the Kivy interface does not freeze while waiting for the API.
        history = list(self.ai_chat_history[-16:])
        threading.Thread(target=self._request_nexovara_reply, args=(prompt, history), daemon=True).start()

    def _request_nexovara_reply(self, prompt, history):
        try:
            contents = []
            for item in history:
                role = "user" if str(item.get("role", "")).lower() == "user" else "model"
                text = str(item.get("text", ""))
                if text and text != "Thinking…":
                    contents.append({"role": role, "parts": [{"text": text}]})
            # Ensure the latest prompt is present exactly once.
            if not contents or contents[-1]["role"] != "user" or contents[-1]["parts"][0]["text"] != prompt:
                contents.append({"role": "user", "parts": [{"text": prompt}]})
            system_text = (
                "You are Nexovara AI, a helpful AI friend inside the SAM NG app. "
                "Answer general questions clearly. For SAM NG questions, explain only known features: "
                "Home feed, Friends, Inbox, Create, Profile, Search, Help Center, and Privacy Policy. "
                "Do not claim access to private user data or app systems you have not been connected to. "
                "Do not diagnose medical conditions; provide general health information and recommend a qualified professional when appropriate. "
                "Be honest when you do not know something."
            )
            payload = {
                "system_instruction": {"parts": [{"text": system_text}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
            }
            url = NEXOVARA_API_URL.format(model=NEXOVARA_MODEL) + "?key=" + NEXOVARA_API_KEY.strip()
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))
            parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            answer = "\n".join(part.get("text", "") for part in parts if part.get("text"))
            if not answer:
                answer = "I received an empty response. Please try asking again."
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:700]
            except Exception:
                detail = str(exc)
            answer = f"AI API error ({exc.code}). Check the API key, model access, and internet connection.\n{detail}"
        except Exception as exc:
            answer = f"Couldn't reach Nexovara AI. Check your internet connection and API key.\nDetails: {exc}"
        Clock.schedule_once(lambda *_: self._finish_nexovara_reply(answer), 0)

    def _finish_nexovara_reply(self, answer):
        # Remove the temporary thinking bubble, then show and save the final answer.
        if hasattr(self, "ai_chat_stack"):
            for child in list(self.ai_chat_stack.children):
                labels = [w.text for w in child.children if isinstance(w, Label)]
                if any("Thinking…" in t or "AI is typing…" in t for t in labels):
                    self.ai_chat_stack.remove_widget(child)
                    break
        self.ai_waiting = False
        self._add_ai_bubble("AI", answer)

    def simple_page(self, title, message, accent, back_to="Home"):
        self.clear_content()
        self.page_title(title, accent, back_to=back_to)
        self.content.add_widget(Label(text=message, color=rgba(GREY),
                                      halign="center", valign="top"))

    def change_tab(self, tab):
        self.active_tab = tab
        for t_name, btn in self.top_tab_buttons.items():
            btn.is_active = (t_name == tab)
            btn.color = rgba(CYAN if t_name == tab else GREY)
        if tab == "For You":
            self.show_feed()
        elif tab == "Following":
            self.simple_page("FOLLOWING", "Posts from creators you follow.", PURPLE)
        else:
            self.simple_page("STEM", "Science • Technology • Engineering • Mathematics", CYAN)

    def pick_media(self, *_):
        """Show Create actions with a visible Back button; use Android system apps."""
        popup = Popup(title="Create a post", size_hint=(.94, None), height=dp(330), auto_dismiss=False)
        layout = BoxLayout(orientation="vertical", spacing=dp(9), padding=dp(12))
        hint = Label(text="Choose what you want to add", color=rgba(GREY),
                     size_hint_y=None, height=dp(28), halign="left")
        hint.bind(size=lambda w, v: setattr(w, "text_size", v))
        layout.add_widget(hint)
        actions = (("Take Photo", lambda: self.open_native_camera("photo")),
                   ("Record Video", lambda: self.open_native_camera("video")),
                   ("Photo / Video Upload", lambda: self.open_picker("media")),
                   ("Document", lambda: self.open_picker("document")),
                   ("← Back to Feed", lambda: self.navigate("Home")))
        for label, action in actions:
            button = NeonButton(text=label, size_hint_y=None, height=dp(44),
                                outline=PURPLE if label.startswith("←") else CYAN,
                                color=rgba(WHITE), radius=14)
            button.bind(on_release=lambda _btn, fn=action: (popup.dismiss(), fn()))
            layout.add_widget(button)
        popup.content = layout
        popup.open()

    def open_native_camera(self, mode="photo"):
        """Launch the phone's installed camera app instead of Plyer's unavailable camera API."""
        if not (self._android_activity is not None and autoclass):
            # Pydroid may not expose PythonActivity. Try Plyer's camera plugin as a
            # fallback; a packaged Android build can use the native Intent path below.
            try:
                if mode == "photo" and camera is not None:
                    target = os.path.join(self.data_dir, "camera_" + str(int(time.time() * 1000)) + ".jpg")
                    camera.take_picture(filename=target, on_complete=self.camera_completed)
                    return
            except Exception:
                pass
            self.message("Camera unavailable", "This Pydroid session cannot launch the Android camera. The camera Intent works in the packaged Android app; use Photo / Video Upload to test posting here.")
            return
        try:
            Intent = autoclass("android.content.Intent")
            if mode == "video":
                intent = Intent("android.media.action.VIDEO_CAPTURE")
                request_code = self._native_camera_video_request_code
            else:
                intent = Intent("android.media.action.IMAGE_CAPTURE")
                request_code = self._native_camera_photo_request_code
            if not intent.resolveActivity(self._android_activity.getPackageManager()):
                self.message("Camera unavailable", "No compatible camera app was found on this device.")
                return
            self._android_activity.startActivityForResult(intent, request_code)
        except Exception as error:
            self.message("Could not open camera", "Allow camera access in Android Settings, then try again.\n" + str(error))

    def open_camera(self):
        # Backwards-compatible name used by any older button binding.
        self.open_native_camera("photo")

    def camera_completed(self, path):
        if path and os.path.isfile(path):
            self.file_selected([path])

    def open_picker(self, kind="media"):
        """Use Android's native content chooser, which can show recent media via Files/Photos."""
        if self._android_activity is not None and autoclass:
            try:
                Intent = autoclass("android.content.Intent")
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                if kind == "document":
                    intent.setType("application/*")
                else:
                    # Keep the base MIME type as images so Android offers the visual
                    # Photos picker (like the user's third screenshot), while allowing
                    # video providers through EXTRA_MIME_TYPES as well.
                    intent.setType("image/*")
                    mime_types = jarray.array(["image/*", "video/*"], "java.lang.String")
                    intent.putExtra(Intent.EXTRA_MIME_TYPES, mime_types)
                self._native_picker_callback = self.file_selected
                self._native_picker_kind = kind
                title = "Choose a document" if kind == "document" else "Choose a photo or video"
                chooser = Intent.createChooser(intent, title)
                self._android_activity.startActivityForResult(chooser, self._native_picker_request_code)
                return
            except Exception as error:
                self._native_picker_callback = None
                self.message("Picker unavailable", "Android could not open the media chooser. Try again or use the file chooser.\n" + str(error))

        # Non-Android fallback only. Android should use the native content picker above.
        if filechooser:
            try:
                filters = [["Documents", "*.pdf", "*.txt", "*.doc", "*.docx"]] if kind == "document" else [["Photos and videos", "*.png", "*.jpg", "*.jpeg", "*.webp", "*.mp4", "*.mov", "*.mkv", "*.3gp"]]
                filechooser.open_file(on_selection=lambda selection: self.file_selected(selection, kind), filters=filters)
                return
            except Exception:
                pass
        popup = Popup(title="Select a file", size_hint=(.96, .88), auto_dismiss=True)
        layout = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        chooser = FileChooserListView(path=os.path.expanduser("~"), filters=["*.pdf", "*.txt", "*.doc", "*.docx"] if kind == "document" else ["*.mp4", "*.mkv", "*.jpg", "*.jpeg", "*.png", "*.webp"], multiselect=False)
        layout.add_widget(chooser)
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        cancel = NeonButton(text="Back", outline="#343440", color=rgba(WHITE))
        choose = NeonButton(text="Select file", outline=CYAN, color=rgba(CYAN))
        cancel.bind(on_release=popup.dismiss)
        choose.bind(on_release=lambda *_: (popup.dismiss(), self.file_selected(chooser.selection, kind)))
        row.add_widget(cancel)
        row.add_widget(choose)
        layout.add_widget(row)
        popup.content = layout
        popup.open()

    def _on_native_picker_result(self, request_code, result_code, intent):
        # Android camera activities return here as well as the media picker.
        if request_code in (self._native_camera_photo_request_code, self._native_camera_video_request_code):
            if result_code != -1 or intent is None:
                return
            try:
                if request_code == self._native_camera_photo_request_code:
                    extras = intent.getExtras()
                    bitmap = extras.get("data") if extras is not None else None
                    if bitmap is None:
                        self.message("Photo not returned", "The camera did not return a photo. Try Photo / Video Upload if needed.")
                        return
                    path = os.path.join(self.data_dir, "camera_" + str(int(time.time() * 1000)) + ".jpg")
                    stream = autoclass("java.io.FileOutputStream")(path)
                    BitmapCompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
                    bitmap.compress(BitmapCompressFormat.JPEG, 95, stream)
                    stream.flush()
                    stream.close()
                else:
                    uri = intent.getData()
                    if uri is None:
                        self.message("Video not returned", "The camera did not return a video file.")
                        return
                    resolver = self._android_activity.getContentResolver()
                    mime = resolver.getType(uri) or "video/mp4"
                    extension = {"video/mp4": ".mp4", "video/3gpp": ".3gp", "video/quicktime": ".mov"}.get(mime, ".mp4")
                    path = os.path.join(self.data_dir, "camera_" + str(int(time.time() * 1000)) + extension)
                    stream = resolver.openInputStream(uri)
                    if stream is None:
                        raise IOError("Android could not read the recorded video")
                    output = open(path, "wb")
                    buffer = jarray.zeros(8192, "b")
                    try:
                        while True:
                            count = stream.read(buffer)
                            if count == -1:
                                break
                            output.write(bytes((int(value) & 255) for value in buffer[:count]))
                    finally:
                        stream.close()
                        output.close()
                Clock.schedule_once(lambda *_: self.file_selected([path]), 0)
            except Exception as error:
                self.message("Camera result failed", "Could not import the camera result. Try Photo / Video Upload instead.\n" + str(error))
            return
        if request_code != self._native_picker_request_code:
            return
        callback = self._native_picker_callback
        kind = self._native_picker_kind
        self._native_picker_callback = None
        if callback is None:
            return
        if result_code != -1 or intent is None:
            # Cancelled selection: return without changing or deleting any existing posts.
            return
        try:
            uri = intent.getData()
            if uri is None:
                return
            resolver = self._android_activity.getContentResolver()
            name = self._native_uri_name(resolver, uri)
            extension = os.path.splitext(name)[1].lower()
            if not extension:
                mime = resolver.getType(uri) or ""
                extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
                             "video/mp4": ".mp4", "video/quicktime": ".mov",
                             "video/3gpp": ".3gp", "application/pdf": ".pdf"}.get(mime, ".bin")
            destination = os.path.join(self.data_dir, "selected_" + str(int(time.time() * 1000)) + extension)
            stream = resolver.openInputStream(uri)
            if stream is None:
                raise IOError("Android could not open the selected file")
            try:
                output = autoclass("java.io.ByteArrayOutputStream")()
                buffer = jarray.zeros(8192, "b")
                while True:
                    count = stream.read(buffer)
                    if count == -1:
                        break
                    output.write(buffer, 0, count)
                data = output.toByteArray()
                with open(destination, "wb") as output_file:
                    output_file.write(bytes((int(value) & 255) for value in data))
                output.close()
            finally:
                stream.close()
            if kind == "profile_image":
                callback([destination])
            else:
                callback([destination], kind)
        except Exception:
            self.message("Selection failed", "Could not read that item. Please choose it again.")

    def _native_uri_name(self, resolver, uri):
        try:
            OpenableColumns = autoclass("android.provider.OpenableColumns")
            cursor = resolver.query(uri, None, None, None, None)
            if cursor is not None:
                try:
                    if cursor.moveToFirst():
                        index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if index >= 0:
                            return str(cursor.getString(index))
                finally:
                    cursor.close()
        except Exception:
            pass
        return "selected_file"

    def file_selected(self, selection, kind="media"):
        if not selection:
            return
        path = selection[0]
        if not os.path.isfile(path):
            self.message("Unsupported file", "Choose a valid media file.")
            return
        extension = os.path.splitext(path)[1].lower()
        # Documents are currently represented as document entries; media uploads remain unchanged.
        if kind == "document":
            try:
                destination = os.path.join(self.data_dir, "document_" + str(int(time.time() * 1000)) + extension)
                if os.path.abspath(path) != os.path.abspath(destination):
                    shutil.copy2(path, destination)
                key = "document:" + destination
                self.post_documents[key] = os.path.basename(path)
                self.posts.append(key)
                self._save_data()
                self.message("Document Added", "Document added to your posts.")
            except Exception as error:
                self.message("Upload failed", str(error))
            return
        if extension not in ALL_MEDIA:
            self.message("Unsupported media format", "Choose a supported image or video file.")
            return
        try:
            destination = os.path.join(self.data_dir, "post_" + str(int(time.time() * 1000)) + extension)
            if os.path.abspath(path) != os.path.abspath(destination):
                shutil.copy2(path, destination)
            if destination not in self.posts:
                self.posts.append(destination)
            self.ask_post_caption(destination)
        except Exception as error:
            self.message("Upload failed", str(error))

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
        row.add_widget(draft_btn)
        row.add_widget(post_btn)
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
            for comment in previous[-15:]:
                history.add_widget(Label(text="Chat: " + comment, color=rgba(WHITE),
                                         size_hint_y=None, height=dp(34),
                                         halign="left", valign="middle"))
            view.add_widget(history)
            layout.add_widget(view)
        entry = RoundedInput(hint_text="Write a comment...", multiline=True,
                             size_hint_y=None, height=dp(80))
        layout.add_widget(entry)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(7))
        popup = Popup(title="Comments", content=layout, size_hint=(.88, .70), pos_hint={'right': 0.98})
        cancel = NeonButton(text="Cancel", outline="#343440", color=rgba(WHITE))
        send = NeonButton(text="Send", outline=CYAN, color=rgba(CYAN))
        cancel.bind(on_release=popup.dismiss)
        def submit(*_):
            value = entry.text.strip()
            if value:
                self.comments.setdefault(path, []).append(value[:500])
                self._save_data()
                popup.dismiss()
                self.show_feed()
            else:
                entry.hint_text = "Type a comment first"
        send.bind(on_release=submit)
        row.add_widget(cancel)
        row.add_widget(send)
        layout.add_widget(row)
        popup.open()

    def share_options(self, path):
        popup = Popup(title="Share post", size_hint=(.9, None), height=dp(280))
        layout = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        layout.add_widget(Label(text=os.path.basename(path),
                                color=rgba(CYAN), size_hint_y=None, height=dp(32)))
        copy_path = NeonButton(text="File details", outline=CYAN, color=rgba(CYAN))
        save_copy = NeonButton(text="Copy to share folder", outline=PURPLE, color=rgba(PURPLE))
        close = NeonButton(text="Close", outline="#343440", color=rgba(WHITE))
        copy_path.bind(on_release=lambda *_: (popup.dismiss(), self.message("Local file", path)))
        def copy_to_share(*_):
            try:
                folder = os.path.join(self.data_dir, "shared_posts")
                os.makedirs(folder, exist_ok=True)
                target = os.path.join(folder, os.path.basename(path))
                shutil.copy2(path, target)
                popup.dismiss()
                self.message("Ready to share", "Saved to:\n" + target)
            except Exception as error:
                popup.dismiss()
                self.message("Share failed", str(error))
        save_copy.bind(on_release=copy_to_share)
        close.bind(on_release=popup.dismiss)
        for b in (copy_path, save_copy, close):
            layout.add_widget(b)
        popup.content = layout
        popup.open()

    def show_profile(self):
        self.active_page = "Profile"
        self.clear_content()
        profile_root = FloatLayout()
        if self.profile_bg_picture and os.path.isfile(self.profile_bg_picture):
            try:
                bg_img = Image(source=self.profile_bg_picture, allow_stretch=True, keep_ratio=False,
                               size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
                               color=(1, 1, 1, max(0, min(1, self.profile_bg_opacity))))
                profile_root.add_widget(bg_img)
            except Exception:
                pass
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        body = BoxLayout(orientation="vertical", size_hint_y=None,
                         spacing=dp(12), padding=(dp(8), dp(8), dp(8), dp(18)))
        body.bind(minimum_height=body.setter("height"))
        banner = FloatLayout(size_hint_y=None, height=dp(180))
        if self.banner_picture and os.path.isfile(self.banner_picture):
            try:
                image = Image(source=self.banner_picture, allow_stretch=True, keep_ratio=False,
                              size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
                              color=(1, 1, 1, max(0, min(1, self.banner_opacity))))
                banner.add_widget(image)
            except Exception:
                pass
        banner.add_widget(Label(text="[b]SAM NG[/b]", markup=True,
                                color=rgba(WHITE), font_size="20sp",
                                pos_hint={"center_x": .5, "center_y": .55}))
        body.add_widget(banner)
        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        back = CleanNavButton(text="< Back", size_hint_x=None, width=dp(60),
                              font_size="14sp", color=rgba(CYAN), bold=True)
        back.bind(on_release=lambda *_: self.navigate("Home"))
        header.add_widget(back)
        header.add_widget(Label(text="PROFILE", color=rgba(CYAN),
                                bold=True, font_size="18sp", halign="left"))
        edit = NeonButton(text="Edit", size_hint_x=None, width=dp(50),
                          outline=PURPLE, color=rgba(PURPLE), font_size="13sp")
        edit.bind(on_release=lambda *_: self.edit_profile())
        header.add_widget(edit)
        settings_button = CleanNavButton(text="...", size_hint_x=None, width=dp(40),
                                         font_size="20sp", color=rgba(PURPLE), bold=True)
        settings_button.bind(on_release=lambda *_: self.show_settings())
        header.add_widget(settings_button)
        body.add_widget(header)
        identity = BoxLayout(size_hint_y=None, height=dp(90), spacing=dp(12))
        avatar = FloatLayout(size_hint_x=None, width=dp(80))
        if self.profile_picture and os.path.isfile(self.profile_picture):
            avatar.add_widget(Image(source=self.profile_picture,
                                    allow_stretch=True, keep_ratio=False, size_hint=(None, None),
                                    size=(dp(70), dp(70)),
                                    pos_hint={"center_x": .5, "center_y": .5}))
        else:
            avatar.add_widget(Label(text=self.profile_name[:1].upper() or "S",
                                    color=rgba(CYAN), bold=True, font_size="28sp",
                                    pos_hint={"center_x": .5, "center_y": .5}))
        details = BoxLayout(orientation="vertical", spacing=dp(2))
        details.add_widget(Label(text=self.profile_name, color=rgba(WHITE),
                                 bold=True, font_size="20sp", halign="left"))
        details.add_widget(Label(text="@" + self.username, color=rgba(CYAN),
                                 font_size="13sp", halign="left"))
        details.add_widget(Label(text=self.bio, color=rgba(GREY),
                                 font_size="12sp", halign="left"))
        identity.add_widget(avatar)
        identity.add_widget(details)
        body.add_widget(identity)
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
            # Photos and videos appear together in a three-column grid.
            active_list = self.posts
        elif self.profile_tab == "Videos":
            active_list = [
                path for path in self.posts
                if os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS
            ]
        elif self.profile_tab == "Saved":
            active_list = list(self.saved)
        elif self.profile_tab == "Private":
            active_list = self.private_posts
        if active_list:
            grid = GridLayout(cols=3, spacing=dp(6), size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            for path in reversed(active_list):
                if path.startswith("document:") or os.path.isfile(path):
                    tile = NeonButton(text="Doc" if path.startswith("document:") else "",
                                      outline=unique_accent(path), color=rgba(WHITE), radius=6,
                                      size_hint_y=None, height=dp(110))
                    if not path.startswith("document:"):
                        try:
                            ext = os.path.splitext(path)[1].lower()
                            if ext in VIDEO_EXTENSIONS:
                                tile.text = "Video"
                            else:
                                tile.add_widget(Image(source=path, allow_stretch=True, keep_ratio=False))
                        except Exception:
                            tile.text = "Media"
                    tile.bind(on_release=lambda _b, p=path: self.open_profile_post(p))
                    grid.add_widget(tile)
            body.add_widget(grid)
        else:
            body.add_widget(Label(text=f"No {self.profile_tab.lower()} items available.",
                                  color=rgba(GREY), size_hint_y=None, height=dp(60)))
        scroll.add_widget(body)
        profile_root.add_widget(scroll)
        self.content.add_widget(profile_root)

    def change_profile_tab(self, tab_name):
        self.profile_tab = tab_name
        self.show_profile()

    def open_profile_post(self, path):
        if path.startswith("document:"):
            self.message("Attached document", self.post_documents.get(path, "Document"))
            return
        self.clear_content()
        self.content.add_widget(self.make_post_card(path))

    def choose_image(self, callback):
        if self._android_activity is not None and autoclass:
            try:
                Intent = autoclass("android.content.Intent")
                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType("image/*")
                self._native_picker_callback = lambda selection, _kind="profile_image": callback(selection)
                self._native_picker_kind = "profile_image"
                self._android_activity.startActivityForResult(intent, self._native_picker_request_code)
                return
            except Exception:
                self._native_picker_callback = None
        if filechooser:
            try:
                filechooser.open_file(on_selection=callback,
                                      filters=[["Images", "*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp", "*.gif"]])
                return
            except Exception:
                pass
        popup = Popup(title="Choose image", size_hint=(.96, .88))
        layout = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        chooser = FileChooserListView(path="/storage/emulated/0",
                                      filters=["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp", "*.gif"])
        layout.add_widget(chooser)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        cancel = NeonButton(text="Cancel", outline="#343440", color=rgba(WHITE))
        use = NeonButton(text="Use image", outline=CYAN, color=rgba(CYAN))
        cancel.bind(on_release=popup.dismiss)
        use.bind(on_release=lambda *_: (popup.dismiss(), callback(chooser.selection)))
        row.add_widget(cancel)
        row.add_widget(use)
        layout.add_widget(row)
        popup.content = layout
        popup.open()

    def edit_profile(self):
        layout = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        name = RoundedInput(text=self.profile_name, hint_text="Display name (1x every 7 days)", multiline=False, size_hint_y=None, height=dp(46))
        username = RoundedInput(text=self.username, hint_text="Username (1x every 30 days)", multiline=False, size_hint_y=None, height=dp(46))
        bio = RoundedInput(text=self.bio, hint_text="Bio (Change anytime)", multiline=False, size_hint_y=None, height=dp(46))
        for field in (name, username, bio):
            layout.add_widget(field)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        popup = Popup(title="Edit profile", content=layout, size_hint=(.92, None), height=dp(440))
        photo = NeonButton(text="Change Profile Picture", outline=CYAN, color=rgba(CYAN),
                           size_hint_y=None, height=dp(42))
        banner = NeonButton(text="Change Profile Banner", outline=PURPLE, color=rgba(PURPLE),
                            size_hint_y=None, height=dp(42))
        background = NeonButton(text="Choose Profile Background", outline=PINK, color=rgba(PINK),
                                size_hint_y=None, height=dp(42))
        photo.bind(on_release=lambda *_: (popup.dismiss(), self.choose_image(self.set_profile_picture)))
        banner.bind(on_release=lambda *_: (popup.dismiss(), self.choose_image(self.set_banner_picture)))
        background.bind(on_release=lambda *_: (popup.dismiss(), self.choose_image(self.set_profile_bg_picture)))
        layout.add_widget(photo)
        layout.add_widget(banner)
        layout.add_widget(background)
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
                    self.message("Name Locked", f"Display name can only be updated once every 7 days. Try again in {rem_days} day(s).")
                    return
                self.profile_name = new_name
                self.last_name_change = now
            if new_user != self.username:
                if now - self.last_username_change < THIRTY_DAYS_SEC:
                    rem_days = int((THIRTY_DAYS_SEC - (now - self.last_username_change)) / 86400) + 1
                    self.message("Username Locked", f"Username can only be updated once every 30 days. Try again in {rem_days} day(s).")
                    return
                self.username = new_user
                self.last_username_change = now
            self.bio = bio.text.strip()[:160]
            self._save_data()
            app = App.get_running_app()
            app.username = self.username
            popup.dismiss()
            if "Profile" in self.nav_buttons:
                self.update_nav_avatar(self.nav_buttons["Profile"])
            self.show_profile()
        save.bind(on_release=save_details)
        row.add_widget(cancel)
        row.add_widget(save)
        layout.add_widget(row)
        popup.open()

    def set_profile_picture(self, selection):
        if not selection:
            return
        self.profile_picture = self._copy_profile_image(selection[0], "profile_picture")
        self._save_data()
        if "Profile" in self.nav_buttons:
            self.update_nav_avatar(self.nav_buttons["Profile"])
        self.show_profile()

    def set_banner_picture(self, selection):
        if not selection:
            return
        self.banner_picture = self._copy_profile_image(selection[0], "profile_banner")
        self._save_data()
        self.show_profile()

    def set_profile_bg_picture(self, selection):
        if not selection:
            return
        self.profile_bg_picture = self._copy_profile_image(selection[0], "profile_bg")
        self._save_data()
        self.show_profile()

    def _copy_profile_image(self, path, prefix):
        try:
            ext = os.path.splitext(path)[1].lower()
            target = os.path.join(self.data_dir, prefix + ext)
            if os.path.abspath(path) != os.path.abspath(target):
                shutil.copy2(path, target)
            return target
        except Exception:
            return path

    def show_settings(self):
        self.active_page = "Settings"
        self.clear_content()
        self.page_title("SETTINGS", PURPLE, "Profile")
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(12))
        body.bind(minimum_height=body.setter("height"))
        scroll.add_widget(body)
        self.content.add_widget(scroll)
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
        disp_row.add_widget(btn_name)
        disp_row.add_widget(btn_user)
        body.add_widget(disp_row)
        body.add_widget(Label(text="ACCOUNT MANAGEMENT", color=rgba(CYAN), bold=True, size_hint_y=None, height=dp(30), halign="left"))
        logout_btn = NeonButton(text="Log Out", size_hint_y=None, height=dp(42), outline=PINK, color=rgba(PINK))
        logout_btn.bind(on_release=lambda *_: self.handle_logout())
        body.add_widget(logout_btn)
        switch_acc_btn = NeonButton(text="Change Account", size_hint_y=None, height=dp(42), outline=PURPLE, color=rgba(WHITE))
        switch_acc_btn.bind(on_release=lambda *_: self.handle_logout())
        body.add_widget(switch_acc_btn)
        body.add_widget(Label(text="SEARCH HISTORY & TRASH BIN", color=rgba(YELLOW), bold=True, size_hint_y=None, height=dp(30), halign="left"))
        hist_str = ", ".join(self.search_history[:5]) if self.search_history else "No history yet"
        body.add_widget(Label(text=f"Recent Searches: {hist_str}", color=rgba(WHITE), size_hint_y=None, height=dp(26), halign="left"))
        body.add_widget(Label(text=f"Trash Bin Items: {len(self.deleted_posts)} (Auto-purged in 7 days)", color=rgba(GREY), size_hint_y=None, height=dp(26), halign="left"))
        body.add_widget(Label(text="HELP & ABOUT APP", color=rgba(PINK), bold=True, size_hint_y=None, height=dp(30), halign="left"))
        for item_title, desc in [
            ("Help & Support", "FAQs, feedback and technical support."),
            ("Privacy Policy", "Read the full SAM NG privacy policy."),
            ("About SAM NG", "SAM NG — local prototype.")
        ]:
            b = NeonButton(text=item_title, size_hint_y=None, height=dp(40), outline="#343440", color=rgba(WHITE))
            if item_title == "Privacy Policy":
                b.bind(on_release=lambda *_: self.show_privacy_policy())
            else:
                b.bind(on_release=lambda _, t=item_title, d=desc: self.message(t, d))
            body.add_widget(b)

    def show_privacy_policy(self):
        """Display the complete policy in a scrollable in-app window."""
        popup = Popup(title="SAM NG Privacy Policy", size_hint=(.94, .88), auto_dismiss=True)
        outer = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        policy_label = Label(text=PRIVACY_POLICY, color=rgba(WHITE), font_size="13sp",
                             size_hint_y=None, halign="left", valign="top", padding=(dp(6), dp(6)))
        policy_label.bind(width=lambda w, width: setattr(w, "text_size", (max(1, width - dp(12)), None)))
        policy_label.bind(texture_size=lambda w, size: setattr(w, "height", size[1] + dp(16)))
        scroll.add_widget(policy_label)
        outer.add_widget(scroll)
        close = NeonButton(text="Close", size_hint_y=None, height=dp(44), outline=CYAN, color=rgba(CYAN))
        close.bind(on_release=popup.dismiss)
        outer.add_widget(close)
        popup.content = outer
        popup.open()

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
        self.title = "SAM NG"
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
