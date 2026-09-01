"""Customer order history and status."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models.order import OrderList, OrderStatus, OrderSummary

if TYPE_CHECKING:
    from .api import API


class OrderHandle:
    """A single order and its status, addressable by id."""

    def __init__(self, api: API, order_id: str) -> None:
        self._api = api
        self.order_id = order_id
        self._summary: OrderSummary | None = None
        self._status: OrderStatus | None = None

    @property
    def cached(self) -> OrderSummary | None:
        """Return the last fetched order summary, if any."""
        return self._summary

    async def fetch(self) -> OrderSummary:
        """Fetch full order details."""
        response = await self._api.send_request(
            endpoint="get_order",
            ORDER_ID=self.order_id,
        )
        if not isinstance(response, dict):
            msg = "Order response was not a JSON object."
            raise TypeError(msg)
        self._summary = OrderSummary.from_dict(response)
        return self._summary

    async def status(self) -> OrderStatus:
        """Fetch live status for this order."""
        response = await self._api.send_request(endpoint="get_order_status")
        if not isinstance(response, dict):
            msg = "Order status response was not a JSON object."
            raise TypeError(msg)
        order_status = OrderStatus.from_dict(response)
        if order_status.order_uid and order_status.order_uid != self.order_id:
            summary = await self.fetch()
            order_status = OrderStatus(
                order_uid=summary.order_uid or summary.order_id,
                total=summary.total or 0.0,
                order_type=summary.slot_type,
                slot_start_time=summary.slot_start_time,
                slot_end_time=summary.slot_end_time,
            )
        self._status = order_status
        return order_status

    @property
    def cached_status(self) -> OrderStatus | None:
        """Return the last fetched order status, if any."""
        return self._status


class Orders:
    """Order history and status for a customer."""

    def __init__(self, api: API) -> None:
        self._api = api
        self._cached: OrderList | None = None

    @property
    def cached(self) -> OrderList | None:
        """Return the last fetched order list, if any."""
        return self._cached

    @property
    def latest(self) -> OrderHandle:
        """Return a handle for the most recent order."""
        if not self._cached or not self._cached.orders:
            msg = "No orders cached; call await orders.fetch() first."
            raise LookupError(msg)
        return OrderHandle(self._api, self._cached.orders[0].order_id)

    def __getitem__(self, order_id: str) -> OrderHandle:
        """Return a handle for an order by id."""
        return OrderHandle(self._api, order_id)

    async def fetch(
        self,
        *,
        page_number: int = 1,
        page_size: int = 20,
    ) -> OrderList:
        """Fetch a page of order history."""
        response = await self._api.send_request(
            endpoint="get_orders",
            params={
                "page_number": page_number,
                "page_size": page_size,
            },
        )
        if not isinstance(response, dict):
            msg = "Orders response was not a JSON object."
            raise TypeError(msg)
        self._cached = OrderList.from_dict(response)
        return self._cached
