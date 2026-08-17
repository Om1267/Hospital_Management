import os
import shutil
import datetime

def backup_database():
    source_db = 'database.db'
    backup_dir = 'backups'
    
    if not os.path.exists(source_db):
        print(f"Error: Database file '{source_db}' does not exist.")
        return False
        
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"Created backup directory: '{backup_dir}'")
        
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f"database_backup_{timestamp}.db")
    
    try:
        shutil.copy2(source_db, backup_file)
        print(f"Database backed up successfully to: {backup_file}")
        return True
    except Exception as e:
        print(f"Failed to backup database: {str(e)}")
        return False

if __name__ == '__main__':
    backup_database()
