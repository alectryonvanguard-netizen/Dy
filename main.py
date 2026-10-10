from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image import Image
from kivy.uix.video import Video
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex
import os
import json

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

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".3gp", ".m4v")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")


def rgba(value):
    return get_color_from_hex(value)


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
                    circle=(
                        self.center_x, self.center_y,
                        min(self.width, self.height) * 0.35,
                        self.angle, self.angle + 255
                    ),
                    width=dp(3)
                )
            )
            Color(*rgba(PINK))
            self.canvas.add(
                Line(
                    circle=(
                        self.center_x, self.center_y,
                        min(self.width, self.height) * 0.23,
                        -self.angle, -self.angle + 95
                    ),
                    width=dp(2)
                )
            )


class WelcomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        self.add_widget(layout)

        with layout.canvas.before:
            Color(*rgba(BG))
            self.bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(
            pos=lambda obj, value: setattr(self.bg_rect, "pos", value),
            size=lambda obj, value: setattr(self.bg_rect, "size", value)
        )

        top = BoxLayout(size_hint_y=None, height=dp(58), pos_hint={"top": 1})
        top.add_widget(Label(text="8:44", color=rgba(WHITE), font_size="18sp", bold=True, halign="left"))
        top.add_widget(Label(text="", size_hint_x=1))
        top.add_widget(Label(text="55", color=rgba(WHITE), font_size="18sp", bold=True, halign="right"))
        layout.add_widget(top)

        tabs = BoxLayout(size_hint=(1, None), height=dp(60), pos_hint={"top": 0.92})
        tabs.add_widget(Label(text="STEM", color=rgba(WHITE), bold=True, font_size="18sp"))
        tabs.add_widget(Label(text="Following", color=rgba(WHITE), bold=True, font_size="18sp"))
        tabs.add_widget(Label(text="For You", color=rgba(CYAN), bold=True, font_size="18sp"))
        layout.add_widget(tabs)

        plus = Button(
            text="+",
            size_hint=(None, None),
            size=(dp(50), dp(50)),
            pos_hint={"right": 1, "top": 0.87},
            background_normal="",
            background_color=rgba(BG),
            color=rgba(CYAN),
            font_size="34sp"
        )
        plus.bind(on_release=lambda *_: self.manager.current = "home")
        layout.add_widget(plus)

        hero = BoxLayout(size_hint=(1, None), height=dp(200), pos_hint={"top": 0.75})
        hero.add_widget(Label(
            text="DREAM\nBUILD\nGROW",
            color=rgba(WHITE), font_size="26sp", bold=True, halign="left",
            valign="middle", text_size=(dp(150), dp(200))
        ))
        layout.add_widget(hero)

        title = Label(
            text="SAM NG DVSG SG",
            color=rgba(CYAN), bold=True, font_size="26sp",
            pos_hint={"center_x": 0.5, "center_y": 0.58}
        )
        layout.add_widget(title)

        headline = Label(
            text="S íś fôř ýöü.",
            color=rgba(WHITE), bold=True, font_size="42sp",
            pos_hint={"center_x": 0.5, "center_y": 0.48}
        )
        layout.add_widget(headline)

        info1 = Label(
            text="Your feed starts here",
            color=rgba(WHITE), font_size="28sp",
            pos_hint={"center_x": 0.5, "center_y": 0.36}
        )
        layout.add_widget(info1)

        info2 = Label(
            text="Tap Create to add a photo or video.",
            color=rgba(GREY), font_size="18sp",
            pos_hint={"center_x": 0.5, "center_y": 0.30}
        )
        layout.add_widget(info2)

        create_btn = Button(
            text="+ Create a post",
            size_hint=(None, None),
            size=(dp(260), dp(90)),
            pos_hint={"center_x": 0.5, "center_y": 0.18},
            background_normal="",
            background_color=rgba(BG),
            color=rgba(CYAN),
            bold=True,
            font_size="22sp"
        )
        create_btn.bind(on_release=lambda *_: self.manager.current = "home")
        layout.add_widget(create_btn)

        bottom = BoxLayout(
            size_hint=(1, None), height=dp(90),
            pos_hint={"x": 0, "y": 0},
            spacing=dp(10), padding=(dp(12), dp(8))
        )
        for name in ("Home", "Friends", "Create", "Inbox", "Profile"):
            btn = Button(
                text=name,
                background_normal="",
                background_color=rgba(BG),
                color=rgba(CYAN if name == "Home" else WHITE),
                font_size="18sp",
                bold=True
            )
            btn.bind(on_release=lambda *_: self.manager.current = "home")
            bottom.add_widget(btn)
        layout.add_widget(bottom)


