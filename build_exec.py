# Save as: build_executable.py
# Run: python build_executable.py

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    required = ['PySide6', 'reportlab']
    
    print("Checking dependencies...")
    for package in required:
        try:
            __import__(package.replace('-', '_').lower())
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ Missing: {package}")
            print(f"  Run: pip install {package}")
            return False
    return True

def create_spec_file():
    """Create PyInstaller spec file"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.building.api import COLLECT, EXE
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree, TOC
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Application name
app_name = "Editor's Logger"

# Add app icon (if you have one)
# icon_path = 'icon.ico'  # For Windows
# icon_path = 'icon.icns'  # For macOS

# Analysis
a = Analysis(
    ['EditorsLogGenerator_final.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include translations.json if it exists
        ('translations.json', '.') if os.path.exists('translations.json') else None,
        # Include any other data files
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'reportlab',
        'reportlab.pdfbase.ttfonts',
        'sqlite3',
        'json',
        'csv',
        're',
        'socket',
        'tempfile',
        'pathlib',
        'datetime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

# Remove None entries from datas
a.datas = [x for x in a.datas if x is not None]

# Executable
pyz = PYZ(a.pure)

# For Windows
if sys.platform == 'win32':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name=app_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,  # Set to True for debugging
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        # icon=icon_path if 'icon_path' in locals() else None,
    )

# For macOS
elif sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name=app_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,  # Important for macOS
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        # icon=icon_path if 'icon_path' in locals() else None,
    )

# For Linux
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name=app_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

# Collect
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)
'''
    
    with open('editors_logger.spec', 'w') as f:
        f.write(spec_content)
    print("✓ Created spec file: editors_logger.spec")

def build_for_windows():
    """Build for Windows"""
    print("\\nBuilding for Windows...")
    
    # Create spec file for Windows
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.building.api import COLLECT, EXE
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree, TOC
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

a = Analysis(
    ['EditorsLogGenerator_final.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('translations.json', '.') if os.path.exists('translations.json') else None,
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'reportlab',
        'reportlab.pdfbase.ttfonts',
        'sqlite3',
        'json',
        'csv',
        're',
        'socket',
        'tempfile',
        'pathlib',
        'datetime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
    optimize=1,
)

# Remove None entries from datas
a.datas = [x for x in a.datas if x is not None]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="Editor's Logger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Editor's Logger",
)
'''
    
    with open('build_windows.spec', 'w') as f:
        f.write(spec_content)
    
    # Build
    cmd = ['pyinstaller', 'build_windows.spec', '--clean', '--noconfirm']
    subprocess.run(cmd)
    
    print("✓ Windows build complete!")
    print(f"  Executable: dist\\Editor's Logger\\Editor's Logger.exe")

def build_for_mac():
    """Build for macOS"""
    print("\\nBuilding for macOS...")
    
    # Create spec file for macOS
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.building.api import COLLECT, EXE
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree, TOC
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# For macOS App Bundle
app_name = "Editor's Logger"

a = Analysis(
    ['EditorsLogGenerator_final.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('translations.json', '.') if os.path.exists('translations.json') else None,
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'reportlab',
        'reportlab.pdfbase.ttfonts',
        'sqlite3',
        'json',
        'csv',
        're',
        'socket',
        'tempfile',
        'pathlib',
        'datetime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

# Remove None entries from datas
a.datas = [x for x in a.datas if x is not None]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # Important for macOS
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# Create .app bundle
app = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name + '.app',
)
'''
    
    with open('build_mac.spec', 'w') as f:
        f.write(spec_content)
    
    # Build
    cmd = ['pyinstaller', 'build_mac.spec', '--clean', '--noconfirm']
    subprocess.run(cmd)
    
    print("✓ macOS build complete!")
    print(f"  App: dist/Editor's Logger.app")

def build_for_linux():
    """Build for Linux"""
    print("\\nBuilding for Linux...")
    
    # Create spec file for Linux
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.building.api import COLLECT, EXE
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree, TOC
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

a = Analysis(
    ['EditorsLogGenerator_final.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('translations.json', '.') if os.path.exists('translations.json') else None,
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'reportlab',
        'reportlab.pdfbase.ttfonts',
        'sqlite3',
        'json',
        'csv',
        're',
        'socket',
        'tempfile',
        'pathlib',
        'datetime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

# Remove None entries from datas
a.datas = [x for x in a.datas if x is not None]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="editors_logger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Editor's Logger",
)
'''
    
    with open('build_linux.spec', 'w') as f:
        f.write(spec_content)
    
    # Build
    cmd = ['pyinstaller', 'build_linux.spec', '--clean', '--noconfirm']
    subprocess.run(cmd)
    
    print("✓ Linux build complete!")
    print(f"  Executable: dist/Editor's Logger/editors_logger")

def create_installer_package():
    """Create a simple installer package"""
    print("\\nCreating distribution package...")
    
    # Create dist folder structure
    dist_folder = "Editor's Logger Distribution"
    os.makedirs(dist_folder, exist_ok=True)
    
    # Copy README
    readme_content = """# Editor's Logger

