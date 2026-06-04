import os
import zipfile

def zip_project(zip_filename="store_intelligence_system.zip"):
    exclude_dirs = {
        '.git', 'node_modules', '__pycache__', '.venv', 'venv', '.vscode', '.idea', 'dist', 
        'Store 1', 'Store 2'
    }
    
    exclude_extensions = {
        '.zip', '.mp4', '.db', '.db-journal', '.log', '.pyc'
    }
    
    allowed_jsonl = "sample_eventsbe42122.jsonl"
    
    # Check if existing zip exists and remove it to avoid zipping into itself
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
        
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Modify dirs in-place to avoid traversing excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, '.')
                
                # Check exclusions
                _, ext = os.path.splitext(file.lower())
                
                # Skip the zip file itself and create_zip.py
                if file == zip_filename or file == "create_zip.py":
                    continue
                    
                if ext in exclude_extensions:
                    if file != allowed_jsonl:
                        continue
                
                path_parts = rel_path.split(os.sep)
                if any(part in exclude_dirs for part in path_parts):
                    continue
                    
                zipf.write(file_path, rel_path)

if __name__ == "__main__":
    zip_project()
    print("Zip file successfully created!")
