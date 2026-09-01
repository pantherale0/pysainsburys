# Sainsbury's Groceries Online API

**pysainsburys** is an async Python client for the Sainsbury's Groceries Online
(GOL) mobile API. It exposes a human-centric interface over product search,
basket management, favourites, orders, stores, and authentication.

## Features

- Async-first API built on **aiohttp**
- Typed domain models under :mod:`pysainsburys.models`, organised by area
- Public catalogue access (search, product detail, nutrition) without login
- Authenticated flows for basket, favourites, orders, and customer profile
- Command-line interface via ``python -m pysainsburys``
- Python 3.10+ with full type hints

## Quick links

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quick-start.md)
- [Models overview](user-guide/models.md)
- [API Reference](api/reference.md)

## Example

```python
import asyncio

from pysainsburys import GOLAuth, Sainsburys


async def main() -> None:
    async with Sainsburys(GOLAuth()) as client:
        results = await client.search_products("semi skimmed milk")
        for product in results.products:
            print(product.product_uid, product.name, product.retail_price)


asyncio.run(main())
```
