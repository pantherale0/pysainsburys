# Sainsbury's GOL App — Reverse Engineering Notebook

> Target: **Sainsbury's Groceries** mobile app for smart-home integration via backend API.

---

## Phase 0 — Application Identification & Acquisition

**Status:** ✅ Complete (2026-08-30)

### Confirmed identity

| Field | Value |
|---|---|
| **App name** | Sainsbury's (Groceries) |
| **Package name** | `com.sainsburys.gol` |
| **Version name** | `3.65.0` |
| **Version code** | `365000000` |
| **Min SDK** | 32 (Android 12L) |
| **Target SDK** | 37 |
| **Download source** | APKPure XAPK bundle |
| **Original path** | `docs/Sainsbury's+Groceries_3.65.0_APKPure.xapk` |
| **Extracted to** | `artifacts/com.sainsburys.gol/3.65.0/` |

### Integrity hashes

| Artifact | SHA-256 |
|---|---|
| XAPK bundle | `13456fd9ebcc86760b3d69ea325c27411ae34285bc395cfee08ef9e5980d335c` |
| Base APK (`com.sainsburys.gol.apk`) | `a946ecd6d2bc41d037298678ef3d9f705ef74cd15c685fef5677d482f3c3989a` |

### Split APKs

| Split | Purpose |
|---|---|
| `com.sainsburys.gol.apk` | Base (DEX, resources) |
| `config.arm64_v8a.apk` | Native libraries (arm64-v8a) |
| `config.en.apk` | English locale |
| `config.mdpi.apk` | mdpi density resources |

### Signing

- APK Signature Block v2/v3 present (no legacy v1 `META-INF/*.RSA` files).
- Certificate fingerprint extraction deferred — no JRE available on host (`apksigner` / `keytool` require Java).

### Permissions (from XAPK manifest.json)

`INTERNET`, `POST_NOTIFICATIONS`, `RECORD_AUDIO`, `CAMERA`, `ACCESS_NETWORK_STATE`, `ACCESS_COARSE_LOCATION`, `ACCESS_FINE_LOCATION`, `WAKE_LOCK`, `EXPAND_STATUS_BAR`, `RECEIVE_BOOT_COMPLETED`, `FOREGROUND_SERVICE`, plus Google/Firebase/Play Services permissions.

**Bluetooth:** None declared. This app is HTTP/API-only; no BLE protocol work expected.

### Native libraries (arm64-v8a)

| Library | Likely purpose |
|---|---|
| `libakamaibmp.so` | Akamai Bot Manager / BMP SDK |
| `libbarhopper_v3.so` | Google ML Kit barcode scanning |
| `libtoolChecker.so` | Root / tamper detection |
| `libimage_processing_util_jni.so` | Camera/image processing |
| `libandroidx.graphics.path.so` | AndroidX graphics |
| `libdatastore_shared_counter.so` | AndroidX DataStore |
| `libsurface_util_jni.so` | Camera surface utils |

### Obfuscation

- **Heavy R8 obfuscation** — most business logic lives under `defpackage/*` with short class names (`bbf`, `r51`, etc.).
- Sainsbury's UI/feature packages retain readable names under `com.sainsburys.gol.*` (438 Java files).
- 4 DEX files (~27 MB total decompiled to ~15,638 classes).
- jadx decompilation completed with 329 errors (typical for R8).

### Application entry point

- **`com.sainsburys.gol.GOLApplication`** — main `Application` class (Hilt/DI, analytics, Firebase, AppsFlyer, mParticle).

### Red flags / protections

| Protection | Evidence |
|---|---|
| **Akamai BMP** | `libakamaibmp.so`, `Akamai BMPSDK/4.0.6` user-agent string, BMP initialization hooks |
| **Certificate pinning** | OkHttp `CertificatePinner` used in network stack |
| **Root detection** | `libtoolChecker.so` native library |
| **Play Integrity** | String references to Play Integrity error codes |
| **Analytics / tracking** | Firebase, AppsFlyer, mParticle, Tealium, New Relic, OneTrust CMP |
| **BFF routing** | Internal OkHttp interceptor rewrites legacy `/gol-services/*` paths to BFF hosts |

### Connected device

| Field | Value |
|---|---|
| **Model** | Pixel 4 XL (`coral`) |
| **Android** | 16 |
| **ADB** | Connected (`99091FFBA000P6`) |
| **App installed** | ✅ v3.65.0 (`com.sainsburys.gol`) |
| **Root shell** | ✅ Root confirmed (`adb shell id` → uid=0) |

### Early API endpoint discovery (strings + static analysis)

| Host | Role |
|---|---|
| `https://api.gs.sainsburys.co.uk` | Primary grocery API (`/shop/api/v1/*`, `/storeinfo/*`, `/nectar/v2/*`) |
| `https://gol-app-bff-commerce.int.prd.jspaas.uk` | BFF for basket/checkout/slot/order |
| `https://gol-app-bff-homepage.int.prd.jspaas.uk` | BFF for homepage data |
| `https://account.sainsburys.co.uk` | Identity / account |
| `https://www.sainsburys.co.uk/smartlists/v1` | Smart lists |
| `https://golapp-config.s3.amazonaws.com` | Remote config |
| `https://integration.sainsburys.citrusad.com` | CitrusAd integration |
| `https://reviews.sainsburys-groceries.co.uk` | Product reviews |
| `https://raider-api.chopchopapp.co.uk` | ChopChop integration |

