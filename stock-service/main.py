"""Serwis Magazynowy (Stock Service) – udostępnia stany magazynowe produktów."""

import logging
import os

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = 8002
# Adres Serwisu Produktów można zmienić zmienną środowiskową.
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
REQUEST_TIMEOUT_SECONDS = 3.0

logger = logging.getLogger("stock-service")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s [STOCK-SERVICE] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
logger.addHandler(handler)
logger.propagate = False


class StockResponse(BaseModel):
    # Nazwa pola zgodna z kontraktem API (JSON), dlatego camelCase.
    productId: int
    quantity: int


# Stany magazynowe. Produkt 127 celowo nie ma wpisu (scenariusz D).
STOCK: dict[int, int] = {
    123: 15,
    124: 7,
    125: 42,
    126: 0,
}

SERVICE_UNAVAILABLE = HTTPException(
    status_code=503,
    detail="Serwis Produktów jest chwilowo niedostępny",
)

app = FastAPI(title="Stock Service")


@app.get("/stock/{product_id}", response_model=StockResponse)
def get_stock(product_id: int) -> StockResponse:
    logger.info("Otrzymano zapytanie o stan produktu %d", product_id)

    # Krok 1: pytamy Serwis Produktów, czy produkt istnieje (prawdziwe HTTP).
    url = f"{PRODUCT_SERVICE_URL}/products/{product_id}"
    logger.info("Wysyłam zapytanie do Serwisu Produktów: %s", url)
    try:
        response = httpx.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.TimeoutException:
        logger.error("Przekroczono czas oczekiwania (%.0f s) na Serwis Produktów",
                     REQUEST_TIMEOUT_SECONDS)
        raise SERVICE_UNAVAILABLE
    except httpx.RequestError as error:
        # Np. odrzucone połączenie, gdy Serwis Produktów jest wyłączony.
        logger.error("Błąd połączenia z Serwisem Produktów: %s", error)
        raise SERVICE_UNAVAILABLE

    logger.info("Serwis Produktów odpowiedział statusem %d", response.status_code)

    # Krok 2: decyzja na podstawie odpowiedzi.
    if response.status_code == 404:
        logger.warning("Produkt %d nie istnieje, zwracam 404", product_id)
        raise HTTPException(
            status_code=404,
            detail=f"Produkt o ID {product_id} nie istnieje",
        )
    if response.status_code != 200:
        # 5xx lub inny nieoczekiwany status – nie możemy potwierdzić produktu.
        logger.error("Nieoczekiwany status %d z Serwisu Produktów, zwracam 503",
                     response.status_code)
        raise SERVICE_UNAVAILABLE

    # Krok 3: produkt istnieje – sprawdzamy lokalny magazyn (brak wpisu = 0).
    quantity = STOCK.get(product_id, 0)
    logger.info("Zwracam stan produktu %d: %d szt.", product_id, quantity)
    return StockResponse(productId=product_id, quantity=quantity)


if __name__ == "__main__":
    logger.info("Uruchamiam Serwis Magazynowy na porcie %d", SERVICE_PORT)
    logger.info("Adres Serwisu Produktów: %s", PRODUCT_SERVICE_URL)
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
