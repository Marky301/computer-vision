#  Contains FreeCAD environment setup code
import os
import sys

#SAVED

def setup_freecad_env():
    """Set up the FreeCAD environment and Python path."""

    """ This portion is for macOS! Please comment this out if you're on windows and use the other sectio"""

    # Use absolute path for macOS
    FREECAD_ROOT = '/Applications/FreeCAD.app'
    FREECAD_RESOURCES = os.path.join(FREECAD_ROOT, 'Contents', 'Resources')
    FREECAD_LIB = os.path.join(FREECAD_RESOURCES, 'lib')

    print(f"Looking for FreeCAD in: {FREECAD_ROOT}")
    print(f"Resources path: {FREECAD_RESOURCES}")
    print(f"Library path: {FREECAD_LIB}")

    if not os.path.exists(FREECAD_ROOT):
        raise EnvironmentError(f"FreeCAD root directory not found: {FREECAD_ROOT}")

    # Add necessary paths for macOS
    sys.path.append(FREECAD_LIB)
    sys.path.append(os.path.join(FREECAD_RESOURCES, 'bin'))
    sys.path.append(os.path.join(FREECAD_LIB, 'site-packages'))

    # Set required environment variables
    os.environ['PYTHONHOME'] = FREECAD_RESOURCES
    os.environ['PYTHONPATH'] = os.path.join(FREECAD_LIB, 'site-packages')

    print("Environment setup completed successfully")



    """ Everything below this section is for windows. Please adjust FREECAD_LIB and FREECAD_ROOT according to your need."""
    # FREECAD_ROOT = r'/Applications/FreeCAD.app'
    # FREECAD_LIB = os.path.join(FREECAD_ROOT, 'bin')
    #
    # if not os.path.exists(FREECAD_ROOT):
    #     raise EnvironmentError(f"FreeCAD root directory not found: {FREECAD_ROOT}")
    #
    # sys.path.append(os.path.join(FREECAD_LIB, 'Lib'))
    # sys.path.append(os.path.join(FREECAD_LIB, 'site-packages'))
    #
    # # Clear existing sys.path to avoid conflicts
    # # sys.path.clear()
    # # sys.path.extend([
    # #     '',
    # #     os.path.join(FREECAD_ROOT, 'lib/python310.zip'),
    # #     os.path.join(FREECAD_ROOT, 'lib/python3.10'),
    # #     os.path.join(FREECAD_ROOT, 'lib/python3.10/lib-dynload'),
    # #     os.path.join(FREECAD_ROOT, 'lib/python3.10/site-packages'),
    # #     FREECAD_LIB
    # # ])
    #
    # #print("Current sys.path:", sys.path)  # Debug print to verify paths
    #
    # # Set required environment variables
    # os.environ['PYTHONHOME'] = FREECAD_ROOT
    # os.environ['PYTHONPATH'] = os.path.join(FREECAD_LIB, 'site-packages')