from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
import knackpy
import keyring
import json

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        # Title
        title = Label(
            text='Knack Login',
            font_size=32,
            size_hint_y=None,
            height=50
        )
        
        # App ID input
        self.app_id_input = TextInput(
            multiline=False,
            hint_text='Enter Knack App ID',
            size_hint_y=None,
            height=50
        )
        
        # API Key input
        self.api_key_input = TextInput(
            multiline=False,
            hint_text='Enter Knack API Key',
            password=True,
            size_hint_y=None,
            height=50
        )
        
        # Buttons layout
        buttons_layout = BoxLayout(
            orientation='horizontal',
            spacing=10,
            size_hint_y=None,
            height=50
        )
        
        # Login button
        login_button = Button(
            text='Login',
            background_color=(0.2, 0.6, 1, 1)
        )
        login_button.bind(on_press=self.login)
        
        # Save credentials button
        save_button = Button(
            text='Save Credentials',
            background_color=(0.2, 0.8, 0.2, 1)
        )
        save_button.bind(on_press=self.save_credentials)
        
        # Add buttons to buttons layout
        buttons_layout.add_widget(login_button)
        buttons_layout.add_widget(save_button)
        
        # Status label
        self.status_label = Label(
            text='',
            size_hint_y=None,
            height=30
        )
        
        # Add widgets to layout
        layout.add_widget(title)
        layout.add_widget(self.app_id_input)
        layout.add_widget(self.api_key_input)
        layout.add_widget(buttons_layout)
        layout.add_widget(self.status_label)
        
        self.add_widget(layout)
        
        # Load saved credentials
        self.load_credentials()
    
    def load_credentials(self):
        try:
            # Try to load credentials from keyring
            credentials = keyring.get_password("knackpy", "credentials")
            if credentials:
                creds = json.loads(credentials)
                self.app_id_input.text = creds.get('app_id', '')
                self.api_key_input.text = creds.get('api_key', '')
                self.status_label.text = 'Credentials loaded from keyring'
                # Attempt automatic connection
                self.login(None)
        except Exception as e:
            self.status_label.text = f'Error loading credentials: {str(e)}'
    
    def save_credentials(self, instance):
        app_id = self.app_id_input.text.strip()
        api_key = self.api_key_input.text.strip()
        
        if not app_id or not api_key:
            self.status_label.text = 'Please enter both App ID and API Key'
            return
        
        try:
            # Save credentials to keyring
            credentials = json.dumps({
                'app_id': app_id,
                'api_key': api_key
            })
            keyring.set_password("knackpy", "credentials", credentials)
            self.status_label.text = 'Credentials saved successfully'
        except Exception as e:
            self.status_label.text = f'Error saving credentials: {str(e)}'
    
    def login(self, instance):
        app_id = self.app_id_input.text.strip()
        api_key = self.api_key_input.text.strip()
        
        if not app_id or not api_key:
            self.status_label.text = 'Please enter both App ID and API Key'
            return
        
        try:
            # Initialize Knack app
            app = knackpy.App(app_id=app_id, api_key=api_key)
            # Test connection by getting app info
            app_info = app.info()
            self.status_label.text = f'Successfully connected! Objects: {app_info["objects"]}, Records: {app_info["records"]}'
        except Exception as e:
            self.status_label.text = f'Error: {str(e)}'

class KnackApp(App):
    def build(self):
        # Set window size
        Window.size = (400, 600)
        
        # Create screen manager
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        
        return sm

if __name__ == '__main__':
    KnackApp().run()