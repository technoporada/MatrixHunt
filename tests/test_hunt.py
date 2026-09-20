"""MatrixHunt Tests"""

import sys
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mock PyQt6 before importing hunt
mock_pyqt6 = MagicMock()
sys.modules["PyQt6"] = mock_pyqt6
sys.modules["PyQt6.QtWidgets"] = mock_pyqt6.QtWidgets
sys.modules["PyQt6.QtWebEngineWidgets"] = mock_pyqt6.QtWebEngineWidgets
sys.modules["PyQt6.QtWebEngineCore"] = mock_pyqt6.QtWebEngineCore
sys.modules["PyQt6.QtCore"] = mock_pyqt6.QtCore
sys.modules["PyQt6.QtGui"] = mock_pyqt6.QtGui

from hunt import (
    Base, Offer, is_safe_url,
    scrape_reddit_freegames, scrape_steam_free, scrape_epic_free,
    scrape_gog_free, scrape_itch_free, scrape_indiegala_free,
    scrape_gamerpower, scrape_all,
)


TEST_DB = "sqlite:///test_hunt.db"
engine = create_engine(TEST_DB, echo=False)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session():
    db = TestSession()
    yield db
    db.close()


def test_is_safe_url():
    assert is_safe_url("https://a9b3c7d2.test") is True
    assert is_safe_url("http://a9b3c7d2.test") is True
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("javascript:alert(1)") is False
    assert is_safe_url("data:text/html,<h1>hi</h1>") is False
    assert is_safe_url("") is True


def test_offer_creation(session):
    offer = Offer(title="Test Game", url="https://a9b3c7d2.test/game", source="test")
    session.add(offer)
    session.commit()
    assert offer.id is not None
    assert offer.is_active is True
    assert offer.requires_login is False


def test_offer_unique_url(session):
    offer1 = Offer(title="Game 1", url="https://a9b3c7d2.test/game", source="test")
    offer2 = Offer(title="Game 2", url="https://a9b3c7d2.test/game", source="test")
    session.add(offer1)
    session.commit()
    session.add(offer2)
    with pytest.raises(Exception):
        session.commit()


def test_offer_repr():
    offer = Offer(title="Test Game Title Here", url="https://a9b3c7d2.test", source="steam")
    assert "steam" in repr(offer)
    assert "Test Game Title Here" in repr(offer)


def test_scrape_reddit_mock(session):
    responses = []
    for sub in ["GameDeals", "FreeGamesForPC", "FreeGameFindings"]:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": f"Free Game {sub}!",
                            "permalink": f"/r/{sub}/comments/abc123/free_game",
                            "selftext": "Get this free game on Steam",
                        }
                    },
                ]
            }
        }
        responses.append(mock_resp)
    empty_resp = MagicMock()
    empty_resp.status_code = 200
    empty_resp.json.return_value = {"data": {"children": []}}
    responses.append(empty_resp)

    with patch("hunt.requests.Session") as mock_session:
        instance = mock_session.return_value
        instance.get.side_effect = responses
        instance.cookies.set.return_value = None
        count = scrape_reddit_freegames(session)
    offers = session.query(Offer).filter_by(source="reddit_freegames").all()
    assert len(offers) >= 1
    assert "Free Game" in offers[0].title


def test_scrape_epic_mock(session):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": [
                        {
                            "title": "Epic Free Game",
                            "productSlug": "free-game",
                            "promotions": {
                                "promotionalOffers": [
                                    {
                                        "promotionalOffers": [
                                            {
                                                "discountSetting": {
                                                    "discountPercentage": 0
                                                }
                                            }
                                        ]
                                    }
                                ]
                            },
                            "price": {"totalPrice": {"discountPrice": 0}},
                        }
                    ]
                }
            }
        }
    }
    with patch("hunt.requests.get", return_value=mock_resp):
        count = scrape_epic_free(session)
    assert count == 1
    offers = session.query(Offer).filter_by(source="epic_free").all()
    assert len(offers) == 1


def test_scrape_gog_mock(session):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "products": [
            {"title": "GOG Free Game", "slug": "free-game"}
        ]
    }
    with patch("hunt.requests.get", return_value=mock_resp):
        count = scrape_gog_free(session)
    assert count == 1
    offers = session.query(Offer).filter_by(source="gog_free").all()
    assert len(offers) == 1


def test_scrape_steam_mock(session):
    html = """
    <html><body>
    <a class="search_result_row" href="https://store.steampowered.com/app/123">
        <span class="title">Free Steam Game</span>
        <span class="discount_final_price">Free</span>
    </a>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    with patch("hunt.requests.get", return_value=mock_resp):
        count = scrape_steam_free(session)
    assert count == 1
    offers = session.query(Offer).filter_by(source="steam_free").all()
    assert len(offers) == 1


def test_scrape_itch_mock(session):
    html = """
    <html><body>
    <div class="game_cell">
        <a class="title" href="https://itch.io/game/free">Free Itch Game</a>
        <span class="price_value">Free</span>
    </div>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    with patch("hunt.requests.get", return_value=mock_resp):
        count = scrape_itch_free(session)
    assert count == 1
    offers = session.query(Offer).filter_by(source="itch_free").all()
    assert len(offers) == 1


def test_scrape_indiegala_mock(session):
    html = """
    <html><body>
    <div class="products-col">
        <div class="products-col-inner">
            <a href="/giveaway/123">
                <div class="product-title">IndieGala Free</div>
            </a>
        </div>
    </div>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    with patch("hunt.requests.get", return_value=mock_resp):
        count = scrape_indiegala_free(session)
    assert count == 1
    offers = session.query(Offer).filter_by(source="indiegala_free").all()
    assert len(offers) == 1


def test_scrape_gamerpower_api_mock(session):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"title": "GP Free Game", "url": "https://gamerpower.com/giveaway/123"}
    ]
    with patch("hunt.requests.get", return_value=mock_resp):
        count = scrape_gamerpower(session)
    assert count == 1
    offers = session.query(Offer).filter_by(source="gamerpower").all()
    assert len(offers) == 1


def test_scrape_gamerpower_403_fallback(session):
    mock_resp_api = MagicMock()
    mock_resp_api.status_code = 403

    html = """
    <html><body>
    <div class="card">
        <img alt="Fallback Game">
        <a href="/giveaway/456"></a>
    </div>
    </body></html>
    """
    mock_resp_web = MagicMock()
    mock_resp_web.status_code = 200
    mock_resp_web.text = html

    with patch("hunt.requests.get", side_effect=[mock_resp_api, mock_resp_web]):
        count = scrape_gamerpower(session)
    assert count == 1


def test_scrape_dedup(session):
    existing = Offer(title="Already exists", url="https://www.gog.com/game/exist", source="test")
    session.add(existing)
    session.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "products": [
            {"title": "Already exists", "slug": "exist"}
        ]
    }
    with patch("hunt.requests.get", return_value=mock_resp):
        count = scrape_gog_free(session)
    assert count == 0
