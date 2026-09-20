# MatrixHunt

Agregator darmowych gier — jeden program, który za Ciebie szuka.

## Co to robi?

MatrixHunt to aplikacja na komputer, która automatycznie sprawdza kilka źródeł gier i zbiera wszystkie darmowe oferty w jednym miejscu. Nie musisz już codziennie wchodzić na reddita, Steam, Epic Games, GOG i Itch.io — program robi to za Ciebie.

Masz listę darmowych gier na lewo i wbudowaną przeglądarkę na prawo. Klikasz na grę i od razu widzisz stronę z nią.

## Dashboard

Po uruchomieniu widzisz panel z szybkimi linkami do:
- **Gaming** — Steam, Epic, GOG, itch.io, IndieGala, GamerPower, Reddit, GG.deals
- **Polskie** — Łowcy Gier, Pepper.pl, Steam Grupa PL, Gry-OnLINE
- **AI** — DeepSeek, ChatGPT, Claude, Gemini
- **Narzędzia** — Pad Tester, Proton Mail, SteamDB

## Skąd bierze gry?

Program sprawdza 7 źródeł:

- **Reddit** — subreddity z darmowymi grami (r/GameDeals, r/FreeGamesForPC, r/FreeGameFindings)
- **Steam** — darmowe gry ze sklepu Steam
- **Epic Games Store** — darmowe gry tygodnia z Epic (GraphQL API)
- **GOG** — darmowe gry z GOG.com (API JSON)
- **Itch.io** — darmowe gry z Itch.io
- **IndieGala** — darmowe giveaways z IndieGala
- **GamerPower** — agregator darmowych gier

## Tester Padów

Wbudowany `pad_test.html` — otwórz go przez przycisk "PAD TESTER" w programie lub osobno w przeglądarce:
- Wykrywanie padów (USB/Bluetooth)
- Test przycisków (A/B/X/Y, LB/RB, LT/RT, D-pad, itd.)
- Radar analogów z wykrywaniem driftu (czy gałka wraca na środek?)
- Test wibracji

## Stealth Shield

Wbudowany AdBlocker blokujący reklamy i trackery w wbudowanej przeglądarce:
- Blokuje Google Analytics, DoubleClick, Facebook Pixel i inne
- Możesz go włączyć/wyłączyć przyciskiem "STEALTH SHIELD"
- Blokuje reklamy w przeglądarkach stron z grami

## Jak zainstalować?

Potrzebujesz Pythona 3.10 lub nowszego. Jeśli nie wiesz jak go mieć — wejdź na https://www.python.org/downloads/ i pobierz najnowszą wersję.

Otwórz terminal (w Windows: naciśnij Win+R, wpisz `cmd` i Enter) i wpisz po kolei:

```
pip install PyQt6 PyQt6-WebEngine requests beautifulsoup4 sqlalchemy
```

To pobraże potrzebne biblioteki. Musisz to zrobić raz.

## Jak uruchomić?

W terminalu wejdź do folderu z programem i wpisz:

```
cd C:\sciezka\do\folderu\hunt
python hunt.py
```

Po uruchomieniu pojawi się okno z czarno-zielonym interfejsem. Program sam zacznie szukać darmowych gier.

## Jak używać?

- **FORCE SCAN** — kliknij, żeby ręcznie sprawdzić wszystkie źródła od nowa
- **SOURCE** — wybierz źródło, żeby zobaczyć gry tylko z niego (np. tylko Steam)
- **SEARCH** — wpisz frazę, żeby znaleźć konkretną grę
- **◄ BACK** — cofnij do poprzedniej strony
- **⌂ HOME** — wróć do dashboardu z linkami
- **► OPEN IN BROWSER** — otwórz aktualną stronę w domyślnej przeglądarce
- **🎮 PAD TESTER** — otwórz testera padów
- **STEALTH SHIELD** — włącz/wyłącz AdBlocker
- Kliknij na grę z listy — otworzy się strona z nią po prawej stronie
- Program sprawdza nowe gry co 5 minut automatycznie

## Ikony przy grach

Każda gra ma oznaczenie źródła:

- `[R]` — Reddit
- `[S]` — Steam
- `[E]` — Epic Games
- `[G]` — GOG
- `[I]` — Itch.io
- `[IG]` — IndieGala
- `[GP]` — GamerPower

Przy grze może też być info:
- **LOGIN** — trzeba się zalogować żeby odebrać
- **ADFLY** — link przechodzi przez skracacz
- **CAPTCHA** — może wyskoczyć captcha

## Co jeszcze?

- Dane zapisują się w pliku `matrixhunt.db` — nie musisz się martwić o duplikaty
- Program zapamiętuje oferty, więc po zamknięciu i ponownym uruchomieniu lista nadal tam jest
- Wystarczy raz uruchomić, a potem tylko klikać "FORCE SCAN" kiedy chcesz
- Stealth Shield blokuje reklamy w przeglądarkach stron z grami

## Nie działa?

Najczęstsze problemy:

1. **"python nie jest rozpoznawany"** — zainstaluj Pythona zaznaczając "Add Python to PATH" przy instalacji
2. **"ModuleNotFoundError"** — wpisz `pip install PyQt6 PyQt6-WebEngine requests beautifulsoup4 sqlalchemy`
3. **Pusta lista** — kliknij FORCE SCAN, bo pierwsze uruchomienie musi pobrać dane
4. **Niektóre źródła nie działają** — to normalne, strony czasami zmieniają wygląd. Program pokaże błąd w konsoli ale reszta źródeł nadal będzie działać
5. **Pad Tester nie działa** — upewnij się, że pad jest podłączony (USB/Bluetooth) i otwarty w przeglądarce Chrome/Edge
