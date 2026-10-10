from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle,Line
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.video import Video
from kivy.uix.progressbar import ProgressBar
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
import os
import json
import random

try:
    from jnius import autoclass
    from android import activity
    ANDROID_PICKER_AVAILABLE = True
except Exception:
    autoclass = None
    activity = None
    ANDROID_PICKER_AVAILABLE = False

BG = "#050508"
PANEL = "#101018"
CYAN = "#00F5E9"
PINK = "#FF286F"
WHITE = "#FFFFFF"
GREY = "#92929D"
DARK = "#0b0d12"

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".3gp", ".m4v")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")

APP_STATE_FILE = "samng_state.json"


def rgba(value):
    return get_color_from_hex(value)


class DataStore:
    def __init__(self, app):
        self.app = app
        self.path = os.path.join(app.user_data_dir, APP_STATE_FILE)

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "logged_in": False,
            "current_user": "",
            "users": {},
            "posts": []
        }

    def save(self, state):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)


class NeonSpinner(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.angle = 0
        self.bind(pos=self.draw_spinner, size=self.draw_spinner)
        Clock.schedule_interval(self.rotate, 1 / 30)

    def rotate(self, dt):
        self.angle = (self.angle + 8) % 360
        self.draw_spinner()

    def draw_spinner(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*rgba(CYAN))
            self.canvas.add(
                Line(
                    circle=(self.center_x, self.center_y,
                            min(self.width, self.height) * 0.35,
                            self.angle, self.angle + 255),
                    width=dp(3)
                )
            )
            Color(*rgba(PINK))
            self.canvas.add(
                Line(
                    circle=(self.center_x, self.center_y,
                            min(self.width, self.height) * 0.23,
                            -self.angle, -self.angle + 95),
                    width=dp(2)
                )
            )


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = FloatLayout()
        self.add_widget(root)

        with root.canvas.before:
            Color(*rgba(BG))
            bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, v: setattr(bg, "pos", v),
                  size=lambda w, v: setattr(bg, "size", v))

        title = Label(text="SAM NG", color=rgba(CYAN), font_size="28sp", bold=True)
        title.pos_hint = {"center_x": 0.5, "center_y": 0.83}
        root.add_widget(title)

        box = BoxLayout(orientation="vertical", size_hint=(0.8, None), height=dp(230), pos_hint={"center_x": 0.5, "center_y": 0.50})
        box.spacing = dp(12)

        self.username = TextInput(hint_text="Username", multiline=False, write_tab=False)
        self.password = TextInput(hint_text="Password", multiline=False, password=True, write_tab=False)

        for field in (self.username, self.password):
            field.background_color = rgba(PANEL)
            field.foreground_color = rgba(WHITE)
            field.hint_text_color = rgba(GREY)
            field.cursor_color = rgba(CYAN)
            field.padding = [dp(16), dp(12), dp(16), dp(12)]
            field.size_hint_y = None
            field.height = dp(52)
            box.add_widget(field)

        btn = Button(
            text="Login",
            background_normal="",
            background_color=rgba(CYAN),
            color=rgba(BG),
            bold=True,
            font_size="18sp",
            size_hint_y=None,
            height=dp(56)
        )
        btn.bind(on_release=self.login)
        box.add_widget(btn)

        root.add_widget(box)

    def login(self, *args):
        username = self.username.text.strip()
        password = self.password.text.strip()
        if not username or not password:
            self.show_message("Please enter username and password")
            return

        state = self.manager.app.state
        if username not in state["users"]:
            state["users"][username] = {
                "password": password,
                "name": username,
                "bio": "Welcome to Sam Ng",
                "avatar": "",
                "banner": "",
                "likes": 0,
                "followers": 0,
                "following": 0
            }
        state["current_user"] = username
        state["logged_in"] = True
        self.manager.app.save_state()
        self.manager.current = "home"

    def show_message(self, message):
        popup = Popup(title="Login", content=Label(text=message, color=rgba(WHITE)), size_hint=(0.7, 0.25))
        popup.open()


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_text = ""
        self.posts = []
        self.recommendations = [
            {"author": "Ari", "tag": "travel"},
            {"author": "Nia", "tag": "music"},
            {"author": "Jules", "tag": "nature"},
            {"author": "Kian", "tag": "video"}
        ]

        self.build_ui()

    def build_ui(self):
        root = FloatLayout()
        self.add_widget(root)

        with root.canvas.before:
            Color(*rgba(BG))
            bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda w, v: setattr(bg, "pos", v),
                  size=lambda w, v: setattr(bg, "size", v))

        # top search + profile avatar
        top = BoxLayout(size_hint=(1, None), height=dp(58), pos_hint={"top": 1}, padding=(dp(16), dp(4)), spacing=dp(12))
        self.search = TextInput(hint_text="Search", multiline=False, write_tab=False)
        self.search.background_color = rgba(PANEL)
        self.search.foreground_color = rgba(WHITE)
        self.search.hint_text_color = rgba(GREY)
        self.search.cursor_color = rgba(CYAN)
        self.search.size_hint_x = 0.75
        self.search.bind(text=self.on_search)
        top.add_widget(self.search)

        avatar_btn = Button(
            text="S",
            background_normal="",
            background_color=rgba(CYAN),
            color=rgba(BG),
            bold=True,
            font_size="22sp",
            size_hint_x=None,
            width=dp(46),
            height=dp(46)
        )
        avatar_btn.bind(on_release=lambda *_: self.manager.current = "profile")
        top.add_widget(avatar_btn)
        root.add_widget(top)

        # feed area
        self.feed_container = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=dp(12), padding=(dp(10), dp(8)))
        self.feed_container.bind(minimum_height=self.feed_container.setter("height"))

        scroll = ScrollView(do_scroll_x=False, size_hint=(1, 0.78), pos_hint={"top": 0.88})
        scroll.add_widget(self.feed_container)
        root.add_widget(scroll)

        # plus nav
        nav = BoxLayout(size_hint=(1, None), height=dp(80), pos_hint={"x": 0, "y": 0})
        nav.padding = (dp(10), dp(10))
        nav.spacing = dp(8)

        for name, color in [("Home", CYAN), ("Friends", WHITE), ("Create", CYAN), ("Inbox", WHITE), ("Profile", WHITE)]:
            btn = Button(
                text=name if name != "Create" else "",
                background_normal="",
                background_color=rgba(BG),
                color=rgba(color),
                font_size="16sp",
                bold=True,
                size_hint_x=1
            )
            if name == "Create":
                btn.text = "+"
                btn.font_size = "30sp"
                btn.background_color = rgba(BG)
                btn.color = rgba(CYAN)
                btn.border = (0, 0, 0, 0)
            btn.bind(on_release=lambda *_ , n=name: self.on_nav(n))
            nav.add_widget(btn)
        root.add_widget(nav)

        self.refresh_feed()

    def on_nav(self, name):
        if name == "Create":
            self.open_create_menu()
        elif name == "Profile":
            self.manager.current = "profile"
        elif name == "Home":
            self.refresh_feed()
        else:
            self.show_message(f"{name} coming soon")

    def show_message(self, message):
        popup = Popup(title="Sam Ng", content=Label(text=message, color=rgba(WHITE)), size_hint=(0.7, 0.25))
        popup.open()

    def on_search(self, instance, value):
        self.search_text = value.lower()
        self.refresh_feed()

    def refresh_feed(self):
        self.feed_container.clear_widgets()
        state = self.manager.app.state
        posts = []
        for post in state["posts"]:
            if self.search_text:
                haystack = f"{post.get('caption','')} {post.get('tags','')} {post.get('author','')}".lower()
                if self.search_text not in haystack:
                    continue
            posts.append(post)

        if not posts:
            empty_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(250), spacing=dp(14), padding=dp(18))
            empty_box.add_widget(Label(text="Your feed starts here", color=rgba(WHITE), font_size="26sp"))
            empty_box.add_widget(Label(text="Tap Create to add a photo or video.", color=rgba(GREY), font_size="18sp"))
            create_btn = Button(
                text="+ Create a post",
                background_normal="",
                background_color=rgba(BG),
                color=rgba(CYAN),
                font_size="22sp",
                bold=True,
                size_hint=(None, None),
                size=(dp(260), dp(84))
            )
            create_btn.bind(on_release=lambda *_: self.open_create_menu())
            empty_box.add_widget(create_btn)
            self.feed_container.add_widget(empty_box)
            return

        for post in reversed(posts):
            self.feed_container.add_widget(self.make_post_card(post))

        rec = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(220), spacing=dp(8), padding=dp(10))
        rec.add_widget(Label(text="Recommended for you", color=rgba(CYAN), font_size="18sp", bold=True))
        for r in self.recommendations:
            row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
            avatar = Button(text="C", background_normal="", background_color=rgba(CYAN), color=rgba(BG), size_hint_x=None, width=dp(38))
            row.add_widget(avatar)
            row.add_widget(Label(text=f"{r['author']} • {r['tag']}", color=rgba(WHITE), font_size="16sp"))
            rec.add_widget(row)
        self.feed_container.add_widget(rec)

    def make_post_card(self, post):
        card = FloatLayout(size_hint_y=None, height=dp(520), padding=dp(8))
        with card.canvas.before:
            Color(*rgba(DARK))
            rect = Rectangle(pos=card.pos, size=card.size)
        card.bind(pos=lambda w, v: setattr(rect, "pos", v),
                  size=lambda w, v: setattr(rect, "size", v))

        header = BoxLayout(size_hint=(1, None), height=dp(42), pos_hint={"x": 0, "top": 1}, padding=(dp(8), 0))
        avatar = Button(text="S", background_normal="", background_color=rgba(CYAN), color=rgba(BG), size_hint_x=None, width=dp(36))
        user_name = Label(text=post.get("author", "Sam Ng"), color=rgba(WHITE), bold=True, font_size="18sp")
        header.add_widget(avatar)
        header.add_widget(user_name)
        card.add_widget(header)

        media_area = FloatLayout(size_hint=(1, 0.78), pos_hint={"x": 0, "y": 0.13})
        media_path = post.get("path")
        if media_path and os.path.exists(media_path):
            ext = os.path.splitext(media_path)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                video = Video(source=media_path, state="play", options={"eos": "loop"}, allow_stretch=True, keep_ratio=True)
                video.size_hint = (1, 1)
                video.pos_hint = {"center_x": 0.5, "center_y": 0.5}
                media_area.add_widget(video)
            else:
                img = Image(source=media_path, allow_stretch=True, keep_ratio=True)
                img.size_hint = (1, 1)
                img.pos_hint = {"center_x": 0.5, "center_y": 0.5}
                media_area.add_widget(img)
        else:
            media_area.add_widget(Label(text="No media", color=rgba(GREY), pos_hint={"center_x": 0.5, "center_y": 0.5}))
        card.add_widget(media_area)

        # Right-side vertical action buttons
        actions = BoxLayout(orientation="vertical", size_hint=(None, None), size=(dp(68), dp(180)), pos_hint={"right": 0.98, "center_y": 0.48}, spacing=dp(8))
        for label, color in [("♡", PINK), ("💬", WHITE), ("↗", CYAN), ("⋯", GREY)]:
            btn = Button(text=label, background_normal="", background_color=rgba(PANEL), color=rgba(color), font_size="20sp", size_hint=(None, None), size=(dp(46), dp(42)))
            actions.add_widget(btn)
        card.add_widget(actions)

        caption = Label(text=post.get("caption", ""), color=rgba(WHITE), font_size="16sp", halign="left", valign="middle", size_hint=(1, None), height=dp(30), pos_hint={"x": 0.02, "top": 0.12})
        card.add_widget(caption)

        return card

    def open_create_menu(self):
        popup = ModalView(size_hint=(0.9, 0.5), auto_dismiss=True)
        panel = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        with panel.canvas.before:
            Color(*rgba(PANEL))
            rect = Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(pos=lambda w, v: setattr(rect, "pos", v),
                   size=lambda w, v: setattr(rect, "size", v))

        panel.add_widget(Label(text="Create new post", color=rgba(CYAN), font_size="24sp", bold=True))
        panel.add_widget(Button(text="Take photo", background_normal="", background_color=rgba(BG), color=rgba(CYAN), on_release=lambda *_: (popup.dismiss(), self.choose_image(kind="photo"))))
        panel.add_widget(Button(text="Record video", background_normal="", background_color=rgba(BG), color=rgba(CYAN), on_release=lambda *_: (popup.dismiss(), self.choose_image(kind="video"))))
        panel.add_widget(Button(text="Choose from gallery", background_normal="", background_color=rgba(BG), color=rgba(CYAN), on_release=lambda *_: (popup.dismiss(), self.pick_media(kind="gallery"))))
        close = Button(text="Cancel", background_normal="", background_color=rgba(BG), color=rgba(WHITE))
        close.bind(on_release=popup.dismiss)
        panel.add_widget(close)
        popup.add_widget(panel)
        popup.open()

    def choose_image(self, kind="photo"):
        self.show_message("Camera capture is available on Android when permissions are granted.")
        self.pick_media(kind="camera" if kind == "photo" else "video")

    def pick_media(self, kind="gallery"):
        if ANDROID_PICKER_AVAILABLE:
            try:
                Intent = autoclass("android.content.Intent")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType("*/*")
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                mime_types = ["image/*", "video/*"]
                if kind == "video":
                    mime_types = ["video/*"]
                elif kind == "photo":
                    mime_types = ["image/*"]
                intent.putExtra(Intent.EXTRA_MIME_TYPES, mime_types)
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                PythonActivity.mActivity.startActivityForResult(intent, 9999)
                return
            except Exception as e:
                self.show_message("Media picker error: " + str(e))
                return
        self.show_message("Gallery picker needs Android runtime support.")

    def on_android_activity_result(self, request_code, result_code, intent):
        if request_code != 9999:
            return
        try:
            Activity = autoclass("android.app.Activity")
            if result_code != Activity.RESULT_OK or intent is None:
                return
            uri = intent.getData()
            if uri is None:
                return
            path = self.copy_uri_to_cache(uri)
            if path and os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                kind = "video" if ext in VIDEO_EXTENSIONS else "image"
                self.save_post(path, kind)
                self.refresh_feed()
        except Exception:
            pass

    def copy_uri_to_cache(self, uri):
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity_instance = PythonActivity.mActivity
            resolver = activity_instance.getContentResolver()
            input_stream = resolver.openInputStream(uri)
            if input_stream is None:
                return None
            cache_dir = os.path.join(self.manager.app.user_data_dir, "posts")
            os.makedirs(cache_dir, exist_ok=True)
            display_name = "upload_" + str(int(Clock.get_time() * 1000))
            kind = resolver.getType(uri) or ""
            ext = ".jpg"
            if "video" in kind:
                ext = ".mp4"
            elif "image" in kind:
                ext = ".jpg"
            path = os.path.join(cache_dir, display_name + ext)
            with open(path, "wb") as out:
                out.write(input_stream.read())
            return path
        except Exception:
            return None

    def save_post(self, path, kind):
        state = self.manager.app.state
        user = state["current_user"]
        post = {
            "id": str(random.randint(1000, 999999)),
            "author": user,
            "path": path,
            "kind": kind,
            "caption": "New post",
            "tags": "general",
            "likes": 0,
            "comments": 0
        }
        state["posts"].append(post)
        self.manager.app.save_state()


