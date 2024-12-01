-------------------------------------------------------------------
Software Requirements:
- FreeCAD (latest version)

Installation:
Clone repository 
Set python configurator to the internal Python configurator in FreeCAD app if using IDE (PyCharm, VSCode, etc.)
  (path ex. /Applications/FreeCAD.app/Contents/Resources/bin/python)
Install requirements (pip install -r requirements.txt)
*Ignore any 'No module named ___' errors, it will still run just make sure to have `from setup import setup_freecad_env` and `setup_freecad_env()` before any FreeCAD imports

Program Executiuon: 

1. Command + shift + p on mac
2. Type: Python: Select Interpreter
3. Add the path, for mac it is the following after you install FreeCAD: /Applications/FreeCAD.app/Contents/Resources/bin/python 
4. Verify installation with: /Applications/FreeCAD.app/Contents/Resources/bin/python -m pip list
5.


WINDOWS:
If there are any missing DLLs:
1. Download and install the latest Visual C++ Redistributables (both x64 and x86 versions):
    https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170
2. After installation, restart your computer to ensure all libraries are loaded correctly.
3. In your FreeCAD\bin path, run:
    pip install msvc-runtime