**Notable request headers (from `bbf` Ktor plugin):**
- `X-SmartShop-Channel: gol` — injected on requests to `api.gs.sainsburys.co.uk`

**BFF path rewriting (from `r51` OkHttp interceptor):**
Legacy paths under `/gol-services/{slot,basket,checkout,order}/` are rewritten to BFF commerce host for:
- `slot/v1/slot/reservation`, `slot/v2/slots`
- `basket/v2/basket`, `basket/v2/basket/item(s)`, `basket/v2/basket/substitutions`
- `checkout/v2/checkout/*`, `checkout/v1/checkout/payment/*`
- `order/v1/order/*`

---

## Phase 1 — Deep Analysis

**Status:** ✅ Complete (2026-08-30) — see [`PHASE1.md`](PHASE1.md)

### Completed

- ✅ App v3.65.0 installed on Pixel 4 XL (`adb install-multiple`)
- ✅ Root confirmed (`adb shell id` → uid=0)
- ✅ jadx decompilation (~15,600 classes)
- ✅ Retrofit API interfaces mapped (basket, product, slot, checkout, order, customer, login, nectar, favourites)
- ✅ Auth flow documented: OAuth OIDC (`gol-android`) → login-access-token → WC tokens
- ✅ API reference written: [`API.md`](API.md)

### Key auth findings

| Setting | Value |
|---|---|
| OAuth client ID | `gol-android` |
| Identity provider | `https://account.sainsburys.co.uk/` |
| Login redirect | `sainsburys://oauth/redirect-login` |
| Commerce token exchange | `POST /groceries-api/gol-services/login/v1/login-access-token` |
| Session headers | `Authorization: Bearer`, `WCAuthToken`, `Cookie`, `refresh_token` |
| Akamai header | `X-acf-sensor-data` (BMP SDK on pinned hosts) |
| SmartShop header | `X-SmartShop-Channel: gol` |

### Barcode / EAN lookup exploration (2026-08-30)

**Goal:** Find an API to resolve a product barcode (EAN) to product metadata.

#### Online grocery API — no barcode lookup

| Surface | Finding |
|---|---|
| `GET …/product/search/suggestions?search=` | Text autocomplete only; EAN → `[]` |
| Product detail endpoints | By UID / SEO URL; responses include `eans[]` but no reverse lookup |
| `GET …/product/v1/product/…` (Retrofit) | No EAN query parameter |

#### Product Finder — text search only

- Base: `https://www.sainsburys.co.uk/product-finder`
- In-app: `ProductFinderFragment`, Ktor client `pw7`
- **Works:** `GET /v2/products?storeId=0474&keyword=milk&page=1&size=20` → aisle, stock, price
- **Does not work:** same URL with `keyword=<13-digit EAN>` → empty `content`
- **Gotcha:** `page` must be **≥ 1** (`page=0` → HTTP 400)
- Batch endpoint `/v2/products/batch?productIds=` takes **product UIDs**, not EANs

#### Practical workaround — Open Food Facts → keyword search (pyukgroceries)

