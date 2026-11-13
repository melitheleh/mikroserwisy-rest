"""Serwis Produktów (Product Service) – udostępnia dane o produktach."""

import logging

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = 8001

# Własny logger z nazwą serwisu w formacie. propagate=False zapobiega
# podwójnemu wyświetlaniu komunikatów (przez nasz handler i logger główny).
logger = logging.getLogger("product-service")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s [PRODUCT-SERVICE] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
logger.addHandler(handler)
logger.propagate = False


class Product(BaseModel):
    id: int
    name: str
    price: float


# "Baza danych" w pamięci – słownik, w którym kluczem jest ID produktu.
PRODUCTS: dict[int, Product] = {
    123: Product(id=123, name="Laptop", price=4500.00),
    124: Product(id=124, name="Monitor", price=899.99),
    125: Product(id=125, name="Klawiatura", price=249.50),
    126: Product(id=126, name="Mysz", price=129.00),
    127: Product(id=127, name="Słuchawki", price=349.00),
}

app = FastAPI(title="Product Service")


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int) -> Product:
    logger.info("Otrzymano zapytanie o produkt %d", product_id)

    product = PRODUCTS.get(product_id)
    if product is None:
        logger.warning("Produkt %d nie istnieje, zwracam 404", product_id)
        raise HTTPException(
            status_code=404,
            detail=f"Produkt o ID {product_id} nie istnieje",
        )

    logger.info("Znaleziono produkt: %s", product.name)
    return product


if __name__ == "__main__":
    logger.info("Uruchamiam Serwis Produktów na porcie %d", SERVICE_PORT)
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