A professional tool for video editors to log and manage takes, shots, and scenes.

## Features
- Project management with SQLite database
- Import CSV files from editing software
- Drag & drop still images
- Keyboard shortcuts for rapid rating
- Generate professional PDF reports
- Multi-language support (English/Vietnamese)

## Installation
Just run the executable. No installation required.

## First Run
1. Create a new project
2. Import CSV from your editing software
3. Drag & drop still images folder
4. Rate takes and add notes
5. Generate PDF reports

## Keyboard Shortcuts
- **1, 2, 3, Q, E**: Rate takes (1-5)
- **Cmd/Ctrl + S**: Save annotations
- **Up/Down Arrow**: Navigate between takes
- **Cmd/Ctrl + C**: Copy text
- **Cmd/Ctrl + V**: Paste text

## Support
For issues or feature requests, please contact the developer.

---
© 2024 Editor's Logger by cubiii.edits
"""
    
    with open(os.path.join(dist_folder, "README.txt"), "w") as f:
        f.write(readme_content)
    
    print(f"✓ Created distribution package in: {dist_folder}/")
    print("  Include:")
    print("  - README.txt")
    print("  - Your built executable")
    print("  - translations.json (if you have translations)")

def main():
    print("=" * 60)
    print("EDITOR'S LOGGER - EXECUTABLE BUILDER")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        print("\\nMissing dependencies. Please install them first.")
        return
    
    # Check if main script exists
    if not os.path.exists("EditorsLogGenerator_final.py"):
        print("\\n✗ Error: EditorsLogGenerator_final.py not found!")
        print("  Make sure it's in the same directory.")
        return
    
    print("\\nMain script found: EditorsLogGenerator_final.py")
    
    # Check if translations.json exists
    if os.path.exists("translations.json"):
        print("✓ Found translations.json")
    else:
        print("⚠ Note: translations.json not found (optional)")
    
    # Menu
    print("\\n" + "=" * 60)
    print("Select build platform:")
    print("1. Windows")
    print("2. macOS")
    print("3. Linux")
    print("4. Create distribution package")
    print("5. Build for all platforms")
    print("Q. Quit")
    print("=" * 60)
    
    choice = input("\\nEnter choice (1-5 or Q): ").strip().lower()
    
    if choice == '1':
        build_for_windows()
    elif choice == '2':
        build_for_mac()
    elif choice == '3':
        build_for_linux()
    elif choice == '4':
        create_installer_package()
    elif choice == '5':
        build_for_windows()
        build_for_mac()
        build_for_linux()
        create_installer_package()
    elif choice == 'q':
        print("\\nGoodbye!")
        return
    else:
        print("\\nInvalid choice!")
        return
    
    print("\\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)
    print("\\nNext steps:")
    print("1. Test the executable in the 'dist' folder")
    print("2. Share the entire 'dist' folder with users")
    print("3. For macOS: You may need to right-click and 'Open'")
    print("   (to bypass Gatekeeper on first run)")
    print("\\nFor professional distribution:")
    print("- Consider code signing for macOS/Windows")
    print("- Create an installer (Inno Setup for Windows)")
    print("- Test on clean systems without Python installed")

if __name__ == "__main__":
    try:
        import PyInstaller
        print("✓ PyInstaller is installed")
    except ImportError:
        print("\\n✗ PyInstaller not installed!")
        print("  Install with: pip install pyinstaller")
        sys.exit(1)
    
    main()