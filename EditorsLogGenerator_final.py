import sys, os, csv, re, sqlite3, json, socket, tempfile  # Added socket import
def get_app_base_path():
    """Get the correct base path for the application"""
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        base_path = os.path.dirname(sys.executable)
        if sys.platform == 'darwin' and '.app' in base_path:
            # For macOS .app bundles, go up to the .app root
            while 'Contents' in base_path:
                base_path = os.path.dirname(base_path)
        return base_path
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))
from datetime import datetime
from pathlib import Path
class TranslationManager:
    """Manages EN/VI translations"""
    def __init__(self, json_path="translations.json"):
        self.current_lang = "en"  # Default language
        self.translations = self._load_translations(json_path)

        try:
            from PySide6.QtCore import QSettings
            settings = QSettings("EditorLogger", "EditorLogger")
            saved_lang = settings.value("language", "en")
            if saved_lang in self.translations:
                self.current_lang = saved_lang
        except Exception as e:
            print(f"Warning: Could not load language settings: {e}")
    
    def _load_translations(self, json_path):
        """Load translations from JSON file - works in both dev and bundled modes"""
        try:
            if getattr(sys, 'frozen', False):
                app_dir = os.path.dirname(sys.executable)
                full_path = os.path.join(app_dir, json_path)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                full_path = os.path.join(script_dir, json_path)
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"WARNING: translations.json not found at {full_path}")
                # Return minimal working translations
                return {
                    "en": {
                        "Add New Take": "Add New Take",
                        "New Project": "New Project",
                        "Back to Projects": "← Back to Projects"
                    },
                    "vi": {
                        "Add New Take": "Thêm Take Mới",
                        "New Project": "Dự Án Mới",
                        "Back to Projects": "← Quay Lại Dự Án"
                    }
                }
        except Exception as e:
            print(f"ERROR loading translations: {e}")
            return {"en": {}, "vi": {}}
    
    def set_language(self, lang_code):
        """Switch language (en or vi)"""
        if lang_code in self.translations:
            self.current_lang = lang_code
            # Save preference
            try:
                from PySide6.QtCore import QSettings
                settings = QSettings("EditorLogger", "EditorLogger")
                settings.setValue("language", lang_code)
            except Exception as e:
                print(f"Warning: Could not save language setting: {e}")
            return True
        return False
    
    def get(self, key, default=None):
        """Get translated text for current language"""
        if self.current_lang in self.translations:
            return self.translations[self.current_lang].get(key, default or key)
        return default or key
    
    def t(self, key):
        """Shorthand for get()"""
        return self.get(key)

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, 
                             QLabel, QLineEdit, QTextEdit, QHeaderView, 
                             QComboBox, QRadioButton, QButtonGroup, QFrame, QFileDialog,
                             QDialog, QSpinBox, QMessageBox, QScrollArea, QGridLayout, QProgressBar)
from PySide6.QtGui import QPixmap, QColor, QFont, QIcon
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QRect, QSize
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

