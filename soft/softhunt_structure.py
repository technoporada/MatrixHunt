"""
SoftHuntHQ - Struktura projektu
"""

# requirements.txt
"""
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
beautifulsoup4==4.12.2
requests==2.31.0
feedparser==6.0.10
pydantic==2.5.0
jinja2==3.1.2
python-multipart==0.0.6
schedule==1.2.0
"""

# config.py
import os
from typing import Dict, List

class Config:
    DATABASE_URL = "sqlite:///softhunt.db"
    SCRAPING_INTERVAL = 300  # 5 minut
    MAX_WORKERS = 4
    USER_AGENT = "SoftHuntHQ/1.0"
    
    # Źródła danych
    SOURCES = {
        "reddit_freegames": {
            "url": "https://www.reddit.com/r/FreeGameFindings/.json",
            "type": "json",
            "parser": "reddit"
        },
        "steam_free": {
            "url": "https://store.steampowered.com/search/?sort_by=Released_DESC&category1=998&supportedlang=english&ndl=1",
            "type": "html",
            "parser": "steam"
        },
        "epic_free": {
            "url": "https://store.epicgames.com/en-US/free-games",
            "type": "html", 
            "parser": "epic"
        },
        "indiegala_free": {
            "url": "https://freebies.indiegala.com/",
            "type": "html",
            "parser": "indiegala"
        }
    }
    
    THEMES = {
        "dark": {
            "bg_color": "#1a1a1a",
            "text_color": "#ffffff",
            "accent_color": "#4a9eff"
        },
        "light": {
            "bg_color": "#ffffff", 
            "text_color": "#333333",
            "accent_color": "#0066cc"
        }
    }

# database.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Offer(Base):
    __tablename__ = "offers"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    url = Column(String(500), nullable=False)
    source = Column(String(100), nullable=False)
    tags = Column(String(255))  # comma-separated
    expires_at = Column(DateTime)
    requires_login = Column(Boolean, default=False)
    has_adfly = Column(Boolean, default=False)
    has_captcha = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)

class DatabaseManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
    
    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

# scrapers/base.py
from abc import ABC, abstractmethod
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import feedparser

class BaseScraper(ABC):
    def __init__(self, user_agent: str):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
    
    @abstractmethod
    def parse(self, url: str) -> List[Dict]:
        pass
    
    def get_html(self, url: str) -> BeautifulSoup:
        response = self.session.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    
    def get_json(self, url: str) -> Dict:
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

# scrapers/reddit.py
from .base import BaseScraper
from typing import List, Dict
from datetime import datetime

class RedditScraper(BaseScraper):
    def parse(self, url: str) -> List[Dict]:
        data = self.get_json(url)
        offers = []
        
        for post in data.get('data', {}).get('children', []):
            post_data = post.get('data', {})
            
            # Filtruj posty o grach/programach
            title = post_data.get('title', '').lower()
            if any(keyword in title for keyword in ['free', 'giveaway', 'steam', 'epic', 'game']):
                offers.append({
                    'title': post_data.get('title', ''),
                    'description': post_data.get('selftext', ''),
                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                    'source': 'reddit_freegames',
                    'tags': self._extract_tags(post_data.get('title', '')),
                    'expires_at': None,
                    'requires_login': True,
                    'has_adfly': 'adfly' in post_data.get('selftext', '').lower(),
                    'has_captcha': False
                })
        
        return offers
    
    def _extract_tags(self, title: str) -> str:
        tags = []
        title_lower = title.lower()
        
        if 'steam' in title_lower:
            tags.append('steam')
        if 'epic' in title_lower:
            tags.append('epic')
        if 'game' in title_lower:
            tags.append('game')
        if 'android' in title_lower:
            tags.append('android')
        if 'windows' in title_lower:
            tags.append('windows')
            
        return ','.join(tags)

# scrapers/steam.py
from .base import BaseScraper
from typing import List, Dict

class SteamScraper(BaseScraper):
    def parse(self, url: str) -> List[Dict]:
        soup = self.get_html(url)
        offers = []
        
        for game in soup.find_all('div', class_='search_result_row'):
            title_elem = game.find('span', class_='title')
            price_elem = game.find('div', class_='search_price')
            
            if title_elem and price_elem and 'free' in price_elem.text.lower():
                offers.append({
                    'title': title_elem.text.strip(),
                    'description': '',
                    'url': game.get('href', ''),
                    'source': 'steam_free',
                    'tags': 'steam,game',
                    'expires_at': None,
                    'requires_login': True,
                    'has_adfly': False,
                    'has_captcha': False
                })
        
        return offers

# scrapers/manager.py
from typing import Dict, List
from .reddit import RedditScraper
from .steam import SteamScraper
from config import Config

class ScraperManager:
    def __init__(self, user_agent: str):
        self.scrapers = {
            'reddit': RedditScraper(user_agent),
            'steam': SteamScraper(user_agent)
        }
    
    def scrape_source(self, source_name: str, source_config: Dict) -> List[Dict]:
        parser_type = source_config.get('parser')
        scraper = self.scrapers.get(parser_type)
        
        if not scraper:
            return []
        
        try:
            return scraper.parse(source_config['url'])
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
            return []

# services/offer_service.py
from sqlalchemy.orm import Session
from database import Offer
from typing import List, Dict, Optional

