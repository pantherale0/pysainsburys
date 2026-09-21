"""Human-readable and JSON output formatters for CLI commands."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any


def emit_json(data: Any) -> None:
    """Print JSON to stdout."""
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def to_jsonable(value: Any) -> Any:
    """Convert a value to JSON, keeping every public dataclass attribute."""
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: to_jsonable(getattr(value, item.name))
            for item in fields(value)
            if not item.name.startswith("_")
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    return value


def emit_raw(records: Sequence[Any]) -> None:
    """Print records as a JSON array with every public attribute."""
    print(json.dumps([to_jsonable(record) for record in records], default=str))


def emit_machine(
    data: Any,
    *,
    as_json: bool,
    raw: bool,
    records: Sequence[Any] | None = None,
) -> bool:
    """Print JSON output when requested and report whether anything was printed."""
    if raw:
        emit_raw([data] if records is None else records)
        return True
    if as_json:
        to_dict = getattr(data, "to_dict", None)
        emit_json(to_dict() if callable(to_dict) else data)
        return True
    return False


def format_price(value: float | None) -> str:
    """Format a price for human-readable output."""
    if value is None:
        return "-"
    return f"£{value:.2f}"


def emit_customer(customer: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print customer profile output."""
    if emit_machine(customer, as_json=as_json, raw=raw):
        return
    print(f"Name:     {customer.display_name}")
    if customer.email:
        print(f"Email:    {customer.email}")
    print(f"User ID:  {customer.user_id}")
    if customer.postcode:
        print(f"Postcode: {customer.postcode}")
    if customer.has_nectar_linked:
        print("Nectar:   linked")


