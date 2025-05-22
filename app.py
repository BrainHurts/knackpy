from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
import knackpy
import keyring
import json
import pandas as pd
import os

class ObjectsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.knack_app = app
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title = Label(
            text='Knack Objects',
            font_size=24,
            size_hint_y=None,
            height=40
        )
        
        # Create header row
        header_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)
        header_row.add_widget(Label(text='Object Name', bold=True, font_size=18, size_hint_x=0.4, halign='center', valign='middle'))
        header_row.add_widget(Label(text='Object Key', bold=True, font_size=18, size_hint_x=0.4, halign='center', valign='middle'))
        header_row.add_widget(Label(text='Record Count', bold=True, font_size=18, size_hint_x=0.2, halign='center', valign='middle'))
        
        # Create scrollable table
        scroll = ScrollView(size_hint=(1, 1))
        self.table_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.table_layout.bind(minimum_height=self.table_layout.setter('height'))
        scroll.add_widget(self.table_layout)
        
        # Buttons layout
        buttons_layout = BoxLayout(
            orientation='horizontal',
            spacing=10,
            size_hint_y=None,
            height=50
        )
        
        # Save button
        save_button = Button(
            text='Save Data',
            background_color=(0.2, 0.8, 0.2, 1)
        )
        save_button.bind(on_press=self.show_save_dialog)
        
        # Logout button
        logout_button = Button(
            text='Logout',
            background_color=(0.8, 0.2, 0.2, 1)
        )
        logout_button.bind(on_press=self.logout)
        
        buttons_layout.add_widget(save_button)
        buttons_layout.add_widget(logout_button)
        
        # Add widgets to layout
        layout.add_widget(title)
        layout.add_widget(header_row)
        layout.add_widget(scroll)
        layout.add_widget(buttons_layout)
        
        self.add_widget(layout)
        self.load_objects()
    
    def load_objects(self):
        self.table_layout.clear_widgets()
        try:
            # Get all objects from Knack
            objects = self.knack_app.containers
            for obj in objects:
                if obj.obj:  # Only show actual objects, not views
                    # Get record count
                    records = self.knack_app.get(obj.obj)
                    record_count = len(records) if records else 0
                    # Add a row for this object
                    row = BoxLayout(orientation='horizontal', size_hint_y=None, height=35, spacing=5)
                    name_label = Label(text=obj.name, size_hint_x=0.4, halign='left', valign='middle')
                    name_label.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width, None)))
                    key_label = Label(text=obj.obj, size_hint_x=0.4, halign='left', valign='middle')
                    key_label.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width, None)))
                    count_label = Label(text=str(record_count), size_hint_x=0.2, halign='center', valign='middle')
                    count_label.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width, None)))
                    row.add_widget(name_label)
                    row.add_widget(key_label)
                    row.add_widget(count_label)
                    self.table_layout.add_widget(row)
        except Exception as e:
            print(f"Error loading objects: {str(e)}")
    
    def show_save_dialog(self, instance):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # File chooser
        file_chooser = FileChooserListView(
            path=os.getcwd(),
            filters=['*.csv', '*.xlsx']
        )
        
        # Buttons
        buttons = BoxLayout(size_hint_y=None, height=50, spacing=10)
        save_btn = Button(text='Save', background_color=(0.2, 0.8, 0.2, 1))
        cancel_btn = Button(text='Cancel', background_color=(0.8, 0.2, 0.2, 1))
        
        buttons.add_widget(save_btn)
        buttons.add_widget(cancel_btn)
        
        content.add_widget(file_chooser)
        content.add_widget(buttons)
        
        popup = Popup(
            title='Save Data',
            content=content,
            size_hint=(0.9, 0.9)
        )
        
        def save_data(instance):
            try:
                selected_path = file_chooser.selection[0]
                if not selected_path:
                    return
                
                # Get all objects and their records
                data = {}
                for obj in self.knack_app.containers:
                    if obj.obj:
                        records = self.knack_app.get(obj.obj)
                        if records:
                            data[obj.name] = [record.format() for record in records]
                
                # Save based on file extension
                if selected_path.endswith('.csv'):
                    for obj_name, records in data.items():
                        df = pd.DataFrame(records)
                        df.to_csv(f"{selected_path[:-4]}_{obj_name}.csv", index=False)
                elif selected_path.endswith('.xlsx'):
                    with pd.ExcelWriter(selected_path) as writer:
                        for obj_name, records in data.items():
                            df = pd.DataFrame(records)
                            df.to_excel(writer, sheet_name=obj_name, index=False)
                
                popup.dismiss()
            except Exception as e:
                print(f"Error saving data: {str(e)}")
        
        save_btn.bind(on_press=save_data)
        cancel_btn.bind(on_press=popup.dismiss)
        
        popup.open()
    
    def logout(self, instance):
        # Switch back to login screen
        self.manager.current = 'login'

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_login_pending = False
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
        self.load_credentials()
    
    def on_enter(self, *args):
        if getattr(self, 'auto_login_pending', False):
            self.auto_login_pending = False
            self.login(None)
    
    def load_credentials(self):
        try:
            credentials = keyring.get_password("knackpy", "credentials")
            if credentials:
                creds = json.loads(credentials)
                self.app_id_input.text = creds.get('app_id', '')
                self.api_key_input.text = creds.get('api_key', '')
                self.status_label.text = 'Credentials loaded from keyring'
                self.auto_login_pending = True
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
            
            # Create and switch to objects screen
            objects_screen = ObjectsScreen(app, name='objects')
            self.manager.add_widget(objects_screen)
            self.manager.current = 'objects'
            
        except Exception as e:
            self.status_label.text = f'Error: {str(e)}'

class KnackApp(App):
    def build(self):
        # Set window size
        Window.size = (800, 600)
        
        # Create screen manager
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        
        return sm

if __name__ == '__main__':
    KnackApp().run()