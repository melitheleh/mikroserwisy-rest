# System rozproszony z wykorzystaniem REST API

Prosty system złożony z dwóch niezależnych mikroserwisów, które komunikują się ze sobą przez REST API. Serwis Magazynowy przed zwróceniem stanu magazynowego sprawdza w Serwisie Produktów (prawdziwym zapytaniem HTTP), czy produkt istnieje.

## Technologie

- Python 3.11+
- FastAPI – framework do tworzenia REST API
- Uvicorn – serwer HTTP uruchamiający aplikacje
- HTTPX – klient HTTP do komunikacji między serwisami
- Pydantic – modele danych i walidacja odpowiedzi

## Architektura

| Serwis | Katalog | Adres | Odpowiedzialność |
|---|---|---|---|
| Serwis Produktów | `product-service/` | `127.0.0.1:8001` | Dane o produktach (`id`, `name`, `price`) |
| Serwis Magazynowy | `stock-service/` | `127.0.0.1:8002` | Stany magazynowe produktów |

Każdy serwis to osobna aplikacja z własnym `main.py` i `requirements.txt`, uruchamiana jako osobny proces. Serwisy nie importują nawzajem swojego kodu – łączy je wyłącznie kontrakt REST API.

Schemat komunikacji:

```text
Klient → Serwis Magazynowy (8002) → Serwis Produktów (8001)
```

## Kontrakt REST API

### Serwis Produktów – `GET /products/{id}`

Sukces – **200 OK**:

```json
{ "id": 123, "name": "Laptop", "price": 4500.0 }
```

Produkt nie istnieje – **404 Not Found**:

```json
{ "detail": "Produkt o ID 999 nie istnieje" }
```

### Serwis Magazynowy – `GET /stock/{productId}`

Produkt istnieje – **200 OK** (jeśli produkt nie ma wpisu w magazynie, `quantity` wynosi `0`):

```json
{ "productId": 123, "quantity": 15 }
```

Produkt nie istnieje – **404 Not Found**:

```json
{ "detail": "Produkt o ID 999 nie istnieje" }
```

Serwis Produktów niedostępny – **503 Service Unavailable**:

```json
{ "detail": "Serwis Produktów jest chwilowo niedostępny" }
```

### Kody HTTP

| Kod | Znaczenie |
|---|---|
| 200 | Zapytanie obsłużone poprawnie |
| 404 | Produkt o podanym ID nie istnieje |
| 503 | Serwis Produktów nie odpowiada (wyłączony, timeout 3 s lub błąd 5xx) |
| 422 | Nieprawidłowy typ ID, np. tekst zamiast liczby (standardowa walidacja FastAPI) |

## Instalacja i uruchomienie

Wszystkie polecenia wykonuj w głównym katalogu projektu (`mikroserwisy-rest`), chyba że napisano inaczej.

### 1. Środowisko wirtualne i zależności

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r product-service/requirements.txt -r stock-service/requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r product-service\requirements.txt -r stock-service\requirements.txt
```

### 2. Terminal 1 – Serwis Produktów

```bash
cd product-service
python main.py
```

### 3. Terminal 2 – Serwis Magazynowy

W nowym terminalu najpierw aktywuj środowisko (`source .venv/bin/activate` lub `.venv\Scripts\Activate.ps1`), a następnie:

```bash
cd stock-service
python main.py
```

Opcjonalnie adres Serwisu Produktów można zmienić zmienną środowiskową `PRODUCT_SERVICE_URL` (domyślnie `http://localhost:8001`).

### 4. Zatrzymanie serwerów

W każdym terminalu z serwerem naciśnij `Ctrl+C`.

## Dane testowe

| ID | Produkt | Stan magazynowy |
|---|---|---|
| 123 | Laptop | 15 |
| 124 | Monitor | 7 |
| 125 | Klawiatura | 42 |
| 126 | Mysz | 0 |
| 127 | Słuchawki | brak wpisu → `0` |
| 999 | nie istnieje | – |

## Przykładowe testy

Na Windows w PowerShell zamiast `curl` użyj `curl.exe`.

| Test | Polecenie | Oczekiwany wynik |
|---|---|---|
| 1 | `curl -i http://localhost:8001/products/123` | 200 + dane produktu |
| 2 | `curl -i http://localhost:8001/products/999` | 404 |
| 3 | `curl -i http://localhost:8002/stock/123` | 200 + `quantity: 15` |
| 4 | `curl -i http://localhost:8002/stock/999` | 404 |
| 5 | `curl -i http://localhost:8002/stock/123` przy wyłączonym Serwisie Produktów | 503 |
| 6 | `curl -i http://localhost:8002/stock/127` | 200 + `quantity: 0` |

Dokumentacja interaktywna (Swagger) jest dostępna pod adresami `http://localhost:8001/docs` i `http://localhost:8002/docs`.

## Jak działa komunikacja między serwisami

Po otrzymaniu zapytania `GET /stock/{productId}` Serwis Magazynowy wysyła przez HTTPX zapytanie `GET /products/{productId}` do Serwisu Produktów, z limitem czasu 3 sekundy. Serwis Produktów jest jedynym źródłem informacji o tym, czy produkt istnieje:

- odpowiedź **200** – Serwis Magazynowy sprawdza lokalny słownik stanów i zwraca ilość (lub `0`),
- odpowiedź **404** – Serwis Magazynowy zwraca klientowi 404,
- brak połączenia, przekroczenie czasu lub błąd 5xx – Serwis Magazynowy zwraca 503.

Każdy krok jest logowany w terminalach obu serwisów, więc w logach widać pełny przepływ zapytania: odebranie żądania przez Serwis Magazynowy, wysłanie zapytania do Serwisu Produktów, jego obsługę i odpowiedź zwróconą klientowi.
