# scrapers/epic.py
from .base import BaseScraper
from typing import List, Dict

class EpicScraper(BaseScraper):
    def parse(self, url: str) -> List[Dict]:
        soup = self.get_html(url)
        offers = []
        
        # Epic Games może wymagać bardziej zaawansowanego scrapowania
        # ze względu na dynamiczne ładowanie zawartości
        try:
            # Szukamy elementów zawierających darmowe gry
            game_cards = soup.find_all('div', {'data-testid': 'offer-card'}) or \
                        soup.find_all('article', class_='css-1mlqmqe') or \
                        soup.find_all('div', class_='css-1myhtyb')
            
            for card in game_cards:
                title_elem = card.find('span', {'data-testid': 'offer-title'}) or \
                           card.find('h3') or card.find('span', class_='css-119zqif')
                
                if title_elem:
                    offers.append({
                        'title': title_elem.text.strip(),
                        'description': 'Darmowa gra z Epic Games Store',
                        'url': 'https://store.epicgames.com/en-US/free-games',
                        'source': 'epic_free',
                        'tags': 'epic,game',
                        'expires_at': None,
                        'requires_login': True,
                        'has_adfly': False,
                        'has_captcha': False
                    })
        except Exception as e:
            print(f"Epic scraper error: {e}")
        
        return offers

# scrapers/indiegala.py
from .base import BaseScraper
from typing import List, Dict

class IndieGalaScraper(BaseScraper):
    def parse(self, url: str) -> List[Dict]:
        soup = self.get_html(url)
        offers = []
        
        try:
            # Scrapowanie IndieGala freebies
            freebie_items = soup.find_all('div', class_='giveaway-item') or \
                          soup.find_all('article', class_='item') or \
                          soup.find_all('div', class_='freebies-item')
            
            for item in freebie_items:
                title_elem = item.find('h3') or item.find('h2') or item.find('.title')
                link_elem = item.find('a')
                
                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    link = link_elem.get('href', '')
                    
                    if not link.startswith('http'):
                        link = 'https://freebies.indiegala.com' + link
                    
                    offers.append({
                        'title': title,
                        'description': 'Darmowa oferta z IndieGala',
                        'url': link,
                        'source': 'indiegala_free',
                        'tags': 'indiegala,game',
                        'expires_at': None,
                        'requires_login': True,
                        'has_adfly': False,
                        'has_captcha': True
                    })
        except Exception as e:
            print(f"IndieGala scraper error: {e}")
        
        return offers

# scrapers/gog.py
from .base import BaseScraper
from typing import List, Dict

class GOGScraper(BaseScraper):
    def parse(self, url: str) -> List[Dict]:
        # GOG nie ma stałego URL-a dla darmowych gier, 
        # ale możemy sprawdzać ich feed lub główną stronę
        try:
            soup = self.get_html('https://www.gog.com/')
            offers = []
            
            # Szukamy promocji i darmowych gier
            promo_tiles = soup.find_all('div', class_='tile') or \
                         soup.find_all('product-tile')
            
            for tile in promo_tiles:
                price_elem = tile.find('span', class_='price')
                title_elem = tile.find('span', class_='title')
                
                if price_elem and title_elem:
                    price_text = price_elem.text.lower()
                    if 'free' in price_text or '$0' in price_text:
                        offers.append({
                            'title': title_elem.text.strip(),
                            'description': 'Darmowa gra z GOG',
                            'url': 'https://www.gog.com/',
                            'source': 'gog_free',
                            'tags': 'gog,game,drm-free',
                            'expires_at': None,
                            'requires_login': True,
                            'has_adfly': False,
                            'has_captcha': False
                        })
            
            return offers
        except Exception as e:
            print(f"GOG scraper error: {e}")
            return []

# scrapers/itch.py
from .base import BaseScraper
from typing import List, Dict

class ItchScraper(BaseScraper):
    def parse(self, url: str) -> List[Dict]:
        # itch.io free games
        try:
            soup = self.get_html('https://itch.io/games/free')
            offers = []
            
            game_cells = soup.find_all('div', class_='game_cell') or \
                        soup.find_all('a', class_='thumb_link')
            
            for cell in game_cells[:20]:  # Limit to first 20
                title_elem = cell.find('div', class_='game_title') or \
                           cell.find('span', class_='game_title')
                link_elem = cell if cell.name == 'a' else cell.find('a')
                
                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    link = link_elem.get('href', '')
                    
                    if not link.startswith('http'):
                        link = 'https://itch.io' + link
                    
                    offers.append({
                        'title': title,
                        'description': 'Darmowa gra indie z itch.io',
                        'url': link,
                        'source': 'itch_free',
                        'tags': 'itch,indie,game',
                        'expires_at': None,
                        'requires_login': False,
                        'has_adfly': False,
                        'has_captcha': False
                    })
            
            return offers
        except Exception as e:
            print(f"Itch.io scraper error: {e}")
            return []

