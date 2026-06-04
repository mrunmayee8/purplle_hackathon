import subprocess
import sys
import time
import os
import signal

def run():
    print("=========================================================")
    print("   Starting Purplle Store Intelligence System Runner   ")
    print("=========================================================")
    
    # 1. Install missing dependencies if needed
    print("[1/3] Ensuring backend dependencies are met...")
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import pydantic
    except ImportError:
        print("Backend dependencies missing. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "sqlalchemy", "pydantic"])
        
    print("[2/3] Launching FastAPI Backend on http://localhost:8000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "backend.main"],
        shell=True,
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    # Give the backend a few seconds to spin up and bind to port 8000
    time.sleep(3)
    
    print("[3/3] Launching Vite React Frontend on http://localhost:5173 ...")
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    
    # Check if node_modules exists, if not run npm install
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("node_modules not found in frontend. Running npm install (this may take a minute)...")
        subprocess.check_call("npm install", shell=True, cwd=frontend_dir)
        
    frontend_proc = subprocess.Popen(
        "npm run dev",
        shell=True,
        cwd=frontend_dir,
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    print("=========================================================")
    print("   System Running. Press Ctrl+C to terminate both servers. ")
    print("=========================================================")
    
    try:
        # Keep the main process alive and monitor child processes
        while True:
            time.sleep(1)
            # If backend died, restart or exit
            if backend_proc.poll() is not None:
                print("Backend server stopped unexpectedly.")
                break
            # If frontend died, exit
            if frontend_proc.poll() is not None:
                print("Frontend server stopped unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nTerminating servers...")
    finally:
        # Clean shutdown
        try:
            if backend_proc.poll() is None:
                if os.name == 'nt':
                    subprocess.call(f"taskkill /F /T /PID {backend_proc.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    backend_proc.terminate()
        except Exception:
            pass
            
        try:
            if frontend_proc.poll() is None:
                if os.name == 'nt':
                    subprocess.call(f"taskkill /F /T /PID {frontend_proc.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    frontend_proc.terminate()
        except Exception:
            pass
            
        print("Servers stopped. Goodbye!")

if __name__ == "__main__":
    run()
