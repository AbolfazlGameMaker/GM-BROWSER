import sys, os, json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QTabWidget, 
    QWidget, QVBoxLayout, QDialog, QPushButton, QLabel, 
    QRadioButton, QFrame, QListWidget, QMessageBox, QHBoxLayout
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtCore import QUrl, Qt
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-gpu-blocklist --no-sandbox"
STYLE = """
QMainWindow { background-color: #050505; }
QToolBar { background: #080808; border-bottom: 1px solid #1a1a1a; padding: 5px; spacing: 10px; }
QLineEdit { background: #111; color: #00f2ff; border: 1px solid #222; padding: 7px 15px; border-radius: 20px; font-size: 13px; }
QPushButton { background: transparent; color: #777; font-size: 14px; padding: 5px; font-weight: bold; border-radius: 5px; }
QPushButton:hover { color: #00f2ff; background: #1a1a1a; }
#HomeBtn { color: #00f2ff; font-size: 16px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: #080808; color: #444; padding: 10px 25px; border-right: 1px solid #111; }
QTabBar::tab:selected { background: #111; color: #00f2ff; border-top: 2px solid #00f2ff; }
QDialog { background: #080808; border: 1px solid #333; color: white; }
QListWidget { background: #0a0a0a; color: #eee; border: 1px solid #222; border-radius: 5px; padding: 5px; }
"""
class GMBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GM-BROWSER")
        self.resize(1200, 800)
        self.setStyleSheet(STYLE)
        self.safe_mode = "active" 
        self.is_fullscreen = False
        self.home_url = QUrl.fromLocalFile(os.path.abspath("home.html"))
        self.bookmarks = self.load_data("bookmarks.json")
        self.history = self.load_data("history.json")
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(lambda i: self.tabs.removeTab(i) if self.tabs.count() > 1 else None)
        self.setCentralWidget(self.tabs)
        self.setup_ui()
        self.add_new_tab(self.home_url, "GM-BROWSER")
    def load_data(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f: return json.load(f)
            except: return []
        return []
    def save_data(self, filename, data):
        with open(filename, 'w') as f: json.dump(data, f)
    def setup_ui(self):
        self.toolbar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setMovable(False)
        btn_home = self.create_nav_btn("🏠", self.go_home)
        btn_home.setObjectName("HomeBtn")
        self.toolbar.addWidget(btn_home)
        self.toolbar.addWidget(self.create_nav_btn("❮", lambda: self.tabs.currentWidget().back()))
        self.toolbar.addWidget(self.create_nav_btn("❯", lambda: self.tabs.currentWidget().forward()))
        self.toolbar.addWidget(self.create_nav_btn("↻", lambda: self.tabs.currentWidget().reload()))
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search with GM-BROWSER...")
        self.url_bar.returnPressed.connect(self.navigate)
        self.toolbar.addWidget(self.url_bar)
        self.toolbar.addWidget(self.create_nav_btn("⭐", self.add_bookmark))
        self.toolbar.addWidget(self.create_nav_btn("📜", self.show_history_dialog))
        self.toolbar.addWidget(self.create_nav_btn("📂", self.show_bookmarks_dialog))
        self.toolbar.addWidget(self.create_nav_btn("➕", lambda: self.add_new_tab(self.home_url, "New Tab")))
        self.toolbar.addWidget(self.create_nav_btn("⚙️", self.open_settings))
    def create_nav_btn(self, text, slot):
        btn = QPushButton(text)
        btn.clicked.connect(slot)
        return btn
    def go_home(self):
        self.tabs.currentWidget().setUrl(self.home_url)
    def add_new_tab(self, qurl, title):
        browser = QWebEngineView()
        browser.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        browser.setUrl(qurl)
        idx = self.tabs.addTab(browser, title)
        self.tabs.setCurrentIndex(idx)
        browser.urlChanged.connect(lambda q: self.handle_url_change(q, browser))
        browser.titleChanged.connect(lambda t: self.tabs.setTabText(self.tabs.indexOf(browser), t[:15]))
    def handle_url_change(self, q, browser):
        url_str = q.toString()
        if "home.html" not in url_str:
            self.url_bar.setText(url_str)
            if not self.history or self.history[-1]['url'] != url_str:
                self.history.append({"title": browser.title() or "Page", "url": url_str})
                self.save_data("history.json", self.history)
        else: self.url_bar.clear()
    def navigate(self):
        text = self.url_bar.text().strip()
        if not text: return
        if "." in text and " " not in text:
            url = text if "://" in text else "https://" + text
        else: url = f"https://www.google.com/search?q={text}&safe={self.safe_mode}"
        self.tabs.currentWidget().setUrl(QUrl(url))
    def add_bookmark(self):
        curr = self.tabs.currentWidget()
        url = curr.url().toString()
        if "home.html" not in url:
            if not any(b['url'] == url for b in self.bookmarks):
                self.bookmarks.append({"title": curr.title() or "Page", "url": url})
                self.save_data("bookmarks.json", self.bookmarks)
                QMessageBox.information(self, "GM-BROWSER", "Site saved to bookmarks.")
    def show_bookmarks_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("GM-BROWSER Bookmarks")
        dlg.setFixedSize(450, 500)
        layout = QVBoxLayout(dlg)
        list_w = QListWidget()
        for b in self.bookmarks: list_w.addItem(f"{b['title']} -> {b['url']}")
        layout.addWidget(list_w)
        btns = QHBoxLayout()
        btn_open = QPushButton("Launch Site")
        btn_del = QPushButton("Delete Bookmark")
        btn_open.clicked.connect(lambda: self.open_bm(list_w, dlg))
        btn_del.clicked.connect(lambda: self.delete_bm(list_w))
        btns.addWidget(btn_open); btns.addWidget(btn_del)
        layout.addLayout(btns)
        dlg.exec()
    def open_bm(self, list_w, dlg):
        if list_w.currentItem():
            url = list_w.currentItem().text().split(" -> ")[-1]
            self.tabs.currentWidget().setUrl(QUrl(url))
            dlg.accept()
    def delete_bm(self, list_w):
        row = list_w.currentRow()
        if row >= 0:
            self.bookmarks.pop(row)
            self.save_data("bookmarks.json", self.bookmarks)
            list_w.takeItem(row)
    def show_history_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("GM-BROWSER History")
        dlg.setFixedSize(500, 500)
        layout = QVBoxLayout(dlg)
        list_w = QListWidget()
        for h in reversed(self.history): list_w.addItem(h['url'])
        layout.addWidget(list_w)
        btn_clear = QPushButton("Clear All History")
        btn_clear.clicked.connect(lambda: [self.history.clear(), self.save_data("history.json", []), list_w.clear()])
        layout.addWidget(btn_clear)
        list_w.itemDoubleClicked.connect(lambda it: [self.tabs.currentWidget().setUrl(QUrl(it.text())), dlg.accept()])
        dlg.exec()
    def open_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("GM-BROWSER Engine Settings")
        dlg.setFixedSize(450, 350)
        layout = QVBoxLayout(dlg)
        frame = QFrame()
        frame.setStyleSheet("background: #001a1a; border: 1px solid #00f2ff; border-radius: 10px; padding: 15px;")
        f_layout = QVBoxLayout(frame)
        rec = QLabel("💎 DEVELOPER TIP:\nSafeSearch ensures a professional experience with GM-BROWSER.")
        rec.setWordWrap(True)
        rec.setStyleSheet("color: #00f2ff; font-weight: bold; font-size: 13px; border: none;")
        f_layout.addWidget(rec)
        layout.addWidget(frame)
        self.r_off = QRadioButton("SafeSearch: Off")
        self.r_blur = QRadioButton("SafeSearch: Blur")
        self.r_filter = QRadioButton("SafeSearch: Filter (Strict)")
        for r in [self.r_off, self.r_blur, self.r_filter]: layout.addWidget(r)
        if self.safe_mode == "off": self.r_off.setChecked(True)
        elif self.safe_mode == "blur": self.r_blur.setChecked(True)
        else: self.r_filter.setChecked(True)
        btn_apply = QPushButton("Apply Configuration")
        btn_apply.setStyleSheet("background: #00f2ff; color: black; padding: 12px; font-weight: bold;")
        btn_apply.clicked.connect(lambda: self.apply_settings(dlg))
        layout.addWidget(btn_apply)
        dlg.exec()
    def apply_settings(self, dlg):
        if self.r_off.isChecked(): self.safe_mode = "off"
        elif self.r_blur.isChecked(): self.safe_mode = "blur"
        else: self.safe_mode = "active"
        dlg.accept()
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F11:
            if self.is_fullscreen: self.showNormal()
            else: self.showFullScreen()
            self.is_fullscreen = not self.is_fullscreen
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GMBrowser()
    window.show()
    sys.exit(app.exec())