def emit_basket(basket: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print basket output."""
    if emit_machine(basket, as_json=as_json, raw=raw, records=basket.items):
        return
    print(
        f"Basket ({basket.item_count} items) — "
        f"subtotal {format_price(basket.subtotal_price)}, "
        f"total {format_price(basket.total_price)}"
    )
    if basket.savings:
        print(f"Savings:  {format_price(basket.savings)}")
    for item in basket.items:
        name = item.name or item.product_uid
        line_total = format_price(item.subtotal)
        refs = [f"sku {item.product_uid}"]
        if item.item_uid:
            refs.append(f"line {item.item_uid}")
        print(f"  {item.quantity:g} x {name}  {line_total}  ({', '.join(refs)})")


def emit_product_list(
    products: Any,
    *,
    as_json: bool,
    title: str,
    raw: bool = False,
) -> None:
    """Print a paginated product list."""
    if emit_machine(products, as_json=as_json, raw=raw, records=products.products):
        return
    controls = products.controls
    print(f"{title} (page {controls.active_page}/{controls.last_page})")
    for product in products.products:
        price = format_price(
            product.retail_price.price if product.retail_price else None
        )
        favourite = " *" if product.is_favourite else ""
        print(f"  {product.product_uid}  {product.name}{favourite}  {price}")


def emit_nectar_offers(offers: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print Nectar bonus-point offers."""
    if emit_machine(offers, as_json=as_json, raw=raw, records=offers.offers):
        return
    status = offers.account_status or "unknown"
    print(f"Nectar offers ({status})")
    if not offers.offers:
        print("  (no bonus-point offers)")
        return
    for offer in offers.offers:
        points = f"{offer.points} pts" if offer.points else "offer"
        skus = ", ".join(offer.skus) if offer.skus else "-"
        expires = offer.expires or "-"
        print(f"  {offer.title} ({points})")
        if offer.subtitle:
            print(f"    {offer.subtitle}")
        print(f"    skus: {skus}  expires: {expires}")


def emit_your_nectar_prices(prices: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print Your Nectar Price offers."""
    if emit_machine(
        prices,
        as_json=as_json,
        raw=raw,
        records=_your_nectar_price_records(prices),
    ):
        return
    if prices.available_until:
        print(f"Your Nectar Prices (available until {prices.available_until})")
    else:
        print("Your Nectar Prices")
    if prices.opted_in:
        print("Unlocked:")
        for offer in prices.opted_in:
            _emit_ynp_line(offer, unlocked=True)
    if prices.not_opted_in:
        print("Locked:")
        for offer in prices.not_opted_in:
            _emit_ynp_line(offer, unlocked=False)
    if not prices.opted_in and not prices.not_opted_in:
        print("  (no offers)")


def _emit_ynp_line(offer: Any, *, unlocked: bool) -> None:
    name = offer.product.name if offer.product else offer.sku
    price = format_price(
        offer.product.retail_price.price
        if offer.product and offer.product.retail_price
        else None
    )
    state = "unlocked" if unlocked else "locked"
    expires = offer.expiry_date or "-"
    print(f"  {offer.sku}  {name}  {price}  [{state}]  expires {expires}")


def emit_nectar_search(results: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print Nectar search results."""
    if emit_machine(results, as_json=as_json, raw=raw, records=results.hits):
        return
    print(f"Nectar search: {results.query!r} ({len(results.hits)} results)")
    for hit in results.hits:
        if hit.kind == "bonus_offer":
            points = f"{hit.points} pts" if hit.points else "offer"
            print(f"  [bonus] {hit.title} ({points})")
            if hit.subtitle:
                print(f"          {hit.subtitle}")
        else:
            name = hit.product.name if hit.product else hit.sku
            price = format_price(
                hit.product.retail_price.price
                if hit.product and hit.product.retail_price
                else None
            )
            state = "unlocked" if hit.opted_in else "locked"
            print(f"  [ynp] {hit.sku}  {name}  {price}  [{state}]")


def emit_order_list(orders: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print a paginated order list."""
    if emit_machine(orders, as_json=as_json, raw=raw, records=orders.orders):
        return
    controls = orders.controls
    print(f"Orders (page {controls.active_page}/{controls.last_page})")
    for order in orders.orders:
        total = format_price(order.total)
        slot = order.slot_start_time or "-"
        status = order.status or "-"
        print(f"  {order.order_id}  {status}  {slot}  {total}")


def emit_order(order: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print a single order."""
    if emit_machine(order, as_json=as_json, raw=raw):
        return
    print(f"Order:  {order.order_id}")
    if order.status:
        print(f"Status: {order.status}")
    if order.total is not None:
        print(f"Total:  {format_price(order.total)}")
    if order.slot_start_time:
        end = order.slot_end_time or "?"
        print(f"Slot:   {order.slot_start_time} - {end}")


def emit_order_status(status: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print active order status."""
    if emit_machine(status, as_json=as_json, raw=raw):
        return
    if status.order_uid:
        print(f"Order:      {status.order_uid}")
    print(f"Type:       {status.order_type or '-'}")
    print(f"Total:      {format_price(status.total)}")
    print(f"Amend mode: {'yes' if status.is_in_amend_mode else 'no'}")
    if status.slot_start_time:
        end = status.slot_end_time or "?"
        print(f"Slot:       {status.slot_start_time} - {end}")


def emit_slot_week(week: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print a slot week listing."""
    if emit_machine(week, as_json=as_json, raw=raw, records=_slot_records(week)):
        return
    slot_type = week.slot_type.value if week.slot_type else "slot"
    header = f"{slot_type.title()} slots"
    if week.week_start_date:
        header = f"{header} (week of {week.week_start_date})"
    print(header)
    if week.store_identifier:
        print(f"Store:    {week.store_identifier}")
    if week.postcode:
        print(f"Postcode: {week.postcode}")
    if not week.days:
        print("  (no days returned)")
        return
    for day in week.days:
        label = day.day_label or day.date or "Day"
        print(f"  {label}")
        if not day.slots:
            print("    (no slots)")
            continue
        for slot in day.slots:
            status = "available" if slot.is_available else "unavailable"
            price = format_price(slot.price)
            start = slot.start_time or "?"
            end = slot.end_time or "?"
            uid = slot.slot_uid or "-"
            print(f"    {start} - {end}  {price}  [{status}]  {uid}")


def emit_slot_reservation(
    reservation: Any,
    *,
    as_json: bool,
    raw: bool = False,
) -> None:
    """Print the current slot reservation."""
    if emit_machine(reservation, as_json=as_json, raw=raw):
        return
    print(f"Type:   {reservation.reservation_type or '-'}")
    if reservation.postcode:
        print(f"Postcode: {reservation.postcode}")
    if reservation.store_identifier:
        print(f"Store:    {reservation.store_identifier}")
    if reservation.is_expired:
        print("Status:   expired")
    elif reservation.slot:
        start = reservation.slot.start_time or "?"
        end = reservation.slot.end_time or "?"
        print(f"Slot:     {start} - {end}")
        print(f"Price:    {format_price(reservation.slot.price)}")
    else:
        print("Slot:     none reserved")


def emit_location_context(context: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print the location context used for slot operations."""
    if emit_machine(context, as_json=as_json, raw=raw):
        return
    print(f"Type:         {context.slot_type or '-'}")
    print(f"Postcode:     {context.postcode or '-'}")
    print(f"Store:        {context.store_identifier or '-'}")
    print(f"Location UID: {context.location_uid or '-'}")
    print(f"Region:       {context.region or '-'}")
    print(f"Order UID:    {context.order_uid or '-'}")


def emit_product(product: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print a single catalogue product."""
    if emit_machine(product, as_json=as_json, raw=raw):
        return
    print(f"{product.name} ({product.product_uid})")
    if product.eans:
        print(f"EANs:      {', '.join(product.eans)}")
    if product.retail_price:
        print(f"Price:     {format_price(product.retail_price.price)}")
    if product.nectar_price:
        print(f"Nectar:    {format_price(product.nectar_price.retail_price)}")
    for promotion in product.promotions:
        label = promotion.strap_line or promotion.promotion_uid
        if promotion.original_price is None:
            print(f"Offer:     {label}")
        else:
            was = format_price(promotion.original_price)
            print(f"Offer:     {label}  (was {was})")
    print(f"Available: {'yes' if product.is_available else 'no'}")
    if product.is_favourite:
        print("Favourite: yes")
    if product.details:
        _emit_product_details(product.details)
    if product.nutrition:
        emit_nutrition(product.nutrition)


def _emit_product_details(details: Any) -> None:
    """Print description, storage, and other product-text sections."""
    sections = (
        ("Description", details.description),
        ("Storage", details.storage),
        ("Dietary information", details.dietary_information),
        ("Ingredients", details.ingredients),
        ("Manufacturer", details.manufacturer),
        ("Preparation", details.preparation),
        ("Country of origin", details.country_of_origin),
        ("Packaging", details.packaging),
    )
    for label, paragraphs in sections:
        if not paragraphs:
            continue
        print(f"{label}:")
        for paragraph in paragraphs:
            print(f"  {paragraph}")


def emit_nutrition(nutrition: Any) -> None:
    """Print parsed nutrition information."""
    if nutrition.summary:
        print("Nutrition:")
        for item in nutrition.summary:
            values = ", ".join(item.values)
            parts = [f"  {item.name}: {values}"]
            if item.reference_intake_percent:
                parts.append(f"({item.reference_intake_percent} RI)")
            if item.level:
                parts.append(f"[{item.level}]")
            print("".join(parts))
    for table in nutrition.tables:
        title = table.title or "Nutrition table"
        print(f"{title}:")
        if table.columns:
            print(f"  Columns: {' | '.join(table.columns)}")
        for row in table.rows:
            if row.values:
                values = " | ".join(row.values)
                print(f"  {row.name}: {values}")
            else:
                print(f"  {row.name}")
    for note in nutrition.notes:
        print(f"  {note}")


def emit_store_list(
    stores: Any,
    *,
    as_json: bool,
    title: str,
    raw: bool = False,
) -> None:
    """Print a paginated store list."""
    if emit_machine(stores, as_json=as_json, raw=raw, records=stores.stores):
        return
    if stores.page is not None:
        print(f"{title} (page {stores.page.number}/{stores.page.total_pages})")
    elif stores.controls is not None:
        print(
            f"{title} (page {stores.controls.active_page}/{stores.controls.last_page})"
        )
    else:
        print(title)
    for store in stores.stores:
        distance = f"  {store.distance:.1f}" if store.distance is not None else ""
        store_ref = store.store_number or store.store_id or store.location_uid or "?"
        collect = "  [click&collect]" if store.click_and_collect_available else ""
        print(f"  {store_ref}  {store.name}{distance}{collect}")
        print(f"    {store.address1}, {store.city} {store.post_code}")


def emit_store(store: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print a single store."""
    if emit_machine(store, as_json=as_json, raw=raw):
        return
    store_ref = store.store_number or store.store_id or "unknown"
    print(f"{store.name} ({store_ref})")
    print(f"Address:  {store.address1}, {store.city} {store.post_code}")
    if store.opening_hours:
        print(f"Hours:    {store.opening_hours}")
    if store.telephone:
        print(f"Phone:    {store.telephone}")
    if store.distance is not None:
        print(f"Distance: {store.distance:.1f}")
    if store.is_open is not None:
        print(f"Open:     {'yes' if store.is_open else 'no'}")
    print(f"Available: {'yes' if store.is_available else 'no'}")
    print(f"Click & collect: {'yes' if store.click_and_collect_available else 'no'}")


def emit_store_product(product: Any, *, as_json: bool, raw: bool = False) -> None:
    """Print a single in-store product."""
    if emit_machine(product, as_json=as_json, raw=raw):
        return
    aisle = f"  aisle {product.aisle}" if product.aisle else ""
    print(f"{product.name} ({product.product_code})")
    print(f"Price:  {format_price(product.price)}")
    print(f"Stock:  {product.stock}{aisle}")


def _your_nectar_price_records(prices: Any) -> list[dict[str, Any]]:
    """Flatten Your Nectar Price offers and keep opt-in state."""
    records: list[dict[str, Any]] = []
    for offer in prices.opted_in:
        record = to_jsonable(offer)
        record["opted_in"] = True
        records.append(record)
    for offer in prices.not_opted_in:
        record = to_jsonable(offer)
        record["opted_in"] = False
        records.append(record)
    return records


def _slot_records(week: Any) -> list[dict[str, Any]]:
    """Flatten delivery slots and keep the day they belong to."""
    records: list[dict[str, Any]] = []
    for day in week.days:
        for slot in day.slots:
            record = to_jsonable(slot)
            record["date"] = day.date
            record["day_label"] = day.day_label
            records.append(record)
    return records


def emit_store_product_list(
    products: Any,
    *,
    as_json: bool,
    title: str,
    raw: bool = False,
) -> None:
    """Print in-store product search results."""
    if emit_machine(products, as_json=as_json, raw=raw, records=products.products):
        return
    page = products.page
    print(f"{title} (page {page.number}/{page.total_pages})")
    for product in products.products:
        price = format_price(product.price)
        aisle = f"  aisle {product.aisle}" if product.aisle else ""
        print(
            f"  {product.product_code}  {product.name}  {price}  {product.stock}{aisle}"
        )
