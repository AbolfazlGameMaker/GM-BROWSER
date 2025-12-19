import sys, os, json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QTabWidget, 
    QWidget, QVBoxLayout, QDialog, QPushButton, QLabel, 
    QRadioButton, QFrame, QListWidget, QMessageBox, QHBoxLayout,
    QProgressBar, QMenu
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtGui import QColor, QKeyEvent, QAction, QIcon
from PySide6.QtCore import QUrl, Qt, QSize

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-gpu-blocklist --no-sandbox"

STYLE = """
QMainWindow { background-color: #050505; }
QToolBar { background: #080808; border-bottom: 1px solid #1a1a1a; padding: 5px; spacing: 10px; }
QLineEdit { background: #111; color: #00f2ff; border: 1px solid #222; padding: 7px 15px; border-radius: 20px; font-size: 13px; }
QPushButton { background: transparent; color: #777; font-size: 14px; padding: 5px; font-weight: bold; border-radius: 5px; }
QPushButton:hover { color: #00f2ff; background: #1a1a1a; }
QProgressBar { border: none; background: #050505; height: 2px; }
QProgressBar::chunk { background-color: #00f2ff; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: #080808; color: #444; padding: 10px 25px; border-right: 1px solid #111; }
QTabBar::tab:selected { background: #111; color: #00f2ff; border-top: 2px solid #00f2ff; }
QDialog { background: #080808; border: 1px solid #333; color: white; }
QListWidget { background: #0a0a0a; color: #eee; border: 1px solid #222; border-radius: 5px; padding: 5px; }
"""

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller/EXE """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class GMBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GM-BROWSER")
        self.resize(1200, 800)
        self.setStyleSheet(STYLE)
        
        self.safe_mode = "active" 
        self.is_fullscreen = False
        self.home_path = resource_path("home.html")
        self.home_url = QUrl.fromLocalFile(self.home_path)
        
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.bookmarks_file = os.path.join(exe_dir, "bookmarks.json")
        self.history_file = os.path.join(exe_dir, "history.json")

        self.bookmarks = self.load_data(self.bookmarks_file)
        self.history = self.load_data(self.history_file)
        
        # UI Elements
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(False)
        
        self.setup_ui()
        self.add_new_tab(self.home_url, "GM-BROWSER")

    def load_data(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f: return json.load(f)
            except: return []
        return []

    def save_data(self, filename, data):
        with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

    def setup_ui(self):
        self.toolbar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setMovable(False)
        
        self.toolbar.addWidget(self.create_nav_btn("🏠", self.go_home))
        self.toolbar.addWidget(self.create_nav_btn("❮", lambda: self.tabs.currentWidget().back()))
        self.toolbar.addWidget(self.create_nav_btn("❯", lambda: self.tabs.currentWidget().forward()))
        self.toolbar.addWidget(self.create_nav_btn("↻", lambda: self.tabs.currentWidget().reload()))
        
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter URL...")
        self.url_bar.returnPressed.connect(self.navigate)
        self.toolbar.addWidget(self.url_bar)
        
        self.toolbar.addWidget(self.create_nav_btn("⭐", self.add_bookmark))
        self.toolbar.addWidget(self.create_nav_btn("📜", self.show_history_dialog))
        self.toolbar.addWidget(self.create_nav_btn("➕", lambda: self.add_new_tab(self.home_url, "New Tab")))
        self.toolbar.addWidget(self.create_nav_btn("⚙️", self.open_settings))

        # Bottom UI layout for progress bar
        layout = QVBoxLayout()
        container = QWidget()
        container.setLayout(layout)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.tabs)
        self.setCentralWidget(container)

    def create_nav_btn(self, text, slot):
        btn = QPushButton(text)
        btn.setMinimumWidth(30)
        btn.clicked.connect(slot)
        return btn

    def add_new_tab(self, qurl, title):
        browser = QWebEngineView()
        browser.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        browser.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        browser.setUrl(qurl)
        
        idx = self.tabs.addTab(browser, title)
        self.tabs.setCurrentIndex(idx)
        
        # Signals
        browser.urlChanged.connect(lambda q: self.handle_url_change(q, browser))
        browser.titleChanged.connect(lambda t: self.tabs.setTabText(self.tabs.indexOf(browser), t[:15]))
        browser.loadProgress.connect(self.progress_bar.setValue)
        browser.loadFinished.connect(lambda: self.progress_bar.setValue(0))
        
        # Download support
        browser.page().profile().downloadRequested.connect(self.handle_download)
        
        # Custom Context Menu
        browser.setContextMenuPolicy(Qt.CustomContextMenu)
        browser.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, browser))

    def handle_download(self, download_item):
        path = os.path.join(os.path.expanduser("~"), "Downloads", download_item.suggestedFileName())
        download_item.setDownloadDirectory(os.path.dirname(path))
        download_item.setDownloadFileName(os.path.basename(path))
        download_item.accept()
        download_item.finished.connect(lambda: QMessageBox.information(self, "Success", "Download Finished!"))

    def show_context_menu(self, pos, browser):
        menu = QMenu(self)
        back_action = QAction("Back", self)
        back_action.triggered.connect(browser.back)
        menu.addAction(back_action)
        
        reload_action = QAction("Reload", self)
        reload_action.triggered.connect(browser.reload)
        menu.addAction(reload_action)
        
        menu.addSeparator()
        copy_action = QAction("Copy Link", self)
        menu.addAction(copy_action)
        
        menu.exec(browser.mapToGlobal(pos))

    def handle_url_change(self, q, browser):
        url_str = q.toString()
        if "home.html" not in url_str:
            self.url_bar.setText(url_str)
            if not self.history or self.history[-1]['url'] != url_str:
                self.history.append({"title": browser.title() or "Page", "url": url_str})
                self.save_data(self.history_file, self.history)
        else:
            self.url_bar.clear()

    def navigate(self):
        text = self.url_bar.text().strip()
        if not text: return
        if "." in text and " " not in text:
            url = text if "://" in text else "https://" + text
        else:
            url = f"https://www.google.com/search?q={text}&safe={self.safe_mode}"
        self.tabs.currentWidget().setUrl(QUrl(url))

    def go_home(self):
        self.tabs.currentWidget().setUrl(self.home_url)

    def close_tab(self, i):
        if self.tabs.count() > 1:
            self.tabs.removeTab(i)
        else:
            self.go_home()

    def add_bookmark(self):
        curr = self.tabs.currentWidget()
        url = curr.url().toString()
        if "home.html" not in url:
            if not any(b['url'] == url for b in self.bookmarks):
                self.bookmarks.append({"title": curr.title() or "Page", "url": url})
                self.save_data(self.bookmarks_file, self.bookmarks)
                QMessageBox.information(self, "Saved", "Added to Bookmarks.")

    def show_history_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("History")
        dlg.setFixedSize(500, 400)
        layout = QVBoxLayout(dlg)
        list_w = QListWidget()
        for h in reversed(self.history): list_w.addItem(h['url'])
        layout.addWidget(list_w)
        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(lambda: [self.history.clear(), self.save_data(self.history_file, []), list_w.clear()])
        layout.addWidget(btn_clear)
        list_w.itemDoubleClicked.connect(lambda it: [self.tabs.currentWidget().setUrl(QUrl(it.text())), dlg.accept()])
        dlg.exec()

    def open_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        layout = QVBoxLayout(dlg)
        lbl = QLabel("Safe Search Mode:")
        layout.addWidget(lbl)
        self.r_off = QRadioButton("Off")
        self.r_on = QRadioButton("Strict")
        layout.addWidget(self.r_off)
        layout.addWidget(self.r_on)
        if self.safe_mode == "active": self.r_on.setChecked(True)
        else: self.r_off.setChecked(True)
        btn = QPushButton("Apply")
        btn.clicked.connect(lambda: self.apply_set(dlg))
        layout.addWidget(btn)
        dlg.exec()

    def apply_set(self, dlg):
        self.safe_mode = "active" if self.r_on.isChecked() else "off"
        dlg.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F11:
            if self.is_fullscreen: self.showNormal()
            else: self.showFullScreen()
            self.is_fullscreen = not self.is_fullscreen
        elif e.key() == Qt.Key_T and e.modifiers() & Qt.ControlModifier:
            self.add_new_tab(self.home_url, "New Tab")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("GM-BROWSER")
    window = GMBrowser()
    window.show()
    sys.exit(app.exec())
    