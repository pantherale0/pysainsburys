# Quick Start

## Minimal example

```python
import asyncio

from pysainsburys import Client, Config

async def main() -> None:
    config = Config(
        base_url="http://192.168.1.10:8080",
    )

    async with Client(config) as client:
        print(f"Ready — talking {client.protocol}")

asyncio.run(main())
```

## Next steps

- [Basic usage](../user-guide/basic-usage.md)
- [API reference](../api/reference.md)
