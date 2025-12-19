import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar,
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QDialog, 
    QPushButton, QLabel, QListWidget, QMessageBox, QFileDialog, 
    QComboBox, QFrame
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtGui import QAction
from PySide6.QtCore import QUrl, Qt, QSize

# فایل‌های ذخیره داده
DOWNLOADS_LOG = "downloads.json"
HISTORY_FILE = "history.json"
BOOKMARKS_FILE = "bookmarks.json"

# --- افزایش سرعت با تنظیمات موتور کرومیوم و GPU ---
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--ignore-certificate-errors "
    "--log-level=3 "
    "--enable-gpu-rasterization "
    "--enable-zero-copy "
    "--disable-software-rasterizer "
    "--ignore-gpu-blocklist "
    "--num-raster-threads=4"
)

# --- استایل نئونی ---
UI_STYLE = """
QMainWindow { background-color: #080a0f; }
QTabWidget::pane { border: none; background-color: #080a0f; }
QTabBar::tab {
    background: #141721; color: #888; padding: 12px 25px;
    border-top-left-radius: 15px; border-top-right-radius: 15px;
    margin-right: 3px; font-weight: 600;
}
QTabBar::tab:selected { background: #1c1f2b; color: #00ffff; border-bottom: 3px solid #00ffff; }
QToolBar { background: #141721; border-bottom: 1px solid #222; padding: 8px; spacing: 12px; }
QLineEdit {
    background: #1c1f2b; color: white; border: 1px solid #333;
    border-radius: 22px; padding: 10px 20px; font-size: 14px;
}
QLineEdit:focus { border: 1px solid #00ffff; background: #222636; }
QDialog { background-color: #0d1117; border-radius: 20px; }
QListWidget { background-color: #141721; color: white; border: 1px solid #333; border-radius: 15px; padding: 10px; }
QPushButton { 
    background-color: #1c1f2b; color: white; border-radius: 12px; 
    padding: 10px 18px; font-weight: bold; border: 1px solid #333;
}
QPushButton:hover { background-color: #282c3d; border-color: #00ffff; }
QPushButton#Danger { background-color: rgba(255, 77, 77, 0.1); color: #ff4d4d; border: 1px solid #ff4d4d; }
QPushButton#Danger:hover { background-color: #ff4d4d; color: white; }
QPushButton#SafeActive { background-color: rgba(0, 255, 255, 0.1); color: #00ffff; border: 1px solid #00ffff; }
"""

