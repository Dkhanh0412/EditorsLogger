#!/usr/bin/env python3
# Fix macOS app bundle structure

import os
import sys
import shutil
import plistlib
from pathlib import Path

def fix_macos_app():
    """Fix macOS .app bundle after PyInstaller build"""
    
    app_name = "Editors Logger"
    app_path = Path(f"dist/{app_name}.app")
    
    if not app_path.exists():
        print(f"❌ App bundle not found: {app_path}")
        return
    
    print(f"🔧 Fixing macOS app bundle: {app_path}")
    
    # Ensure proper structure
    contents_dir = app_path / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    
    # Create directories
    for dir_path in [contents_dir, macos_dir, resources_dir]:
        dir_path.mkdir(exist_ok=True, parents=True)
    
    # Move the executable
    old_executable = app_path / app_name
    if old_executable.exists():
        new_executable = macos_dir / app_name
        shutil.move(str(old_executable), str(new_executable))
        os.chmod(str(new_executable), 0o755)
        print(f"✓ Moved executable to: {new_executable}")
    
    # Move translations.json to Resources
    translations_src = Path("translations.json")
    if translations_src.exists():
        translations_dest = resources_dir / "translations.json"
        shutil.copy(str(translations_src), str(translations_dest))
        print(f"✓ Copied translations.json to Resources")
    
    # Create Info.plist
    info_plist = {
        'CFBundleName': app_name,
        'CFBundleDisplayName': app_name,
        'CFBundleIdentifier': 'com.cubiii.edits.EditorsLogger',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'CFBundleExecutable': app_name,
        'CFBundleIconFile': '',
        'LSMinimumSystemVersion': '10.15',
        'NSHumanReadableCopyright': '© 2024 by cubiii.edits',
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
        'LSUIElement': False,  # Show in Dock
    }
    
    plist_path = contents_dir / "Info.plist"
    with open(plist_path, 'wb') as f:
        plistlib.dump(info_plist, f)
    print(f"✓ Created Info.plist")
    
    # Create PkgInfo
    with open(contents_dir / "PkgInfo", 'w') as f:
        f.write('APPL????')
    
    print(f"\n✅ macOS app bundle fixed successfully!")
    print(f"📦 App location: {app_path}")
    print("\n📝 First run instructions:")
    print("   1. Right-click the app")
    print("   2. Select 'Open'")
    print("   3. Click 'Open' when warned about unidentified developer")
    print("\n📁 Files will be saved in:")
    print(f"   {app_path}/Contents/Resources/EditorLog_Projects/")

if __name__ == "__main__":
    fix_macos_app()