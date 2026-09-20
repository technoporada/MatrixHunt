"""
MATRIXHUNT DESKTOP - Agregator darmowych gier z wbudowaną przeglądarką
Instalacja: pip install PyQt6 PyQt6-WebEngine requests beautifulsoup4 sqlalchemy
Uruchom: python hunt.py
"""

import sys
import os
import json
import requests
import random
import re
import webbrowser
import xml.etree.ElementTree as ET
import defusedxml.ElementTree as DefusedET
import time
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Index
from sqlalchemy.orm import declarative_base, sessionmaker

from bs4 import BeautifulSoup

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QLineEdit, QComboBox, QSplitter, QScrollArea,
    QProgressBar, QMessageBox, QTabWidget, QTextEdit, QCheckBox, QFrame,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineUrlRequestInterceptor
from PyQt6.QtCore import QUrl, QTimer, Qt, pyqtSignal, QThread
from PyQt6.QtGui import QPalette, QColor, QFont

from urllib.parse import urlparse


def is_safe_url(url: str) -> bool:
    """Block file://, javascript:, data:, and other dangerous URL schemes."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in ("http", "https", "")


# ===================== AD BLOCKER =====================

class AdBlocker(QWebEngineUrlRequestInterceptor):
    def __init__(self):
        super().__init__()
        self.enabled = True
        self.blocked_domains = [
            "doubleclick.net", "googlesyndication.com", "google-analytics.com",
            "amazon-adsystem.com", "adnxs.com", "rubiconproject.com",
            "pubmatic.com", "moatads.com", "ads.twitter.com",
            "adservice.google.com", "pagead2.googlesyndication.com",
            "ad.doubleclick.net", "tracking.epicgames.com",
            "analytics.google.com", "facebook.com/tr",
        ]

    def interceptRequest(self, info):
        if not self.enabled:
            return
        url = info.requestUrl().toString().lower()
        for domain in self.blocked_domains:
            if domain in url:
                info.block(True)
                return

# ===================== DATABASE =====================

Base = declarative_base()


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    url = Column(Text, nullable=False)
    source = Column(String(50), nullable=False)
    image_url = Column(Text, default="")
    requires_login = Column(Boolean, default=False)
    has_adfly = Column(Boolean, default=False)
    has_captcha = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_offers_url", "url", unique=True),
        Index("ix_offers_active", "is_active"),
    )

    def __repr__(self):
        return f"<Offer {self.source}: {self.title[:40]}>"


DB_PATH = "sqlite:///matrixhunt.db"
engine = create_engine(DB_PATH, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ===================== SCRAPERS =====================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_reddit_freegames(session):
    """Scrape r/GameDeals and r/FreeGamesForPC via Reddit JSON API."""
    count = 0
    subreddits = ["GameDeals", "FreeGamesForPC", "FreeGameFindings"]
    http = requests.Session()
    http.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json",
    })
    http.cookies.set("over18", "1", domain="reddit.com")
    for sub in subreddits:
        try:
            time.sleep(2)
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=25"
            resp = http.get(url, timeout=15)
            if resp.status_code == 429:
                print(f"[REDDIT] Rate limited on r/{sub}, skipping")
                continue
            if resp.status_code == 403:
                print(f"[REDDIT] 403 on r/{sub}, trying old.reddit.com...")
                resp = http.get(f"https://old.reddit.com/r/{sub}/new.json?limit=25", timeout=15)
                if resp.status_code != 200:
                    print(f"[REDDIT] Also failed on old.reddit.com: {resp.status_code}")
                    continue
            resp.raise_for_status()
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                p = post.get("data", {})
                title = p.get("title", "")
                permalink = p.get("permalink", "")
                selftext = p.get("selftext", "").lower()
                full_url = f"https://www.reddit.com{permalink}" if permalink else ""
                if not full_url:
                    continue
                is_free = "free" in title.lower()
                if not is_free:
                    is_free = "free" in selftext and (
                        "steam" in selftext or "epic" in selftext
                        or "gog" in selftext or "giveaway" in selftext
                    )
                if not is_free:
                    continue
                existing = session.query(Offer).filter_by(url=full_url).first()
                if existing:
                    continue
                offer = Offer(
                    title=title,
                    url=full_url,
                    source="reddit_freegames",
                    requires_login="login" in title.lower() or "sign" in title.lower(),
                    has_adfly="adfly" in title.lower() or "shorten" in title.lower(),
                )
                session.add(offer)
                count += 1
        except Exception as e:
            print(f"[REDDIT] Error scraping r/{sub}: {e}")
    session.commit()
    return count


def scrape_steam_free(session):
    """Scrape free games from Steam via search API."""
    count = 0
    try:
        url = "https://store.steampowered.com/search/?specials=1&maxprice=free&ignore_preferences=1&ndl=1"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("a.search_result_row")
        for row in rows:
            title_el = row.select_one(".title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = row.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://store.steampowered.com{href}"
            price_el = row.select_one(".discount_final_price")
            price_text = price_el.get_text(strip=True) if price_el else ""
            if "Free" not in price_text and price_text != "":
                continue
            existing = session.query(Offer).filter_by(url=href).first()
            if existing:
                continue
            offer = Offer(title=title, url=href, source="steam_free", requires_login=True)
            session.add(offer)
            count += 1
    except Exception as e:
        print(f"[STEAM] Error: {e}")
    session.commit()
    return count


def scrape_epic_free(session):
    """Scrape free games from Epic Games Store via freeGamesPromotions API."""
    count = 0
    try:
        url = (
            "https://store-site-backend-static-ipv4.ak.epicgames.com/"
            "freeGamesPromotions?locale=en-US&country=US&allowCountries=US"
        )
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        elements = (
            data.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
        )
        for item in elements:
            title = item.get("title", "")
            slug = item.get("productSlug") or item.get("urlSlug") or ""
            promos = item.get("promotions")
            is_free = False
            if promos:
                for promo_group in promos.get("promotionalOffers", []):
                    for po in promo_group.get("promotionalOffers", []):
                        disc = po.get("discountSetting", {}).get("discountPercentage")
                        if disc == 0:
                            is_free = True
                            break
            if not is_free:
                price = (
                    item.get("price", {})
                    .get("totalPrice", {})
                    .get("discountPrice", -1)
                )
                if price == 0:
                    is_free = True
            if not is_free:
                continue
            game_url = (
                f"https://store.epicgames.com/en-US/p/{slug}"
                if slug
                else "https://store.epicgames.com/en-US/free-games"
            )
            existing = session.query(Offer).filter_by(url=game_url).first()
            if existing:
                continue
            offer = Offer(
                title=title,
                url=game_url,
                source="epic_free",
                requires_login=True,
            )
            session.add(offer)
            count += 1
    except Exception as e:
        print(f"[EPIC] Error: {e}")
    session.commit()
    return count


def scrape_gog_free(session):
    """Scrape free games from GOG."""
    count = 0
    try:
        url = "https://www.gog.com/games/ajax/filtered?mediaType=game&is_free=true"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        products = data.get("products", [])
        for product in products:
            title = product.get("title", "")
            slug = product.get("slug", "")
            game_url = f"https://www.gog.com/game/{slug}" if slug else "https://www.gog.com/en/games?priceRange=0,0"
            existing = session.query(Offer).filter_by(url=game_url).first()
            if existing:
                continue
            offer = Offer(
                title=title,
                url=game_url,
                source="gog_free",
            )
            session.add(offer)
            count += 1
    except Exception as e:
        print(f"[GOG] Error: {e}")
    session.commit()
    return count


def scrape_itch_free(session):
    """Scrape free games from itch.io."""
    count = 0
    try:
        url = "https://itch.io/games/free/tag-free"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        game_cells = soup.select(".game_cell")
        for cell in game_cells[:30]:
            title_el = cell.select_one("a.title") or cell.select_one(".game_title a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://itch.io{href}"
            price_el = cell.select_one(".price_value")
            price_text = price_el.get_text(strip=True) if price_el else ""
            if price_text and price_text != "Free":
                continue
            existing = session.query(Offer).filter_by(url=href).first()
            if existing:
                continue
            offer = Offer(
                title=title,
                url=href,
                source="itch_free",
                requires_login=True,
            )
            session.add(offer)
            count += 1
    except Exception as e:
        print(f"[ITCH] Error: {e}")
    session.commit()
    return count


def scrape_indiegala_free(session):
    """Scrape free giveaways from IndieGala."""
    count = 0
    try:
        url = "https://freebies.indiegala.com/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cols = soup.select("div.products-col")
        for col in cols:
            inner = col.find("div", class_="products-col-inner")
            if not inner:
                continue
            link_el = inner.find("a", href=True)
            title_div = inner.find("div", class_="product-title")
            if not title_div or not link_el:
                continue
            title = title_div.get_text(strip=True)
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://freebies.indiegala.com{href}"
            existing = session.query(Offer).filter_by(url=href).first()
            if existing:
                continue
            offer = Offer(
                title=title,
                url=href,
                source="indiegala_free",
                requires_login=True,
                has_captcha=True,
            )
            session.add(offer)
            count += 1
    except Exception as e:
        print(f"[INDIEGALA] Error: {e}")
    session.commit()
    return count


def scrape_gamerpower(session):
    """Scrape free game deals from GamerPower API."""
    count = 0
    try:
        url = "https://www.gamerpower.com/api/giveaways"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://www.gamerpower.com/",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 403:
            print("[GAMERPOWER] API blocked, trying web scrape...")
            return scrape_gamerpower_web(session)
        resp.raise_for_status()
        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", data.get("giveaways", []))
        for item in items:
            title = item.get("title", "")
            href = item.get("url", item.get("link", ""))
            if not title or not href:
                continue
            existing = session.query(Offer).filter_by(url=href).first()
            if existing:
                continue
            offer = Offer(
                title=title,
                url=href,
                source="gamerpower",
                requires_login=True,
            )
            session.add(offer)
            count += 1
    except Exception as e:
        print(f"[GAMERPOWER] Error: {e}")
    session.commit()
    return count


def scrape_gamerpower_web(session):
    """Fallback: scrape GamerPower website directly."""
    count = 0
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
        }
        resp = requests.get("https://www.gamerpower.com/giveaway", headers=headers, timeout=15)
        if resp.status_code == 403:
            print("[GAMERPOWER] Web also blocked, skipping")
            return 0
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.card")
        for card in cards[:20]:
            img_el = card.find("img")
            link_el = card.find("a", href=True)
            if not link_el:
                continue
            title = img_el.get("alt", "") if img_el else ""
            if not title:
                continue
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = f"https://www.gamerpower.com{href}"
            existing = session.query(Offer).filter_by(url=href).first()
            if existing:
                continue
            offer = Offer(
                title=title,
                url=href,
                source="gamerpower",
                requires_login=True,
            )
            session.add(offer)
            count += 1
    except Exception as e:
        print(f"[GAMERPOWER] Web error: {e}")
    session.commit()
    return count


SCRAPERS = [
    ("Reddit", scrape_reddit_freegames),
    ("Steam", scrape_steam_free),
    ("Epic", scrape_epic_free),
    ("GOG", scrape_gog_free),
    ("Itch", scrape_itch_free),
    ("IndieGala", scrape_indiegala_free),
    ("GamerPower", scrape_gamerpower),
]


def scrape_all(session):
    """Run all scrapers and return total count."""
    total = 0
    for name, scraper in SCRAPERS:
        try:
            n = scraper(session)
            print(f"  [{name}] +{n} offers")
            total += n
        except Exception as e:
            print(f"  [{name}] FAILED: {e}")
    return total


# ===================== SCRAPER THREAD =====================

class ScraperThread(QThread):
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def run(self):
        session = Session()
        try:
            count = scrape_all(session)
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            session.close()


# ===================== MAIN WINDOW =====================

class MatrixHuntApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("▓▓▓ MATRIXHUNT AGGREGATOR ▓▓▓")
        self.setGeometry(100, 100, 1400, 900)
        self._stats_cache = {"total": 0, "last": "NEVER"}
        self._stats_cache_time = 0

        self.setup_matrix_theme()

        # AdBlocker
        self.ad_blocker = AdBlocker()
        profile = QWebEngineProfile.defaultProfile()
        profile.setUrlRequestInterceptor(self.ad_blocker)
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        layout.addWidget(self.create_header())
        layout.addWidget(self.create_stats_bar())

        # Navigation toolbar
        nav = self.create_navbar()
        layout.addWidget(nav)

        layout.addWidget(self.create_filters())

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout()
        left.setLayout(left_layout)

        self.offers_count_label = QLabel("▓ OFFERS: 0 ▓")
        self.offers_count_label.setStyleSheet(
            "color: #0f0; font-weight: bold; padding: 5px;"
        )
        left_layout.addWidget(self.offers_count_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: #000; border: 1px solid #0a0; }"
        )
        self.offers_container = QWidget()
        self.offers_layout = QVBoxLayout()
        self.offers_container.setLayout(self.offers_layout)
        self.scroll_area.setWidget(self.offers_container)
        left_layout.addWidget(self.scroll_area)

        splitter.addWidget(left)

        self.browser = QWebEngineView()
        splitter.addWidget(self.browser)

        splitter.setSizes([450, 950])
        layout.addWidget(splitter)

        self.statusBar().setStyleSheet("color: #0f0; background: #000;")
        self.statusBar().showMessage("SYS INITIALIZED — READY")

        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.animate_stats)
        self.stats_timer.start(2000)

        self.scrape_timer = QTimer()
        self.scrape_timer.timeout.connect(self.auto_scrape)
        self.scrape_timer.start(300000)

        self.load_offers()

        # Start with dashboard
        self.load_dashboard()

        session = Session()
        try:
            count = session.query(Offer).filter_by(is_active=True).count()
        finally:
            session.close()
        if count == 0:
            self.manual_scrape()

    def setup_matrix_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 255, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 20, 0))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(0, 30, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 255, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(0, 40, 0))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 255, 0))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 80, 0))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        self.setPalette(palette)
        self.setFont(QFont("Courier New", 10))

    def create_header(self):
        header = QLabel("▓▓▓ MATRIXHUNT AGGREGATOR ▓▓▓")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                color: #0f0;
                font-size: 22px;
                font-weight: bold;
                padding: 12px;
                background: rgba(0, 20, 0, 0.9);
                border: 2px solid #0f0;
                border-radius: 5px;
            }
        """)
        return header

    def create_stats_bar(self):
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)

        self.stat_offers = QLabel("OFFERS: 0")
        self.stat_last = QLabel("LAST SCAN: NEVER")
        self.stat_sources = QLabel("SOURCES: 7")
        self.stat_status = QLabel("STATUS: IDLE")

        for stat in [self.stat_offers, self.stat_last, self.stat_sources, self.stat_status]:
            stat.setStyleSheet("""
                QLabel {
                    color: #0f0;
                    font-weight: bold;
                    padding: 8px;
                    background: rgba(0, 40, 0, 0.5);
                    border: 1px solid #0a0;
                    border-radius: 3px;
                }
            """)
            layout.addWidget(stat)
        return widget

    def create_filters(self):
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)

        self.source_filter = QComboBox()
        self.source_filter.addItems([
            "ALL SOURCES", "REDDIT", "STEAM", "EPIC", "GOG", "ITCH", "INDIEGALA", "GAMERPOWER"
        ])
        self.source_filter.currentTextChanged.connect(self.load_offers)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("SEARCH OFFERS...")
        self.search_box.textChanged.connect(self.load_offers)

        self.scrape_btn = QPushButton("⟳ FORCE SCAN")
        self.scrape_btn.clicked.connect(self.manual_scrape)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #000; border: 1px solid #0a0; }
            QProgressBar::chunk { background: #0f0; }
        """)

        btn_style = """
            QComboBox, QLineEdit, QPushButton {
                background: rgba(0, 40, 0, 0.8);
                color: #0f0;
                border: 2px solid #0a0;
                padding: 8px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: rgba(0, 60, 0, 0.8);
                border-color: #0f0;
            }
            QPushButton:disabled {
                color: #060;
                border-color: #030;
            }
        """
        for w in [self.source_filter, self.search_box, self.scrape_btn]:
            w.setStyleSheet(btn_style)

        layout.addWidget(QLabel("SOURCE:"))
        layout.addWidget(self.source_filter)
        layout.addWidget(QLabel("SEARCH:"))
        layout.addWidget(self.search_box)
        layout.addWidget(self.scrape_btn)
        layout.addWidget(self.progress_bar)
        return widget

    def create_navbar(self):
        nav_widget = QWidget()
        nav_layout = QHBoxLayout()
        nav_widget.setLayout(nav_layout)

        self.back_btn = QPushButton("◄ BACK")
        self.back_btn.setFixedWidth(90)
        self.back_btn.clicked.connect(lambda: self.browser.back())

        self.home_btn = QPushButton("⌂ HOME")
        self.home_btn.setFixedWidth(90)
        self.home_btn.clicked.connect(self.load_dashboard)

        self.ext_btn = QPushButton("► OPEN IN BROWSER")
        self.ext_btn.setFixedWidth(140)
        self.ext_btn.clicked.connect(self.open_external)
        self.ext_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 40, 0, 0.8);
                color: #ff0;
                border: 2px solid #660;
                padding: 8px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover { background: rgba(60, 60, 0, 0.8); border-color: #ff0; }
        """)

        self.pad_btn = QPushButton("🎮 PAD TESTER")
        self.pad_btn.setFixedWidth(120)
        self.pad_btn.clicked.connect(self.open_pad_tester)
        self.pad_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 40, 0, 0.8);
                color: #f0f;
                border: 2px solid #606;
                padding: 8px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover { background: rgba(60, 0, 60, 0.8); border-color: #f0f; }
        """)

        self.stealth_cb = QCheckBox("STEALTH SHIELD")
        self.stealth_cb.setChecked(True)
        self.stealth_cb.toggled.connect(self.toggle_stealth)
        self.stealth_cb.setStyleSheet("""
            QCheckBox { color: #0f0; font-weight: bold; padding: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
        """)

        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.home_btn)
        nav_layout.addWidget(self.ext_btn)
        nav_layout.addWidget(self.pad_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.stealth_cb)

        nav_style = """
            QPushButton {
                background: rgba(0, 40, 0, 0.8);
                color: #0f0;
                border: 2px solid #0a0;
                padding: 8px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: rgba(0, 60, 0, 0.8);
                border-color: #0f0;
            }
        """
        self.back_btn.setStyleSheet(nav_style)
        self.home_btn.setStyleSheet(nav_style)

        return nav_widget

    def toggle_stealth(self, checked):
        self.ad_blocker.enabled = checked
        state = "ACTIVE" if checked else "DISABLED"
        self.statusBar().showMessage(f"STEALTH SHIELD: {state}")

    def open_external(self):
        url = self.browser.url().toString()
        if url and url != "about:blank" and is_safe_url(url):
            webbrowser.open(url)

    def open_pad_tester(self):
        pad_path = os.path.join(os.getcwd(), "pad_test.html")
        if os.path.exists(pad_path):
            pad_url = "file:///" + pad_path.replace("\\", "/")
            self.browser.setUrl(QUrl(pad_url))
            self.statusBar().showMessage("PAD TESTER LOADED")
        else:
            QMessageBox.warning(self, "Pad Tester", "pad_test.html not found in project directory.")

    def load_dashboard(self):
        pad_path = os.path.join(os.getcwd(), "pad_test.html").replace("\\", "/")
        html = f"""
        <html><head><style>
            body {{ background:#000b1a; color:#a9a9a9; font-family:'Courier New',monospace; text-align:center; padding:20px; }}
            h1 {{ color:#0f0; letter-spacing:8px; font-size:22px; text-shadow:0 0 15px #0f0; }}
            .label {{ color:#060; font-size:10px; letter-spacing:3px; margin:20px 0 10px 0; }}
            .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; max-width:1000px; margin:0 auto; }}
            .card {{ padding:15px; border:1px solid #0a0; border-radius:5px; cursor:pointer; background:#001a00;
                     transition:0.2s; color:#0f0; font-weight:bold; font-size:12px; font-family:inherit; }}
            .card:hover {{ background:#0f0; color:#000; transform:scale(1.05); box-shadow:0 0 15px #0f0; }}
            .ai {{ border-color:#8a2be2; color:#8a2be2; }}
            .ai:hover {{ background:#8a2be2; color:#fff; }}
            .pl {{ border-color:#ff4100; color:#ff4100; }}
            .pl:hover {{ background:#ff4100; color:#fff; }}
            .pad {{ border-color:#f0f; color:#f0f; }}
            .pad:hover {{ background:#f0f; color:#000; }}
            .info {{ color:#030; font-size:9px; margin-top:30px; letter-spacing:2px; }}
        </style></head><body>
            <h1>MATRIXHUNT COMMAND CENTER</h1>
            <div class="label">GAMING SOURCES</div>
            <div class="grid">
                <div class="card" onclick="window.location='https://store.steampowered.com/search/?specials=1&maxprice=free'">STEAM</div>
                <div class="card" onclick="window.location='https://store.epicgames.com/en-US/free-games'">EPIC GAMES</div>
                <div class="card" onclick="window.location='https://www.gog.com/en/games?price=free'">GOG</div>
                <div class="card" onclick="window.location='https://itch.io/games/free'">ITCH.IO</div>
                <div class="card" onclick="window.location='https://freebies.indiegala.com/'">INDIEGALA</div>
                <div class="card" onclick="window.location='https://www.gamerpower.com/giveaway'">GAMERPOWER</div>
                <div class="card" onclick="window.location='https://www.reddit.com/r/FreeGameFindings/'">REDDIT</div>
                <div class="card" onclick="window.location='https://gg.deals/free-games/'">GG.DEALS</div>
            </div>
            <div class="label">POLISH SOURCES</div>
            <div class="grid">
                <div class="card pl" onclick="window.location='https://lowcygier.pl/darmowe/'">LOWCY GIER</div>
                <div class="card pl" onclick="window.location='https://www.pepper.pl/grupa/gry'">PEPPER.PL</div>
                <div class="card pl" onclick="window.location='https://www.steamcommunity.com/sharedfiles/filedetails/?id=1258430853'">STEAM GRUPA PL</div>
                <div class="card pl" onclick="window.location='https://www.gry-online.pl/darmowe-gry/'">GRY-ONLINE</div>
            </div>
            <div class="label">AI TOOLS</div>
            <div class="grid">
                <div class="card ai" onclick="window.location='https://www.deepseek.com/'">DEEPSEEK</div>
                <div class="card ai" onclick="window.location='https://chatgpt.com/'">CHATGPT</div>
                <div class="card ai" onclick="window.location='https://claude.ai/'">CLAUDE</div>
                <div class="card ai" onclick="window.location='https://gemini.google.com/'">GEMINI</div>
            </div>
            <div class="label">TOOLS</div>
            <div class="grid">
                <div class="card pad" onclick="window.location='file:///{pad_path}'">PAD TESTER</div>
                <div class="card" onclick="window.location='https://mail.proton.me/'">PROTON MAIL</div>
                <div class="card" onclick="window.location='https://steamdb.info/upcoming/free/'">STEAMDB</div>
                <div class="card" onclick="window.location='https://steamdb.info/sales/?min_discount=100&min_rating=0'">STEAM SALES</div>
            </div>
            <div class="info">MATRIXHUNT DESKTOP // 7 SOURCES ACTIVE // STEALTH MODE ENABLED</div>
        </body></html>
        """
        self.browser.setHtml(html)

    def load_offers(self):
        while self.offers_layout.count():
            child = self.offers_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        session = Session()
        try:
            query = session.query(Offer).filter_by(is_active=True)

            source_filter = self.source_filter.currentText()
            source_map = {
                "REDDIT": "reddit_freegames",
                "STEAM": "steam_free",
                "EPIC": "epic_free",
                "GOG": "gog_free",
                "ITCH": "itch_free",
                "INDIEGALA": "indiegala_free",
                "GAMERPOWER": "gamerpower",
            }
            if source_filter in source_map:
                query = query.filter(Offer.source == source_map[source_filter])

            search_term = self.search_box.text().strip()
            if search_term:
                safe = search_term.replace("%", "\\%").replace("_", "\\_")
                query = query.filter(Offer.title.ilike(f"%{safe}%", escape="\\"))

            offers = query.order_by(Offer.created_at.desc()).limit(100).all()

            self.offers_count_label.setText(f"▓ {len(offers)} OFFERS DETECTED ▓")
            self.stat_offers.setText(f"OFFERS: {len(offers)}")

            if not offers:
                empty_label = QLabel("NO OFFERS FOUND — RUN A SCAN")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_label.setStyleSheet("color: #060; font-size: 16px; padding: 40px;")
                self.offers_layout.addWidget(empty_label)

            for offer in offers:
                card = self.create_offer_card(offer)
                self.offers_layout.addWidget(card)
        finally:
            session.close()

        self.offers_layout.addStretch()

    def create_offer_card(self, offer):
        card = QPushButton()
        card.setFixedHeight(100)
        card.clicked.connect(lambda checked, url=offer.url: self.open_in_browser(url))

        source_icons = {
            "reddit_freegames": "R",
            "steam_free": "S",
            "epic_free": "E",
            "gog_free": "G",
            "itch_free": "I",
            "indiegala_free": "IG",
            "gamerpower": "GP",
        }
        icon = source_icons.get(offer.source, "?")

        flags = []
        if offer.requires_login:
            flags.append("LOGIN")
        if offer.has_adfly:
            flags.append("ADFLY")
        if offer.has_captcha:
            flags.append("CAPTCHA")
        flags_text = " ".join(flags)

        card_text = (
            f"[{icon}] {offer.title[:50]}\n"
            f"{'=' * 40}\n"
            f"{offer.source.upper()} {'| ' + flags_text if flags_text else ''}"
        )
        card.setText(card_text)

        card.setStyleSheet("""
            QPushButton {
                background: rgba(0, 30, 0, 0.9);
                color: #0f0;
                border: 2px solid #0a0;
                padding: 8px;
                text-align: left;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: rgba(0, 50, 0, 0.9);
                border-color: #0f0;
                color: #0ff;
            }
        """)
        return card

    def open_in_browser(self, url):
        if not is_safe_url(url):
            self.statusBar().showMessage(f"BLOCKED unsafe URL: {url[:60]}")
            return
        self.browser.setUrl(QUrl(url))
        self.statusBar().showMessage(f"OPENED: {url[:80]}")

    def animate_stats(self):
        now = time.time()
        if now - self._stats_cache_time < 30:
            return
        self._stats_cache_time = now
        session = Session()
        try:
            total = session.query(Offer).filter_by(is_active=True).count()
            last = session.query(Offer).filter_by(is_active=True).order_by(Offer.created_at.desc()).first()
            last_time = last.created_at.strftime("%H:%M") if last else "NEVER"
            self._stats_cache = {"total": total, "last": last_time}
            self.stat_offers.setText(f"OFFERS: {total}")
            self.stat_last.setText(f"LAST: {last_time}")
        except Exception:
            pass
        finally:
            session.close()

    def manual_scrape(self):
        if hasattr(self, "scraper") and self.scraper.isRunning():
            return
        self.scrape_btn.setEnabled(False)
        self.scrape_btn.setText("⟳ SCANNING...")
        self.progress_bar.setVisible(True)
        self.stat_status.setText("STATUS: SCANNING...")
        self.statusBar().showMessage("SCAN IN PROGRESS...")

        self.scraper = ScraperThread()
        self.scraper.finished.connect(self.scrape_finished)
        self.scraper.error.connect(self.scrape_error)
        self.scraper.start()

    def scrape_finished(self, count):
        self.scrape_btn.setEnabled(True)
        self.scrape_btn.setText("⟳ FORCE SCAN")
        self.progress_bar.setVisible(False)
        self.stat_status.setText("STATUS: IDLE")
        self.stat_last.setText(f"LAST SCAN: {datetime.now().strftime('%H:%M:%S')}")
        self.load_offers()
        self.statusBar().showMessage(f"SCAN COMPLETE — {count} new offers found")

    def scrape_error(self, error_msg):
        self.scrape_btn.setEnabled(True)
        self.scrape_btn.setText("⟳ FORCE SCAN")
        self.progress_bar.setVisible(False)
        self.stat_status.setText("STATUS: ERROR")
        self.statusBar().showMessage(f"SCAN FAILED: {error_msg}")
        QMessageBox.warning(self, "Scan Error", f"Scraping failed:\n{error_msg}")

    def auto_scrape(self):
        if hasattr(self, "scraper") and self.scraper.isRunning():
            return
        self.scraper = ScraperThread()
        self.scraper.finished.connect(lambda c: self.load_offers())
        self.scraper.start()


# ===================== MAIN =====================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MatrixHuntApp()
    window.show()
    sys.exit(app.exec())
