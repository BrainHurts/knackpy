# Knackpy Backup Tool

A simple GUI tool for backing up data from [Knack](https://knack.com) applications, built on the [Knackpy](https://github.com/cityofaustin/knackpy) library.

## Features

- Connect to Knack applications using your App ID and API Key
- Select specific objects to backup
- Export data to both CSV and JSON formats
- Automatic timestamped backups
- Simple, user-friendly interface

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/knackpy-backup.git
   cd knackpy-backup
   ```

2. Install required dependencies:
   ```
   pip install knackpy
   ```
   Note: tkinter is included with most Python installations.

## Usage

Run the application:
```
python main.py
```

### Creating a Backup

1. **Connect to your Knack app**
   - Enter your App ID and API Key
   - Click "Connect"

2. **Select objects to backup**
   - Check the boxes for the objects you want to backup
   - You can use "Select All" to check all objects at once

3. **Choose backup location**
   - Set the directory where backups will be saved
   - Each backup will be created in a timestamped folder

4. **Start the backup**
   - Click "Backup Selected"
   - Monitor progress in the status bar
   - When complete, the tool will show you the backup location

### Backup Format

Backups are saved in two formats:
- **CSV files**: Easy to open in Excel or other spreadsheet software
- **JSON files**: Complete data including complex field types

## Scheduling Backups

The tool includes a command-line version that can be scheduled to run automatically. Here's how to set it up:

### 1. Set Environment Variables

Set your Knack credentials as environment variables:

```bash
# macOS/Linux
export KNACK_APP_ID="your_app_id"
export KNACK_API_KEY="your_api_key"
export KNACK_BACKUP_DIR="/path/to/backup/directory"  # Optional

# Windows (Command Prompt)
set KNACK_APP_ID=your_app_id
set KNACK_API_KEY=your_api_key
set KNACK_BACKUP_DIR=C:\path\to\backup\directory

# Windows (PowerShell)
$env:KNACK_APP_ID="your_app_id"
$env:KNACK_API_KEY="your_api_key"
$env:KNACK_BACKUP_DIR="C:\path\to\backup\directory"
```

### 2. Schedule the Backup

#### On macOS/Linux (using cron):

1. Open your crontab:
   ```bash
   crontab -e
   ```

2. Add a line to run the backup daily at 10:19 AM:
   ```bash
   21 10 * * * cd /Users/ckinsfather/Desktop/Backup && /usr/bin/python3 scheduled_backup.py
   ```

#### On Windows (using Task Scheduler):

1. Open Task Scheduler
2. Create a new Basic Task
3. Set the trigger (e.g., Daily at 2:00 AM)
4. Action: Start a program
5. Program/script: `python`
6. Add arguments: `scheduled_backup.py`
7. Start in: `C:\path\to\knackpy-backup`

### 3. Monitor Backups

The scheduled backup script creates a log file (`knack_backup.log`) that records all backup operations. Check this file to monitor the success of your scheduled backups.

## Requirements

- Python 3.6+
- knackpy
- tkinter (included with Python)

## Why Use This Tool?

- Create regular backups of your Knack application data
- Export data for offline use or analysis
- Move data between Knack applications
- Simplify the process of backing up your Knack data without writing code

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [City of Austin](https://github.com/cityofaustin) for creating the knackpy library
- [Knack](https://www.knack.com/) for their low-code platform