Prior art: [pantherale0/pyukgroceries](https://github.com/pantherale0/pyukgroceries)
(`ukgroceries/pysainsburysgroc/__init__.py`).

Sainsbury's stores EANs on products but **cannot search by barcode**. The workaround:

1. **Resolve barcode → name** via [Open Food Facts](https://world.openfoodfacts.org/)  
   `GET https://world.openfoodfacts.org/api/v2/product/{ean}.json`  
   (pyukgroceries uses the `openfoodfacts` Python package: `find_name_from_barcode()`)

2. **Keyword search** on grocery API (no auth required in practice):  
   `GET /groceries-api/gol-services/product/v1/product?filter[keyword]={brand} {name}&page_number=1&page_size=24`

3. **Filter results** where `ean` ∈ `product.eans[]` (pyukgroceries compares with `barcode.zfill(12)`;
   EAN-13 direct match is safer — see live test below)

```python
# pyukgroceries core logic (abbreviated)
ofdb = find_name_from_barcode(barcode)
results = await search(query=f"{ofdb['brands']} {ofdb['product_name']}")
matches = [p for p in results.products if p.barcode == barcode.zfill(12)]
```

**Live validation (2026-08-30):** EAN `8002270018213`

| Step | Result |
|---|---|
| Open Food Facts | `Nestlé, San Pellegrino…` / `Natural mineral water` |
| Keyword search | 5 products, including uid `6731637` with matching EAN |
| Unauthenticated search | HTTP 200 (same endpoint, `User-Agent: GOLAppAndroid/…` only) |

**Pros:** Works online, no SmartShop/in-store session, no Frida capture needed.  
**Cons:** Depends on OFF coverage; search query quality varies; may return wrong variant
(e.g. 500ml vs 1L) if multiple SKUs match the name — **EAN filter step is essential**.
Multiple results or zero OFF hits → fall back to manual search or SmartShop in-store.

---

#### SmartShop — in-store native barcode path ✅

- Base: `https://api.gs.sainsburys.co.uk` (separate from `groceries-api`)
- Scanner: Google ML Kit via `libbarhopper_v3.so`; callback `onBarcodeRead(String ean)`
- **No dedicated lookup call** — scan flow:
  1. `POST /shop/api/v1/shops` with `{"storeId":"0474"}` → shop session id
  2. `POST /shop/api/v1/shops/{shopId}/basket/items` with `{"storeId","itemId":"<EAN>","quantity":1}`
  3. Response `ShopDTO.embedded.basket` contains resolved product
- EAN quantity updates: **PATCH** (not DELETE) `/…/basket/items/eans/{ean}` with `UpdateQuantityDTO`
- Headers: `X-SmartShop-Channel: gol`, `X-Store-Id`, `Authorization: Bearer` (OAuth, not WCAuthToken)
- Local SQLite `SmartShopEans` maps generic↔actual EAN for loose items (15-day TTL)
- Store entry often requires **QR code confirmation** (`SmartShopLandingViewModel` log message)

**Live probes with web-authenticated session:**

| Endpoint | Status | Meaning |
|---|---|---|
| `GET /shop/api/v1/shops` | 401 | Bearer not accepted for shop list (or no SmartShop entitlement) |
| `POST /shop/api/v1/shops` | 403 | Forbidden — likely needs in-store / geo / QR validation |
| `GET /identity/api/v1/users/me` | 422 | Token valid but SmartShop user profile incomplete |

**Next capture step:** Frida hook on `api.gs.sainsburys.co.uk` while running SmartShop in a
SmartShop-enabled store (scan QR → scan product barcode). Zero SmartShop requests in the
2026-08-30 browse-only capture.

See [`API.md`](API.md) SmartShop and Product Finder sections for endpoint tables.

### Next steps (Phase 2)

1. ~~Implement `pysainsburys` async HTTP client with OAuth + WC session management~~ ✅
2. Decide Akamai strategy (cookie replay vs. browser login automation)
3. Validate write paths (`POST …/basket/item`, slot booking)
4. **SmartShop live capture** for barcode → product resolution
5. Prioritise smart-home workflows with user

### Live API capture (2026-08-30)

Automated capture via `uv run python artifacts/scripts/run_live_capture.py`:

- **183 HTTP requests** logged from Favourites, Trolley, Shop, Home tabs
- **9 unique grocery API paths** confirmed (see [`API.md`](API.md) validation table)
- **Auth headers validated:** `Authorization: Bearer` (JWT ~1229 chars), `WCAuthToken` (`682092082%2C…`), `Cookie` (Akamai `ak_bmsc` + WC session cookies), `User-Agent: GOLAppAndroid/3.65.0`
- **Store context:** `store_identifier=0474`, `personalization_id=1740501147938-35`
- Output: `artifacts/captures/live-capture.log`, `live-capture-summary.json`

Capture recipe: clear app cache → cold start → Frida CLI attach (`RealInterceptorChain.proceed` hook) → automated navigation.

### Live login validation (2026-08-30)

Login completed on device → `MainNavigationActivity`. Confirmed via root storage dump + Frida:

| Item | Validated value |
|---|---|
| Customer ID (plain prefs) | `168292530` in `gol_plain_preferences.xml` |
| Commerce user ID (cookie) | `682092082` in `WC_AUTHENTICATION_*` cookie |
| OAuth/AppAuth state | `files/datastore/auth_state.preferences_pb` (~10 KB encrypted blob) |
| Encrypted token store | `shared_prefs/gol_hybrid.xml` (EncryptedSharedPreferences) |
| Session cookies | `WC_SESSION_ESTABLISHED`, `WC_ACTIVEPOINTER`, `WC_PERSISTENT`, `WC_USERACTIVITY_*`, `WC_AUTHENTICATION_*`, `JSESSIONID`, `AWSALB*` |
| WCAuthToken format | Built from `WCSTokenEntity.wc_trusted_token`; cookie name `WC_AUTHENTICATION_{user_id}` |

Frida note: `Java` bridge is unavailable in Python `script.load()` attach mode on Frida 17; use `uv run frida -U -p <pid> -l script.js` instead.

---

## Phase 2 — Python Library

**Status:** ⏸ Ready to start — Phase 1 complete.

Template scaffold exists at `pysainsburys/` with async HTTP `Client` / `HttpAdapter` (aiohttp). Defaults are placeholders.

---

## Open questions

1. Which smart-home workflows are priority? (e.g. add to basket, check order status, book delivery slot, manage favourites)
2. Akamai bypass strategy for headless Python client — cookie replay vs. BMP vs. browser automation
3. Confirm BFF routing for basket/checkout in production (feature flag)
