import dearpygui.dearpygui as dpg
import knackpy
import json
import os
import csv
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import threading
import logging
import shutil
import keyring

class KnackpyBackupGUI:
    def __init__(self):
        self.job_metadata = {}  # job_id -> {'hour': int, 'minute': int, 'objects': list}
        self.app = None
        self.containers = []
        
        # Backup variables
        self.selected_containers = []
        self.backup_dir = os.path.join(os.getcwd(), "knack_backup")
        self.container_vars = {}  # Initialize container_vars dictionary
        
        # Scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        # Track job last run times and selected objects
        self.job_last_runs = {}
        self.job_selected_objects = {}
        
        # Initialize Dear PyGui
        dpg.create_context()
        dpg.create_viewport(title="Knackpy Backup Tool", width=800, height=600)
        dpg.set_viewport_clear_color((30, 30, 30, 255))
        dpg.setup_dearpygui()
        
        # Create the UI first
        self.create_ui()
        
        # Then load saved schedules and credentials
        self.status_message = "Not connected"
        self.load_credentials_from_keyring(auto_connect=True)
        self.load_schedules()
        
        # Start the GUI
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()
    
    def create_ui(self):
        with dpg.window(label="Knackpy Backup Tool", tag="Primary Window"):
            # Connection Section
            with dpg.collapsing_header(label="Connection", default_open=True):
                dpg.add_text("App ID:")
                dpg.add_input_text(tag="app_id", width=400)
                dpg.add_text("API Key:")
                dpg.add_input_text(tag="api_key", width=400, password=True)
                dpg.add_button(label="Connect", callback=self.connect_to_app)
                dpg.add_button(label="Save Credentials", callback=self.save_credentials_to_keyring)
                dpg.add_text(tag="status_text", default_value="Not connected")
            
            # Backup Section
            with dpg.collapsing_header(label="Backup", default_open=True):
                dpg.add_text("Select Objects to Backup:")
                dpg.add_child_window(tag="container_window", width=700, height=120)
                dpg.add_text("Backup Directory:")
                dpg.add_input_text(tag="backup_dir", default_value=self.backup_dir, width=600)
                dpg.add_button(label="Browse", callback=self.select_backup_dir)
                
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Select All", callback=self.select_all_containers)
                    dpg.add_button(label="Deselect All", callback=self.deselect_all_containers)
                    dpg.add_button(label="Backup Selected", callback=self.backup_selected)
                
                dpg.add_text(tag="progress_text", default_value="")
                dpg.add_progress_bar(tag="progress_bar", default_value=0, width=700)
            
            # Schedule Section
            with dpg.collapsing_header(label="Scheduled Jobs", default_open=False):
                dpg.add_text("Current Jobs:")
                # Create a table using a child window with a grid layout
                with dpg.child_window(tag="jobs_table", width=700, height=120):
                    # Header row
                    with dpg.group(horizontal=True):
                        with dpg.group(width=200):
                            dpg.add_text("Objects")
                        with dpg.group(width=100):
                            dpg.add_text("Status")
                        with dpg.group(width=200):
                            dpg.add_text("Last Run")
                        with dpg.group(width=200):
                            dpg.add_text("Next Run")
                    # Add a separator
                    dpg.add_separator()
                    # Container for job rows
                    dpg.add_group(tag="jobs_table_rows")
                
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Add Schedule", callback=self.show_add_schedule_dialog)
                    dpg.add_button(label="Remove Selected", callback=self.remove_selected_job)
                
                dpg.add_text(tag="schedule_status", default_value="Scheduler is running")
    
    def connect_to_app(self):
        try:
            app_id = dpg.get_value("app_id")
            api_key = dpg.get_value("api_key")
            
            self.app = knackpy.App(app_id=app_id, api_key=api_key)
            self.status_message = "Connected to Knack application"
            dpg.set_value("status_text", self.status_message)
            
            # Clear existing container checkboxes
            dpg.delete_item("container_window", children_only=True)
            
            # Reset selected containers and container vars
            self.selected_containers = []
            self.container_vars = {}
            
            # Get only objects
            objects = [c for c in self.app.containers if c.obj is not None]
            
            if not objects:
                self.show_message("No objects found in this application")
                return
            
            # Create checkboxes for each object
            for container in objects:
                checkbox_tag = f"checkbox_{container.obj}"
                dpg.add_checkbox(
                    parent="container_window",
                    label=f"{container.name} ({container.obj})",
                    callback=self.update_selected_containers,
                    user_data=container.obj,
                    tag=checkbox_tag
                )
                self.container_vars[container.obj] = checkbox_tag
            
            message = f"Connected to Knack application successfully!\nFound {len(objects)} objects."
            self.status_message = message
            dpg.set_value("status_text", message)
            
        except Exception as e:
            self.status_message = f"Error: {str(e)}"
            dpg.set_value("status_text", self.status_message)
    
    def update_selected_containers(self, sender, app_data, user_data):
        self.selected_containers = [
            container_id for container_id, checkbox_tag in self.container_vars.items() 
            if dpg.get_value(checkbox_tag)
        ]
    
    def select_all_containers(self):
        for checkbox_tag in self.container_vars.values():
            dpg.set_value(checkbox_tag, True)
        self.update_selected_containers(None, None, None)
    
    def deselect_all_containers(self):
        for checkbox_tag in self.container_vars.values():
            dpg.set_value(checkbox_tag, False)
        self.update_selected_containers(None, None, None)
    
    def select_backup_dir(self):
        # Note: Dear PyGui doesn't have a built-in file dialog
        # You might want to use tkinter's filedialog here
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        directory = filedialog.askdirectory(initialdir=self.backup_dir)
        if directory:
            self.backup_dir = directory
            dpg.set_value("backup_dir", directory)
    
    def show_message(self, message):
        """Show a message dialog using Dear PyGui"""
        window_tag = "message_window"
        if dpg.does_item_exist(window_tag):
            dpg.delete_item(window_tag)
        with dpg.window(label="Message", modal=True, autosize=True, tag=window_tag):
            dpg.add_text(message)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item(window_tag))
    
    def backup_selected(self):
        if not self.app:
            self.show_message("Please connect to a Knack application first")
            return
        
        if not self.selected_containers:
            self.show_message("Please select at least one object to backup")
            return
        
        # Create backup directory if it doesn't exist
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        # Create timestamp directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = os.path.join(self.backup_dir, f"backup_{timestamp}")
        os.makedirs(backup_folder)
        
        # Set up progress tracking
        total_containers = len(self.selected_containers)
        dpg.set_value("progress_bar", 0)
        dpg.configure_item("progress_bar", overlay=f"0/{total_containers}")
        
        # Perform backup for each selected container
        for i, container_id in enumerate(self.selected_containers):
            try:
                # Update progress
                container_name = self._get_container_name(container_id)
                dpg.set_value("progress_text", f"Backing up {container_name} ({i+1}/{total_containers})")
                dpg.set_value("progress_bar", (i + 1) / total_containers)
                dpg.configure_item("progress_bar", overlay=f"{i+1}/{total_containers}")
                
                # Get records
                records = self.app.get(container_id)
                
                if records:
                    # Format records
                    formatted_records = [record.format() for record in records]
                    
                    # Save to CSV
                    self._save_to_csv(formatted_records, container_id, container_name, backup_folder)
                    
                    # Also save raw JSON for complete backup
                    self._save_to_json(formatted_records, container_id, container_name, backup_folder)
                
            except Exception as e:
                self.show_message(f"Failed to backup {container_id}: {str(e)}")
        
        # Complete progress
        dpg.set_value("progress_bar", 1.0)
        dpg.configure_item("progress_bar", overlay=f"{total_containers}/{total_containers}")
        dpg.set_value("progress_text", "Backup completed!")
        self.status_message = f"Backup completed successfully! Backup saved to: {backup_folder}"
        dpg.set_value("status_text", self.status_message)
    
    def _get_container_name(self, container_id):
        if not self.app or not hasattr(self.app, 'containers'):
            return container_id
        for container in self.app.containers:
            if container.obj == container_id:
                return container.name
        return container_id
    
    def _save_to_csv(self, records, container_id, container_name, backup_folder):
        if not records:
            return
            
        # Create CSV filename
        filename = f"{container_name}_{container_id}.csv"
        safe_filename = self._make_safe_filename(filename)
        filepath = os.path.join(backup_folder, safe_filename)
        
        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            # Get fieldnames from first record
            fieldnames = list(records[0].keys())
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write all records
            for record in records:
                # Handle complex data types (convert to string)
                for key, value in record.items():
                    if isinstance(value, (dict, list)):
                        record[key] = json.dumps(value)
                writer.writerow(record)
    
    def _save_to_json(self, records, container_id, container_name, backup_folder):
        if not records:
            return
            
        # Create JSON filename
        filename = f"{container_name}_{container_id}.json"
        safe_filename = self._make_safe_filename(filename)
        filepath = os.path.join(backup_folder, safe_filename)
        
        # Write to JSON
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(records, jsonfile, indent=2)
    
    def _make_safe_filename(self, filename):
        # Replace any characters that are not allowed in filenames
        for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            filename = filename.replace(char, '_')
        return filename
    
    def show_add_schedule_dialog(self):
        if not self.app:
            self.show_message("Please connect to a Knack application first")
            return
        if not self.selected_containers:
            self.show_message("Please select at least one object to backup")
            return
        
        # Create dialog window
        with dpg.window(label="Add Schedule", tag="schedule_dialog", width=400, height=300):
            dpg.add_text("Time (24-hour format):")
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="hour_input", width=50, default_value=str(datetime.now().hour))
                dpg.add_text(":")
                dpg.add_input_text(tag="minute_input", width=50, default_value=str(datetime.now().minute))
            
            dpg.add_text("Selected Objects:")
            dpg.add_text("\n".join([self._get_container_name(container_id) for container_id in self.selected_containers]))
            
            dpg.add_button(label="Add Schedule", callback=self.add_schedule)
    
    def add_schedule(self):
        try:
            hour = int(dpg.get_value("hour_input"))
            minute = int(dpg.get_value("minute_input"))
            
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time values")
            
            # Create job ID
            job_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Store the selected objects for this job
            self.job_selected_objects[job_id] = self.selected_containers.copy()
            self.job_metadata[job_id] = {
                'hour': hour,
                'minute': minute,
                'objects': self.selected_containers.copy()
            }
            
            # Create a backup function that captures the current state
            def scheduled_backup():
                try:
                    # Store the last run time
                    self.job_last_runs[job_id] = datetime.now()
                    self.update_job_list()
                    
                    # Perform the backup with the stored objects
                    self._perform_backup_with_objects(self.job_selected_objects[job_id])
                except Exception as e:
                    logging.error(f"Error in scheduled backup {job_id}: {str(e)}")
                    self.status_message = f"Scheduled backup failed: {str(e)}"
                    dpg.set_value("status_text", self.status_message)
            
            # Add the job to the scheduler
            self.scheduler.add_job(
                scheduled_backup,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=job_id,
                name=f"Daily Backup at {hour:02d}:{minute:02d}"
            )
            
            # Update the UI
            self.update_job_list()
            
            # Save schedules immediately
            self.save_schedules()
            
            # Close the dialog
            dpg.delete_item("schedule_dialog")
            
            # Show success message
            self.status_message = f"Schedule added successfully for {hour:02d}:{minute:02d}"
            dpg.set_value("status_text", self.status_message)
            
        except ValueError as e:
            dpg.show_info(str(e))
    
    def update_job_list(self):
        # Clear existing items
        dpg.delete_item("jobs_table_rows", children_only=True)
        
        # Add current jobs
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M') if job.next_run_time else 'N/A'
            last_run = self.job_last_runs.get(job.id, 'N/A')
            if isinstance(last_run, datetime):
                last_run = last_run.strftime('%Y-%m-%d %H:%M')
            
            job_objects = self.job_selected_objects.get(job.id, [])
            selected_names = [self._get_container_name(container_id) for container_id in job_objects]
            objects_str = ', '.join(selected_names)
            if len(objects_str) > 50:
                objects_str = objects_str[:47] + '...'
            
            with dpg.group(parent="jobs_table_rows", horizontal=True):
                with dpg.group(width=200):
                    dpg.add_text(objects_str)
                with dpg.group(width=100):
                    dpg.add_text("Active")
                with dpg.group(width=200):
                    dpg.add_text(last_run)
                with dpg.group(width=200):
                    dpg.add_text(next_run)
    
    def remove_selected_job(self):
        # Since we can't get selected items directly, we'll need to track selection manually
        # For now, we'll just remove the last added job
        jobs = self.scheduler.get_jobs()
        if not jobs:
            self.show_message("No jobs to remove")
            return
        
        # Remove the last job
        job = jobs[-1]
        self.scheduler.remove_job(job.id)
        self.job_last_runs.pop(job.id, None)
        self.job_selected_objects.pop(job.id, None)
        self.job_metadata.pop(job.id, None)
        
        self.update_job_list()
        self.save_schedules()
    
    def save_credentials_to_keyring(self):
        app_id = dpg.get_value("app_id")
        api_key = dpg.get_value("api_key")
        keyring.set_password("knackpy_backup", "app_id", app_id)
        keyring.set_password("knackpy_backup", "api_key", api_key)
        self.status_message = "App ID and API Key saved to system keyring."
        dpg.set_value("status_text", self.status_message)
    
    def load_credentials_from_keyring(self, auto_connect=False):
        app_id = keyring.get_password("knackpy_backup", "app_id")
        api_key = keyring.get_password("knackpy_backup", "api_key")
        if app_id:
            dpg.set_value("app_id", app_id)
        if api_key:
            dpg.set_value("api_key", api_key)
        if app_id and api_key and auto_connect:
            self.status_message = "Loaded credentials from keyring. Connecting..."
            dpg.set_value("status_text", self.status_message)
            self.connect_to_app()
        elif app_id or api_key:
            self.status_message = "Loaded credentials from keyring."
            dpg.set_value("status_text", self.status_message)
        else:
            self.status_message = "No credentials found in keyring."
            dpg.set_value("status_text", self.status_message)
    
    def load_schedules(self):
        """Load saved schedules from JSON file"""
        try:
            if not os.path.exists('schedules.json'):
                logging.info("No schedules file found")
                return
                
            with open('schedules.json', 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    logging.error(f"Corrupt schedules.json: {e}")
                    self.status_message = "Your schedules.json file is corrupt and will be reset."
                    dpg.set_value("status_text", self.status_message)
                    shutil.move('schedules.json', 'schedules.json.bak')
                    return
                
                if not data.get('jobs'):
                    logging.info("No jobs found in schedules file")
                    return
                
                # Clear existing jobs
                self.scheduler.remove_all_jobs()
                self.job_last_runs.clear()
                self.job_selected_objects.clear()
                self.job_metadata.clear()
                
                # Restore jobs
                for job_data in data['jobs']:
                    try:
                        job_id = job_data['id']
                        hour = job_data['hour']
                        minute = job_data['minute']
                        objects = job_data['objects']
                        
                        # Store the selected objects for this job
                        self.job_selected_objects[job_id] = objects
                        self.job_metadata[job_id] = {
                            'hour': hour,
                            'minute': minute,
                            'objects': objects
                        }
                        
                        # Create the backup function
                        def create_scheduled_backup(job_id=job_id):
                            try:
                                self.job_last_runs[job_id] = datetime.now()
                                self.update_job_list()
                                self._perform_backup_with_objects(self.job_selected_objects[job_id])
                            except Exception as e:
                                logging.error(f"Error in scheduled backup {job_id}: {str(e)}")
                                self.status_message = f"Scheduled backup failed: {str(e)}"
                                dpg.set_value("status_text", self.status_message)
                        
                        # Add the job to the scheduler
                        self.scheduler.add_job(
                            create_scheduled_backup,
                            trigger=CronTrigger(hour=hour, minute=minute),
                            id=job_id,
                            name=f"Daily Backup at {hour:02d}:{minute:02d}"
                        )
                        
                        # Restore last run time if it exists
                        if job_id in data.get('last_runs', {}):
                            try:
                                self.job_last_runs[job_id] = datetime.fromisoformat(data['last_runs'][job_id])
                            except (ValueError, TypeError) as e:
                                logging.error(f"Error parsing last run time for job {job_id}: {e}")
                    
                    except Exception as e:
                        logging.error(f"Error loading job {job_data.get('id', 'unknown')}: {e}")
                        continue
                
                logging.info(f"Successfully loaded {len(data['jobs'])} schedules")
                
        except Exception as e:
            logging.error(f"Error loading schedules: {str(e)}")
    
    def save_schedules(self):
        """Save current schedules to JSON file atomically and with backup."""
        try:
            data = {
                'jobs': [],
                'last_runs': {}
            }
            for job_id, meta in self.job_metadata.items():
                job_data = {
                    'id': job_id,
                    'hour': meta['hour'],
                    'minute': meta['minute'],
                    'objects': meta['objects']
                }
                data['jobs'].append(job_data)
            data['last_runs'] = {
                job_id: time.isoformat()
                for job_id, time in self.job_last_runs.items()
                if job_id in self.job_metadata
            }
            tmpfile = 'schedules.json.tmp'
            with open(tmpfile, 'w') as f:
                json.dump(data, f, indent=2)
            if os.path.exists('schedules.json'):
                shutil.copy2('schedules.json', 'schedules.json.bak')
            os.replace(tmpfile, 'schedules.json')
            logging.info(f"Successfully saved {len(data['jobs'])} schedules")
        except Exception as e:
            logging.error(f"Error saving schedules: {str(e)}")

    def _perform_backup_with_objects(self, objects_to_backup):
        """Perform backup with a specific set of objects"""
        if not self.app:
            self.status_message = "Not connected to Knack app."
            dpg.set_value("status_text", self.status_message)
            return
        
        # Create backup directory if it doesn't exist
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        # Create timestamp directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = os.path.join(self.backup_dir, f"backup_{timestamp}")
        os.makedirs(backup_folder)
        
        # Set up progress tracking
        total_containers = len(objects_to_backup)
        dpg.set_value("progress_bar", 0)
        dpg.configure_item("progress_bar", overlay=f"0/{total_containers}")
        
        # Perform backup for each selected container
        for i, container_id in enumerate(objects_to_backup):
            try:
                # Update progress
                container_name = self._get_container_name(container_id)
                dpg.set_value("progress_text", f"Backing up {container_name} ({i+1}/{total_containers})")
                dpg.set_value("progress_bar", (i + 1) / total_containers)
                dpg.configure_item("progress_bar", overlay=f"{i+1}/{total_containers}")
                
                # Get records
                records = self.app.get(container_id)
                
                if records:
                    # Format records
                    formatted_records = [record.format() for record in records]
                    
                    # Save to CSV
                    self._save_to_csv(formatted_records, container_id, container_name, backup_folder)
                    
                    # Also save raw JSON for complete backup
                    self._save_to_json(formatted_records, container_id, container_name, backup_folder)
                
            except Exception as e:
                logging.error(f"Failed to backup {container_id}: {str(e)}")
                self.status_message = f"Failed to backup {container_id}: {str(e)}"
                dpg.set_value("status_text", self.status_message)
        
        # Complete progress
        dpg.set_value("progress_bar", 1.0)
        dpg.configure_item("progress_bar", overlay=f"{total_containers}/{total_containers}")
        dpg.set_value("progress_text", "Backup completed!")
        self.status_message = f"Backup completed successfully! Backup saved to: {backup_folder}"
        dpg.set_value("status_text", self.status_message)

def main():
    app = KnackpyBackupGUI()

if __name__ == "__main__":
    main() 