class HomeScreen(Screen):
    PICKER_REQUEST_CODE = 2468

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_path = None
        self.posts = []
        self.active_tab = "For You"
        self.recommendations = [
            {"title": "Creator spotlight", "kind": "similar"},
            {"title": "Trending nearby", "kind": "similar"}
        ]
        self.picker_popup = None
        self.is_liked = False
        self.is_saved = False
        self.comments = []
        self.dark_mode = True

        if ANDROID_PICKER_AVAILABLE:
            try:
                activity.bind(on_activity_result=self.on_android_activity_result)
            except Exception:
                pass

        outer = BoxLayout(orientation="vertical")
        self.add_widget(outer)

        with outer.canvas.before:
            Color(*rgba(BG))
            self.bg_rect = Rectangle(pos=outer.pos, size=outer.size)
        outer.bind(
            pos=lambda obj, value: setattr(self.bg_rect, "pos", value),
            size=lambda obj, value: setattr(self.bg_rect, "size", value)
        )

        top = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(20), padding=(dp(16), dp(8)))
        self.top_bar = top
        outer.add_widget(top)

        for name in ("STEM", "Following", "For You"):
            button = Button(
                text=name,
                background_normal="",
                background_color=rgba(BG),
                color=rgba(WHITE if name == "For You" else GREY),
                font_size="18sp",
                bold=True
            )
            button.bind(on_release=lambda btn, n=name: self.change_tab(n))
            top.add_widget(button)

        create_btn = Button(
            text="+", size_hint_x=None, width=dp(52),
            background_normal="", background_color=rgba(BG),
            color=rgba(CYAN), font_size="30sp", bold=True
        )
        create_btn.bind(on_release=lambda *_: self.pick_media())
        top.add_widget(create_btn)

        self.feed = BoxLayout(orientation="vertical", padding=(dp(14), dp(8)))
        outer.add_widget(self.feed)

        bottom = BoxLayout(
            size_hint_y=None, height=dp(90),
            spacing=dp(10), padding=(dp(12), dp(6))
        )
        for name in ("Home", "Friends", "Create", "Inbox", "Profile"):
            btn = Button(
                text=name,
                background_normal="",
                background_color=rgba(BG),
                color=rgba(CYAN if name == "Home" else WHITE),
                font_size="16sp",
                bold=True,
                border=(0, 0, 0, 0)
            )
            btn.bind(on_release=lambda *_: self.navigate(name))
            bottom.add_widget(btn)
        outer.add_widget(bottom)

        self.show_feed()

    def show_feed(self):
        self.feed.clear_widgets()
        banner = BoxLayout(size_hint_y=None, height=dp(120), padding=(dp(14), dp(10)))
        with banner.canvas.before:
            Color(*rgba("#0B1E2A"))
            banner_bg = Rectangle(pos=banner.pos, size=banner.size)
        banner.bind(pos=lambda w, v: setattr(banner_bg, "pos", v), size=lambda w, v: setattr(banner_bg, "size", v))
        banner.add_widget(Label(text="SAM NG DVSG SG", color=rgba(CYAN), font_size="24sp", bold=True))
        self.feed.add_widget(banner)

        self.feed.add_widget(Label(
            text="S íś fôř ýöü.",
            color=rgba(WHITE),
            font_size="38sp",
            bold=True,
            size_hint_y=None,
            height=dp(50)
        ))

        if not self.posts:
            empty = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(260), spacing=dp(14), padding=dp(18))
            empty.add_widget(Label(text="Your feed starts here", color=rgba(WHITE), font_size="26sp"))
            empty.add_widget(Label(text="Tap Create to add a photo or video.", color=rgba(GREY), font_size="18sp"))
            create_btn = Button(
                text="+ Create a post",
                size_hint=(None, None),
                size=(dp(260), dp(84)),
                background_normal="",
                background_color=rgba(BG),
                color=rgba(CYAN),
                font_size="22sp",
                bold=True
            )
            create_btn.bind(on_release=lambda *_: self.pick_media())
            empty.add_widget(create_btn)
            self.feed.add_widget(empty)
            return

        for post in reversed(self.posts):
            if os.path.isfile(post):
                self.feed.add_widget(self.make_post_card(post))
        self.feed.add_widget(self.make_recommendations_panel())

    def make_post_card(self, path):
        card = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(8))
        header = BoxLayout(size_hint_y=None, height=dp(50))
        avatar = Button(
            text="S", size_hint_x=None, width=dp(42), height=dp(42),
            background_normal="", background_color=rgba(CYAN), color=rgba(BG),
            bold=True, font_size="20sp"
        )
        header.add_widget(avatar)
        header.add_widget(Label(text="Sam Ng", color=rgba(WHITE), bold=True, font_size="18sp"))
        card.add_widget(header)

        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in VIDEO_EXTENSIONS:
                media = Video(source=path, allow_stretch=True, keep_ratio=True, size_hint_y=None, height=dp(350))
            else:
                media = Image(source=path, allow_stretch=True, keep_ratio=True, size_hint_y=None, height=dp(350))
            card.add_widget(media)
        except Exception:
            card.add_widget(Label(text="Could not load media", color=rgba(PINK)))

        action_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        for text, color in [
            ("♡ Like", rgba(WHITE)),
            ("↗ Share", rgba(CYAN)),
            ("▣ Save", rgba(WHITE)),
            ("☰ Comment", rgba(WHITE))
        ]:
            btn = Button(
                text=text,
                background_normal="",
                background_color=rgba(PANEL),
                color=color,
                font_size="12sp"
            )
            action_row.add_widget(btn)
        card.add_widget(action_row)
        return card

    def make_recommendations_panel(self):
        panel = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=(dp(8), dp(10)))
        panel.add_widget(Label(text="Recommended for you", color=rgba(CYAN), bold=True, font_size="18sp"))
        for item in self.recommendations:
            row = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(8))
            avatar = Button(text="C", size_hint_x=None, width=dp(42), background_normal="", background_color=rgba(CYAN), color=rgba(BG))
            row.add_widget(avatar)
            row.add_widget(Label(text=item["title"], color=rgba(WHITE), font_size="16sp"))
            panel.add_widget(row)
        return panel

    def change_tab(self, name):
        self.active_tab = name
        self.show_feed()

    def navigate(self, name):
        if name == "Profile":
            self.manager.current = "profile"
        elif name == "Home":
            self.manager.current = "home"
        elif name == "Create":
            self.pick_media()
        else:
            self.show_message("Coming soon", f"{name} is coming soon.")

    def show_message(self, title, description):
        self.feed.clear_widgets()
        self.feed.add_widget(Label(text=title, color=rgba(CYAN), font_size="22sp", bold=True))
        self.feed.add_widget(Label(text=description, color=rgba(WHITE), font_size="16sp"))

    def pick_media(self):
        if ANDROID_PICKER_AVAILABLE:
            try:
                Intent = autoclass("android.content.Intent")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType("*/*")
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                mime_types = ["image/*", "video/*"]
                intent.putExtra(Intent.EXTRA_MIME_TYPES, mime_types)
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                PythonActivity.mActivity.startActivityForResult(intent, self.PICKER_REQUEST_CODE)
                return
            except Exception as e:
                self.show_message("Picker error", str(e))
                return
        self.open_recent_media_sheet()

    def open_recent_media_sheet(self):
        sheet = ModalView(size_hint=(1, 0.80), pos_hint={"x": 0, "y": 0}, background_color=(0, 0, 0, 0.72))
        panel = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        with panel.canvas.before:
            Color(*rgba(PANEL))
            panel_bg = Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(pos=lambda w, v: setattr(panel_bg, \"pos\", v), size=lambda w, v: setattr(panel_bg, \"size\", v))
        panel.add_widget(Label(text="Recent media", color=rgba(WHITE), bold=True, font_size="18sp"))
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, row_default_height=dp(140), row_force_default=True)
        grid.bind(minimum_height=grid.setter("height"))
        panel.add_widget(grid)
        sheet.add_widget(panel)

        for i in range(4):
            item = Button(text=f"Item {i + 1}", background_normal="", background_color=rgba(BG), color=rgba(CYAN))
            item.bind(on_release=lambda *_: sheet.dismiss())
            grid.add_widget(item)
        sheet.open()

    def on_android_activity_result(self, request_code, result_code, intent):
        if request_code != self.PICKER_REQUEST_CODE:
            return
        try:
            Activity = autoclass("android.app.Activity")
            if result_code != Activity.RESULT_OK or intent is None:
                return
            uri = intent.getData()
            if uri is not None:
                path = self.copy_uri_to_cache(uri)
                if path and os.path.isfile(path):
                    self.posts.append(path)
                    self.show_feed()
        except Exception:
            pass

    def copy_uri_to_cache(self, uri):
        cache_dir = os.path.join(os.getcwd(), "selected_media")
        os.makedirs(cache_dir, exist_ok=True)
        destination = os.path.join(cache_dir, "selected_" + str(int(Clock.get_time() * 1000)) + ".jpg")
        try:
            from urllib.request import urlretrieve
            import tempfile
            return destination
        except Exception:
            return None


class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical")
        self.add_widget(layout)

        banner = BoxLayout(size_hint_y=None, height=dp(120))
        with banner.canvas.before:
            Color(*rgba(CYAN))
            banner_bg = Rectangle(pos=banner.pos, size=banner.size)
        banner.bind(pos=lambda w, v: setattr(banner_bg, \"pos\", v), size=lambda w, v: setattr(banner_bg, \"size\", v))
        banner.add_widget(Label(text="BANNER", color=rgba(BG), bold=True, font_size="20sp"))
        layout.add_widget(banner)

        info = BoxLayout(size_hint_y=None, height=dp(80), padding=(dp(16), dp(10)))
        avatar = Button(text="S", background_normal="", background_color=rgba(CYAN), color=rgba(BG), font_size="22sp", bold=True)
        info.add_widget(avatar)
        info.add_widget(Label(text="Sam Ng", color=rgba(WHITE), font_size="20sp", bold=True))
        layout.add_widget(info)

        layout.add_widget(Label(text="Your videos & posts", color=rgba(CYAN), font_size="18sp", bold=True))
        layout.add_widget(Label(text="No posts yet", color=rgba(GREY), font_size="16sp"))

        back_btn = Button(text="Back", background_normal="", background_color=rgba(PANEL), color=rgba(WHITE))
        back_btn.bind(on_release=lambda *_: self.manager.current = "home")
        layout.add_widget(back_btn)


class SamNgApp(App):
    def build(self):
        Window.clearcolor = rgba(BG)
        manager = ScreenManager(transition=FadeTransition(duration=0.2))
        manager.add_widget(WelcomeScreen(name="welcome"))
        manager.add_widget(HomeScreen(name="home"))
        manager.add_widget(ProfileScreen(name="profile"))
        manager.current = "welcome"
        return manager


if __name__ == "__main__":
    SamNgApp().run()
