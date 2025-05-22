import knackpy
import json
import os
import csv
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('knack_backup.log'),
        logging.StreamHandler()
    ]
)

class KnackpyScheduledBackup:
    def __init__(self, app_id, api_key, backup_dir=None):
        self.app_id = app_id
        self.api_key = api_key
        self.backup_dir = backup_dir or os.path.join(os.getcwd(), "knack_backup")
        self.app = None
        
    def connect(self):
        try:
            self.app = knackpy.App(app_id=self.app_id, api_key=self.api_key)
            logging.info("Connected to Knack application successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to connect: {str(e)}")
            return False
    
    def backup_all_objects(self):
        if not self.app:
            if not self.connect():
                return False
        
        # Create backup directory if it doesn't exist
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        # Create timestamp directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = os.path.join(self.backup_dir, f"backup_{timestamp}")
        os.makedirs(backup_folder)
        
        # Get only objects (not views)
        objects = [c for c in self.app.containers if c.obj is not None]
        
        if not objects:
            logging.warning("No objects found in this application")
            return False
        
        total_objects = len(objects)
        logging.info(f"Starting backup of {total_objects} objects")
        
        # Perform backup for each object
        for i, container in enumerate(objects, 1):
            try:
                logging.info(f"Backing up {container.name} ({i}/{total_objects})")
                
                # Get records
                records = self.app.get(container.obj)
                
                if records:
                    # Format records
                    formatted_records = [record.format() for record in records]
                    
                    # Save to CSV
                    self._save_to_csv(formatted_records, container.obj, container.name, backup_folder)
                    
                    # Also save raw JSON for complete backup
                    self._save_to_json(formatted_records, container.obj, container.name, backup_folder)
                    
                    logging.info(f"Successfully backed up {container.name} ({len(records)} records)")
                else:
                    logging.warning(f"No records found for {container.name}")
                
            except Exception as e:
                logging.error(f"Failed to backup {container.name}: {str(e)}")
        
        logging.info(f"Backup completed! Backup saved to: {backup_folder}")
        return True
    
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
    # Load configuration from environment variables or config file
    app_id = os.getenv('KNACK_APP_ID')
    api_key = os.getenv('KNACK_API_KEY')
    backup_dir = os.getenv('KNACK_BACKUP_DIR')
    
    if not app_id or not api_key:
        logging.error("Please set KNACK_APP_ID and KNACK_API_KEY environment variables")
        return
    
    backup = KnackpyScheduledBackup(app_id, api_key, backup_dir)
    backup.backup_all_objects()

if __name__ == "__main__":
    main() 