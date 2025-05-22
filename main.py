import knackpy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import csv
from datetime import datetime

class KnackpyBackupUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Knackpy Backup Tool")
        self.root.geometry("800x600")
        
        self.app_id = tk.StringVar()
        self.api_key = tk.StringVar()
        self.app = None
        self.containers = []
        
        # Backup variables
        self.selected_containers = []
        self.backup_dir = tk.StringVar(value=os.path.join(os.getcwd(), "knack_backup"))
        
        self.create_widgets()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Connection frame
        connection_frame = ttk.LabelFrame(main_frame, text="Connection", padding="10")
        connection_frame.pack(fill=tk.X, pady=10)
        
        # App ID
        ttk.Label(connection_frame, text="App ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(connection_frame, textvariable=self.app_id, width=40).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # API Key
        ttk.Label(connection_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(connection_frame, textvariable=self.api_key, width=40, show="*").grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Connect button
        ttk.Button(connection_frame, text="Connect", command=self.connect_to_app).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Backup frame
        backup_frame = ttk.LabelFrame(main_frame, text="Backup", padding="10")
        backup_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Container selection
        ttk.Label(backup_frame, text="Select Objects to Backup:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Container list with checkboxes
        self.container_frame = ttk.Frame(backup_frame)
        self.container_frame.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, pady=5)
        
        # Backup directory
        ttk.Label(backup_frame, text="Backup Directory:").grid(row=2, column=0, sticky=tk.W, pady=5)
        dir_frame = ttk.Frame(backup_frame)
        dir_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Entry(dir_frame, textvariable=self.backup_dir, width=40).pack(side=tk.LEFT)
        ttk.Button(dir_frame, text="...", command=self.select_backup_dir, width=3).pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(backup_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Select All", command=self.select_all_containers).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self.deselect_all_containers).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Backup Selected", command=self.backup_selected).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress_frame = ttk.Frame(backup_frame)
        self.progress_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=5)
        
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(anchor=tk.W, pady=5)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, mode="determinate", length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Not connected")
        self.status_label.pack(anchor=tk.W, pady=5)
        
        # Configure grid weights
        backup_frame.columnconfigure(1, weight=1)
        backup_frame.rowconfigure(1, weight=1)
    
    def connect_to_app(self):
        try:
            self.app = knackpy.App(app_id=self.app_id.get(), api_key=self.api_key.get())
            self.status_label.config(text=f"Connected to Knack application")
            
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
            
            messagebox.showinfo("Success", f"Connected to Knack application successfully!\nFound {num_objects} objects.")
            
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
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
        
        # Show success message
        messagebox.showinfo("Success", f"Backup completed successfully!\nBackup saved to: {backup_folder}")
    
    def _get_container_name(self, container_id):
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

def main():
    root = tk.Tk()
    app = KnackpyBackupUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
