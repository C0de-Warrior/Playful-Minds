import os
import json
import subprocess
import sys

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.metrics import dp
from kivy.config import Config

# Set window icon
Config.set('kivy', 'window_icon', 'assets/logo.png')
Window.clearcolor = (0.93, 0.95, 0.96, 1)  # Light blue background


class PlayfulMindsApp(App):
    # Color properties
    PRIMARY_BLUE = [0.16, 0.32, 0.75, 1]
    SECONDARY_BLUE = [0.25, 0.58, 0.89, 1]
    ACCENT_BLUE = [0.04, 0.15, 0.47, 1]
    LIGHT_BLUE = [0.79, 0.88, 0.96, 1]
    TEXT_COLOR = [1, 1, 1, 1]

    def build(self):
        Builder.load_string(KV)
        self.sm = ScreenManager(transition=FadeTransition(duration=0.3))
        self.sm.add_widget(WelcomeScreen(name='welcome'))
        self.sm.add_widget(GameSelectionScreen(name='game_selection'))
        self.sm.add_widget(SettingsScreen(name='settings'))
        self.sm.add_widget(GameScreen(name='game'))
        self.camera_index = 0
        self.load_config()
        return self.sm

    def load_config(self):
        config_dir = os.path.join(os.getcwd(), "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        config_path = os.path.join(config_dir, "settings.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    self.camera_index = config.get("camera_index", 0)
            except Exception as e:
                print(f"Config error: {e}")
                self.set_camera_index(0)
        else:
            self.set_camera_index(0)

    def set_camera_index(self, index):
        self.camera_index = index
        config_path = os.path.join("config", "settings.json")
        with open(config_path, "w") as f:
            json.dump({"camera_index": index}, f)

    def launch_game(self, game_file):
        game_path = os.path.join("games", game_file)
        if os.path.exists(game_path):
            subprocess.Popen([sys.executable, game_path])
        else:
            print(f"Missing game: {game_path}")


KV = '''
#:import dp kivy.metrics.dp
#:import app __main__.PlayfulMindsApp

<WelcomeScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(30)
        spacing: dp(20)
        canvas.before:
            Color:
                rgba: app.LIGHT_BLUE
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Welcome to Playful Minds!"
            font_size: '32sp'
            color: app.PRIMARY_BLUE
            bold: True
        Button:
            text: "Go to Game Selection"
            size_hint: (0.6, 0.2)
            pos_hint: {'center_x': 0.5}
            background_color: app.SECONDARY_BLUE
            color: app.TEXT_COLOR
            on_release: root.manager.current = 'game_selection'

<SettingsScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(30)
        spacing: dp(20)
        canvas.before:
            Color:
                rgba: app.LIGHT_BLUE
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Settings"
            font_size: '32sp'
            color: app.PRIMARY_BLUE
            bold: True
        Spinner:
            id: camera_spinner
            text: "Select Camera"
            values: ["0", "1", "2", "3"]
            size_hint: (0.6, 0.2)
            pos_hint: {'center_x': 0.5}
            background_color: app.LIGHT_BLUE
            color: app.ACCENT_BLUE
            on_text: app.set_camera_index(int(self.text))
        Button:
            text: "Back"
            size_hint: (0.6, 0.2)
            pos_hint: {'center_x': 0.5}
            background_color: app.SECONDARY_BLUE
            color: app.TEXT_COLOR
            on_release: root.manager.current = 'game_selection'

<GameScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(30)
        spacing: dp(20)
        canvas.before:
            Color:
                rgba: app.LIGHT_BLUE
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Game Screen - Launching Game..."
            font_size: '32sp'
            color: app.PRIMARY_BLUE
            bold: True
        Button:
            text: "Back to Menu"
            size_hint: (0.6, 0.2)
            pos_hint: {'center_x': 0.5}
            background_color: app.SECONDARY_BLUE
            color: app.TEXT_COLOR
            on_release: root.manager.current = 'game_selection'

<GameSelectionScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: app.LIGHT_BLUE
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Select a Game"
            font_size: '32sp'
            color: app.PRIMARY_BLUE
            bold: True
            size_hint_y: None
            height: dp(60)
        ScrollView:
            do_scroll_x: False
            bar_width: dp(10)
            bar_color: app.SECONDARY_BLUE
            BoxLayout:
                id: game_list
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(15)
                padding: [dp(10), dp(10), dp(10), dp(10)]
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            spacing: dp(10)
            padding: dp(10)
            Button:
                text: "Settings"
                background_color: app.SECONDARY_BLUE
                color: app.TEXT_COLOR
                on_release: root.manager.current = 'settings'
            Button:
                text: "Quit"
                background_color: app.ACCENT_BLUE
                color: app.TEXT_COLOR
                on_release: app.stop()

<GameItem>:
    size_hint_y: None
    height: dp(160)
    background_normal: ''
    background_color: app.SECONDARY_BLUE
    canvas.before:
        Color:
            rgba: app.PRIMARY_BLUE
        Line:
            width: 1.5
            rectangle: [self.x, self.y, self.width, self.height]
    BoxLayout:
        orientation: 'horizontal'
        padding: dp(15)
        spacing: dp(15)
        size: root.size
        pos: root.pos

        # Image container
        BoxLayout:
            size_hint_x: 0.3
            padding: dp(5)
            canvas:
                Color:
                    rgba: app.LIGHT_BLUE
                Rectangle:
                    pos: self.pos
                    size: self.size
            RelativeLayout:
                Image:
                    source: root.game_image
                    allow_stretch: True
                    keep_ratio: True
                    mipmap: True
                    opacity: 1 if root.has_image else 0
                    size_hint: (0.9, 0.9)
                    pos_hint: {'center_x': 0.5, 'center_y': 0.5}
                Label:
                    text: "No Image"
                    opacity: 0 if root.has_image else 1
                    color: app.ACCENT_BLUE
                    font_size: '16sp'
                    pos_hint: {'center_x': 0.5, 'center_y': 0.5}

        # Text container
        BoxLayout:
            orientation: 'vertical'
            size_hint_x: 0.7
            spacing: dp(8)
            Label:
                text: root.game_title
                font_size: '22sp'
                bold: True
                color: app.TEXT_COLOR
                size_hint_y: None
                height: dp(40)
                text_size: self.width, None
                halign: 'left'
                valign: 'middle'
                padding: [0, dp(5)]

            Label:
                text: root.game_description
                font_size: '16sp'
                color: app.TEXT_COLOR
                size_hint_y: None
                height: dp(80)
                text_size: self.width - dp(10), None
                halign: 'left'
                valign: 'top'
                padding: [0, dp(5)]
'''


class GameItem(Button):
    game_title = StringProperty("")
    game_description = StringProperty("")
    game_file = StringProperty("")
    game_image = StringProperty("")
    has_image = BooleanProperty(False)

    def on_game_image(self, instance, value):
        if value:
            norm_path = os.path.normpath(value)
            self.has_image = os.path.exists(norm_path)
            if self.has_image:
                self.game_image = norm_path
        else:
            self.has_image = False


class WelcomeScreen(Screen): pass


class SettingsScreen(Screen): pass


class GameScreen(Screen): pass


class GameSelectionScreen(Screen):
    def on_enter(self):
        if not self.ids.game_list.children:
            base_path = os.path.join("assets", "logos")
            self.games = [
                {
                    "title": "Edible Game",
                    "file": "edible.py",
                    "description": "Bite edible items while avoiding non-edible ones.",
                    "image": os.path.join(base_path, "edible.png")
                },
                {
                    "title": "Color Smash",
                    "file": "color_smash.py",
                    "description": "Match colors in a fun and fast-paced game.",
                    "image": os.path.join(base_path, "color_smash.png")
                },
                {
                    "title": "Number Dash",
                    "file": "number_dash.py",
                    "description": "Run through numbers in a challenging dash.",
                    "image": os.path.join(base_path, "number_dash.png")
                },
                {
                    "title": "Odd One Out",
                    "file": "odd_one_out.py",
                    "description": "Identify the odd item among similar ones.",
                    "image": os.path.join(base_path, "odd_one_out.png")
                },
                {
                    "title": "Shape Sorter",
                    "file": "shape-sorter.py",
                    "description": "Sort shapes to boost your visual skills.",
                    "image": os.path.join(base_path, "shape-sorter.png")
                },
                {
                    "title": "Spell Drop",
                    "file": "spell_drop.py",
                    "description": "Drop letters to form words correctly.",
                    "image": os.path.join(base_path, "spell_drop.png")
                },
                {
                    "title": "Text Recognition",
                    "file": "text_reco.py",
                    "description": "Recognize text in images and have fun.",
                    "image": os.path.join(base_path, "text_reco.png")
                },
                {
                    "title": "Word Builder",
                    "file": "word_builder.py",
                    "description": "Construct words from jumbled letters.",
                    "image": os.path.join(base_path, "word_builder.png")
                }
            ]
            for game in self.games:
                full_image_path = os.path.abspath(game["image"])
                item = GameItem(
                    game_title=game["title"],
                    game_description=game["description"],
                    game_file=game["file"],
                    game_image=full_image_path
                )
                self.ids.game_list.add_widget(item)


if __name__ == '__main__':
    PlayfulMindsApp().run()