# Zaktualizowany scrapers/manager.py z nowymi scraperami
from typing import Dict, List
from .reddit import RedditScraper
from .steam import SteamScraper
from .epic import EpicScraper
from .indiegala import IndieGalaScraper
from .gog import GOGScraper
from .itch import ItchScraper

class ScraperManager:
    def __init__(self, user_agent: str):
        self.scrapers = {
            'reddit': RedditScraper(user_agent),
            'steam': SteamScraper(user_agent),
            'epic': EpicScraper(user_agent),
            'indiegala': IndieGalaScraper(user_agent),
            'gog': GOGScraper(user_agent),
            'itch': ItchScraper(user_agent)
        }
    
    def scrape_source(self, source_name: str, source_config: Dict) -> List[Dict]:
        parser_type = source_config.get('parser')
        scraper = self.scrapers.get(parser_type)
        
        if not scraper:
            print(f"No scraper found for parser type: {parser_type}")
            return []
        
        try:
            print(f"Scraping {source_name}...")
            offers = scraper.parse(source_config['url'])
            print(f"Found {len(offers)} offers from {source_name}")
            return offers
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
            return []

# docker-compose.yml
"""
version: '3.8'
services:
  softhunt:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=sqlite:///data/softhunt.db
      - LOG_LEVEL=INFO
    restart: unless-stopped
"""

# Dockerfile
"""
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data logs static templates

EXPOSE 8000

CMD ["python", "main.py"]
"""

# README.md
"""
# SoftHuntHQ

Lokalny agregator darmowych gier i oprogramowania.

## Funkcje
- Automatyczne scrapowanie ofert z wielu źródeł (Steam, Epic, Reddit, IndieGala, GOG, itch.io)
- Filtrowanie i kategoryzowanie ofert
- Interfejs webowy z notatkami użytkownika
- Tryb ciemny/jasny
- CLI do zarządzania
- Lokalna baza SQLite

## Instalacja

1. Sklonuj repozytorium
2. Zainstaluj zależności: `pip install -r requirements.txt`
3. Uruchom: `python main.py`
4. Otwórz http://localhost:8000

## Użycie CLI

```bash
# Uruchom scraper
python cli.py --scrape

# Wylistuj oferty
python cli.py --list --limit 10

# Filtruj po źródle
python cli.py --list --source steam_free

# Filtruj po tagach
python cli.py --list --tags game
```

## Konfiguracja

Edytuj `config.py` aby:
- Dodać nowe źródła
- Zmienić interwał scrapowania
- Dostosować motywy kolorystyczne

## Struktura plików

```
softhunt/
├── main.py              # FastAPI aplikacja
├── cli.py               # Interface CLI
├── config.py            # Konfiguracja
├── database.py          # SQLAlchemy modele
├── services/
│   └── offer_service.py # Logika biznesowa
├── scrapers/
│   ├── base.py          # Bazowa klasa scrapera
│   ├── manager.py       # Manager scraperów
│   ├── reddit.py        # Scraper Reddit
│   ├── steam.py         # Scraper Steam
│   ├── epic.py          # Scraper Epic Games
│   ├── indiegala.py     # Scraper IndieGala
│   ├── gog.py           # Scraper GOG
│   └── itch.py          # Scraper itch.io
└── templates/
    └── index.html       # Template HTML
```

## Licencja

MIT License - używaj jak chcesz, na własną odpowiedzialność.
"""

# start.py - Pomocny skrypt startowy
import subprocess
import sys
import os

def install_requirements():
    """Instaluje wymagane pakiety"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Zależności zainstalowane")
    except subprocess.CalledProcessError:
        print("❌ Błąd instalacji zależności")
        sys.exit(1)

def create_directories():
    """Tworzy potrzebne katalogi"""
    dirs = ['data', 'logs', 'static', 'templates', 'scrapers', 'services']
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
    print("✅ Katalogi utworzone")

def main():
    print("🎮 SoftHuntHQ - Inicjalizacja")
    print("=" * 40)
    
    # Sprawdź czy requirements.txt istnieje
    if not os.path.exists('requirements.txt'):
        print("❌ Brak pliku requirements.txt")
        sys.exit(1)
    
    # Zainstaluj zależności
    install_requirements()
    
    # Utwórz katalogi
    create_directories()
    
    print("\n✅ Inicjalizacja zakończona!")
    print("\nAby uruchomić aplikację:")
    print("  python main.py")
    print("\nAby użyć CLI:")
    print("  python cli.py --help")
    print("\nInterfejs webowy:")
    print("  http://localhost:8000")

if __name__ == "__main__":
    main()
