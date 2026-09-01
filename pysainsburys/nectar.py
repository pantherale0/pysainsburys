"""Authenticated Nectar offers and Your Nectar Price operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models.nectar import (
    NectarOffer,
    NectarOffers,
    NectarSearchHit,
    NectarSearchResults,
    UnlockYourNectarPriceResult,
    YourNectarPrices,
)
from .models.product import Product, ProductList, bind_products

if TYPE_CHECKING:
    from .api import API

_PRODUCT_BATCH_SIZE = 50


class Nectar:
    """Fetch and search Nectar offers for the authenticated customer."""

    def __init__(self, api: API) -> None:
        self._api = api
        self._offers_cache: NectarOffers | None = None
        self._prices_cache: YourNectarPrices | None = None

    @property
    def offers_cached(self) -> NectarOffers | None:
        """Return the last fetched Nectar offers response, if any."""
        return self._offers_cache

    @property
    def prices_cached(self) -> YourNectarPrices | None:
        """Return the last fetched Your Nectar Prices response, if any."""
        return self._prices_cache

    async def fetch_offers(self) -> NectarOffers:
        """Fetch personalised Nectar bonus-point offers."""
        response = await self._api.send_request(endpoint="get_nectar_offers")
        if not isinstance(response, dict):
            msg = "Nectar offers response was not a JSON object."
            raise TypeError(msg)
        offers = NectarOffers.from_dict(response)
        self._offers_cache = offers
        return offers

    async def fetch_your_nectar_prices(self) -> YourNectarPrices:
        """Fetch Your Nectar Price opt-in state."""
        response = await self._api.send_request(endpoint="get_ynp_opt_ins")
        if not isinstance(response, dict):
            msg = "Your Nectar Prices response was not a JSON object."
            raise TypeError(msg)
        prices = YourNectarPrices.from_dict(response)
        self._prices_cache = prices
        return prices

    async def unlock_your_nectar_prices(
        self,
        offer_id: str | None = None,
    ) -> UnlockYourNectarPriceResult:
        """
        Unlock Your Nectar Price offers.

        The API accepts a single ``offer_id`` but may unlock the full weekly
        selection in one request.
        """
        if offer_id is None:
            prices = await self.fetch_your_nectar_prices()
            if not prices.not_opted_in:
                msg = "No locked Your Nectar Price offers are available to unlock."
                raise ValueError(msg)
            offer_id = prices.not_opted_in[0].offer_id
        response = await self._api.send_request(
            endpoint="unlock_ynp_opt_ins",
            body={"offer_id": offer_id},
        )
        if not isinstance(response, dict):
            msg = "Unlock Your Nectar Prices response was not a JSON object."
            raise TypeError(msg)
        self._prices_cache = None
        return UnlockYourNectarPriceResult.from_dict(response)

    async def search(
        self,
        keyword: str,
        *,
        enrich_products: bool = True,
    ) -> NectarSearchResults:
        """Search Nectar offers and Your Nectar Prices by keyword."""
        query = keyword.strip().casefold()
        if not query:
            return NectarSearchResults(query=keyword, hits=[])

        offers = await self.fetch_offers()
        prices = await self.fetch_your_nectar_prices()
        products: dict[str, Product] = {}
        if enrich_products:
            skus = {price.sku for price in prices.all_offers if price.sku}
            for bonus in offers.offers:
                skus.update(bonus.skus)
            products = await self._fetch_products_for_skus(skus)
            for price in prices.all_offers:
                if price.sku in products:
                    price.product = products[price.sku]

        opted_in_ids = {price.offer_id for price in prices.opted_in}
        hits: list[NectarSearchHit] = []

        for bonus in offers.offers:
            if not self._matches_offer(query, bonus):
                continue
            sku = bonus.skus[0] if bonus.skus else None
            hits.append(
                NectarSearchHit(
                    kind="bonus_offer",
                    offer_id=bonus.offer_id,
                    title=bonus.title,
                    subtitle=bonus.subtitle,
                    points=bonus.points,
                    sku=sku,
                    expires=bonus.expires,
                    product=products.get(sku) if sku else None,
                )
            )

        for price in prices.all_offers:
            product = products.get(price.sku)
            name = product.name if product else ""
            if query not in price.sku.casefold() and query not in name.casefold():
                continue
            hits.append(
                NectarSearchHit(
                    kind="your_nectar_price",
                    offer_id=price.offer_id,
                    sku=price.sku,
                    title=name or None,
                    expires=price.expiry_date,
                    opted_in=price.offer_id in opted_in_ids,
                    product=product,
                )
            )

        return NectarSearchResults(query=keyword, hits=hits)

    async def enrich_your_nectar_prices(
        self,
        prices: YourNectarPrices | None = None,
    ) -> YourNectarPrices:
        """Attach catalogue product details to Your Nectar Price offers."""
        prices = prices or await self.fetch_your_nectar_prices()
        products = await self._fetch_products_for_skus(
            {offer.sku for offer in prices.all_offers if offer.sku}
        )
        for offer in prices.all_offers:
            if offer.sku in products:
                offer.product = products[offer.sku]
        return prices

    async def _fetch_products_for_skus(
        self,
        skus: set[str],
    ) -> dict[str, Product]:
        """Fetch catalogue products for a set of SKUs."""
        if not skus:
            return {}
        ordered = sorted(skus)
        products: dict[str, Product] = {}
        for index in range(0, len(ordered), _PRODUCT_BATCH_SIZE):
            batch = ordered[index : index + _PRODUCT_BATCH_SIZE]
            response = await self._api.send_request(
                endpoint="search_products",
                params={"uid": ",".join(batch)},
            )
            if not isinstance(response, dict):
                continue
            product_list = ProductList.from_dict(response)
            bind_products(self._api, product_list.products)
            for product in product_list.products:
                products[product.product_uid] = product
        return products

    @staticmethod
    def _matches_offer(query: str, offer: NectarOffer) -> bool:
        haystacks = [
            offer.title,
            offer.subtitle,
            offer.offer_id,
            *offer.skus,
        ]
        return any(query in value.casefold() for value in haystacks if value)