class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        banner = BoxLayout(size_hint_y=None, height=dp(120))
        with banner.canvas.before:
            Color(*rgba(CYAN))
            rect = Rectangle(pos=banner.pos, size=banner.size)
        banner.bind(pos=lambda w, v: setattr(rect, "pos", v),
                    size=lambda w, v: setattr(rect, "size", v))
        banner.add_widget(Label(text="BANNER", color=rgba(BG), font_size="22sp", bold=True))
        root.add_widget(banner)

        info = BoxLayout(size_hint_y=None, height=dp(80), padding=(dp(16), dp(10)))
        avatar = Button(text="S", background_normal="", background_color=rgba(CYAN), color=rgba(BG), font_size="20sp", bold=True, size_hint_x=None, width=dp(54))
        user_name = Label(text="Sam Ng", color=rgba(WHITE), font_size="22sp", bold=True)
        info.add_widget(avatar)
        info.add_widget(user_name)
        root.add_widget(info)

        root.add_widget(Label(text="Your posts", color=rgba(CYAN), bold=True, font_size="18sp", size_hint_y=None, height=dp(30)))

        self.posts_area = BoxLayout(orientation="vertical", spacing=dp(10), padding=(dp(12), dp(10)))
        self.posts_area.bind(minimum_height=self.posts_area.setter("height"))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.posts_area)
        root.add_widget(scroll)

        back_btn = Button(text="Back", background_normal="", background_color=rgba(PANEL), color=rgba(WHITE), size_hint_y=None, height=dp(48))
        back_btn.bind(on_release=lambda *_: self.manager.current = "home")
        root.add_widget(back_btn)

        self.refresh_profile()

    def refresh_profile(self):
        self.posts_area.clear_widgets()
        state = self.manager.app.state
        posts = [p for p in state["posts"] if p.get("author") == state["current_user"]]
        if not posts:
            self.posts_area.add_widget(Label(text="No posts yet", color=rgba(GREY), font_size="18sp"))
            return
        for p in reversed(posts):
            tile = BoxLayout(size_hint_y=None, height=dp(110), spacing=dp(8))
            if p.get("kind") == "video":
                tile.add_widget(Label(text="VIDEO", color=rgba(CYAN), bold=True, font_size="18sp"))
            else:
                tile.add_widget(Label(text="PHOTO", color=rgba(CYAN), bold=True, font_size="18sp"))
            tile.add_widget(Label(text=p.get("caption", "New post"), color=rgba(WHITE), font_size="16sp"))
            self.posts_area.add_widget(tile)


class SamNgApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.store = DataStore(self)
        self.state = self.store.load()

    def save_state(self):
        self.store.save(self.state)

    def build(self):
        Window.clearcolor = rgba(BG)

        manager = ScreenManager(transition=FadeTransition(duration=0.22))
        self.login_screen = LoginScreen(name="login")
        self.home_screen = HomeScreen(name="home")
        self.profile_screen = ProfileScreen(name="profile")

        manager.add_widget(self.login_screen)
        manager.add_widget(self.home_screen)
        manager.add_widget(self.profile_screen)

        if self.state.get("logged_in", False):
            manager.current = "home"
        else:
            manager.current = "login"

        return manager


if __name__ == "__main__":
    SamNgApp().run()
