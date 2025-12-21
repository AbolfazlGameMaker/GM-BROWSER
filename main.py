import sys
import os
import ctypes

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QToolBar, QLineEdit, QPushButton, QTabWidget, 
    QProgressBar, QGraphicsDropShadowEffect, QFileDialog
)

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
    QWebEngineDownloadRequest, QWebEngineUrlRequestInterceptor
)

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor, QPalette, QIcon, QAction, QKeySequence

# ================== AD-BLOCKER ENGINE ==================
class AdBlocker(QWebEngineUrlRequestInterceptor):
    def __init__(self):
        super().__init__()
        self.enabled = True  # Default status: ON

    def interceptRequest(self, info):
        if not self.enabled:
            return
            
        url = info.requestUrl().toString()
        # Blacklist of common ad domains
        ad_filters = [
            "doubleclick.net", "google-analytics.com", "adservice.google",
            "popads.net", "adform.net", "adbrn.com", "pixel.facebook.com"
        ]
        if any(filter in url for filter in ad_filters):
            info.block(True)

# ================== CONFIG ==================
APP_NAME = "GM-BROWSER"
UI_ACCENT = "#00ff88"
APP_ID = "com.gm.browser.ultimate.2025"

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except:
    pass

# ================== BROWSER ENGINE ==================
class BrowserEngine(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.setBackgroundColor(QColor(5, 5, 5))
        
        s = self.settings()
        s.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        s.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, True)
        s.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        s.setAttribute(QWebEngineSettings.FocusOnNavigationEnabled, True)

