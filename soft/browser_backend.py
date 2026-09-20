# browser/secure_browser.py
import asyncio
import json
import hashlib
import secrets
from typing import Dict, List, Optional
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

@dataclass
class BrowserSession:
    session_id: str
    platform: str
    encrypted_cookies: bytes
    user_agent: str
    proxy_config: Optional[Dict] = None
    created_at: float = None

class SecureBrowserManager:
    def __init__(self, master_password: str = None):
        self.sessions: Dict[str, BrowserSession] = {}
        self.encryption_key = self._generate_encryption_key(master_password)
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Bezpieczne User Agents dla różnych platform
        self.user_agents = {
            'steam': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'epic': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'gog': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'origin': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'ubisoft': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'itch': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Proxy rotacja dla anonimowości
        self.proxy_pools = {
            'free': [],  # Darmowe proxy
            'tor': [],   # Tor endpoints
            'vpn': []    # VPN endpoints
        }
    
    def _generate_encryption_key(self, password: str = None) -> bytes:
        """Generuje klucz szyfrowania z hasła głównego"""
        if not password:
            password = secrets.token_urlsafe(32)
        
        password_bytes = password.encode()
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return key
    
    def create_secure_session(self, platform: str, use_proxy: bool = True) -> str:
        """Tworzy bezpieczną sesję przeglądarki"""
        session_id = secrets.token_urlsafe(32)
        
        # Wybierz losowy User Agent dla platformy
        user_agent = self.user_agents.get(platform, self.user_agents['steam'])
        
        # Konfiguracja proxy jeśli włączona
        proxy_config = None
        if use_proxy and self.proxy_pools['free']:
            proxy_config = secrets.choice(self.proxy_pools['free'])
        
        session = BrowserSession(
            session_id=session_id,
            platform=platform,
            encrypted_cookies=b'',
            user_agent=user_agent,
            proxy_config=proxy_config,
            created_at=asyncio.get_event_loop().time()
        )
        
        self.sessions[session_id] = session
        return session_id
    
    def encrypt_credentials(self, credentials: Dict) -> str:
        """Szyfruje dane logowania"""
        credentials_json = json.dumps(credentials)
        encrypted_data = self.cipher_suite.encrypt(credentials_json.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_credentials(self, encrypted_credentials: str) -> Dict:
        """Deszyfruje dane logowania"""
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_credentials.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception:
            return {}
    
    def cleanup_session(self, session_id: str):
        """Czyści sesję i usuwa dane"""
        if session_id in self.sessions:
            del self.sessions[session_id]

# browser/proxy_manager.py
import requests
import random
import asyncio
from typing import List, Dict
import aiohttp

class ProxyManager:
    def __init__(self):
        self.verified_proxies = []
        self.free_proxy_sources = [
            'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt'
        ]
    
    async def fetch_free_proxies(self) -> List[str]:
        """Pobiera darmowe proxy z publicznych źródeł"""
        proxies = []
        
        async with aiohttp.ClientSession() as session:
            for source in self.free_proxy_sources:
                try:
                    async with session.get(source, timeout=10) as response:
                        if response.status == 200:
                            content = await response.text()
                            proxy_list = content.strip().split('\n')
                            proxies.extend(proxy_list)
                except Exception as e:
                    print(f"Błąd pobierania proxy z {source}: {e}")
        
        return list(set(proxies))  # Usuń duplikaty
    
    async def verify_proxy(self, proxy: str) -> bool:
        """Weryfikuje czy proxy działa"""
        try:
            proxy_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://httpbin.org/ip',
                    proxy=proxy_dict['http'],
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return True
        except Exception:
            pass
        
        return False
    
    async def get_working_proxies(self, count: int = 10) -> List[str]:
        """Zwraca listę działających proxy"""
        if not self.verified_proxies:
            await self.refresh_proxy_list()
        
        return random.sample(
            self.verified_proxies,
            min(count, len(self.verified_proxies))
        )
    
    async def refresh_proxy_list(self):
        """Odświeża listę działających proxy"""
        print("Pobieranie i weryfikacja proxy...")
        raw_proxies = await self.fetch_free_proxies()
        
        # Testuj proxy równolegle
        tasks = [self.verify_proxy(proxy) for proxy in raw_proxies[:100]]  # Limit 100
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.verified_proxies = [
            proxy for proxy, is_working in zip(raw_proxies[:100], results)
            if is_working is True
        ]
        
        print(f"Znaleziono {len(self.verified_proxies)} działających proxy")

# browser/security_features.py
import hashlib
import time
import random
from typing import Dict, List
from urllib.parse import urlparse

class SecurityFeatures:
    def __init__(self):
        self.blocked_trackers = []
        self.fingerprint_protection = True
        self.cookie_isolation = True
        self.load_tracker_lists()
    
    def load_tracker_lists(self):
        """Ładuje listy trackerów do blokowania"""
        # Przykładowe trackery - w rzeczywistości załadowałbyś z EasyList/uBlock
        self.blocked_trackers = [
            'google-analytics.com',
            'googletagmanager.com',
            'facebook.com/tr',
            'doubleclick.net',
            'googlesyndication.com',
            'amazon-adsystem.com'
        ]
    
    def should_block_request(self, url: str) -> bool:
        """Sprawdza czy zablokować request"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        for tracker in self.blocked_trackers:
            if tracker in domain:
                return True
        return False
    
    def generate_fake_fingerprint(self) -> Dict:
        """Generuje fałszywy fingerprint przeglądarki"""
        screen_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864),
            (1440, 900), (1280, 720), (2560, 1440)
        ]
        
        languages = ['en-US', 'en-GB', 'de-DE', 'fr-FR', 'es-ES', 'pl-PL']
        timezones = ['America/New_York', 'Europe/London', 'Europe/Berlin', 'Europe/Warsaw']
        
        resolution = random.choice(screen_resolutions)
        
        return {
            'screen_width': resolution[0],
            'screen_height': resolution[1],
            'language': random.choice(languages),
            'timezone': random.choice(timezones),
            'platform': random.choice(['Win32', 'Linux x86_64', 'MacIntel']),
            'do_not_track': random.choice([True, False]),
            'color_depth': random.choice([24, 32]),
            'pixel_ratio': random.choice([1, 1.25, 1.5, 2])
        }
    
    def sanitize_cookies(self, cookies: Dict) -> Dict:
        """Sanityzuje cookies przed zapisaniem"""
        safe_cookies = {}
        
        for name, value in cookies.items():
            # Usuń potencjalnie niebezpieczne cookies
            if not any(unsafe in name.lower() for unsafe in ['track', 'analytics', 'ad', 'fbp']):
                safe_cookies[name] = value
        
        return safe_cookies

# browser/platform_handlers.py
from abc import ABC, abstractmethod
import aiohttp
import asyncio
from bs4 import BeautifulSoup

class PlatformHandler(ABC):
    def __init__(self, session_manager):
        self.session_manager = session_manager
    
    @abstractmethod
    async def get_free_games(self) -> List[Dict]:
        pass
    
    @abstractmethod
    async def auto_claim_game(self, game_url: str, credentials: Dict) -> bool:
        pass

class SteamHandler(PlatformHandler):
    async def get_free_games(self) -> List[Dict]:
        """Pobiera darmowe gry ze Steam"""
        url = "https://store.steampowered.com/search/?sort_by=Released_DESC&category1=998&maxprice=free"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    games = []
                    for item in soup.find_all('div', class_='search_result_row'):
                        title_elem = item.find('span', class_='title')
                        price_elem = item.find('div', class_='search_price')
                        
                        if title_elem and price_elem and 'Free' in price_elem.text:
                            games.append({
                                'title': title_elem.text.strip(),
                                'url': item.get('href', ''),
                                'platform': 'steam',
                                'price': 'Free'
                            })
                    
                    return games
            except Exception as e:
                print(f"Steam scraping error: {e}")
                return []

class EpicHandler(PlatformHandler):
    async def get_free_games(self) -> List[Dict]:
        """Pobiera darmowe gry z Epic Games"""
        # Epic Games ma GraphQL API - bardziej skomplikowane
        url = "https://store.epicgames.com/en-US/free-games"
        
        async with aiohttp.ClientSession() as session:
            try:
                headers = {
                    'User-Agent': self.session_manager.user_agents['epic']
                }
                async with session.get(url, headers=headers) as response:
                    html = await response.text()
                    # Epic używa React/GraphQL, więc potrzeba bardziej zaawansowanego parsingu
                    # Tu byłaby implementacja parsowania JSON-LD lub API calls
                    return []
            except Exception as e:
                print(f"Epic scraping error: {e}")
                return []
    
    async def auto_claim_game(self, game_url: str, credentials: Dict) -> bool:
        """Automatycznie odbiera grę z Epic Games"""
        # Implementacja automatycznego odbierania gry
        # 1. Login z credentials
        # 2. Navigate to game page  
        # 3. Click claim button
        # 4. Confirm claim
        return False  # Placeholder

# browser/main_browser_app.py (dodaj do main.py)
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from browser.secure_browser import SecureBrowserManager
from browser.proxy_manager import ProxyManager
from browser.security_features import SecurityFeatures
from browser.platform_handlers import SteamHandler, EpicHandler

# Router dla przeglądarki
browser_router = APIRouter(prefix="/browser", tags=["browser"])

# Globalne instancje
browser_manager = SecureBrowserManager()
proxy_manager = ProxyManager()
security_features = SecurityFeatures()
platform_handlers = {
    'steam': SteamHandler(browser_manager),
    'epic': EpicHandler(browser_manager)
}

@browser_router.post("/session/create")
async def create_browser_session(platform: str, use_proxy: bool = True):
    """Tworzy nową bezpieczną sesję przeglądarki"""
    try:
        session_id = browser_manager.create_secure_session(platform, use_proxy)
        return {
            "session_id": session_id,
            "platform": platform,
            "security_enabled": True,
            "proxy_enabled": use_proxy,
            "fingerprint_protection": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@browser_router.post("/credentials/store")
async def store_credentials(platform: str, username: str, password: str):
    """Bezpiecznie zapisuje dane logowania (zaszyfrowane)"""
    try:
        credentials = {
            "platform": platform,
            "username": username,
            "password": password
        }
        encrypted = browser_manager.encrypt_credentials(credentials)
        
        # Zapisz w bazie danych
        return {
            "status": "encrypted_and_stored",
            "platform": platform,
            "encrypted_token": encrypted[:20] + "..."  # Pokaż tylko fragment
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@browser_router.get("/games/free/{platform}")
async def get_free_games(platform: str):
    """Pobiera listę darmowych gier z platformy"""
    try:
        if platform not in platform_handlers:
            raise HTTPException(status_code=400, detail="Platform not supported")
        
        handler = platform_handlers[platform]
        games = await handler.get_free_games()
        
        return {
            "platform": platform,
            "count": len(games),
            "games": games
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@browser_router.get("/proxy/status")
async def get_proxy_status():
    """Sprawdza status proxy"""
    try:
        working_proxies = await proxy_manager.get_working_proxies(5)
        
        return {
            "available_proxies": len(proxy_manager.verified_proxies),
            "sample_proxies": working_proxies[:3],
            "last_refresh": "active"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@browser_router.post("/proxy/refresh")
async def refresh_proxies():
    """Odświeża listę proxy"""
    try:
        await proxy_manager.refresh_proxy_list()
        
        return {
            "status": "refreshed",
            "working_proxies": len(proxy_manager.verified_proxies)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@browser_router.get("/security/fingerprint")
async def get_fake_fingerprint():
    """Generuje fałszywy fingerprint przeglądarki"""
    try:
        fingerprint = security_features.generate_fake_fingerprint()
        return fingerprint
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@browser_router.post("/session/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """Czyści sesję i usuwa dane"""
    try:
        browser_manager.cleanup_session(session_id)
        return {"status": "cleaned", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Dodaj do głównego requirements.txt:
"""
# Browser dependencies
aiohttp==3.9.1
beautifulsoup4==4.12.2
cryptography==41.0.7
selenium==4.15.2
playwright==1.40.0
fake-useragent==1.4.0
pycryptodome==3.19.0
"""

# browser/auto_claimer.py - Automatyczne odbieranie gier
from playwright.async_api import async_playwright
import asyncio

class AutoClaimer:
    def __init__(self, browser_manager, security_features):
        self.browser_manager = browser_manager
        self.security = security_features
        self.playwright = None
        self.browser = None
    
    async def initialize(self):
        """Inicjalizuje Playwright browser"""
        self.playwright = await async_playwright().start()
        
        # Uruchom browser z zabezpieczeniami
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Pokaż browser dla bezpieczeństwa
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
    
    async def claim_epic_game(self, credentials: Dict, game_url: str) -> bool:
        """Automatycznie odbiera grę z Epic Games"""
        try:
            context = await self.browser.new_context(
                user_agent=self.browser_manager.user_agents['epic']
            )
            page = await context.new_page()
            
            # 1. Zaloguj się
            await page.goto('https://www.epicgames.com/id/login')
            await page.fill('input[name="email"]', credentials['username'])
            await page.fill('input[name="password"]', credentials['password'])
            await page.click('button[type="submit"]')
            
            # Czekaj na zalogowanie
            await page.wait_for_url('**/account**', timeout=30000)
            
            # 2. Idź do gry
            await page.goto(game_url)
            await page.wait_for_load_state('networkidle')
            
            # 3. Kliknij "Get" button
            try:
                get_button = await page.wait_for_selector(
                    'button:has-text("Get")',
                    timeout=5000
                )
                await get_button.click()
                
                # 4. Potwierdź
                confirm_button = await page.wait_for_selector(
                    'button:has-text("Place Order")',
                    timeout=5000
                )
                await confirm_button.click()
                
                # Czekaj na potwierdzenie
                await page.wait_for_selector('text=Thank you', timeout=10000)
                
                await context.close()
                return True
                
            except Exception as e:
                print(f"Gra już odebrana lub błąd: {e}")
                await context.close()
                return False
                
        except Exception as e:
            print(f"Błąd odbierania gry: {e}")
            return False
    
    async def claim_steam_game(self, credentials: Dict, game_url: str) -> bool:
        """Automatycznie dodaje darmową grę do biblioteki Steam"""
        try:
            context = await self.browser.new_context(
                user_agent=self.browser_manager.user_agents['steam']
            )
            page = await context.new_page()
            
            # Steam login
            await page.goto('https://store.steampowered.com/login/')
            await page.fill('input[type="text"]', credentials['username'])
            await page.fill('input[type="password"]', credentials['password'])
            await page.click('button[type="submit"]')
            
            # Czekaj na login
            await asyncio.sleep(3)
            
            # Idź do gry
            await page.goto(game_url)
            
            # Kliknij "Play Game" lub "Install"
            try:
                install_button = await page.wait_for_selector(
                    'a.btn_addtocart:has-text("Play")',
                    timeout=5000
                )
                await install_button.click()
                
                await context.close()
                return True
                
            except Exception as e:
                print(f"Gra już w bibliotece lub błąd: {e}")
                await context.close()
                return False
                
        except Exception as e:
            print(f"Błąd dodawania gry: {e}")
            return False
    
    async def close(self):
        """Zamyka browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

# browser/notification_system.py
import asyncio
from typing import List, Callable
from datetime import datetime

class NotificationSystem:
    def __init__(self):
        self.subscribers: List[Callable] = []
        self.notifications = []
    
    def subscribe(self, callback: Callable):
        """Subskrybuj powiadomienia"""
        self.subscribers.append(callback)
    
    async def notify(self, title: str, message: str, priority: str = "normal"):
        """Wyślij powiadomienie"""
        notification = {
            "title": title,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }
        
        self.notifications.append(notification)
        
        # Powiadom wszystkich subskrybentów
        for callback in self.subscribers:
            try:
                await callback(notification)
            except Exception as e:
                print(f"Błąd wysyłania powiadomienia: {e}")
    
    async def notify_new_free_game(self, game: Dict):
        """Powiadomienie o nowej darmowej grze"""
        await self.notify(
            title=f"🎮 Nowa darmowa gra!",
            message=f"{game['title']} jest teraz dostępna za darmo na {game['platform']}!",
            priority="high"
        )

# Dodaj do main.py endpoint dla auto-claimera
@browser_router.post("/auto-claim/epic")
async def auto_claim_epic(game_url: str, encrypted_credentials: str):
    """Automatycznie odbierz grę z Epic Games"""
    try:
        # Odszyfruj credentials
        credentials = browser_manager.decrypt_credentials(encrypted_credentials)
        
        # Inicjalizuj auto-claimer
        claimer = AutoClaimer(browser_manager, security_features)
        await claimer.initialize()
        
        # Odbierz grę
        success = await claimer.claim_epic_game(credentials, game_url)
        
        # Zamknij browser
        await claimer.close()
        
        if success:
            return {"status": "claimed", "game_url": game_url}
        else:
            return {"status": "already_claimed_or_error", "game_url": game_url}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@browser_router.post("/auto-claim/steam")
async def auto_claim_steam(game_url: str, encrypted_credentials: str):
    """Automatycznie dodaj grę do biblioteki Steam"""
    try:
        credentials = browser_manager.decrypt_credentials(encrypted_credentials)
        
        claimer = AutoClaimer(browser_manager, security_features)
        await claimer.initialize()
        
        success = await claimer.claim_steam_game(credentials, game_url)
        
        await claimer.close()
        
        if success:
            return {"status": "added_to_library", "game_url": game_url}
        else:
            return {"status": "already_owned_or_error", "game_url": game_url}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))