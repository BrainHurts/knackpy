import knackpy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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

class KnackpyBackupUI:
    def __init__(self, root):
        self.job_metadata = {}  # job_id -> {'hour': int, 'minute': int, 'objects': list}
        self.root = root
        self.root.title("Knackpy Backup Tool")
        self.root.geometry("800x1000")
        
        self.app_id = tk.StringVar()
        self.api_key = tk.StringVar()
        self.app = None
        self.containers = []
        
        # Backup variables
        self.selected_containers = []
        self.backup_dir = tk.StringVar(value=os.path.join(os.getcwd(), "knack_backup"))
        
        # Scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        # Track job last run times and selected objects
        self.job_last_runs = {}
        self.job_selected_objects = {}
        
        # Load saved schedules
        self.status_message = tk.StringVar(value="Not connected")
        self.load_credentials_from_keyring(auto_connect=True)  # Load and try to connect
        self.load_schedules()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_widgets()
    
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
                    messagebox.showerror("Schedule Error", "Your schedules.json file is corrupt and will be reset.")
                    # Backup the corrupt file
                    shutil.move('schedules.json', 'schedules.json.bak')
                    return
                
                if not data.get('jobs'):
                    logging.info("No jobs found in schedules file")
                    return
                
                # Clear existing jobs
                self.scheduler.remove_all_jobs()
                self.job_last_runs.clear()
                self.job_selected_objects.clear()
                
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
                                messagebox.showerror("Backup Error", f"Scheduled backup failed: {str(e)}")
                        
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
    
    def on_closing(self):
        """Handle window closing"""
        try:
            # Save schedules
            self.save_schedules()
            
            # Shutdown scheduler
            self.scheduler.shutdown()
            
            # Destroy window
            self.root.destroy()
        except Exception as e:
            logging.error(f"Error during application shutdown: {str(e)}")
            self.root.destroy()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        connection_frame = ttk.LabelFrame(main_frame, text="Connection", padding="10")
        connection_frame.pack(fill=tk.X, pady=10)
        ttk.Label(connection_frame, text="App ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(connection_frame, textvariable=self.app_id, width=40).grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Label(connection_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(connection_frame, textvariable=self.api_key, width=40, show="*").grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Button(connection_frame, text="Connect", command=self.connect_to_app).grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(connection_frame, text="Save Credentials", command=self.save_credentials_to_keyring).grid(row=3, column=0, columnspan=2, pady=5)
        self.status_label = ttk.Label(main_frame, textvariable=self.status_message)
        self.status_label.pack(anchor=tk.W, pady=5)
        
        # --- Backup frame ---
        backup_frame = ttk.LabelFrame(main_frame, text="Backup", padding="10")
        backup_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        ttk.Label(backup_frame, text="Select Objects to Backup:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.container_frame = ttk.Frame(backup_frame)
        self.container_frame.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=5)
        ttk.Label(backup_frame, text="Backup Directory:").grid(row=2, column=0, sticky=tk.W, pady=5)
        dir_frame = ttk.Frame(backup_frame)
        dir_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Entry(dir_frame, textvariable=self.backup_dir, width=40).pack(side=tk.LEFT)
        ttk.Button(dir_frame, text="...", command=self.select_backup_dir, width=3).pack(side=tk.LEFT, padx=5)
        button_frame = ttk.Frame(backup_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Select All", command=self.select_all_containers).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self.deselect_all_containers).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Backup Selected", command=self.backup_selected).pack(side=tk.LEFT, padx=5)
        self.progress_frame = ttk.Frame(backup_frame)
        self.progress_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=5)
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(anchor=tk.W, pady=5)
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, mode="determinate", length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)

        # --- Schedule frame ---
        schedule_frame = ttk.LabelFrame(main_frame, text="Scheduled Jobs", padding="10")
        schedule_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        columns = ('Time', 'Objects', 'Status', 'Last Run', 'Next Run')
        self.jobs_tree = ttk.Treeview(schedule_frame, columns=columns, show='headings')
        self.jobs_tree.heading('Time', text='Time')
        self.jobs_tree.heading('Objects', text='Objects')
        self.jobs_tree.heading('Status', text='Status')
        self.jobs_tree.heading('Last Run', text='Last Run')
        self.jobs_tree.heading('Next Run', text='Next Run')
        self.jobs_tree.column('Time', width=80)
        self.jobs_tree.column('Objects', width=200)
        self.jobs_tree.column('Status', width=80)
        self.jobs_tree.column('Last Run', width=150)
        self.jobs_tree.column('Next Run', width=150)
        scrollbar = ttk.Scrollbar(schedule_frame, orient=tk.VERTICAL, command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=scrollbar.set)
        self.jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        schedule_button_frame = ttk.Frame(main_frame)
        schedule_button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(schedule_button_frame, text="Add Schedule", command=self.show_add_schedule_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(schedule_button_frame, text="Remove Selected", command=self.remove_selected_job).pack(side=tk.LEFT, padx=5)
        self.schedule_status = ttk.Label(main_frame, text="Scheduler is running")
        self.schedule_status.pack(anchor=tk.W, pady=5)
        self.update_job_list()
    
    def show_add_schedule_dialog(self):
        if not self.app:
            messagebox.showerror("Error", "Please connect to a Knack application first")
            return
            
        if not self.selected_containers:
            messagebox.showerror("Error", "Please select at least one object to backup")
            return
            
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Schedule")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Time selection
        time_frame = ttk.Frame(dialog, padding="10")
        time_frame.pack(fill=tk.X, pady=5)
        
        now = datetime.now()
        hour_var = tk.StringVar(value=str(now.hour))
        minute_var = tk.StringVar(value=str(now.minute))
        
        ttk.Label(time_frame, text="Hour (0-23):").pack(side=tk.LEFT)
        ttk.Entry(time_frame, textvariable=hour_var, width=5).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(time_frame, text="Minute (0-59):").pack(side=tk.LEFT)
        ttk.Entry(time_frame, textvariable=minute_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # Show selected objects
        objects_frame = ttk.LabelFrame(dialog, text="Selected Objects", padding="10")
        objects_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create a text widget to show selected objects
        objects_text = tk.Text(objects_frame, height=5, wrap=tk.WORD)
        objects_text.pack(fill=tk.BOTH, expand=True)
        
        # Add selected objects to the text widget
        selected_names = [self._get_container_name(container_id) for container_id in self.selected_containers]
        objects_text.insert('1.0', '\n'.join(selected_names))
        objects_text.config(state='disabled')
        
        # Add button
        def add_schedule():
            try:
                hour = int(hour_var.get())
                minute = int(minute_var.get())
                logging.info(f"[DEBUG] Adding job with hour={hour}, minute={minute}")
                
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
                        messagebox.showerror("Backup Error", f"Scheduled backup failed: {str(e)}")
                
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
                dialog.destroy()
                
                # Show success message
                messagebox.showinfo("Success", f"Schedule added successfully for {hour:02d}:{minute:02d}")
                
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=dialog)
        
        ttk.Button(dialog, text="Add Schedule", command=add_schedule).pack(pady=10)
    
    def _perform_backup_with_objects(self, objects_to_backup):
        """Perform backup with a specific set of objects"""
        if not self.app:
            return
        
        # Create backup directory if it doesn't exist
        backup_dir = self.backup_dir.get()
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Create timestamp directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = os.path.join(backup_dir, f"backup_{timestamp}")
        os.makedirs(backup_folder)
        
        # Set up progress tracking
        total_containers = len(objects_to_backup)
        self.progress_bar["maximum"] = total_containers
        self.progress_bar["value"] = 0
        
        # Perform backup for each selected container
        for i, container_id in enumerate(objects_to_backup):
            try:
                # Update progress
                container_name = self._get_container_name(container_id)
                self.progress_label.config(text=f"Backing up {container_name} ({i+1}/{total_containers})")
                self.progress_bar["value"] = i
                self.root.update()
                
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
                messagebox.showerror("Error", f"Failed to backup {container_id}: {str(e)}")
        
        # Complete progress
        self.progress_bar["value"] = total_containers
        self.progress_label.config(text="Backup completed!")
        
        # Show success message
        messagebox.showinfo("Success", f"Backup completed successfully!\nBackup saved to: {backup_folder}")
    
    def update_job_list(self):
        # Clear existing items
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        # Add current jobs
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M') if job.next_run_time else 'N/A'
            last_run = self.job_last_runs.get(job.id, 'N/A')
            if isinstance(last_run, datetime):
                last_run = last_run.strftime('%Y-%m-%d %H:%M')
            
            # Get stored objects for this job
            job_objects = self.job_selected_objects.get(job.id, [])
            selected_names = [self._get_container_name(container_id) for container_id in job_objects]
            objects_str = ', '.join(selected_names)
            if len(objects_str) > 50:  # Truncate if too long
                objects_str = objects_str[:47] + '...'
            
            # Get time from trigger
            trigger = job.trigger
            hour = getattr(trigger, 'hour', '*')
            minute = getattr(trigger, 'minute', '*')
            
            # Convert to integers if possible
            try:
                if isinstance(hour, set) and len(hour) == 1:
                    hour = next(iter(hour))
                if isinstance(minute, set) and len(minute) == 1:
                    minute = next(iter(minute))
                
                # Format time string
                if isinstance(hour, int) and isinstance(minute, int):
                    time_str = f"{hour:02d}:{minute:02d}"
                else:
                    time_str = f"{hour}:{minute}"
            except (ValueError, TypeError):
                time_str = f"{hour}:{minute}"
            
            self.jobs_tree.insert('', 'end', values=(
                time_str,
                objects_str,
                'Active',
                last_run,
                next_run,
                job.id  # Store job ID in the last column
            ))
        
        # Schedule next update
        self.root.after(1000, self.update_job_list)
    
    def remove_selected_job(self):
        selected = self.jobs_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a job to remove")
            return
        
        for item in selected:
            # Get the job ID from the tree item's values
            values = self.jobs_tree.item(item)['values']
            job_id = values[5] if len(values) > 5 else None
            if job_id and job_id in self.scheduler.get_jobs():
                self.scheduler.remove_job(job_id)
                # Clean up stored data
                self.job_last_runs.pop(job_id, None)
                self.job_selected_objects.pop(job_id, None)
                self.job_metadata.pop(job_id, None)
        
        self.update_job_list()
        self.save_schedules()
    
    def connect_to_app(self):
        try:
            self.app = knackpy.App(app_id=self.app_id.get(), api_key=self.api_key.get())
            self.status_message.set(f"Connected to Knack application")
            
            # Clear existing container checkboxes
            for widget in self.container_frame.winfo_children():
                widget.destroy()
            
            # Reset selected containers
            self.selected_containers = []
            
            # Create checkboxes for each object (not views)
            self.container_vars = {}
            
            # Get only objects
            objects = [c for c in self.app.containers if c.obj is not None]
            
            if not objects:
                messagebox.showinfo("Info", "No objects found in this application")
                return
            
            # Calculate grid layout
            num_objects = len(objects)
            cols = 3  # Number of columns in the grid
            rows = (num_objects + cols - 1) // cols  # Ceiling division
            
            # Create checkboxes in a grid layout
            for i, container in enumerate(objects):
                row = i // cols
                col = i % cols
                
                var = tk.BooleanVar(value=False)
                self.container_vars[container.obj] = var
                
                ttk.Checkbutton(
                    self.container_frame, 
                    text=f"{container.name} ({container.obj})", 
                    variable=var,
                    command=self.update_selected_containers
                ).grid(row=row, column=col, sticky=tk.W, padx=10, pady=2)
            
            message = f"Connected to Knack application successfully!\nFound {num_objects} objects."
            self.status_message.set(message)
            
        except Exception as e:
            self.status_message.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")
    
    def update_selected_containers(self):
        self.selected_containers = [
            container_id for container_id, var in self.container_vars.items() if var.get()
        ]
    
    def select_all_containers(self):
        for var in self.container_vars.values():
            var.set(True)
        self.update_selected_containers()
    
    def deselect_all_containers(self):
        for var in self.container_vars.values():
            var.set(False)
        self.update_selected_containers()
    
    def select_backup_dir(self):
        directory = filedialog.askdirectory(initialdir=self.backup_dir.get())
        if directory:
            self.backup_dir.set(directory)
    
    def backup_selected(self):
        if not self.app:
            messagebox.showerror("Error", "Please connect to a Knack application first")
            return
        
        if not self.selected_containers:
            messagebox.showerror("Error", "Please select at least one object to backup")
            return
        
        # Create backup directory if it doesn't exist
        backup_dir = self.backup_dir.get()
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Create timestamp directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = os.path.join(backup_dir, f"backup_{timestamp}")
        os.makedirs(backup_folder)
        
        # Set up progress tracking
        total_containers = len(self.selected_containers)
        self.progress_bar["maximum"] = total_containers
        self.progress_bar["value"] = 0
        
        # Perform backup for each selected container
        for i, container_id in enumerate(self.selected_containers):
            try:
                # Update progress
                container_name = self._get_container_name(container_id)
                self.progress_label.config(text=f"Backing up {container_name} ({i+1}/{total_containers})")
                self.progress_bar["value"] = i
                self.root.update()
                
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
                messagebox.showerror("Error", f"Failed to backup {container_id}: {str(e)}")
        
        # Complete progress
        self.progress_bar["value"] = total_containers
        self.progress_label.config(text="Backup completed!")
    
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

    def save_credentials_to_keyring(self):
        keyring.set_password("knackpy_backup", "app_id", self.app_id.get())
        keyring.set_password("knackpy_backup", "api_key", self.api_key.get())
        self.status_message.set("App ID and API Key saved to system keyring.")

    def load_credentials_from_keyring(self, auto_connect=False):
        app_id = keyring.get_password("knackpy_backup", "app_id")
        api_key = keyring.get_password("knackpy_backup", "api_key")
        if app_id:
            self.app_id.set(app_id)
        if api_key:
            self.api_key.set(api_key)
        if app_id and api_key and auto_connect:
            self.status_message.set("Loaded credentials from keyring. Connecting...")
            self.root.after(100, self.connect_to_app)
        elif app_id or api_key:
            self.status_message.set("Loaded credentials from keyring.")
        else:
            self.status_message.set("No credentials found in keyring.")

def main():
    root = tk.Tk()
    app = KnackpyBackupUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
