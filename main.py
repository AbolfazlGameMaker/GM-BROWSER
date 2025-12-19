import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QTabWidget, 
    QWidget, QVBoxLayout, QDialog, QPushButton, 
    QLabel, QMessageBox, QListWidget, QHBoxLayout, QInputDialog, QRadioButton, QButtonGroup, QListWidgetItem
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtCore import QUrl, Qt, QSize
from PySide6.QtGui import QColor

# Performance and UI Stability Optimization
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--enable-gpu-rasterization --ignore-gpu-blocklist "
    "--disable-features=SurfaceControl --mute-audio"
)

class GMBROWSER(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GM-BROWSER")
        self.resize(1300, 900)
        
        self.db_path = "gm_database_v3.json"
        self.load_data()

        self.setStyleSheet("""
            QMainWindow { background: #050505; }
            QToolBar { background: #0a0a0a; border-bottom: 1px solid #1a1a1a; padding: 10px; spacing: 8px; }
            QLineEdit { background: #151515; color: #00f2ff; border: 1px solid #333; border-radius: 15px; padding: 8px 18px; font-size: 13px; }
            QTabWidget::pane { border: none; background: #050505; }
            QTabBar::tab { background: #0a0a0a; color: #888; padding: 12px 25px; border: 1px solid #1a1a1a; margin-right: 2px; }
            QTabBar::tab:selected { background: #111; color: #00f2ff; border: 1px solid #00f2ff; }
            QPushButton { background: #111; color: #eee; border: 1px solid #333; border-radius: 8px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { border-color: #00f2ff; color: #00f2ff; }
            QListWidget { background: #0a0a0a; color: #00f2ff; border: 1px solid #333; padding: 5px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #1a1a1a; }
        """)

        self.home_url = QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "home.html"))
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        self.create_nav()
        self.add_tab(self.home_url, "Home")

    def load_data(self):
        default_data = {"history": [], "bookmarks": [], "password": "", "safesearch": "active"}
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except: self.data = default_data
        else: self.data = default_data
        
        self.history = self.data.get("history", [])
        self.bookmarks = self.data.get("bookmarks", [])
        self.app_password = self.data.get("password", "")
        self.safesearch_mode = self.data.get("safesearch", "active")

    def save_data(self):
        self.data = {
            "history": self.history,
            "bookmarks": self.bookmarks,
            "password": self.app_password,
            "safesearch": self.safesearch_mode
        }
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)

    def create_nav(self):
        nav_bar = QToolBar()
        self.addToolBar(nav_bar)

        nav_bar.addAction(" ❮ ", self.back)
        nav_bar.addAction(" ❯ ", self.forward)
        nav_bar.addAction(" ↻ ", self.reload)
        nav_bar.addAction(" 🏠 ", self.go_home)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter URL...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        nav_bar.addWidget(self.url_bar)

        nav_bar.addAction(" ⭐ ", self.manage_bookmarks)
        nav_bar.addAction(" 📖 ", self.manage_history)
        nav_bar.addAction(" ⚙️ ", self.open_settings)
        nav_bar.addAction(" ＋ ", lambda: self.add_tab(self.home_url, "New Tab"))

    def add_tab(self, url, title):
        browser = QWebEngineView()
        browser.page().setBackgroundColor(QColor("#050505"))
        browser.setUrl(url)
        idx = self.tabs.addTab(browser, title)
        self.tabs.setCurrentIndex(idx)
        browser.urlChanged.connect(lambda q, b=browser: self.update_url(q, b))
        browser.loadFinished.connect(lambda _, b=browser: self.tabs.setTabText(self.tabs.indexOf(b), b.page().title()[:12]))

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text: return
        if "." in text and " " not in text:
            url = QUrl(text if "://" in text else "https://" + text)
        else:
            url = QUrl(f"https://www.google.com/search?q={text}&safe={self.safesearch_mode}")
        self.tabs.currentWidget().setUrl(url)

    def update_url(self, q, browser):
        if browser == self.tabs.currentWidget():
            u = q.toString()
            self.url_bar.setText("" if "home.html" in u else u)
            if u.startswith("http") and "google.com/search" not in u:
                if not self.history or self.history[-1]['url'] != u:
                    self.history.append({"title": browser.page().title(), "url": u})
                    self.save_data()

    def manage_bookmarks(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Bookmarks Manager")
        dlg.setMinimumSize(450, 550)
        layout = QVBoxLayout(dlg)
        
        list_w = QListWidget()
        def reload_list():
            list_w.clear()
            for b in reversed(self.bookmarks): list_w.addItem(f"{b['title']} | {b['url']}")
        
        reload_list()
        
        btns = QHBoxLayout()
        add_btn = QPushButton("Save Current Page")
        del_btn = QPushButton("Delete Selected")
        clear_btn = QPushButton("Clear All")
        
        add_btn.clicked.connect(lambda: self.add_bookmark_logic(reload_list))
        del_btn.clicked.connect(lambda: self.delete_bookmark_logic(list_w, reload_list))
        clear_btn.clicked.connect(lambda: self.clear_bookmarks_logic(reload_list))
        
        list_w.itemDoubleClicked.connect(lambda i: [self.add_tab(QUrl(i.text().split(" | ")[-1]), "Loading..."), dlg.accept()])

        btns.addWidget(add_btn); btns.addWidget(del_btn); btns.addWidget(clear_btn)
        layout.addWidget(list_w); layout.addLayout(btns)
        dlg.exec()

    def add_bookmark_logic(self, callback):
        b = self.tabs.currentWidget()
        url = b.url().toString()
        if "home.html" not in url:
            self.bookmarks.append({"title": b.page().title(), "url": url})
            self.save_data(); callback()

    def delete_bookmark_logic(self, list_w, callback):
        for item in list_w.selectedItems():
            url = item.text().split(" | ")[-1]
            self.bookmarks = [b for b in self.bookmarks if b['url'] != url]
        self.save_data(); callback()

    def clear_bookmarks_logic(self, callback):
        if QMessageBox.question(self, "Clear", "Clear all bookmarks?") == QMessageBox.Yes:
            self.bookmarks = []; self.save_data(); callback()

    def manage_history(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("History Manager")
        dlg.setMinimumSize(450, 550)
        layout = QVBoxLayout(dlg)
        list_w = QListWidget()
        
        def reload_list():
            list_w.clear()
            for h in reversed(self.history): list_w.addItem(f"{h['title']} | {h['url']}")
        
        reload_list()
        
        btns = QHBoxLayout()
        del_btn = QPushButton("Delete Selected")
        clear_btn = QPushButton("Clear All History")
        
        del_btn.clicked.connect(lambda: self.delete_history_logic(list_w, reload_list))
        clear_btn.clicked.connect(lambda: self.clear_history_logic(reload_list))
        
        list_w.itemDoubleClicked.connect(lambda i: [self.add_tab(QUrl(i.text().split(" | ")[-1]), "Loading..."), dlg.accept()])

        btns.addWidget(del_btn); btns.addWidget(clear_btn)
        layout.addWidget(list_w); layout.addLayout(btns)
        dlg.exec()

    def delete_history_logic(self, list_w, callback):
        for item in list_w.selectedItems():
            url = item.text().split(" | ")[-1]
            self.history = [h for h in self.history if h['url'] != url]
        self.save_data(); callback()

    def clear_history_logic(self, callback):
        if QMessageBox.question(self, "Clear", "Clear all browsing history?") == QMessageBox.Yes:
            self.history = []; self.save_data(); callback()

    def open_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.setFixedSize(400, 480)
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel("🔒 SECURITY ACCESS"))
        p_btn = QPushButton("Set Password")
        p_btn.clicked.connect(self.set_pwd)
        r_btn = QPushButton("Remove Password")
        r_btn.clicked.connect(self.rem_pwd)
        layout.addWidget(p_btn); layout.addWidget(r_btn)

        layout.addWidget(QLabel("\n🛡 GOOGLE SAFESEARCH"))
        group = QButtonGroup(dlg)
        r1 = QRadioButton("Filter (Strict Content)"); r2 = QRadioButton("Blur (Blur Sensitive)"); r3 = QRadioButton("Off (No Filtering)")
        group.addButton(r1); group.addButton(r2); group.addButton(r3)
        
        if self.safesearch_mode == "active": r1.setChecked(True)
        elif self.safesearch_mode == "images": r2.setChecked(True)
        else: r3.setChecked(True)
        
        layout.addWidget(r1); layout.addWidget(r2); layout.addWidget(r3)
        
        save = QPushButton("APPLY ALL SETTINGS")
        save.setStyleSheet("background: #00f2ff; color: #000;")
        save.clicked.connect(lambda: self.apply_set(dlg, r1, r2, r3))
        layout.addWidget(save)
        dlg.exec()

    def apply_set(self, dlg, r1, r2, r3):
        if r1.isChecked(): self.safesearch_mode = "active"
        elif r2.isChecked(): self.safesearch_mode = "images"
        else: self.safesearch_mode = "off"
        self.save_data(); dlg.accept()

    def set_pwd(self):
        p, ok = QInputDialog.getText(self, "Security", "Set New Password:", QLineEdit.Password)
        if ok and p: self.app_password = p; self.save_data()

    def rem_pwd(self): self.app_password = ""; self.save_data()

    def close_tab(self, i):
        if self.tabs.count() > 1: self.tabs.removeTab(i)
        else: self.go_home()

    def back(self): self.tabs.currentWidget().back()
    def forward(self): self.tabs.currentWidget().forward()
    def reload(self): self.tabs.currentWidget().reload()
    def go_home(self): self.tabs.currentWidget().setUrl(self.home_url)

class LoginDialog(QDialog):
    def __init__(self, pwd):
        super().__init__()
        self.pwd = pwd
        self.setWindowTitle("Security Lock")
        self.setFixedSize(320, 160)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background: #050505; border: 2px solid #00f2ff; border-radius: 10px;")
        l = QVBoxLayout(self)
        title = QLabel("LOCKED: ACCESS DENIED")
        title.setStyleSheet("color: #00f2ff; font-weight: bold; border: none;")
        title.setAlignment(Qt.AlignCenter)
        l.addWidget(title)
        self.inp = QLineEdit()
        self.inp.setEchoMode(QLineEdit.Password)
        self.inp.setPlaceholderText("Enter Key to Unlock...")
        self.inp.setStyleSheet("padding: 8px; color: white; background: #111; border: 1px solid #333;")
        l.addWidget(self.inp)
        b = QPushButton("UNLOCK BROWSER")
        b.clicked.connect(self.check)
        b.setStyleSheet("background: #00f2ff; color: #000; font-weight: bold;")
        l.addWidget(b)

    def check(self):
        if self.inp.text() == self.pwd: self.accept()
        else: QMessageBox.critical(self, "Denied", "Incorrect Password!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Load Security State
    temp_data = {}
    if os.path.exists("gm_database_v3.json"):
        with open("gm_database_v3.json", 'r') as f:
            try: temp_data = json.load(f)
            except: pass
    
    pwd = temp_data.get("password", "")
    if pwd:
        login = LoginDialog(pwd)
        if login.exec() != QDialog.Accepted: sys.exit()
    
    window = GMBROWSER()
    window.show()
    sys.exit(app.exec())
    