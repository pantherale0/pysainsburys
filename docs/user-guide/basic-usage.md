# Basic Usage

## Working with the client

The usual pattern is to create a client, connect, do your work, then disconnect:

```python
from pysainsburys import Client, Config

config = Config(
    base_url="http://192.168.1.10:8080",
)

async with Client(config) as client:
    adapter = client.adapter
    # protocol-specific work happens here
```

Or call `connect()` and `disconnect()` yourself if you need finer control.

## Configuration

All connection settings live in `Config`. See `config.py` for the fields available for the **http** protocol.

## HTTP requests

Use the aiohttp session from the adapter:

```python
session = client.adapter.session
```
