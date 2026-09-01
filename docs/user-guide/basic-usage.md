# Basic Usage

## Client lifecycle

Create a :class:`~pysainsburys.Sainsburys` client with a :class:`~pysainsburys.GOLAuth`
session and close it when finished. The async context manager is the simplest
pattern:

```python
from pysainsburys import GOLAuth, Sainsburys

auth = GOLAuth.from_session_file("~/.config/pysainsburys/session.json")

async with Sainsburys(auth) as client:
    customer = await client.get_customer()
    basket = await customer.basket.fetch()
```

For public endpoints (search, product detail, store lookup), an empty
``GOLAuth()`` is sufficient — no saved session is required.

## Authentication

| Method | When to use |
| --- | --- |
| ``GOLAuth.from_session_file(path)`` | Reuse a session saved by the CLI or a previous login |
| ``auth.login(email, password)`` | Credential login (MFA supported) |
| ``auth.send_login_request()`` + ``auth.finish_login(redirect)`` | Browser-based OAuth with PKCE |

After login, persist the session for reuse:

```python
auth.save_session_file("~/.config/pysainsburys/session.json")
```

## Products

```python
# Search (public)
results = await client.search_products("milk", page_number=1, page_size=24)

# Detail with nutrition (public)
product = await client.get_product("3236048")
print(product.nutrition.summary if product.nutrition else "no nutrition data")
```

## Basket

Authenticated basket changes go through ``customer.basket``:

```python
customer = await client.get_customer()

basket = await customer.basket.fetch()
await customer.basket.add("3236048", 2)
await customer.basket.set_quantity("3236048", 3, item_uid="line-uid")
await customer.basket.remove("3236048")
await customer.basket.clear()
```

You can also mutate a bound :class:`~pysainsburys.models.product.product.Product`:

```python
product = await client.get_product("3236048")
await product.add_to_basket(2)
await product.set_basket_quantity(0)  # removes the line
```

CLI examples::

    pysainsburys basket show
    pysainsburys basket add 3236048 --quantity 2
    pysainsburys basket set 3236048 3 --item-uid LINE_UID
    pysainsburys basket remove 3236048
    pysainsburys basket clear

Use ``basket show`` to read each line's ``line`` id before ``set`` or ``remove``.

## Customer resources

Authenticated helpers hang off :class:`~pysainsburys.models.customer.Customer`:

```python
customer = await client.get_customer()

favourites = await customer.favourites.fetch()
await customer.favourites.add("3236048")

orders = await customer.orders.fetch()
status = await customer.orders.latest.status()
```

## Stores

```python
# Nearby stores (public)
stores = await client.find_stores(lat=51.5, lon=-0.12)

# Click and collect by postcode (public)
stores = await client.find_stores_by_postcode("SW1A 1AA")

# In-store aisle search (store must be bound to client)
store = await client.get_store("1234")
products = await store.search_products("milk")
```

## Refreshing cached state

Call :meth:`~pysainsburys.Sainsburys.update` to reload customer, basket,
favourites, orders, and the latest order status in one pass:

```python
await client.update()
```

Register callbacks to run after each update cycle:

```python
client.register_callback(lambda: print("data refreshed"))
```

## Models

Domain objects live under :mod:`pysainsburys.models`. See the
[models guide](models.md) for the package layout and import recommendations.

## CLI

Command groups mirror the library modules:

| Group | Commands |
| --- | --- |
| `auth` | `url`, `finish`, `login`, `mfa`, `resend-mfa`, `refresh`, `logout` |
| `customer` | `show` |
| `basket` | `show`, `add`, `set`, `remove`, `clear` |
| `favourites` | `list`, `add`, `remove` |
| `orders` | `list`, `show`, `status` |
| `product` | `show`, `search` |
| `store` | `near`, `postcode`, `show`, `search` |

```bash
python -m pysainsburys --help
python -m pysainsburys product search bread --page 2
python -m pysainsburys product show 3236048 --json
python -m pysainsburys basket add 3236048 --quantity 2
python -m pysainsburys favourites add 3236048
python -m pysainsburys store search 2665 milk
python -m pysainsburys auth refresh
```

Session files default to ``~/.config/pysainsburys/session.json``. Override with
``--session /path/to/session.json``.