class OfferService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_offer(self, offer_data: Dict) -> Offer:
        # Sprawdź czy oferta już istnieje
        existing = self.db.query(Offer).filter(
            Offer.title == offer_data['title'],
            Offer.source == offer_data['source']
        ).first()
        
        if existing:
            return existing
        
        offer = Offer(**offer_data)
        self.db.add(offer)
        self.db.commit()
        self.db.refresh(offer)
        return offer
    
    def get_offers(self, 
                   skip: int = 0, 
                   limit: int = 100,
                   source: Optional[str] = None,
                   tags: Optional[str] = None,
                   active_only: bool = True) -> List[Offer]:
        query = self.db.query(Offer)
        
        if active_only:
            query = query.filter(Offer.is_active == True)
        
        if source:
            query = query.filter(Offer.source == source)
        
        if tags:
            query = query.filter(Offer.tags.contains(tags))
        
        return query.order_by(Offer.created_at.desc()).offset(skip).limit(limit).all()
    
    def update_notes(self, offer_id: int, notes: str) -> Optional[Offer]:
        offer = self.db.query(Offer).filter(Offer.id == offer_id).first()
        if offer:
            offer.notes = notes
            self.db.commit()
            self.db.refresh(offer)
        return offer
    
    def deactivate_offer(self, offer_id: int) -> Optional[Offer]:
        offer = self.db.query(Offer).filter(Offer.id == offer_id).first()
        if offer:
            offer.is_active = False
            self.db.commit()
            self.db.refresh(offer)
        return offer

# main.py
from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import DatabaseManager
from services.offer_service import OfferService
from scrapers.manager import ScraperManager
from config import Config
import schedule
import threading
import time

app = FastAPI(title="SoftHuntHQ", version="1.0.0")

# Inicjalizacja
db_manager = DatabaseManager(Config.DATABASE_URL)
scraper_manager = ScraperManager(Config.USER_AGENT)
templates = Jinja2Templates(directory="templates")

# Statyczne pliki
app.mount("/static", StaticFiles(directory="static"), name="static")

def background_scraper():
    """Scraper działający w tle"""
    def scrape_all():
        db = next(db_manager.get_db())
        service = OfferService(db)
        
        for source_name, source_config in Config.SOURCES.items():
            offers = scraper_manager.scrape_source(source_name, source_config)
            
            for offer_data in offers:
                service.create_offer(offer_data)
        
        db.close()
    
    schedule.every(Config.SCRAPING_INTERVAL).seconds.do(scrape_all)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# Uruchom scraper w tle
scraper_thread = threading.Thread(target=background_scraper, daemon=True)
scraper_thread.start()

# Endpointy API
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(db_manager.get_db)):
    service = OfferService(db)
    offers = service.get_offers(limit=50)
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "offers": offers,
        "theme": Config.THEMES["dark"]
    })

@app.get("/api/offers")
async def get_offers(
    skip: int = 0,
    limit: int = 100,
    source: str = None,
    tags: str = None,
    db: Session = Depends(db_manager.get_db)
):
    service = OfferService(db)
    offers = service.get_offers(skip=skip, limit=limit, source=source, tags=tags)
    return [
        {
            "id": offer.id,
            "title": offer.title,
            "description": offer.description,
            "url": offer.url,
            "source": offer.source,
            "tags": offer.tags,
            "expires_at": offer.expires_at,
            "requires_login": offer.requires_login,
            "has_adfly": offer.has_adfly,
            "has_captcha": offer.has_captcha,
            "created_at": offer.created_at,
            "notes": offer.notes
        }
        for offer in offers
    ]

@app.post("/api/offers/{offer_id}/notes")
async def update_notes(
    offer_id: int,
    notes: str = Form(...),
    db: Session = Depends(db_manager.get_db)
):
    service = OfferService(db)
    offer = service.update_notes(offer_id, notes)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"message": "Notes updated successfully"}

@app.post("/api/offers/{offer_id}/deactivate")
async def deactivate_offer(
    offer_id: int,
    db: Session = Depends(db_manager.get_db)
):
    service = OfferService(db)
    offer = service.deactivate_offer(offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"message": "Offer deactivated successfully"}

@app.post("/api/scrape")
async def manual_scrape(db: Session = Depends(db_manager.get_db)):
    """Ręczne uruchomienie scrapera"""
    service = OfferService(db)
    total_offers = 0
    
    for source_name, source_config in Config.SOURCES.items():
        offers = scraper_manager.scrape_source(source_name, source_config)
        
        for offer_data in offers:
            service.create_offer(offer_data)
            total_offers += 1
    
    return {"message": f"Scraped {total_offers} new offers"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# cli.py
import argparse
from database import DatabaseManager
from services.offer_service import OfferService
from scrapers.manager import ScraperManager
from config import Config

def main():
    parser = argparse.ArgumentParser(description="SoftHuntHQ CLI")
    parser.add_argument("--scrape", action="store_true", help="Run scraper")
    parser.add_argument("--list", action="store_true", help="List offers")
    parser.add_argument("--source", help="Filter by source")
    parser.add_argument("--tags", help="Filter by tags")
    parser.add_argument("--limit", type=int, default=20, help="Limit results")
    
    args = parser.parse_args()
    
    db_manager = DatabaseManager(Config.DATABASE_URL)
    db = next(db_manager.get_db())
    service = OfferService(db)
    
    if args.scrape:
        scraper_manager = ScraperManager(Config.USER_AGENT)
        total = 0
        
        for source_name, source_config in Config.SOURCES.items():
            offers = scraper_manager.scrape_source(source_name, source_config)
            
            for offer_data in offers:
                service.create_offer(offer_data)
                total += 1
        
        print(f"Scraped {total} offers")
    
    if args.list:
        offers = service.get_offers(
            limit=args.limit,
            source=args.source,
            tags=args.tags
        )
        
        for offer in offers:
            print(f"[{offer.source}] {offer.title}")
            print(f"  URL: {offer.url}")
            print(f"  Tags: {offer.tags}")
            if offer.notes:
                print(f"  Notes: {offer.notes}")
            print()

if __name__ == "__main__":
    main()
