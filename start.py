#!/bin/bash

import os
import subprocess
import time
import sys

def main():
    # Get the absolute path to the test directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(current_dir, 'test')
    
    # Path to FreeCAD's Python
    # UPDATE THIS ACCORDING TO YOUR COMPUTER AFTER INSTALLING FREECAD

    # macOS specific location of FreCAD python. Please change according to your own path.
    # Windows version is below (still need to change path)
    freecad_python = r'/Applications/FreeCAD.app/Contents/Resources/bin/python'
    # freecad_python = r'C:\Users\bmoss\FreeCAD\bin\python.exe'

    
    # Command to start the main FreeCAD application
    main_cmd = [freecad_python, 'main.py']
    
    # Command to start the hand tracking client
    client_cmd = [freecad_python, 'hand_tracking_client.py']
    
    try:
        # Change to test directory
        os.chdir(test_dir)
        print("Starting FreeCAD application...")
        
        # Start FreeCAD app in a new process
        freecad_process = subprocess.Popen(main_cmd)
        
        # Wait a bit for FreeCAD to initialize
        time.sleep(3)
        
        print("Starting hand tracking client...")
        # Start hand tracking client
        client_process = subprocess.Popen(client_cmd)
        
        # Wait for processes to complete
        freecad_process.wait()
        client_process.wait()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        # Clean up processes
        if 'freecad_process' in locals():
            freecad_process.terminate()
        if 'client_process' in locals():
            client_process.terminate()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()