class ListManagerDialog(QDialog):
    def __init__(self, title, items, storage_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title); self.setFixedSize(500, 600); self.setStyleSheet(UI_STYLE)
        self.items = items; self.storage_file = storage_file; self.action_type = None
        
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget(); self.refresh_ui()
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        open_btn = QPushButton("Open"); open_btn.clicked.connect(self.handle_open)
        del_btn = QPushButton("Delete"); del_btn.setObjectName("Danger"); del_btn.clicked.connect(self.handle_delete)
        clear_btn = QPushButton("Clear All"); clear_btn.setObjectName("Danger"); clear_btn.clicked.connect(self.handle_clear_all)
        
        btn_layout.addWidget(open_btn); btn_layout.addWidget(del_btn); btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

    def refresh_ui(self):
        self.list_widget.clear()
        for item in reversed(self.items):
            self.list_widget.addItem(f"{item['title']}\n{item['url']}")

    def handle_open(self):
        if self.list_widget.currentRow() != -1:
            self.action_type = "open"; self.accept()

    def handle_delete(self):
        row = self.list_widget.currentRow()
        if row != -1:
            index_to_del = len(self.items) - 1 - row
            del self.items[index_to_del]; self.save_to_disk(); self.refresh_ui()

    def handle_clear_all(self):
        if QMessageBox.question(self, "Confirm", "Delete everything?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.items.clear(); self.save_to_disk(); self.refresh_ui()

    def save_to_disk(self):
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(self.items, f, indent=4)

class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings"); self.setFixedSize(400, 450); self.setStyleSheet(UI_STYLE)
        layout = QVBoxLayout(self); layout.setContentsMargins(30, 30, 30, 30)
        
        layout.addWidget(QLabel("🛡 GOOGLE SAFESEARCH MODE"))
        safe_layout = QHBoxLayout()
        self.btn_f = QPushButton("Filter"); self.btn_b = QPushButton("Blur"); self.btn_o = QPushButton("Off")
        for b in [self.btn_f, self.btn_b, self.btn_o]: safe_layout.addWidget(b)
        layout.addLayout(safe_layout)
        
        self.btn_f.clicked.connect(lambda: self.set_s("active"))
        self.btn_b.clicked.connect(lambda: self.set_s("images"))
        self.btn_o.clicked.connect(lambda: self.set_s("off"))
        self.update_btns()
        layout.addStretch()
        done = QPushButton("Done"); done.setStyleSheet("background:#00ffff; color:#000;"); done.clicked.connect(self.accept)
        layout.addWidget(done)

    def set_s(self, m):
        self.parent.safe_mode = m; self.update_btns()

    def update_btns(self):
        m = self.parent.safe_mode
        self.btn_f.setObjectName("SafeActive" if m == "active" else "")
        self.btn_b.setObjectName("SafeActive" if m == "images" else "")
        self.btn_o.setObjectName("SafeActive" if m == "off" else "")
        self.setStyleSheet(UI_STYLE)

class AdvancedBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GM-BROWSER"); self.resize(1280, 850); self.setStyleSheet(UI_STYLE)
        
        self.history = self.load_json(HISTORY_FILE, [])
        self.bookmarks = self.load_json(BOOKMARKS_FILE, [])
        self.safe_mode = "active"
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.home_url = QUrl.fromLocalFile(os.path.join(base_path, "home.html"))

        self.tabs = QTabWidget(); self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        self.create_toolbar()
        self.add_tab(self.home_url, "Home")

    def create_toolbar(self):
        bar = QToolBar(); bar.setMovable(False); self.addToolBar(bar)
        acts = [(" ❮ ", self.current_back), (" ❯ ", self.current_forward), 
                (" ↻ ", self.current_reload), (" 🏠 ", self.go_home)]
        for t, c in acts:
            a = QAction(t, self); a.triggered.connect(c); bar.addAction(a)

        self.url_bar = QLineEdit(); self.url_bar.returnPressed.connect(self.navigate); bar.addWidget(self.url_bar)
        bar.addAction(QAction(" ⭐ ", self, triggered=self.add_bookmark))
        bar.addAction(QAction(" 📖 ", self, triggered=self.show_bookmarks))
        bar.addAction(QAction(" 🕒 ", self, triggered=self.show_history))
        bar.addAction(QAction(" ➕ ", self, triggered=lambda: self.add_tab(self.home_url, "New Tab")))
        bar.addAction(QAction(" ⚙️ ", self, triggered=lambda: SettingsDialog(self).exec()))

    # --- توابع مدیریت تاریخچه و بوکمارک که ارور می‌دادند ---
    def show_history(self):
        dialog = ListManagerDialog("Browsing History", self.history, HISTORY_FILE, self)
        if dialog.exec() and dialog.action_type == "open":
            row = dialog.list_widget.currentRow()
            self.current().setUrl(QUrl(self.history[len(self.history)-1-row]['url']))

    def show_bookmarks(self):
        dialog = ListManagerDialog("Bookmarks", self.bookmarks, BOOKMARKS_FILE, self)
        if dialog.exec() and dialog.action_type == "open":
            row = dialog.list_widget.currentRow()
            self.current().setUrl(QUrl(self.bookmarks[len(self.bookmarks)-1-row]['url']))

    def navigate(self):
        text = self.url_bar.text().strip()
        if not text: return
        if "." in text and " " not in text:
            url = QUrl(text)
        else:
            url = QUrl(f"https://www.google.com/search?q={text.replace(' ', '+')}&safe={self.safe_mode}")
        if url.scheme() == "": url.setScheme("https")
        self.current().setUrl(url)

    def add_tab(self, url, title):
        web = QWebEngineView()
        s = web.settings()
        s.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        s.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        
        web.setUrl(url)
        web.page().profile().downloadRequested.connect(self.handle_download)
        
        def quick_safe(q_url):
            u = q_url.toString()
            if "google.com" in u and "safe=" not in u:
                sep = "&" if "?" in u else "?"
                web.blockSignals(True)
                web.setUrl(QUrl(u + f"{sep}safe={self.safe_mode}"))
                web.blockSignals(False)

        web.urlChanged.connect(quick_safe)
        idx = self.tabs.addTab(web, title)
        self.tabs.setCurrentIndex(idx)
        web.urlChanged.connect(lambda q: self.update_url_bar(q, web))
        web.titleChanged.connect(lambda t: self.update_tab_title(t, web))
        web.loadFinished.connect(lambda: self.log_history(web))

    def log_history(self, web):
        url = web.url().toString()
        if url and "home.html" not in url:
            self.history.append({"title": web.title(), "url": url})
            self.save_json(HISTORY_FILE, self.history)

    def handle_download(self, d):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", d.suggestedFileName())
        if path:
            d.setDownloadDirectory(os.path.dirname(path)); d.setDownloadFileName(os.path.basename(path)); d.accept()

    def update_url_bar(self, q, web):
        if web == self.current(): self.url_bar.setText("" if "home.html" in q.toString() else q.toString())

    def update_tab_title(self, t, web):
        idx = self.tabs.indexOf(web)
        if idx != -1: self.tabs.setTabText(idx, t[:15])

    def close_tab(self, idx):
        if self.tabs.count() > 1: self.tabs.removeTab(idx)

    def current(self): return self.tabs.currentWidget()
    def current_back(self): self.current().back()
    def current_forward(self): self.current().forward()
    def current_reload(self): self.current().reload()
    def go_home(self): self.current().setUrl(self.home_url)

    def add_bookmark(self):
        self.bookmarks.append({"title": self.current().title(), "url": self.current().url().toString()})
        self.save_json(BOOKMARKS_FILE, self.bookmarks)
        QMessageBox.information(self, "Saved", "Added to Bookmarks!")

    def load_json(self, f, default):
        if os.path.exists(f):
            try:
                with open(f, "r", encoding="utf-8") as file: return json.load(file)
            except: pass
        return default

    def save_json(self, f, d):
        with open(f, "w", encoding="utf-8") as file: json.dump(d, file, indent=4)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdvancedBrowser()
    window.show()
    sys.exit(app.exec())