class ProjectManager:
    """Manages SQLite database for projects - Works for both dev and bundled apps"""
    def __init__(self, db_path=None):
        if db_path is None:
            # Get the correct base path for bundled vs development
            if getattr(sys, 'frozen', False):
                # Running as bundled executable
                if sys.platform == 'darwin':
                    # macOS: Put in app bundle's Resources folder
                    base_dir = os.path.dirname(os.path.dirname(sys.executable))
                    if base_dir.endswith('.app/Contents/MacOS'):
                        base_dir = base_dir.replace('Contents/MacOS', '')
                    db_dir = os.path.join(base_dir, 'Resources', 'EditorLog_Projects')
                else:
                    # Windows/Linux: Put next to executable
                    base_dir = os.path.dirname(sys.executable)
                    db_dir = os.path.join(base_dir, 'EditorLog_Projects')
            else:
                # Running as script
                db_dir = os.path.expanduser("~/Documents/EditorLog_Projects")
            
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, 'projects.db')
        
        print(f"📁 Database path: {db_path}")
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database with projects table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL,
                created_date TEXT,
                modified_date TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def create_project(self, name):
        """Create new project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        try:
            cursor.execute('''
                INSERT INTO projects (name, data, created_date, modified_date)
                VALUES (?, ?, ?, ?)
            ''', (name, json.dumps({}), now, now))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def get_projects(self):
        """Get all projects"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name, modified_date FROM projects ORDER BY modified_date DESC')
        projects = cursor.fetchall()
        conn.close()
        return projects
    
    def get_project_data(self, name):
        """Load project data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM projects WHERE name = ?', (name,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return {}
        
        try:
            return json.loads(result[0])
        except json.JSONDecodeError:
            print(f"⚠️ Corrupt project data for '{name}'")
            return {}
    
    def save_project_data(self, name, data):
        """Save project data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE projects SET data = ?, modified_date = ? WHERE name = ?
        ''', (json.dumps(data), now, name))
        conn.commit()
        conn.close()
    
    def delete_project(self, name):
        """Delete project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM projects WHERE name = ?', (name,))
        conn.commit()
        conn.close()

class CustomNotesBox(QTextEdit):
    """Custom QTextEdit that allows Cmd+S shortcut while typing"""
    save_requested = Signal()
    
    def eventFilter(self, obj, event):
        """Global event filter to catch key presses"""
        if event.type() == event.Type.KeyPress and not event.isAutoRepeat():
            # Check if we're in the main editor window (not home screen)
            if not hasattr(self, 'note_box'):
                return super().eventFilter(obj, event)
            
            # Get focused widget
            focused = QApplication.focusWidget()
            
            # Check if typing in note_box or content_box specifically
            is_in_notes = focused == self.note_box
            is_in_content = focused == self.content_box
            
            # Debug logging
            key_name = {Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3", Qt.Key_Q: "Q", Qt.Key_E: "E", Qt.Key_S: "S"}.get(event.key(), "")
            if key_name:
                print(f"Key: {key_name}, In notes: {is_in_notes}, In content: {is_in_content}, Focused: {type(focused).__name__}")
            
            # Cmd+S works everywhere - high priority
            if event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
                print("Cmd+S detected, calling confirm_save()")
                if hasattr(self, 'confirm_save'):
                    self.confirm_save()
                    return True
            
            # Rating shortcuts only when NOT in text boxes
            if not is_in_notes and not is_in_content:
                if event.key() == Qt.Key_1:
                    print("Setting rating 1")
                    self.set_rating(1)
                    return True
                elif event.key() == Qt.Key_2:
                    print("Setting rating 2")
                    self.set_rating(2)
                    return True
                elif event.key() == Qt.Key_3:
                    print("Setting rating 3")
                    self.set_rating(3)
                    return True
                elif event.key() == Qt.Key_Q:
                    print("Setting rating 4")
                    self.set_rating(4)
                    return True
                elif event.key() == Qt.Key_E:
                    print("Setting rating 5")
                    self.set_rating(5)
                    return True
        
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        # Only handle Cmd+S, let everything else pass through normally
        if event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.save_requested.emit()
            return
        
        # Let all other keys work normally (including 1,2,3,Q,W for typing)
        super().keyPressEvent(event)

class ToastNotification(QLabel):
    """Toast notification that appears in top-right corner"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLabel {
                background-color: #2D2D2D;
                color: #00FF00;
                border-radius: 5px;
                padding: 15px 25px;
                font-family: 'Arial';
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #3d5afe;
            }
        """)
        self.setMaximumWidth(350)
        self.setWordWrap(True)
        self.hide()
    
    def show_toast(self, message, duration=2000):
        """Show toast notification with auto-hide"""
        self.setText(message)
        self.show()
        self.raise_()  # Make sure it's on top
        QApplication.processEvents()  # Force UI update
        
        if duration > 0:
            QTimer.singleShot(duration, self.hide)
        # If duration=0, it won't auto-hide
    
    def show_persistent(self, message):
        """Show a message that won't auto-hide"""
        self.show_toast(message, duration=0)
    
    def update_message(self, new_message):
        """Update the current toast message"""
        if self.isVisible():
            self.setText(new_message)
            QApplication.processEvents()

class DragDropLabel(QLabel):
    """Custom label that accepts drag-drop events and captures keyboard shortcuts on hover"""
    dropped = Signal(list)
    rating_shortcut = Signal(int)  # Emit rating when key pressed while hovering
    save_shortcut = Signal()  # Emit save request
    navigate_take = Signal(str)  # Emit 'up' or 'down' for navigation
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.parent_window = parent
        self.default_style = "border: 2px dashed #3d5afe; background: #000; border-radius: 4px; color: #666;"
        self.focused_style = "border: 2px solid #00FF00; background: #001100; border-radius: 4px; color: #666;"
    
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
    
    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
    
    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            paths = [url.toLocalFile() for url in urls]
            self.dropped.emit(paths)
            e.acceptProposedAction()
    
    def enterEvent(self, event):
        """When mouse enters the still preview area, grab focus and highlight"""
        self.setFocus()
        self.setStyleSheet(self.focused_style)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """When mouse leaves, restore normal style"""
        self.setStyleSheet(self.default_style)
        super().leaveEvent(event)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts when hovering over still preview"""
        if event.isAutoRepeat():
            return
        
        # Arrow keys for navigation
        if event.key() == Qt.Key_Up:
            self.navigate_take.emit('up')
            return
        elif event.key() == Qt.Key_Down:
            self.navigate_take.emit('down')
            return
        
        # Cmd+S to save
        if event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.save_shortcut.emit()
            return
        
        # Rating shortcuts
        if event.key() == Qt.Key_1:
            self.rating_shortcut.emit(1)
        elif event.key() == Qt.Key_2:
            self.rating_shortcut.emit(2)
        elif event.key() == Qt.Key_3:
            self.rating_shortcut.emit(3)
        elif event.key() == Qt.Key_Q:
            self.rating_shortcut.emit(4)
        elif event.key() == Qt.Key_E:
            self.rating_shortcut.emit(5)
        else:
            super().keyPressEvent(event)

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        self.label = QLabel("Editor's Logger\nLoading...")
        self.label.setStyleSheet("color: #3d5afe; font-size: 18px; font-weight: bold;")
        self.label.setAlignment(Qt.AlignCenter)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate progress
        
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        self.setLayout(layout)
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.center() - self.rect().center())
        
    def update_message(self, message):
        self.label.setText(f"Editor's Logger\n{message}")
        QApplication.processEvents()  # Update UI

class AddTakeDialog(QDialog):
    """Dialog to add new takes"""
    def __init__(self, parent=None, translator=None):
        super().__init__(parent)
        self.translator = translator or TranslationManager()
        self.setWindowTitle(self.translator.t("Add New Take"))
        self.setModal(True)
        self.setGeometry(100, 100, 700, 400)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel(self.translator.t("Shot Number:")))
        self.shot_input = QLineEdit()
        self.shot_input.setPlaceholderText(self.translator.t("e.g., SH-001"))
        self.shot_input.setMinimumHeight(40)
        layout.addWidget(self.shot_input)
        
        layout.addWidget(QLabel(self.translator.t("Source Filename:")))
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText(self.translator.t("e.g., A001_C001.MXF"))
        self.file_input.setMinimumHeight(40)
        layout.addWidget(self.file_input)
        
        layout.addWidget(QLabel(self.translator.t("Initial Notes:")))
        self.notes_input = QTextEdit()
        self.notes_input.setMinimumHeight(150)
        layout.addWidget(self.notes_input)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(self.translator.t("✓ Add Take"))
        ok_btn.setMinimumHeight(40)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(self.translator.t("✗ Cancel"))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def get_data(self):
        return {
            'shot': self.shot_input.text(),
            'file': self.file_input.text(),
            'notes': self.notes_input.toPlainText()
        }

class NewProjectDialog(QDialog):
    """Dialog to create new project"""
    def __init__(self, parent=None, translator=None):
        super().__init__(parent)
        self.translator = translator or TranslationManager()
        self.setWindowTitle(self.translator.t("New Project"))
        self.setModal(True)
        self.setGeometry(100, 100, 500, 200)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel(self.translator.t("Project Name:")))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self.translator.t("e.g., Shaun of the Dead"))
        self.name_input.setMinimumHeight(40)
        layout.addWidget(self.name_input)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(self.translator.t("✓ Create"))
        ok_btn.setMinimumHeight(40)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(self.translator.t("✗ Cancel"))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # Center the dialog on parent window
        if parent:
            parent_geometry = parent.geometry()
            dialog_width = 500
            dialog_height = 200
            x = parent_geometry.x() + (parent_geometry.width() - dialog_width) // 2
            y = parent_geometry.y() + (parent_geometry.height() - dialog_height) // 2
            self.setGeometry(x, y, dialog_width, dialog_height)
    
    def get_name(self):
        return self.name_input.text()

class ProjectCardWidget(QFrame):
    """Project card widget for home screen"""
    clicked = Signal(str)
    delete_requested = Signal(str)
    renamed = Signal(str, str)
    
    def __init__(self, name, modified_date, parent=None):
        super().__init__(parent)
        self.name = name
        self.is_editing_name = False
        self.original_name = name

        self.setStyleSheet("""
            QFrame {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 20px;
            }
            QFrame:hover {
                border: 1px solid #3d5afe;
                background-color: #252525;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)
        
        # Single horizontal layout with name, date, and delete button
        layout = QHBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Project name on the left - CREATE BEFORE USING
        self.title = QLabel(name)
        self.title.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 16px;")
        self.title.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.title)
        
        # Create the editable version
        self.title_edit = QLineEdit()
        self.title_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252525;
                border: 2px solid #3d5afe;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 16px;
                padding: 5px;
                border-radius: 4px;
            }
        """)
        self.title_edit.hide()
        self.title_edit.returnPressed.connect(self.save_name)
        self.title_edit.editingFinished.connect(self.cancel_edit_name)
        layout.addWidget(self.title_edit)
        
        # Stretch to push date and button to the right
        layout.addStretch()
        
        # Modified date on the right (read-only, not clickable)
        date_str = datetime.fromisoformat(modified_date).strftime('%d/%m/%Y %H:%M')
        self.date_label = QLabel(f"Modified: {date_str}")
        self.date_label.setStyleSheet("color: #888; font-size: 12px;")
        self.date_label.setCursor(Qt.ArrowCursor)
        self.date_label.setEnabled(False)
        layout.addWidget(self.date_label)
        
        # Delete button on the far right
        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setFixedSize(35, 35)
        self.delete_btn.setStyleSheet("background-color: #d32f2f; color: white; border-radius: 3px; font-size: 14px;")
        self.delete_btn.clicked.connect(self.on_delete)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.delete_btn)
    
    def mousePressEvent(self, event):
        """Handle clicks on the card"""
        # Don't open project if we're currently editing
        if self.is_editing_name:
            return
        
        if event.button() == Qt.LeftButton:
            # Check if click was on the delete button
            delete_btn_rect = self.delete_btn.geometry()
            if delete_btn_rect.contains(event.position().toPoint()):
                return
            
            # Otherwise, open the project (unless editing)
            self.clicked.emit(self.name)
    
    def mouseDoubleClickEvent(self, event):
        """Double-click to edit the project name"""
        if event.button() == Qt.LeftButton:
            title_rect = self.title.geometry()
            if title_rect.contains(event.pos()):
                self.start_edit_name()

    def start_edit_name(self):
        """Start editing the project name"""
        self.is_editing_name = True
        self.original_name = self.name
        
        self.title.hide()
        self.title_edit.show()
        self.title_edit.setText(self.name)
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def save_name(self):
        """Save the new project name"""
        new_name = self.title_edit.text().strip()
        
        if not new_name:
            # Empty name, cancel edit
            self.cancel_edit_name()
            return
        
        if new_name == self.original_name:
            # No change, just cancel
            self.cancel_edit_name()
            return
        
        # Emit signal to parent to handle the rename
        self.renamed.emit(self.original_name, new_name)
        
        # Update the card
        self.name = new_name
        self.title.setText(new_name)
        self.cancel_edit_name()
    
    def cancel_edit_name(self):
        """Cancel editing the project name"""
        self.is_editing_name = False
        self.title_edit.hide()
        self.title.show()

    def on_delete(self):
        self.delete_requested.emit(self.name)

class HomeScreen(QWidget):
    """Home screen with project list"""
    project_opened = Signal(str)

    def __init__(self, parent=None, translator=None):  # ADD translator parameter
        super().__init__(parent)
        self.pm = ProjectManager()
        self.translator = translator or TranslationManager()  # Use passed translator
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Centered title section
        title_layout = QVBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("EDITOR'S LOGGER")
        title.setStyleSheet("color: #3d5afe; font-weight: bold; font-size: 32px;")
        title.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title)
        
        version = QLabel("v1.0.0\nby cubiii.edits")
        version.setStyleSheet("color: #888; font-size: 14px; margin-top: 5px;")
        version.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(version)

        # ADD FLAG BUTTONS FOR LANGUAGE SELECTION
        flag_layout = QHBoxLayout()
        flag_layout.addStretch()  # Push flags to the right

        # US/UK split flag button
        self.english_flag_btn = QPushButton("🇺🇸/🇬🇧")
        self.english_flag_btn.setFixedSize(70, 45)
        self.english_flag_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                border: 2px solid #3d5afe;
                border-radius: 5px;
                font-size: 16px;
                color: white;
            }
            QPushButton:hover {
                background-color: #3d5afe;
            }
            QPushButton:pressed {
                background-color: #2a49c4;
            }
        """)
        self.english_flag_btn.setToolTip("English")
        self.english_flag_btn.clicked.connect(lambda: self.set_language("en"))
        flag_layout.addWidget(self.english_flag_btn)

        # Vietnam flag button
        self.vietnam_flag_btn = QPushButton("🇻🇳")
        self.vietnam_flag_btn.setFixedSize(70, 45)
        self.vietnam_flag_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                border: 2px solid #DA251D;
                border-radius: 5px;
                font-size: 22px;
                color: white;
            }
            QPushButton:hover {
                background-color: #DA251D;
            }
            QPushButton:pressed {
                background-color: #B51C15;
            }
        """)
        self.vietnam_flag_btn.setToolTip("Tiếng Việt")
        self.vietnam_flag_btn.clicked.connect(lambda: self.set_language("vi"))
        flag_layout.addWidget(self.vietnam_flag_btn)

        title_layout.addSpacing(50)
        title_layout.addLayout(flag_layout)

        layout.addLayout(title_layout)

        # Update button highlights based on current language
        self.update_flag_highlights()
        
        # New project button (centered)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.new_project_btn = QPushButton(self.translator.t("➕ New Project"))  # Store as instance variable
        self.new_project_btn.setMinimumHeight(50)
        self.new_project_btn.setMinimumWidth(200)
        self.new_project_btn.clicked.connect(self.create_new_project)
        button_layout.addWidget(self.new_project_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addSpacing(20)
        
        # Projects list in scroll area
        scroll = QScrollArea()
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #121212; }")
        scroll.setWidgetResizable(True)
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: #121212;")
        
        # Use vertical layout instead of grid - keeps uniform width
        self.cards_layout = QVBoxLayout(scroll_widget)
        self.cards_layout.setSpacing(15)
        self.cards_layout.setContentsMargins(20, 20, 20, 20)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        self.refresh_projects()

    def refresh_ui_with_translation(self):
        """Refresh UI elements with current translation"""
        # Update the new project button
        if hasattr(self, 'new_project_btn'):
            self.new_project_btn.setText(self.translator.t("➕ New Project"))
        
        # Refresh projects list
        self.refresh_projects()
    
    def refresh_projects(self):
        """Refresh project list"""
        # Check if cards_layout exists
        if not hasattr(self, 'cards_layout'):
            return

        # Clear all cards
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item:
                if item.widget():
                    item.widget().deleteLater()
        
        projects = self.pm.get_projects()
        if not projects:
            no_proj = QLabel(self.translator.t("No projects yet. Create one to get started!"))
            no_proj.setStyleSheet("color: #666; font-size: 14px;")
            no_proj.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(no_proj)
            return
        
        # Display projects in a single column - each card expands to fill width
        for name, modified_date in projects:
            card = ProjectCardWidget(name, modified_date)
            card.setMinimumHeight(80)   # Uniform height
            card.clicked.connect(self.on_project_clicked)
            card.delete_requested.connect(self.on_delete_project)
            self.cards_layout.addWidget(card, stretch=0)
        
        # Add spacer at the bottom to push cards to top
        self.cards_layout.addStretch()
    
    def on_project_clicked(self, project_name):
        self.project_opened.emit(project_name)
    
    def on_delete_project(self, project_name):
        """Delete a project after confirmation"""
        reply = QMessageBox.question(
            self,
            self.translator.t("Delete Project"),
            self.translator.t(f"Are you sure you want to delete '{project_name}'?\nThis cannot be undone."),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.pm.delete_project(project_name)
            self.refresh_projects()
    
    def create_new_project(self):
        dialog = NewProjectDialog(self, self.translator)
        if dialog.exec():
            name = dialog.get_name().strip()
            if not name:
                QMessageBox.warning(self, "Error", "Project name cannot be empty")
                return
            if self.pm.create_project(name):
                self.refresh_projects()
                QMessageBox.information(self, "Success", f"Project '{name}' created!")
            else:
                QMessageBox.warning(self, "Error", "Project already exists")

    def set_language(self, lang_code):
        """Set language and update UI"""
        if self.translator.set_language(lang_code):
            self.update_flag_highlights()
            self.refresh_ui_with_translation()

    def update_flag_highlights(self):
        """Update which flag is highlighted based on current language"""
        if not hasattr(self, 'english_flag_btn') or not hasattr(self, 'vietnam_flag_btn'):
            return
        
        if self.translator.current_lang == "en":
            # Highlight English flag
            self.english_flag_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d5afe;
                    border: 2px solid #3d5afe;
                    border-radius: 8px;
                    font-size: 22px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #4a6aff;
                }
            """)
            self.vietnam_flag_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D2D;
                    border: 2px solid #DA251D;
                    border-radius: 8px;
                    font-size: 22px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #DA251D;
                }
            """)
        else:  # Vietnamese
            # Highlight Vietnam flag
            self.english_flag_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D2D;
                    border: 2px solid #3d5afe;
                    border-radius: 8px;
                    font-size: 22px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #3d5afe;
                }
            """)
            self.vietnam_flag_btn.setStyleSheet("""
                QPushButton {
                    background-color: #DA251D;
                    border: 2px solid #DA251D;
                    border-radius: 8px;
                    font-size: 22px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #E83028;
                }
            """)
        
        self.refresh_projects()

class EditorsLogProV5(QMainWindow):
    def __init__(self, translator=None):
        super().__init__()
        self.translator = translator or TranslationManager()
        sys.excepthook = exception_hook
        self.setWindowTitle("Editor's Logger - v1.0.0")
        self.resize(1600, 950)
        self.setAcceptDrops(True)
        
        self.pm = ProjectManager()
        self.data = {} 
        self.found_stills = {}
        self.active_shot = None 
        self.active_take_idx = 0
        self.project_name = "UNTITLED PROJECT"
        self.current_project = None
        self.auto_save = False
        
        self._setup_fonts()
        self.apply_theme()
        self.show_home_screen()

    def _setup_fonts(self):
        self.pdf_font = "Helvetica"
        try:
            # Cross-platform font paths
            paths = [
                # macOS
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                # Windows
                "C:\\Windows\\Fonts\\Arial.ttf",
                "C:\\Windows\\Fonts\\arialuni.ttf",
                # Linux
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"
            ]
            
            for p in paths:
                if os.path.exists(p):
                    try:
                        pdfmetrics.registerFont(TTFont("VietFont", p))
                        self.pdf_font = "VietFont"
                        print(f"✓ Registered font: {p}")
                        break
                    except Exception as e:
                        print(f"× Failed to register {p}: {e}")
                        continue
        except Exception as e:
            print(f"Font setup error: {e}")

    def show_home_screen(self):
        """Show project home screen"""
        home = HomeScreen(self, self.translator)
        home.project_opened.connect(self.open_project)
        self.setCentralWidget(home)
        self.apply_theme()
    
    def open_project(self, project_name):
        """Open a project for editing"""
        self.current_project = project_name
        self.project_name = project_name
        self.data = self.pm.get_project_data(project_name)
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.toast = ToastNotification(self)
        self.toast.setGeometry(self.width() - 380, 20, 350, 60)
        self.toast.raise_()
            # ========== ADD EXPORT INDICATOR ==========
        self.export_indicator = QLabel(self)
        self.export_indicator.setGeometry(self.width() - 200, 90, 180, 40)
        self.export_indicator.setStyleSheet("""
            QLabel {
                background-color: #3d5afe;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self.export_indicator.setAlignment(Qt.AlignCenter)
        self.export_indicator.hide()
        self.export_indicator.raise_()
        # ========== END EXPORT INDICATOR ==========
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        header = QHBoxLayout()
        back_btn = QPushButton(self.translator.t("← Back to Projects"))
        back_btn.setMaximumWidth(300)
        back_btn.setMinimumHeight(40)
        back_btn.clicked.connect(self.back_to_home)
        header.addWidget(back_btn)
        
        self.proj_in = QLineEdit()
        self.proj_in.setText(self.project_name)
        self.proj_in.setReadOnly(True)
        self.proj_in.setAlignment(Qt.AlignCenter)
        
        self.scene_input = QLineEdit()
        self.scene_input.setPlaceholderText(self.translator.t("SCENE XX"))
        self.scene_input.setAlignment(Qt.AlignCenter)
        self.scene_input.setMaximumWidth(120)
        self.scene_input.textChanged.connect(self.on_scene_changed)
        
        self.date_label = QLabel(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        header.addWidget(QLabel(self.translator.t("PROJECT:")), 0)
        header.addWidget(self.proj_in, 2)
        header.addWidget(QLabel(self.translator.t("SCENE:")), 0)
        header.addWidget(self.scene_input, 1)
        header.addWidget(self.date_label, 0)
        content_layout.addLayout(header)

        content = QHBoxLayout()
        left_panel = QVBoxLayout()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["SHOT", "TK", "FILE", "SCORE", "STATUS"])
        self.table.setMaximumWidth(600)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        left_panel.addWidget(QLabel("LISTS:"))
        left_panel.addWidget(self.table, 2)

        add_take_btn = QPushButton(self.translator.t("➕ Add New Take"))
        add_take_btn.setMinimumHeight(40)
        add_take_btn.clicked.connect(self.add_new_take)
        left_panel.addWidget(add_take_btn)
        
        import_btn = QPushButton(self.translator.t("📥 Import from CSV"))
        import_btn.setMinimumHeight(40)
        import_btn.clicked.connect(self.import_csv_dialog)
        left_panel.addWidget(import_btn)
        
        self.logs_text = QTextEdit()
        self.logs_text.setMaximumHeight(150)
        self.logs_text.setReadOnly(True)
        self.logs_text.setStyleSheet("background-color: #0a0a0a; color: #00ff00; font-family: 'Courier New'; font-size: 9px;")
        left_panel.addWidget(QLabel(self.translator.t("LIVE LOGS:")))
        left_panel.addWidget(self.logs_text)
        content.addLayout(left_panel, 1)

        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel(self.translator.t("TAKE SELECTOR:")))
        self.take_selector = QComboBox()
        self.take_selector.currentIndexChanged.connect(self.on_take_dropdown_changed)
        right_layout.addWidget(self.take_selector)

        # Still + Content side by side
        still_content_layout = QHBoxLayout()
        
        self.img_box = DragDropLabel(self)
        self.img_box.setText(self.translator.t("DRAG & DROP FOLDER/CSV\nor SELECT A TAKE\n\n(Hover: ↑↓ navigate, 1,2,3,Q,E to rate, Cmd+S save)"))
        self.img_box.setMaximumSize(500, 300)
        self.img_box.setMinimumSize(500, 300)
        self.img_box.setScaledContents(True)
        self.img_box.setAlignment(Qt.AlignCenter)
        self.img_box.dropped.connect(self.handle_drop)
        self.img_box.rating_shortcut.connect(self.set_rating)
        self.img_box.save_shortcut.connect(self.confirm_save)
        self.img_box.navigate_take.connect(self.navigate_takes)
        still_content_layout.addWidget(self.img_box)

        content_section = QVBoxLayout()
        content_section.addWidget(QLabel(self.translator.t("SHOT CONTENT:")))
        self.content_box = QTextEdit()
        self.content_box.setMinimumHeight(300)
        self.content_box.setMaximumHeight(400)
        self.content_box.setPlaceholderText(self.translator.t("Describe what this shot is about...\n(Shared across all takes)"))
        content_section.addWidget(self.content_box)
        still_content_layout.addLayout(content_section)
        
        right_layout.addLayout(still_content_layout)

        rating_label = QLabel(self.translator.t("SCORE (1-5):"))
        rating_label.setStyleSheet("color: #3d5afe; font-weight: bold; font-size: 10px;")
        right_layout.addWidget(rating_label)
        
        rat_row = QHBoxLayout()
        self.rating_group = QButtonGroup(self)
        self.rating_buttons = {}
        for i in range(1, 6):
            rb = QRadioButton(f"Score: {i}")
            rb.setStyleSheet("QRadioButton { color: #FFFFFF; font-size: 12px; }")
            rb.setMaximumWidth(80)
            self.rating_group.addButton(rb, i)
            self.rating_buttons[i] = rb
            rat_row.addWidget(rb)
        self.rating_buttons[3].setChecked(True)
        right_layout.addLayout(rat_row)

        right_layout.addWidget(QLabel(self.translator.t("NOTES:")))
        self.note_box = CustomNotesBox(self)
        self.note_box.setMinimumHeight(200)
        self.note_box.save_requested.connect(self.confirm_save)
        right_layout.addWidget(self.note_box)

        self.save_btn = QPushButton(self.translator.t("💾 SAVE ANNOTATIONS"))
        self.save_btn.setMinimumHeight(50)
        self.save_btn.clicked.connect(self.confirm_save)
        right_layout.addWidget(self.save_btn)
        
        content.addWidget(right_panel, 2)
        content_layout.addLayout(content)

        self.export_btn = QPushButton(self.translator.t("🚀 GENERATE PDF REPORT"))
        self.export_btn.setMinimumHeight(60)
        self.export_btn.clicked.connect(self.generate_pdf)
        content_layout.addWidget(self.export_btn)
        
        batch_btn = QPushButton(self.translator.t("📦 BATCH GENERATE ALL SCENES"))
        batch_btn.setMinimumHeight(60)
        batch_btn.clicked.connect(self.batch_generate_pdf)
        content_layout.addWidget(batch_btn)
        
        main_layout.addWidget(content_widget)
        
        # Set focus policy to receive key events
        main_widget.setFocusPolicy(Qt.StrongFocus)
        self.setFocusPolicy(Qt.StrongFocus)
        
        self.refresh_table()

    def apply_theme(self):
        font_f = f"'{self.pdf_font}', sans-serif"
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: #121212; color: #FFFFFF; font-family: {font_f}; }}
            QLineEdit, QComboBox, QTextEdit {{ background-color: #1E1E1E; border: 1px solid #333; color: #FFF; padding: 5px; border-radius: 3px; }}
            QTableWidget {{ 
                background-color: #1E1E1E; 
                gridline-color: #222; 
                selection-background-color: #3d5afe; 
                selection-color: #FFFFFF;
                color: #FFF; 
            }}
            QHeaderView::section {{ background-color: #2D2D2D; color: #3d5afe; font-weight: bold; border: none; }}
            QPushButton {{ background-color: #3d5afe; color: white; border-radius: 5px; font-weight: bold; border: none; padding: 5px; }}
            QLabel {{ color: #888; }}
        """)

    def back_to_home(self):
        """Save and return to home screen"""
        if self.data and self.current_project:
            self.pm.save_project_data(self.current_project, self.data)
        self.current_project = None
        self.data = {}
        self.found_stills = {}
        self.active_shot = None
        self.active_take_idx = 0
        self.auto_save = False
        home = HomeScreen(self, self.translator)
        home.project_opened.connect(self.open_project)
        self.setCentralWidget(home)
        self.apply_theme()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self.handle_drop([url.toLocalFile() for url in e.mimeData().urls()])

    def handle_drop(self, paths):
        csv_to_load = None
        for path in paths:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(('.jpg', '.png', '.jpeg')):
                            core = os.path.splitext(file)[0].split('_')[0].lower()
                            self.found_stills[core] = os.path.join(root, file)
                        if file.lower().endswith('.csv'):
                            csv_to_load = os.path.join(root, file)
            elif os.path.isfile(path) and path.lower().endswith('.csv'):
                csv_to_load = path
        if csv_to_load:
            self.import_csv(csv_to_load)

    def import_csv_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if path:
            self.import_csv(path)

    def import_csv(self, path):
        """Import CSV data - ALWAYS APPENDS, skips duplicates"""
        scene = self.scene_input.text() or "SCENE 1"
        
        # Initialize scene if it doesn't exist
        if scene not in self.data:
            self.data[scene] = {'takes': {}, 'content': {}}
        
        # Ensure proper structure
        if 'takes' not in self.data[scene]:
            self.data[scene] = {'takes': {}, 'content': {}}
        if 'content' not in self.data[scene]:
            self.data[scene]['content'] = {}
        
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                new_count = 0
                duplicate_count = 0
                
                for row in reader:
                    shot = row.get('Shot', row.get('Timeline_Name', 'Unknown')).strip()
                    if not shot:
                        continue
                        
                    file_val = row.get('Source_Filename', row.get('Filename', '')).strip()
                    
                    # Initialize shot array if doesn't exist
                    if shot not in self.data[scene]['takes']:
                        self.data[scene]['takes'][shot] = []
                    
                    # Check if this exact file already exists for this shot
                    is_duplicate = False
                    for existing_take in self.data[scene]['takes'][shot]:
                        if existing_take.get('file', '').strip() == file_val:
                            is_duplicate = True
                            duplicate_count += 1
                            break
                    
                    # Skip duplicates, only add new files
                    if not is_duplicate:
                        still_path = row.get('Still_Path', '').strip()
                        if not os.path.exists(still_path):
                            core = os.path.splitext(file_val)[0].split('_')[0].lower()
                            still_path = self.found_stills.get(core, still_path)
                        
                        self.data[scene]['takes'][shot].append({
                            'file': file_val, 
                            'still': still_path,
                            'note': row.get('Notes', ''), 
                            'rating': 3
                        })
                        new_count += 1
                
                # Show clear notification
                if new_count > 0:
                    if duplicate_count > 0:
                        self.toast.show_toast(f"✓ Added {new_count} new takes, skipped {duplicate_count} duplicates")
                        self.log(f"✓ Added {new_count} new takes, skipped {duplicate_count} duplicates")
                    else:
                        self.toast.show_toast(f"✓ Added {new_count} new takes")
                        self.log(f"✓ Added {new_count} new takes")
                else:
                    self.toast.show_toast(f"✗ All takes were duplicates")
                    self.log(f"✗ All takes were duplicates")
                
                self.refresh_table()
                self.prompt_auto_save()
                
        except Exception as e: 
            self.toast.show_toast(f"✗ Import Error: {str(e)}")
            self.log(f"✗ Import Error: {str(e)}")

    def add_new_take(self):
        scene = self.scene_input.text() or "SCENE 1"
        dialog = AddTakeDialog(self, self.translator)
        if dialog.exec():
            data = dialog.get_data()
            if not data['shot']:
                return
            
            # Ensure proper structure
            if scene not in self.data:
                self.data[scene] = {'takes': {}, 'content': {}}
            if 'takes' not in self.data[scene]:
                self.data[scene] = {'takes': {}, 'content': {}}
            if 'content' not in self.data[scene]:
                self.data[scene]['content'] = {}
            
            if data['shot'] not in self.data[scene]['takes']:
                self.data[scene]['takes'][data['shot']] = []
            
            self.data[scene]['takes'][data['shot']].append({
                'file': data['file'], 
                'still': '', 
                'note': data['notes'], 
                'rating': 3
            })
            
            self.refresh_table()
            self.toast.show_toast(f"✓ Added new take: {data['shot']}")
            self.prompt_auto_save()

    def refresh_table(self):
        self.table.setRowCount(0)
        scene = self.scene_input.text()
        if not scene or scene not in self.data: 
            return
        
        # Handle both old format (direct dict) and new format (with 'takes' key)
        takes_data = self.data[scene].get('takes', self.data[scene]) if isinstance(self.data[scene], dict) else {}
        
        for shot, takes in takes_data.items():
            if shot == 'content':  # Skip the content key
                continue
            if not isinstance(takes, list):  # Skip non-list values
                continue
                
            for i, t in enumerate(takes):
                r = self.table.rowCount()
                self.table.insertRow(r)
                
                # Set vertical header (row number) with center alignment
                header_item = QTableWidgetItem(str(r + 1))
                header_item.setTextAlignment(Qt.AlignCenter)
                self.table.setVerticalHeaderItem(r, header_item)
                
                shot_text = shot if i == 0 else ""
                items = [
                    QTableWidgetItem(shot_text),
                    QTableWidgetItem(str(i + 1)),
                    QTableWidgetItem(t.get('file', '')),
                    QTableWidgetItem(f"{t.get('rating', 3)}/5"),
                    QTableWidgetItem("🎬 OK" if t.get('still') and os.path.exists(t.get('still', '')) else "⚠ No Still")
                ]
                
                for col, item in enumerate(items):
                    item.setForeground(QColor("#FFFFFF"))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(r, col, item)

    def on_row_selected(self):
        row = self.table.currentRow()
        if row < 0: 
            return
        # Load the take data
        self.load_active_take()
        
        # ========== NEW CODE: Highlight the entire row ==========
        # Select the entire row across all columns
        self.table.selectRow(row)
        
        # Force selection across all columns
        for col in range(self.table.columnCount()):
            self.table.setCurrentItem(self.table.item(row, col))
        
        # Scroll to make it visible
        self.table.scrollToItem(self.table.item(row, 0))
        
        # Find the shot name by looking upward for non-empty SHOT cell
        curr = row
        while curr >= 0:
            item = self.table.item(curr, 0)
            if item is None:
                curr -= 1
                continue
            if item.text():  # Found non-empty shot
                break
            curr -= 1
        
        # Safety check
        if curr < 0:
            return
        
        shot_item = self.table.item(curr, 0)
        if shot_item is None:
            return
            
        self.active_shot = shot_item.text()
        self.active_take_idx = row - curr
        
        scene = self.scene_input.text()
        if not scene or scene not in self.data:
            return
        
        # Handle both old and new format
        takes_data = self.data[scene].get('takes', self.data[scene]) if isinstance(self.data[scene], dict) else {}
        
        if self.active_shot not in takes_data:
            return
            
        takes = takes_data[self.active_shot]
        
        # Update dropdown
        self.take_selector.blockSignals(True)
        self.take_selector.clear()
        self.take_selector.addItems([f"Take {i+1}" for i in range(len(takes))])
        self.take_selector.setCurrentIndex(self.active_take_idx)
        self.take_selector.blockSignals(False)
        
        self.load_active_take()

    def on_take_dropdown_changed(self, idx):
        if idx >= 0:
            self.active_take_idx = idx
            self.load_active_take()
            # ========== NEW CODE: Find and highlight corresponding row ==========
            # Find the row in the table that corresponds to this take
            scene = self.scene_input.text()
            if scene and scene in self.data and self.active_shot:
                takes_data = self.data[scene].get('takes', self.data[scene]) if isinstance(self.data[scene], dict) else {}
                
                if self.active_shot in takes_data:
                    takes = takes_data[self.active_shot]
                    
                    # Find the row index for this take
                    row_to_select = -1
                    current_row = 0
                    
                    for shot in takes_data.keys():
                        if shot == 'content':
                            continue
                        if not isinstance(takes_data[shot], list):
                            continue
                            
                        shot_takes = takes_data[shot]
                        for i in range(len(shot_takes)):
                            if shot == self.active_shot and i == self.active_take_idx:
                                row_to_select = current_row
                                break
                            current_row += 1
                        if row_to_select != -1:
                            break
                    
                    # Select the row if found (automatically highlights all columns)
                    if row_to_select != -1:
                        self.table.selectRow(row_to_select)
                        self.table.scrollToItem(self.table.item(row_to_select, 0))

    def load_active_take(self):
        scene = self.scene_input.text()
        if not scene or scene not in self.data or not self.active_shot:
            return
        
        # Handle both old and new format
        takes_data = self.data[scene].get('takes', self.data[scene]) if isinstance(self.data[scene], dict) else {}
        
        if self.active_shot not in takes_data:
            return
        
        takes = takes_data[self.active_shot]
        if self.active_take_idx >= len(takes):
            return
            
        t = takes[self.active_take_idx]
        
        # Load take-specific note
        self.note_box.setText(t.get('note', ''))
        
        # Load shot-level content
        content_data = self.data[scene].get('content', {})
        self.content_box.setText(content_data.get(self.active_shot, ''))
        
        # Load rating
        rating = t.get('rating', 3)
        if rating in self.rating_buttons:
            self.rating_buttons[rating].setChecked(True)
        
        # Load still image
        still_path = t.get('still', '')
        if still_path and os.path.exists(still_path):
            self.img_box.setPixmap(QPixmap(still_path))
        else:
            self.img_box.clear()
            self.img_box.setText(f"STILL NOT FOUND\n{still_path or 'None'}")

    def confirm_save(self):
        if not self.active_shot: 
            self.toast.show_toast("⚠ No take selected")
            return
        
        scene = self.scene_input.text()
        if not scene or scene not in self.data:
            return
        
        rating = self.rating_group.checkedId()
        
        # Ensure proper structure
        if 'takes' not in self.data[scene]:
            self.data[scene] = {'takes': {}, 'content': {}}
        if 'content' not in self.data[scene]:
            self.data[scene]['content'] = {}
        
        # Save take-level data
        if self.active_shot in self.data[scene]['takes']:
            self.data[scene]['takes'][self.active_shot][self.active_take_idx].update({
                'note': self.note_box.toPlainText(), 
                'rating': rating
            })
        
        # Save shot-level content
        self.data[scene]['content'][self.active_shot] = self.content_box.toPlainText()
        
        self.refresh_table()
        self.toast.show_toast(f"✓ Saved Shot {self.active_shot} Take {self.active_take_idx+1} (Score: {rating})")
        self.log(f"✓ Saved Shot {self.active_shot} Take {self.active_take_idx+1} (Score: {rating})")
        
        if self.auto_save and self.current_project:
            self.pm.save_project_data(self.current_project, self.data)

    def prompt_auto_save(self):
        """Ask user if they want to auto-save"""
        if self.auto_save:
            return
        
        reply = QMessageBox.question(
            self, 
            "Auto-Save",
            "Enable auto-save for this project?\nChanges will be automatically saved after each annotation.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.auto_save = True
            self.toast.show_toast("✓ Auto-save enabled")

    def log(self, message: str):
        self.logs_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.logs_text.verticalScrollBar().setValue(self.logs_text.verticalScrollBar().maximum())

    def navigate_takes(self, direction):
        """Navigate up or down in the takes table"""
        current_row = self.table.currentRow()
        
        if direction == 'up' and current_row > 0:
            # Move to previous row and highlight entire row
            self.table.selectRow(current_row - 1)
            for col in range(self.table.columnCount()):
                self.table.setCurrentItem(self.table.item(current_row - 1, col))
        elif direction == 'down' and current_row < self.table.rowCount() - 1:
            # Move to next row and highlight entire row
            self.table.selectRow(current_row + 1)
            for col in range(self.table.columnCount()):
                self.table.setCurrentItem(self.table.item(current_row + 1, col))

    def on_scene_changed(self):
        """Handle scene change - reset UI and load new scene data"""
        # Clear dropdown
        self.take_selector.blockSignals(True)
        self.take_selector.clear()
        self.take_selector.blockSignals(False)
        
        # Clear text fields
        self.note_box.clear()
        self.content_box.clear()
        
        # Reset rating to default (3)
        if 3 in self.rating_buttons:
            self.rating_buttons[3].setChecked(True)
        
        # Clear still preview
        self.img_box.clear()
        self.img_box.setText("DRAG & DROP FOLDER/CSV\nor SELECT A TAKE")
        
        # Reset active selection
        self.active_shot = None
        self.active_take_idx = 0
        
        # Reload table for new scene
        self.refresh_table()

    def set_rating(self, rating):
        """Set rating via keybind"""
        if 1 <= rating <= 5:
            self.rating_buttons[rating].setChecked(True)
            self.toast.show_toast(f"✓ Score set to {rating}/5")

    def keyPressEvent(self, event):
        """Handle key press events (backup method)"""
        # This is now a backup - eventFilter should catch most events
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Reposition toast notification when window is resized"""
        super().resizeEvent(event)
        if hasattr(self, 'toast'):
            self.toast.setGeometry(self.width() - 380, 20, 350, 60)

    def generate_pdf(self):
        """Generates PDF for single scene"""
        scene = self.scene_input.text() or "SCENE 1"
        project = self.proj_in.text() or "UNTITLED PROJECT"
        
        if scene not in self.data:
            self.toast.show_toast("✗ No data for this scene")
            self.log("✗ No data for this scene")
            return
        
        # Check if scene has takes
        takes_data = self.data[scene].get('takes', self.data[scene]) if isinstance(self.data[scene], dict) else {}
        has_takes = any(isinstance(v, list) and len(v) > 0 for k, v in takes_data.items() if k != 'content')
        
        if not has_takes:
            self.toast.show_toast("✗ No takes added for this scene")
            self.log("✗ No takes added for this scene")
            return
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"{project}_{scene}.pdf", "PDF (*.pdf)")
        if not save_path:
            return
        
        self._generate_pdf_file(save_path, project, scene)
    
    def batch_generate_pdf(self):
        """Generate PDFs for all scenes"""
        if not self.data:
            self.toast.show_toast("✗ No scenes to export")
            return
        
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not folder:
            return
        
        project = self.proj_in.text() or "UNTITLED PROJECT"
        count = 0
        
        for scene in self.data.keys():
            # Check if scene has takes
            takes_data = self.data[scene].get('takes', self.data[scene]) if isinstance(self.data[scene], dict) else {}
            has_takes = any(isinstance(v, list) and len(v) > 0 for k, v in takes_data.items() if k != 'content')
            
            if has_takes:
                save_path = os.path.join(folder, f"{project}_{scene}.pdf")
                self._generate_pdf_file(save_path, project, scene)
                count += 1
        
        self.toast.show_toast(f"✓ Generated {count} PDFs!")
        self.log(f"✓ Batch generated {count} PDFs")
    
    def _generate_pdf_file(self, save_path, project, scene):
            """Generate PDF - Per-shot tables with B7 styling (handles 100+ entries)"""
            try:
                from reportlab.lib.styles import ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                from reportlab.lib import colors
                from PySide6.QtCore import QTimer
                import gc

                # SHOW PERSISTENT TOAST
                self.toast.show_persistent("⏳ Starting PDF export...")
                for _ in range(3):
                    QApplication.processEvents()

                # ========== VIETNAMESE FONT SETUP ==========
                font_name = "Helvetica"
                
                font_paths = [
                    "/Library/Fonts/Arial Unicode.ttf",
                    "/System/Library/Fonts/Arial.ttf",
                    "C:\\Windows\\Fonts\\Arial.ttf",
                    "C:\\Windows\\Fonts\\Arial Unicode.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                ]
                
                for font_path in font_paths:
                    try:
                        if os.path.exists(font_path):
                            pdfmetrics.registerFont(TTFont("VietnameseFont", font_path))
                            font_name = "VietnameseFont"
                            print(f"✓ Registered Vietnamese font: {font_path}")
                            break
                    except Exception as e:
                        print(f"✗ Failed to register {font_path}: {e}")
                        continue

                self.toast.update_message("⏳ Setting up document...")
                QApplication.processEvents()
                
                # Get data
                takes_data = self.data[scene].get('takes', self.data[scene]) if isinstance(self.data[scene], dict) else {}
                content_data = self.data[scene].get('content', {})

                # Sort shots
                sorted_shots = [s for s in takes_data.keys() 
                                      if s != 'content' and isinstance(takes_data[s], list) and takes_data[s]]
                
                if not sorted_shots:
                    self.toast.show_toast("✗ No data to export")
                    return
                
                total_shots = len(sorted_shots)
                total_takes = sum(len(takes_data[shot]) for shot in sorted_shots)
                
                self.toast.update_message(f"⏳ Processing {total_shots} shots, {total_takes} takes...")
                QApplication.processEvents()
                
                # ========== COLUMN WIDTHS (ENLARGED FOR BETTER READABILITY) ==========
                col_widths = [
                    0.85*inch,   # SHOT (was 0.75)
                    0.45*inch,   # TK (was 0.4)
                    1.35*inch,   # FILE (was 1.2)
                    1.35*inch,   # STILL (was 1.1) - BIGGER IMAGES
                    0.6*inch,    # SCORE (was 0.55)
                    1.8*inch,    # CONTENT (was 1.6)
                    4.35*inch    # NOTES (was 4.2)
                ]
                
                # ========== PARAGRAPH STYLES ==========
                header_style = ParagraphStyle(
                    'Header',
                    fontName=font_name,
                    fontSize=12,
                    alignment=TA_CENTER,
                    textColor=colors.white,
                    spaceAfter=2,
                    encoding='utf-8'
                )
                
                shot_style = ParagraphStyle(
                    'Shot',
                    fontName=font_name,
                    fontSize=10,
                    alignment=TA_CENTER,
                    leading=11,
                    encoding='utf-8'
                )
                
                cell_style = ParagraphStyle(
                    'Cell',
                    fontName=font_name,
                    fontSize=10,
                    alignment=TA_CENTER,
                    leading=11,
                    encoding='utf-8'
                )
                
                note_style = ParagraphStyle(
                    'Note',
                    fontName=font_name,
                    fontSize=9,
                    alignment=TA_LEFT,
                    leading=10,
                    wordWrap='CJK',
                    encoding='utf-8'
                )
                
                content_style = ParagraphStyle(
                    'Content',
                    fontName=font_name,
                    fontSize=10,
                    alignment=TA_CENTER,
                    leading=11,
                    wordWrap='CJK',
                    encoding='utf-8'
                )
                
                info_style = ParagraphStyle(
                    'Info', 
                    fontName=font_name, 
                    fontSize=9, 
                    alignment=TA_CENTER,
                    encoding='utf-8'
                )
                
                # ========== CREATE DOCUMENT ==========
                self.toast.update_message("⏳ Creating document...")
                QApplication.processEvents()
                
                doc = SimpleDocTemplate(
                    save_path, 
                    pagesize=landscape(letter),
                    topMargin=0.35*inch,
                    bottomMargin=0.35*inch,
                    leftMargin=0.3*inch,
                    rightMargin=0.3*inch
                )
                
                elements = []
                
                # ========== COVER PAGE ==========
                title_style = ParagraphStyle(
                    'Title', 
                    fontName=font_name, 
                    fontSize=16,
                    alignment=TA_CENTER,
                    spaceAfter=6,
                    textColor=colors.HexColor('#3d5afe'),
                    encoding='utf-8'
                )
                
                elements.append(Spacer(1, 1*inch))
                elements.append(Paragraph("EDITOR'S LOG", title_style))
                elements.append(Spacer(1, 0.3*inch))
                elements.append(Paragraph(
                    f"<b>Project:</b> {project}   •   <b>Scene:</b> {scene}   •   <b>Date:</b> {datetime.now().strftime('%d/%m/%Y')}",
                    info_style
                ))
                elements.append(Spacer(1, 0.3*inch))
                elements.append(Paragraph(
                    f"<b>Total Shots:</b> {total_shots}   •   <b>Total Takes:</b> {total_takes}",
                    info_style
                ))
                elements.append(PageBreak())
                
                # ========== PROCESS EACH SHOT ==========
                for shot_index, shot in enumerate(sorted_shots):
                    takes = takes_data[shot]
                    shot_content = content_data.get(shot, '')
                    num_takes = len(takes)
                    
                    # Update progress
                    if shot_index % max(1, total_shots // 10) == 0 or shot_index == total_shots - 1:
                        self.toast.update_message(f"⏳ Processing shot {shot_index + 1} of {total_shots}...")
                        QApplication.processEvents()
                    
                    # Add shot header
                    elements.append(Paragraph(f"SHOT: {shot}", shot_style))
                    elements.append(Paragraph(
                        f"<b>Project:</b> {project}   •   <b>Scene:</b> {scene}   •   <b>Content:</b> {shot_content[:100]}{'...' if len(shot_content) > 100 else ''}",
                        info_style
                    ))
                    elements.append(Spacer(1, 0.1*inch))
                    
                    # ========== BUILD TABLE FOR THIS SHOT ==========
                    header_row = [
                        Paragraph("SHOT", header_style), 
                        Paragraph("TK", header_style), 
                        Paragraph("FILE", header_style), 
                        Paragraph("STILL", header_style), 
                        Paragraph("SCORE", header_style),
                        Paragraph("CONTENT", header_style),
                        Paragraph("NOTES", header_style)
                    ]
                    
                    shot_rows = [header_row]
                    
                    for i, take in enumerate(takes):
                        # ========== STILL IMAGE HANDLING ==========
                        still_path = take.get('still', '')
                        img_cell = Paragraph("–", cell_style)
                        
                        if still_path and os.path.exists(still_path):
                            try:
                                img = RLImage(still_path, width=1.0*inch, height=0.65*inch)
                                img_cell = img
                            except Exception as img_e:
                                print(f"⚠ Image error {still_path}: {img_e}")
                                img_cell = Paragraph("–", cell_style)
                        
                        # ========== CONTENT (SHOW ONLY IN FIRST ROW) ==========
                        content_text = str(shot_content) if shot_content else ""
                        if len(content_text) > 80:
                            content_text = content_text[:77] + "..."
                        content_cell = Paragraph(content_text, content_style) if i == 0 else Paragraph("", content_style)
                        
                        # ========== FILE NAME ==========
                        file_name = take.get('file', '')
                        if len(file_name) > 20:
                            name, ext = os.path.splitext(file_name)
                            if len(name) > 16:
                                name = name[:16]
                            file_name = f"{name}...{ext}"
                        
                        # ========== NOTES ==========
                        note_text = str(take.get('note', ''))
                        if len(note_text) > 150:
                            note_text = note_text[:147] + "..."
                        
                        # ========== SCORE ==========
                        rating = take.get('rating', 3)
                        score_text = f"{rating}/5"
                        
                        shot_rows.append([
                            Paragraph(str(shot) if i == 0 else "", shot_style),
                            Paragraph(str(i + 1), cell_style),
                            Paragraph(file_name, cell_style),
                            img_cell,
                            Paragraph(score_text, cell_style),
                            content_cell,
                            Paragraph(note_text, note_style)
                        ])
                    
                    # ========== CREATE TABLE FOR THIS SHOT ==========
                    table_style = [
                        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3d5afe')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('FONTNAME', (0, 0), (-1, 0), font_name),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING', (0, 0), (-1, -1), 5),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (0, 1), (5, -1), 'CENTER'),
                        ('ALIGN', (6, 1), (6, -1), 'LEFT'),
                        ('FONTSIZE', (0, 1), (-1, -1), 10),
                        ('LEADING', (6, 1), (6, -1), 12),
                        ('FONTNAME', (0, 1), (-1, -1), font_name),
                    ]
                    
                    # Add alternating row colors
                    for row_idx in range(1, len(shot_rows)):
                        if row_idx % 2 == 0:
                            table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#f5f5f5')))
                        else:
                            table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.white))
                    
                    try:
                        # Create table with larger row heights for bigger images
                        row_heights = [0.4*inch] + [0.8*inch] * (len(shot_rows) - 1)
                        tbl = Table(shot_rows, colWidths=col_widths, rowHeights=row_heights)
                        tbl.setStyle(TableStyle(table_style))
                        elements.append(tbl)
                    except Exception as tbl_e:
                        print(f"⚠ Table error for shot {shot}: {tbl_e}")
                        # Fallback: simple text
                        for i, take in enumerate(takes):
                            elements.append(Paragraph(
                                f"Take {i+1}: {take.get('file', '')} - Score: {take.get('rating', 3)}/5",
                                cell_style
                            ))
                    
                    elements.append(Spacer(1, 0.2*inch))
                    
                    # Add page break after each shot (except last)
                    if shot_index < total_shots - 1:
                        elements.append(PageBreak())
                    
                    # Memory cleanup
                    if shot_index % 50 == 0:
                        gc.collect()
                
                # ========== BUILD PDF ==========
                self.toast.update_message("⏳ Building PDF...")
                QApplication.processEvents()
                
                try:
                    doc.build(elements)
                except Exception as build_e:
                    print(f"⚠ Build error: {build_e}")
                    # Create minimal fallback
                    try:
                        fallback_elements = [
                            Paragraph("EDITOR'S LOG", title_style),
                            Paragraph(f"Project: {project} • Scene: {scene}", info_style),
                            Spacer(1, 0.2*inch),
                            Paragraph(f"Shots: {total_shots}, Takes: {total_takes}", info_style),
                            Spacer(1, 0.2*inch),
                            Paragraph("(Details not available - PDF too large)", info_style),
                        ]
                        fallback_doc = SimpleDocTemplate(save_path, pagesize=landscape(letter))
                        fallback_doc.build(fallback_elements)
                        self.toast.show_toast("⚠ PDF saved (summary only)")
                    except:
                        raise build_e
                
                # ========== SUCCESS ==========
                self.toast.update_message(f"✓ PDF Saved")
                QTimer.singleShot(3000, self.toast.hide)
                
                self.log(f"✓ PDF Generated: {os.path.basename(save_path)}")
                self.log(f"✓ Using font: {font_name}")
                self.log(f"✓ Layout: Per-shot pages | Data: {total_shots} shots, {total_takes} takes")
                self.toast.show_toast(f"✓ PDF Saved ({total_shots} shots, {total_takes} takes)")
                
            except Exception as e: 
                self.toast.update_message(f"✗ PDF Error: {str(e)[:50]}...")
                QTimer.singleShot(4000, self.toast.hide)
                self.toast.show_toast(f"✗ PDF Error: {str(e)[:50]}...")
                self.log(f"✗ PDF Error: {str(e)}")
                import traceback
                traceback.print_exc()

def exception_hook(exc_type, exc_value, exc_traceback):
    """Global exception handler"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Get the correct directory for crash logs
    if getattr(sys, 'frozen', False):
        # Bundled app
        if sys.platform == 'darwin':
            base_dir = os.path.dirname(os.path.dirname(sys.executable))
            if base_dir.endswith('.app/Contents/MacOS'):
                base_dir = base_dir.replace('Contents/MacOS', '')
            crash_dir = os.path.join(base_dir, 'Resources', 'EditorLog_Projects', 'crashes')
        else:
            crash_dir = os.path.join(os.path.dirname(sys.executable), 'EditorLog_Projects', 'crashes')
    else:
        # Development
        crash_dir = os.path.expanduser('~/Documents/EditorLog_Projects/crashes')
    
    os.makedirs(crash_dir, exist_ok=True)
    crash_file = os.path.join(crash_dir, f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

def prevent_multiple_instances():
    """
    Robust singleton lock that works for both script and bundled app
    """
    import tempfile
    import atexit
    
    # Get app-specific directory for lock file
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            # macOS: Use app bundle Resources folder
            base_dir = os.path.dirname(os.path.dirname(sys.executable))
            if base_dir.endswith('.app/Contents/MacOS'):
                base_dir = base_dir.replace('Contents/MacOS', 'Resources')
            lock_dir = os.path.join(base_dir, 'EditorLog_Projects')
        else:
            # Windows/Linux: Use executable directory
            lock_dir = os.path.dirname(sys.executable)
    else:
        # Development: Use script directory
        lock_dir = os.path.dirname(os.path.abspath(__file__))
    
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, 'editors_logger.lock')
    
    # Try to create and lock the file
    try:
        # Check if lock file exists and process is still running
        if os.path.exists(lock_path):
            try:
                with open(lock_path, 'r') as f:
                    existing_pid = f.read().strip()
                if existing_pid:
                    # Check if process exists
                    try:
                        os.kill(int(existing_pid), 0)
                        # Process exists - another instance is running
                        return False
                    except (OSError, ValueError):
                        # Process doesn't exist - stale lock
                        os.remove(lock_path)
            except:
                # Corrupt lock file
                os.remove(lock_path)
        
        # Create new lock file
        with open(lock_path, 'w') as f:
            f.write(str(os.getpid()))
        
        # Register cleanup
        def cleanup_lock():
            try:
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except:
                pass
        
        atexit.register(cleanup_lock)
        return True
        
    except Exception as e:
        # If we can't lock, assume we can run (graceful degradation)
        print(f"Lock warning: {e}")
        return True

# --- Main Execution ---
if __name__ == "__main__":
    print("--- Starting Editor's Logger ---")
    
    # Prevent multiple instances
    if not prevent_multiple_instances():
        print("Editor's Logger is already running! Exiting.")
        sys.exit(1)
    
    print("Singleton check passed. Continuing with app startup...")
    
    # Fix for macOS specific issues
    if sys.platform == "darwin":
        os.environ["QT_MAC_WANTS_LAYER"] = "1"

    # Create QApplication instance
    app = QApplication(sys.argv)
    app.setApplicationName("Editor's Logger")
    app.setOrganizationName("EditorLogger")

    # Initialize translator
    translator = TranslationManager()

    # Show splash screen
    splash = SplashScreen()
    splash.show()
    splash.update_message("Starting up...")
    QApplication.processEvents()

    try:
        # Create main window with translator
        splash.update_message("Loading interface...")
        QApplication.processEvents()
        window = EditorsLogProV5(translator)

        # Hide splash and show main window
        splash.close()
        window.show()

        # Execute application
        sys.exit(app.exec())

    except Exception as e:
        # Close splash if there's an error
        splash.close()
        # Show error message using QApplication
        error_msg = QMessageBox()
        error_msg.setIcon(QMessageBox.Critical)
        error_msg.setWindowTitle("Fatal Error")
        error_msg.setText(f"Application failed to start:\n{str(e)}")
        error_msg.exec()
        import traceback
        traceback.print_exc()
        sys.exit(1)