# ================== MAIN INTERFACE ==================
class GMBrowserNexus(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize Ad-Blocker on the default profile
        self.ad_blocker = AdBlocker()
        QWebEngineProfile.defaultProfile().setUrlRequestInterceptor(self.ad_blocker)
        
        self.root_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        self.home_url = os.path.join(self.root_dir, "home.html")
        self.icon_url = os.path.join(self.root_dir, "logo.ico")
        
        self.setWindowTitle(APP_NAME)
        self.resize(1400, 900)
        if os.path.exists(self.icon_url):
            self.setWindowIcon(QIcon(self.icon_url))
            
        self.setup_ui_nexus()
        self.add_new_tab()
        self.setup_shortcuts()

    def setup_ui_nexus(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- TOOLBAR ---
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background: #050505;
                border-bottom: 1px solid #111;
                padding: 10px 20px;
                spacing: 15px;
            }}
            QPushButton {{
                background: transparent;
                color: #666;
                border: none;
                font-size: 20px;
            }}
            QPushButton:hover {{
                color: {UI_ACCENT};
            }}
        """)

        self.toolbar.addWidget(self.create_nav_btn("←", self.go_back))
        self.toolbar.addWidget(self.create_nav_btn("→", self.go_forward))
        self.toolbar.addWidget(self.create_nav_btn("↻", self.reload_page))
        self.toolbar.addWidget(self.create_nav_btn("⌂", self.go_home))
        
        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText("Search or enter URL...")
        self.address_bar.returnPressed.connect(self.navigate_to_input)
        self.address_bar.setStyleSheet(f"""
            QLineEdit {{
                background: #0d0d0d;
                color: #fff;
                border: 1px solid #222;
                border-radius: 10px;
                padding: 8px 15px;
            }}
            QLineEdit:focus {{ border-color: {UI_ACCENT}; }}
        """)
        self.toolbar.addWidget(self.address_bar)

        # Ad-block control button
        self.ad_btn = self.create_nav_btn("🛡️", self.toggle_adblock)
        self.ad_btn.setStyleSheet(f"color: {UI_ACCENT}; font-size: 18px;") # Default: Green (Enabled)
        self.toolbar.addWidget(self.ad_btn)

        self.toolbar.addWidget(self.create_nav_btn("+", self.add_new_tab))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.progress_line = QProgressBar()
        self.progress_line.setFixedHeight(2)
        self.progress_line.setTextVisible(False)
        self.progress_line.setStyleSheet(f"QProgressBar {{ background: transparent; border: none; }} QProgressBar::chunk {{ background: {UI_ACCENT}; }}")
        main_layout.addWidget(self.progress_line)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_address_bar)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: #000; }}
            QTabBar::tab {{
                background: #050505; color: #444;
                padding: 12px 25px; min-width: 150px;
                border: none;
            }}
            QTabBar::tab:selected {{ 
                background: #0a0a0a; color: {UI_ACCENT}; 
                border-bottom: 2px solid {UI_ACCENT};
            }}
        """)
        main_layout.addWidget(self.tabs)

    def toggle_adblock(self):
        self.ad_blocker.enabled = not self.ad_blocker.enabled
        if self.ad_blocker.enabled:
            self.ad_btn.setStyleSheet(f"color: {UI_ACCENT}; font-size: 18px;")
            self.ad_btn.setText("🛡️")
        else:
            self.ad_btn.setStyleSheet("color: #ff4444; font-size: 18px;")
            self.ad_btn.setText("🔓")

    def setup_shortcuts(self):
        # Navigation and Tab shortcuts
        self._add_action("Ctrl+T", self.add_new_tab)
        self._add_action("Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex()))
        self._add_action("F11", self.toggle_fullscreen)
        self._add_action("Ctrl+B", self.toggle_adblock) # Ad-block toggle shortcut
        
        # Zoom shortcuts
        self._add_action("Ctrl+=", self.zoom_in)
        self._add_action("Ctrl+-", self.zoom_out)
        self._add_action("Ctrl+0", self.zoom_reset)

    def _add_action(self, shortcut, slot):
        action = QAction(self)
        action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        self.addAction(action)

    def zoom_in(self):
        current_view = self.tabs.currentWidget()
        if current_view: current_view.setZoomFactor(current_view.zoomFactor() + 0.1)

    def zoom_out(self):
        current_view = self.tabs.currentWidget()
        if current_view: current_view.setZoomFactor(max(0.25, current_view.zoomFactor() - 0.1))

    def zoom_reset(self):
        current_view = self.tabs.currentWidget()
        if current_view: current_view.setZoomFactor(1.0)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.toolbar.show()
        else:
            self.showFullScreen()
            self.toolbar.hide()

    def create_nav_btn(self, icon, slot):
        btn = QPushButton(icon)
        btn.setFixedSize(40, 40)
        btn.clicked.connect(slot)
        return btn

    def add_new_tab(self, qurl=None):
        view = QWebEngineView()
        view.setZoomFactor(1.0)
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self.handle_download)
        page = BrowserEngine(profile, view)
        view.setPage(page)
        view.loadProgress.connect(self.progress_line.setValue)
        view.urlChanged.connect(self.sync_address_bar)
        view.titleChanged.connect(lambda t: self.update_tab_title(view, t))
        if qurl: view.setUrl(qurl)
        elif os.path.exists(self.home_url): view.setUrl(QUrl.fromLocalFile(self.home_url))
        else: view.setUrl(QUrl("https://www.google.com"))
        idx = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(idx)

    def update_tab_title(self, view, title):
        idx = self.tabs.indexOf(view)
        if idx != -1: self.tabs.setTabText(idx, (title[:15] + "..") if len(title) > 15 else title)

    def close_tab(self, i):
        if self.tabs.count() > 1:
            w = self.tabs.widget(i)
            self.tabs.removeTab(i)
            w.deleteLater()
        else: self.close()

    def navigate_to_input(self):
        text = self.address_bar.text().strip()
        if not text: return
        url = text if "." in text and " " not in text else f"https://www.google.com/search?q={text}"
        if "://" not in url: url = "https://" + url
        self.tabs.currentWidget().setUrl(QUrl(url))

    def sync_address_bar(self):
        curr = self.tabs.currentWidget()
        if curr:
            url_str = curr.url().toString()
            self.address_bar.setText("" if "home.html" in url_str else url_str)

    def handle_download(self, download: QWebEngineDownloadRequest):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", download.downloadFileName())
        if path:
            download.setDownloadDirectory(os.path.dirname(path))
            download.setDownloadFileName(os.path.basename(path))
            download.accept()

    def go_back(self): self.tabs.currentWidget().back()
    def go_forward(self): self.tabs.currentWidget().forward()
    def reload_page(self): self.tabs.currentWidget().reload()
    def go_home(self):
        if os.path.exists(self.home_url):
            self.tabs.currentWidget().setUrl(QUrl.fromLocalFile(self.home_url))

# ================== RUN ==================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor(0, 0, 0))
    p.setColor(QPalette.Base, QColor(5, 5, 5))
    p.setColor(QPalette.Text, Qt.white)
    app.setPalette(p)
    browser = GMBrowserNexus()
    browser.show()
    sys.exit(app.exec())
    