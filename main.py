import sys, os, ctypes
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QToolBar, QLineEdit,
    QPushButton, QTabWidget, QProgressBar, QFileDialog
)
from PySide6.QtGui import QAction, QIcon, QKeySequence, QFont, QFontDatabase, QColor, QPalette
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
    QWebEngineUrlRequestInterceptor, QWebEngineDownloadRequest
)
from PySide6.QtCore import QUrl, Qt

APP_NAME = "GM-BROWSER"
APP_ID = "com.gm.browser.ultimate.2025"
UI_ACCENT = "#1a73e8"

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except:
    pass

def load_modern_font():
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Manrope-VariableFont_wght.ttf")
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)
        return QFont("Manrope", 10)
    return QFont("Segoe UI", 10)

class AdBlocker(QWebEngineUrlRequestInterceptor):
    BLOCK_LIST = (
        "doubleclick.net","google-analytics.com","adservice.google",
        "popads.net","adform.net","pixel.facebook.com"
    )
    def __init__(self):
        super().__init__()
        self.enabled = True
    def interceptRequest(self, info):
        if self.enabled and any(ad in info.requestUrl().toString() for ad in self.BLOCK_LIST):
            info.block(True)

class BrowserPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.setBackgroundColor(QColor(18,18,18))
        s = self.settings()
        s.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        s.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, True)
        s.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        s.setAttribute(QWebEngineSettings.FocusOnNavigationEnabled, True)

class GMBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.home_path = os.path.join(self.root_dir, "home.html")
        self.icon_path = os.path.join(self.root_dir, "logo.ico")

        self.setWindowTitle(APP_NAME)
        self.resize(1400,900)
        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))

        self.profile = QWebEngineProfile.defaultProfile()
        self.ad_blocker = AdBlocker()
        self.profile.setUrlRequestInterceptor(self.ad_blocker)

        self._build_ui()
        self._setup_shortcuts()
        self.add_tab()

    def _update_tab_title(self, view, title):
        idx = self.tabs.indexOf(view)
        if idx != -1:
            self.tabs.setTabText(idx, title[:18]+"…" if len(title) > 18 else title)

    def _nav_btn(self, text, slot):
        btn = QPushButton(text)
        btn.setFixedSize(36,36)
        btn.clicked.connect(slot)
        btn.setStyleSheet(f"QPushButton {{ background:transparent; color:#bbb; border:none; font-size:16px }} QPushButton:hover {{ color:{UI_ACCENT} }}")
        return btn

    def toggle_adblock(self):
        self.ad_blocker.enabled = not self.ad_blocker.enabled
        self.ad_btn.setText("🛡" if self.ad_blocker.enabled else "🔓")

    def _bind(self,key,slot):
        act = QAction(self)
        act.setShortcut(QKeySequence(key))
        act.triggered.connect(slot)
        act.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(act)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.toolbar.show()
        else:
            self.showFullScreen()
            self.toolbar.show()  # Keep toolbar visible in fullscreen

    def go_back(self): self.tabs.currentWidget().back()
    def go_forward(self): self.tabs.currentWidget().forward()
    def reload_page(self): self.tabs.currentWidget().reload()
    def go_home(self):
        self.tabs.currentWidget().setUrl(QUrl.fromLocalFile(self.home_path))

    def handle_download(self, download: QWebEngineDownloadRequest):
        path,_ = QFileDialog.getSaveFileName(self, "Save File", download.downloadFileName())
        if path:
            download.setDownloadDirectory(os.path.dirname(path))
            download.setDownloadFileName(os.path.basename(path))
            download.accept()

    # --- BOOKMARK SYSTEM REMOVED ---
    # def add_bookmark(self): pass
    # def show_bookmarks(self): pass

    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setFixedHeight(60)
        self.toolbar.setStyleSheet(f"QToolBar {{ background:#121212; border-bottom:1px solid #333; padding:4px 12px; spacing:8px }}")
        for txt, slot in [("←",self.go_back),("→",self.go_forward),("↻",self.reload_page),("⌂",self.go_home)]:
            self.toolbar.addWidget(self._nav_btn(txt,slot))

        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText("Search with Google or enter address")
        self.address_bar.returnPressed.connect(self.navigate)
        self.address_bar.setFixedHeight(36)
        self.address_bar.setFont(QFont("Segoe UI", 10))
        self.address_bar.setStyleSheet(f"""
            QLineEdit {{ background-color:#1e1e1e; color:#e8eaed;
                border:1px solid #444; border-radius:18px;
                padding:0 12px; selection-background-color:{UI_ACCENT}; selection-color:#000 }}
            QLineEdit::placeholder {{ color:#888 }}
            QLineEdit:focus {{ border-color:{UI_ACCENT}; outline:none }}
        """)
        self.toolbar.addWidget(self.address_bar)

        self.ad_btn = self._nav_btn("🛡", self.toggle_adblock)
        self.toolbar.addWidget(self.ad_btn)
        self.toolbar.addWidget(self._nav_btn("+", self.add_tab))
        # --- BOOKMARK BUTTON REMOVED ---
        # self.toolbar.addWidget(self._nav_btn("★", self.add_bookmark))
        self.addToolBar(self.toolbar)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"QProgressBar::chunk {{ background:{UI_ACCENT} }}")

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_address)
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{ background:#1e1e1e; color:#ccc; padding:8px 20px; min-width:120px }}
            QTabBar::tab:selected {{ background:#2a2a2a; color:{UI_ACCENT}; border-bottom:2px solid {UI_ACCENT} }}
        """)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.progress)
        layout.addWidget(self.tabs)

    def add_tab(self, url: str = None):
        view = QWebEngineView()
        view.setPage(BrowserPage(self.profile, view))
        view.loadProgress.connect(self.progress.setValue)
        view.urlChanged.connect(self.sync_address)
        view.titleChanged.connect(lambda t: self._update_tab_title(view, t))
        self.profile.downloadRequested.connect(self.handle_download)

        if not url or not isinstance(url, str):
            view.setUrl(QUrl.fromLocalFile(self.home_path))
        else:
            view.setUrl(QUrl(url))

        index = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(index)

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.widget(index).deleteLater()
            self.tabs.removeTab(index)
        else:
            self.close()

    def navigate(self):
        text = self.address_bar.text().strip()
        if not text: return
        if text.lower() == "home":
            url = QUrl.fromLocalFile(self.home_path)
        elif "://" in text:
            url = QUrl(text)
        else:
            url = QUrl(f"https://www.google.com/search?q={text}")
        self.tabs.currentWidget().setUrl(url)

    def sync_address(self):
        view = self.tabs.currentWidget()
        if view:
            url = view.url().toString()
            if url.startswith("file://") and os.path.basename(url) == "home.html":
                self.address_bar.setText("")
            else:
                self.address_bar.setText(url)

    def _setup_shortcuts(self):
        self._bind("Ctrl+T", lambda: self.add_tab())
        self._bind("Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex()))
        self._bind("F11", self.toggle_fullscreen)
        self._bind("Ctrl+R", self.reload_page)
        self._bind("Ctrl+L", lambda: self.address_bar.setFocus())
        # --- BOOKMARK SHORTCUT REMOVED ---
        # self._bind("Ctrl+B", self.show_bookmarks)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(load_modern_font())
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(18,18,18))
    palette.setColor(QPalette.Base, QColor(30,30,30))
    palette.setColor(QPalette.Text, QColor(232,234,237))
    app.setPalette(palette)

    browser = GMBrowser()
    browser.show()
    sys.exit(app.exec())
