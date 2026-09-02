# Quick Start

## Install

```bash
pip install pysainsburys
# or, from a checkout:
uv sync
```

## Search products (no login)

```python
import asyncio

from pysainsburys import GOLAuth, Sainsburys


async def main() -> None:
    async with Sainsburys(GOLAuth()) as client:
        results = await client.search_products("bread", page_size=5)
        for product in results.products:
            price = product.retail_price.price if product.retail_price else None
            print(product.product_uid, product.name, price)


asyncio.run(main())
```

## Product detail and nutrition

Product detail responses include base64-encoded HTML. The client parses
nutrition tables automatically:

```python
product = await client.get_product("3236048")
if product.nutrition:
    for item in product.nutrition.summary:
        print(item.name, item.values, item.level)
```

## Sign in

Save a session file after browser or credential login:

```bash
python -m pysainsburys auth login
# or complete browser login:
python -m pysainsburys auth url
python -m pysainsburys auth finish 'https://www.sainsburys.co.uk/gol-ui/oauth/redirect?code=...'
```

Then use the saved session in Python:

```python
from pysainsburys import GOLAuth, Sainsburys

auth = await GOLAuth.from_session_file("~/.config/pysainsburys/session.json")
async with Sainsburys(auth) as client:
    customer = await client.get_customer()
    print(customer.display_name)
    basket = await customer.basket.fetch()
    print(basket.item_count, "items")
```

## Command line

```bash
python -m pysainsburys product search bread
python -m pysainsburys product show 3236048
python -m pysainsburys basket show
python -m pysainsburys favourites list
```

## Next steps

- [Basic usage](../user-guide/basic-usage.md)
- [Models](../user-guide/models.md)
- [API reference](../api/reference.md)
