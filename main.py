from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label


class SamNgApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical')
        root.add_widget(Label(text='Hello Sam Ng!'))
        return root


if __name__ == '__main__':
    SamNgApp().run()
