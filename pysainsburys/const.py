"""Sainsbury's GOL API constants."""

GOL_APP_USER_AGENT = "GOLAppAndroid/3.65.0"
GOL_BASE_URL = "https://www.sainsburys.co.uk"
GOL_API_PREFIX = "/groceries-api/gol-services"
PRODUCT_FINDER_BASE_URL = "https://www.sainsburys.co.uk/product-finder"

AUTH_BASE_URL = "https://account.sainsburys.co.uk"
AUTH_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)
AUTH_DISCOVERY_URL = f"{AUTH_BASE_URL}/.well-known/openid-configuration"

# Desktop web OAuth (gol-ui). The grocery API is shared with the Android app.
AUTH_CLIENT_ID = "gol"
AUTH_REDIRECT_URI = f"{GOL_BASE_URL}/gol-ui/oauth/redirect"
AUTH_EXTRA_PARAMS = {
    "missionId": "gol",
    "audience": "gol.sainsburys.co.uk",
    "response_mode": "query",
}

AUTH_LOGIN_URL = f"{AUTH_BASE_URL}/gol/login"
AUTH_MFA_URL = f"{AUTH_BASE_URL}/gol/login/mfa"
AUTH_SEND_MFA_URL = f"{AUTH_BASE_URL}/gol/login/send-mfa"
AUTH_LOGIN_INIT_URL = f"{AUTH_BASE_URL}/login-init"

AUTH_SCOPES = ["openid", "offline", "gol-session"]
AUTH_SCOPE = " ".join(AUTH_SCOPES)
AUTH_CODE_CHALLENGE_METHOD = "S256"
AUTH_TOKEN_URL = f"{AUTH_BASE_URL}/oauth2/token"
AUTH_AUTHORIZE_URL = f"{AUTH_BASE_URL}/oauth2/auth"

BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": AUTH_BROWSER_USER_AGENT,
    "Accept": (
        "application/json,text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}

GOL_ENDPOINTS: dict[str, dict[str, str]] = {
    "login_access_token": {
        "method": "POST",
        "endpoint": f"{GOL_API_PREFIX}/login/v1/login-access-token",
    },
    "logout": {
        "method": "DELETE",
        "endpoint": f"{GOL_API_PREFIX}/login/logout",
    },
    "customer_profile": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/customer/v1/customer/profile",
    },
    "customer_identity": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/customer/v1/customer/identity-profile",
    },
    "customer_address": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/customer/v1/customer/address",
    },
    "get_basket": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/basket/v2/basket",
    },
    "update_basket": {
        "method": "PUT",
        "endpoint": f"{GOL_API_PREFIX}/basket/v2/basket",
    },
    "clear_basket": {
        "method": "DELETE",
        "endpoint": f"{GOL_API_PREFIX}/basket/v2/basket",
    },
    "add_basket_item": {
        "method": "POST",
        "endpoint": f"{GOL_API_PREFIX}/basket/v2/basket/item",
    },
    "remove_basket_items": {
        "method": "DELETE",
        "endpoint": f"{GOL_API_PREFIX}/basket/v2/basket/items",
    },
    "get_favourites": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/product/v1/favourites",
    },
    "add_favourite": {
        "method": "POST",
        "endpoint": f"{GOL_API_PREFIX}/product/v1/product/favourites",
    },
    "remove_favourite": {
        "method": "DELETE",
        "endpoint": f"{GOL_API_PREFIX}/product/v1/favourites/{{PRODUCT_SKU}}",
    },
    "get_orders": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/order/v1/order",
    },
    "get_order": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/order/v1/order/{{ORDER_ID}}",
    },
    "get_order_status": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/order/v1/order/status",
    },
    "get_product": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/product/v1/product/{{PRODUCT_UID}}",
    },
    "search_products": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/product/v1/product",
    },
    "click_and_collect": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/location/v1/location/click-and-collect",
    },
    "get_nectar_offers": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/nectar/v1/nectar/offers",
    },
    "get_ynp_opt_ins": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/nectar/v1/nectar/ynp-opt-ins",
    },
    "unlock_ynp_opt_ins": {
        "method": "PUT",
        "endpoint": f"{GOL_API_PREFIX}/nectar/v1/nectar/ynp-opt-ins",
    },
    "list_slots": {
        "method": "POST",
        "endpoint": f"{GOL_API_PREFIX}/slot/v2/slots",
        "headers": {"X-Http-Method-Override": "GET"},
    },
    "get_slot_reservation": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/slot/v1/slot/reservation",
    },
    "get_slot_location_context": {
        "method": "GET",
        "endpoint": f"{GOL_API_PREFIX}/slot/v1/slot/reservation/location-context",
    },
}
