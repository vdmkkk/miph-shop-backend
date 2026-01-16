# FastAPI Educational Shop Backend Spec (Final)
Version: **1.0**  
Currency: **Russian rubles (RUB)** using **float values in API** (DB stores `NUMERIC(12,2)`)

This document is the **implementation contract** for Cursor. It defines:
- **DB schemas** (PostgreSQL)
- **Public API** (`/api/v1`) for students/frontends
- **Admin API** (`/admin/v1`) for managing catalog + orders
- **Auth flow**: email **magic link** + optional profile completion
- **Cart sync**: merge guest (localStorage) cart into backend after login/signup
- **Docker + docker-compose + Nginx routing**

---

## 0) Tech & repo requirements

### Must use
- **FastAPI** (Python 3.12 recommended)
- **PostgreSQL** only (no SQLite)
- **SQLAlchemy 2.0** (async) + `asyncpg`
- **Alembic** for migrations
- **Pydantic v2**
- Dockerized services:
  - `public_api` (FastAPI)
  - `admin_api` (FastAPI)
  - `postgres`
  - `nginx` as a reverse proxy/router

### Repo layout (recommended)
```
repo/
  apps/
    public_api/
      main.py
      routers/
    admin_api/
      main.py
      routers/
  core/
    config.py
    db.py
    auth.py
    models/
    schemas/
    services/
  alembic/
  alembic.ini
  docker/
    public_api.Dockerfile
    admin_api.Dockerfile
    nginx/
      nginx.conf
  docker-compose.yml
  .env.example
  README.md
```

### Nginx routing requirements
Single host, routes by path prefix:
- `http://localhost/api/...` → **public_api**
- `http://localhost/admin/...` → **admin_api**

Nginx must forward:
- `X-Forwarded-For`, `X-Forwarded-Proto`, `Host`
- Support large JSON bodies (set `client_max_body_size`)

---

## 1) API conventions

### 1.1 Base paths
- Public API base: **`/api/v1`**
- Admin API base: **`/admin/v1`**

### 1.2 JSON naming
- **camelCase** for request and response JSON
- UUIDs are strings.

### 1.3 Dates/times
- ISO 8601 strings in UTC, e.g. `"2026-01-15T12:34:56Z"`

### 1.4 Money (RUB)
- All monetary values are **RUB**.
- All monetary fields in API are **float** (example: `1299.99`).
- In Postgres, store money as **`NUMERIC(12,2)`**.
  - In Python, use `Decimal` internally; serialize to float for responses.

### 1.5 Pagination
Use page pagination everywhere lists exist:
- Query params: `page` (default 1), `perPage` (default 20, max 100)
- Response includes:
```json
{
  "data": [],
  "page": 1,
  "perPage": 20,
  "total": 123,
  "totalPages": 7
}
```

### 1.6 Error format
All errors:
```json
{
  "error": {
    "code": "SOME_CODE",
    "message": "Human readable message",
    "details": { "any": "json" }
  }
}
```

Suggested status codes:
- `400` validation/business errors
- `401` unauthenticated
- `403` forbidden (e.g., disabled user, admin auth missing)
- `404` not found
- `409` conflict (e.g., profile required during signup)
- `422` request validation errors (FastAPI default is OK but wrap if desired)

---

## 2) Authentication & sessions

### 2.1 Public auth method
**Email magic link**:
1) Frontend sends email to request link  
2) Backend generates token, stores **hashed** token, and sends email with link  
3) Frontend opens link, extracts token, calls consume endpoint  
4) If user exists → login; else → require profile completion and then create user

**No password**.

### 2.2 Tokens
- Access token: JWT (short-lived, e.g. 15 minutes)
- Refresh token: opaque string stored hashed in DB (longer-lived, e.g. 30 days)
- Auth header: `Authorization: Bearer <accessToken>`

### 2.3 Security notes
- Do **not** reveal whether email exists during magic link request.
- Magic link token stored **hashed**.
- Rate-limit magic link requests (simple IP+email throttling).

---

## 3) Database schema (PostgreSQL)

All tables use:
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Enable extension:
```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### 3.1 Catalog

#### `categories`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| slug | text | unique, lowercase |
| title | text | |
| parent_id | uuid | nullable FK -> categories.id |
| is_active | boolean | default true |
| sort_rank | int | default 0 |

Indexes:
- unique(slug)
- index(parent_id)
- index(is_active)

#### `tags`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| slug | text | unique |
| title | text | |
| is_active | boolean | default true |

#### `items`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| slug | text | unique |
| title | text | |
| description | text | |
| brand | text | nullable |
| is_active | boolean | default true |
| sort_rank | int | default 0 |
| min_price_rub | numeric(12,2) | denormalized for list sorting/filtering |
| max_price_rub | numeric(12,2) | denormalized |
| has_stock | boolean | denormalized: any active variant stock>0 |

Notes:
- `min_price_rub`, `max_price_rub`, `has_stock` must be recalculated whenever variants change.

#### `item_categories`
Many-to-many.
| column | type | notes |
|---|---|---|
| item_id | uuid | FK -> items.id |
| category_id | uuid | FK -> categories.id |
Primary key: (item_id, category_id)

#### `item_tags`
Many-to-many.
| column | type | notes |
|---|---|---|
| item_id | uuid | FK -> items.id |
| tag_id | uuid | FK -> tags.id |
Primary key: (item_id, tag_id)

#### `item_images`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| item_id | uuid | FK -> items.id |
| url | text | |
| alt | text | nullable |
| sort_order | int | default 0 |
| is_main | boolean | default false |

#### `item_variants`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| item_id | uuid | FK -> items.id |
| sku | text | unique |
| title | text | e.g. "Red / M" |
| attributes | jsonb | e.g. {"color":"red","size":"M"} |
| price_rub | numeric(12,2) | required |
| compare_at_price_rub | numeric(12,2) | nullable |
| stock | int | default 0 |
| is_active | boolean | default true |

Indexes:
- index(item_id)
- index(is_active)
- gin(attributes)

---

### 3.2 Users & auth

#### `users`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| email | citext | unique |
| name | text | |
| phone | text | nullable |
| is_active | boolean | default true |
| last_login_at | timestamptz | nullable |

Notes:
- `is_active=false` blocks login and any authenticated actions.

Enable extension:
```sql
CREATE EXTENSION IF NOT EXISTS citext;
```

#### `auth_magic_tokens`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| email | citext | |
| token_hash | text | hashed token |
| expires_at | timestamptz | |
| consumed_at | timestamptz | nullable |
| flow_context | jsonb | nullable; used to resume checkout etc |
| cart_snapshot | jsonb | nullable; optional snapshot sent by frontend |

Indexes:
- index(email)
- index(expires_at)
- index(consumed_at)

#### `auth_refresh_tokens`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK -> users.id |
| token_hash | text | hashed |
| expires_at | timestamptz | |
| revoked_at | timestamptz | nullable |
| user_agent | text | nullable |
| ip | text | nullable |

---

### 3.3 Likes

#### `likes`
| column | type | notes |
|---|---|---|
| user_id | uuid | FK -> users.id |
| item_id | uuid | FK -> items.id |
| created_at | timestamptz | default now() |

Primary key: (user_id, item_id)

---

### 3.4 Server-side cart (for logged-in users)

#### `carts`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | unique FK -> users.id |
| updated_at | timestamptz | |

#### `cart_items`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| cart_id | uuid | FK -> carts.id |
| variant_id | uuid | FK -> item_variants.id |
| qty | int | min 1 |

Constraints:
- unique(cart_id, variant_id)
- qty > 0

---

### 3.5 Orders

#### `orders`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK -> users.id |
| status | text | enum-like |
| currency | text | always "RUB" |
| subtotal_rub | numeric(12,2) | |
| delivery_rub | numeric(12,2) | default 0 |
| total_rub | numeric(12,2) | |
| contact_name | text | |
| contact_phone | text | |
| email | citext | |
| delivery_method | text | e.g. "courier" |
| delivery_address | jsonb | |
| comment | text | nullable |
| placed_at | timestamptz | default now() |
| paid_at | timestamptz | nullable |
| canceled_at | timestamptz | nullable |

Order status values (string constants):
- `placed`
- `paid`
- `packed`
- `shipped`
- `delivered`
- `canceled`
- `refunded`

#### `order_items`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| order_id | uuid | FK -> orders.id |
| item_id | uuid | FK -> items.id |
| variant_id | uuid | FK -> item_variants.id |
| title | text | snapshot of item title |
| variant_title | text | snapshot |
| sku | text | snapshot |
| unit_price_rub | numeric(12,2) | snapshot |
| qty | int | |
| line_total_rub | numeric(12,2) | unit_price*qty |

#### `order_events`
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| order_id | uuid | FK -> orders.id |
| from_status | text | nullable |
| to_status | text | |
| note | text | nullable |
| created_by | text | "system" or admin identifier |
| created_at | timestamptz | default now() |

---

## 4) Shared API schemas (JSON)

Below are the JSON shapes Cursor must implement. All money fields are floats in RUB.

### 4.1 Category
```json
{
  "id": "uuid",
  "slug": "electronics",
  "title": "Electronics",
  "parentId": null,
  "isActive": true,
  "sortRank": 0
}
```

### 4.2 Tag
```json
{
  "id": "uuid",
  "slug": "new",
  "title": "New",
  "isActive": true
}
```

### 4.3 Variant
```json
{
  "id": "uuid",
  "sku": "TSHIRT-RED-M",
  "title": "Red / M",
  "attributes": { "color": "red", "size": "M" },
  "priceRub": 1299.99,
  "compareAtPriceRub": 1499.99,
  "stock": 12,
  "isActive": true
}
```

### 4.4 Item (list)
```json
{
  "id": "uuid",
  "slug": "tshirt-basic",
  "title": "Basic T-Shirt",
  "shortDescription": "Optional derived field",
  "isActive": true,
  "mainImageUrl": "https://...",
  "minPriceRub": 999.00,
  "maxPriceRub": 1299.99,
  "hasStock": true,
  "categorySlugs": ["clothes"],
  "tagSlugs": ["new", "sale"]
}
```

### 4.5 Item (detail)
```json
{
  "id": "uuid",
  "slug": "tshirt-basic",
  "title": "Basic T-Shirt",
  "description": "Long description...",
  "brand": "Acme",
  "isActive": true,
  "categories": [ { "id": "...", "slug": "...", "title": "..." } ],
  "tags": [ { "id": "...", "slug": "...", "title": "..." } ],
  "images": [
    { "id": "uuid", "url": "https://...", "alt": null, "sortOrder": 0, "isMain": true }
  ],
  "variants": [ /* Variant[] */ ]
}
```

### 4.6 User
```json
{
  "id": "uuid",
  "email": "student@example.com",
  "name": "Ivan",
  "phone": "+79991234567",
  "isActive": true,
  "createdAt": "2026-01-15T12:00:00Z"
}
```

### 4.7 Cart
```json
{
  "id": "uuid",
  "items": [
    {
      "variantId": "uuid",
      "itemId": "uuid",
      "slug": "tshirt-basic",
      "title": "Basic T-Shirt",
      "variantTitle": "Red / M",
      "sku": "TSHIRT-RED-M",
      "qty": 2,
      "unitPriceRub": 1299.99,
      "lineTotalRub": 2599.98,
      "available": true,
      "stock": 12,
      "imageUrl": "https://..."
    }
  ],
  "totals": {
    "itemsCount": 2,
    "subtotalRub": 2599.98
  },
  "updatedAt": "2026-01-15T12:34:56Z"
}
```

### 4.8 Order
```json
{
  "id": "uuid",
  "status": "placed",
  "subtotalRub": 2599.98,
  "deliveryRub": 0.0,
  "totalRub": 2599.98,
  "placedAt": "2026-01-15T12:40:00Z",
  "items": [
    {
      "id": "uuid",
      "itemId": "uuid",
      "variantId": "uuid",
      "title": "Basic T-Shirt",
      "variantTitle": "Red / M",
      "sku": "TSHIRT-RED-M",
      "unitPriceRub": 1299.99,
      "qty": 2,
      "lineTotalRub": 2599.98
    }
  ],
  "delivery": {
    "method": "courier",
    "address": { "city": "Moscow", "street": "Tverskaya", "house": "1", "apartment": "10" }
  },
  "contact": {
    "name": "Ivan",
    "phone": "+79991234567",
    "email": "student@example.com"
  },
  "events": [
    { "id": "uuid", "fromStatus": null, "toStatus": "placed", "note": null, "createdBy": "system", "createdAt": "..." }
  ]
}
```

---

## 5) Public API (`/api/v1`)

### 5.1 Health
#### `GET /api/v1/health`
Response:
```json
{ "status": "ok" }
```

---

### 5.2 Auth (magic link)

#### `POST /api/v1/auth/magic/request`
Purpose: request a login/signup link by email.

Request:
```json
{
  "email": "student@example.com",
  "flowContext": { "flow": "checkout", "returnTo": "/checkout?step=delivery" },
  "cartSnapshot": {
    "items": [
      { "variantId": "uuid", "qty": 2 }
    ]
  }
}
```

Response (always 200, do not enumerate emails):
```json
{ "ok": true }
```

Email content must include a frontend URL like:
`FRONTEND_BASE_URL/auth/finish?token=<token>`

> Implementation note: sending email can be via SMTP or dev-mode console logging.
> In dev, print the link into logs so students can copy it.

---

#### `POST /api/v1/auth/magic/consume`
Purpose: consume token, login existing users, or complete signup for new users.

Request (existing user):
```json
{ "token": "raw-token-from-url" }
```

Request (new user completing profile):
```json
{
  "token": "raw-token-from-url",
  "profile": { "name": "Ivan", "phone": "+79991234567" }
}
```

Optional cart merge in the same call (nice UX):
```json
{
  "token": "raw-token",
  "profile": { "name": "Ivan", "phone": "+7999..." },
  "mergeCart": {
    "mode": "add",
    "items": [ { "variantId": "uuid", "qty": 2 } ]
  }
}
```

Success response:
```json
{
  "accessToken": "jwt",
  "refreshToken": "opaque",
  "user": { /* User */ },
  "flowContext": { "flow": "checkout", "returnTo": "/checkout?step=delivery" },
  "cart": { /* Cart, optional if mergeCart used */ }
}
```

If profile is required (token valid but user does not exist and profile missing):
- Status: `409`
```json
{
  "error": {
    "code": "PROFILE_REQUIRED",
    "message": "Please complete profile to finish signup",
    "details": { "requiredFields": ["name", "phone"] }
  },
  "flowContext": { "flow": "checkout", "returnTo": "/checkout?step=delivery" }
}
```

---

#### `POST /api/v1/auth/refresh`
Request:
```json
{ "refreshToken": "opaque" }
```
Response:
```json
{ "accessToken": "jwt", "refreshToken": "opaque" }
```

#### `POST /api/v1/auth/logout`
Request:
```json
{ "refreshToken": "opaque" }
```
Response:
```json
{ "ok": true }
```

---

### 5.3 Me (profile)
#### `GET /api/v1/me`
Response:
```json
{ "user": { /* User */ } }
```

#### `PATCH /api/v1/me`
Request:
```json
{ "name": "New Name", "phone": "+7999..." }
```
Response:
```json
{ "user": { /* User */ } }
```

---

### 5.4 Catalog

#### `GET /api/v1/categories`
Returns active categories (isActive=true) by default.

Response:
```json
{ "data": [ /* Category[] */ ] }
```

#### `GET /api/v1/tags`
Returns active tags.

Response:
```json
{ "data": [ /* Tag[] */ ] }
```

#### `GET /api/v1/items`
Query params:
- `q` (string) search by title/description
- `category` (slug)
- `tags` (comma-separated slugs) e.g. `tags=new,sale`
- `priceMinRub` (float)
- `priceMaxRub` (float)
- `inStock` (bool) only items with `hasStock=true`
- `sort` one of:
  - `newest` (default)
  - `priceAsc`
  - `priceDesc`
  - `titleAsc`
- `page`, `perPage`

Response:
```json
{
  "data": [ /* Item(list)[] */ ],
  "page": 1,
  "perPage": 20,
  "total": 123,
  "totalPages": 7
}
```

#### `GET /api/v1/items/{slug}`
Response:
```json
{ "item": { /* Item(detail) */ } }
```

---

### 5.5 Likes (logged-in only)

#### `GET /api/v1/me/likes`
Response:
```json
{
  "data": [ /* Item(list)[] */ ],
  "page": 1,
  "perPage": 20,
  "total": 10,
  "totalPages": 1
}
```

#### `POST /api/v1/me/likes/{itemId}`
Response:
```json
{ "ok": true }
```

#### `DELETE /api/v1/me/likes/{itemId}`
Response:
```json
{ "ok": true }
```

---

### 5.6 Cart (logged-in server cart)

#### `GET /api/v1/me/cart`
Response:
```json
{ "cart": { /* Cart */ } }
```

#### `POST /api/v1/me/cart/merge`
Purpose: merge guest cart (localStorage) into server cart after login/signup.

Request:
```json
{
  "mode": "add",
  "items": [
    { "variantId": "uuid", "qty": 2 },
    { "variantId": "uuid2", "qty": 1 }
  ]
}
```

Rules:
- For duplicates (same variantId):
  - `add`: serverQty += guestQty
  - `replace`: serverQty = guestQty (and remove server-only items)
  - `max`: serverQty = max(serverQty, guestQty)
- Clamp qty to stock if needed and report warnings.

Response:
```json
{
  "cart": { /* Cart */ },
  "mergeWarnings": [
    { "variantId": "uuid-x", "reason": "out_of_stock" },
    { "variantId": "uuid-y", "reason": "variant_not_found" }
  ]
}
```

#### `PUT /api/v1/me/cart/items/{variantId}`
Request:
```json
{ "qty": 3 }
```
Response:
```json
{ "cart": { /* Cart */ } }
```

#### `DELETE /api/v1/me/cart/items/{variantId}`
Response:
```json
{ "cart": { /* Cart */ } }
```

#### `POST /api/v1/me/cart/clear`
Response:
```json
{ "cart": { /* Cart */ } }
```

---

### 5.7 Orders (checkout)

#### `POST /api/v1/me/orders`
Creates an order **from the current server cart** and then clears the cart.

Request:
```json
{
  "delivery": {
    "method": "courier",
    "address": {
      "city": "Moscow",
      "street": "Tverskaya",
      "house": "1",
      "apartment": "10",
      "postalCode": "125009"
    }
  },
  "contact": {
    "name": "Ivan",
    "phone": "+79991234567",
    "email": "student@example.com"
  },
  "comment": "Leave at the door"
}
```

Response:
```json
{ "order": { /* Order */ } }
```

Errors:
- `400 CART_EMPTY`
- `400 OUT_OF_STOCK` with details about offending variants

#### `GET /api/v1/me/orders`
Response is paginated:
```json
{
  "data": [ /* Order (without events maybe) */ ],
  "page": 1,
  "perPage": 20,
  "total": 3,
  "totalPages": 1
}
```

#### `GET /api/v1/me/orders/{orderId}`
Response:
```json
{ "order": { /* Order including events */ } }
```

#### `POST /api/v1/me/orders/{orderId}/cancel`
Allowed when status in: `placed` (optionally `paid` if you want).
Response:
```json
{ "order": { /* Order */ } }
```

#### `POST /api/v1/me/orders/{orderId}/simulate-payment`
**Dev-only** endpoint (enabled via `ENABLE_DEV_ENDPOINTS=true`).
Moves `placed -> paid`.

Response:
```json
{ "order": { /* Order */ } }
```

---

## 6) Admin API (`/admin/v1`)

### 6.1 Admin authentication (simple)
All admin endpoints require header:

`X-Admin-Api-Key: <ADMIN_API_KEY>`

If missing/invalid:
- `403` with `ADMIN_AUTH_REQUIRED`

---

### 6.2 Health
#### `GET /admin/v1/health`
```json
{ "status": "ok" }
```

---

### 6.3 Categories (CRUD)

#### `GET /admin/v1/categories`
Returns all categories (including inactive), paginated.

#### `POST /admin/v1/categories`
Request:
```json
{ "slug": "clothes", "title": "Clothes", "parentId": null, "isActive": true, "sortRank": 0 }
```

#### `PATCH /admin/v1/categories/{id}`
#### `DELETE /admin/v1/categories/{id}`
Soft delete by setting `isActive=false` (do not hard delete).

---

### 6.4 Tags (CRUD)
Same patterns as categories.

---

### 6.5 Items (CRUD)

#### `GET /admin/v1/items`
Paginated, supports `q`, `isActive`, `category`, `tag`.

#### `POST /admin/v1/items`
Request:
```json
{
  "slug": "tshirt-basic",
  "title": "Basic T-Shirt",
  "description": "Long...",
  "brand": "Acme",
  "isActive": true,
  "sortRank": 0,
  "categoryIds": ["uuid"],
  "tagIds": ["uuid"]
}
```

#### `PATCH /admin/v1/items/{id}`
Same shape, all fields optional.

#### `DELETE /admin/v1/items/{id}`
Soft delete by setting `isActive=false`.

---

### 6.6 Item images

#### `POST /admin/v1/items/{itemId}/images`
Request:
```json
{ "url": "https://...", "alt": null, "sortOrder": 0, "isMain": true }
```

#### `PATCH /admin/v1/images/{imageId}`
#### `DELETE /admin/v1/images/{imageId}`

Rules:
- If `isMain=true` is set on one image, clear it on others for that item.

---

### 6.7 Variants

#### `POST /admin/v1/items/{itemId}/variants`
Request:
```json
{
  "sku": "TSHIRT-RED-M",
  "title": "Red / M",
  "attributes": { "color": "red", "size": "M" },
  "priceRub": 1299.99,
  "compareAtPriceRub": 1499.99,
  "stock": 12,
  "isActive": true
}
```

#### `PATCH /admin/v1/variants/{variantId}`
Same fields optional.

#### `DELETE /admin/v1/variants/{variantId}`
Soft delete (`isActive=false`).

Variant side effects (required):
- After create/update/delete, recalc:
  - item.min_price_rub
  - item.max_price_rub
  - item.has_stock

---

### 6.8 Orders management

#### `GET /admin/v1/orders`
Query params:
- `status`
- `email`
- `page`, `perPage`

Response:
Paginated list with basic info.

#### `GET /admin/v1/orders/{orderId}`
Returns full order with items and events.

#### `POST /admin/v1/orders/{orderId}/status`
Request:
```json
{ "toStatus": "shipped", "note": "Tracking #123" }
```

Rules:
- Append an `order_event`
- Update `orders.status`
- Set timestamps when appropriate:
  - `paid_at` on `paid`
  - `canceled_at` on `canceled`

---

### 6.9 Users management (minimal)

#### `GET /admin/v1/users`
Query params: `q` (email/name), `isActive`, pagination

#### `PATCH /admin/v1/users/{userId}`
Request:
```json
{ "isActive": false }
```

---

## 7) Cart sync UX (frontend contract)

### 7.1 Guest cart storage
Frontend stores guest cart in `localStorage`:
```json
{
  "items": [ { "variantId": "uuid", "qty": 2 } ],
  "updatedAt": 1737000000
}
```

### 7.2 Sync trigger
After successful magic-link consume (login/signup), frontend:
1) If guest cart has items → call `POST /api/v1/me/cart/merge`
2) Replace in-memory cart state with backend response
3) Clear `localStorage` cart

### 7.3 Resume checkout
Frontend sends `flowContext` on magic request. After consume, backend returns the same `flowContext` so frontend can route to:
- `/checkout?...` etc.

---

## 8) Docker & deployment contract

Cursor must create:

### 8.1 `docker/public_api.Dockerfile`
- Install deps
- Copy code
- Run `uvicorn apps.public_api.main:app --host 0.0.0.0 --port 8000`

### 8.2 `docker/admin_api.Dockerfile`
- Same, but run admin app on port 8001

### 8.3 `docker/nginx/nginx.conf`
Must route:
- `/api/` → `public_api:8000`
- `/admin/` → `admin_api:8001`

Example (Cursor can adapt):
```nginx
events {}

http {
  client_max_body_size 20m;

  upstream public_api_upstream { server public_api:8000; }
  upstream admin_api_upstream  { server admin_api:8001; }

  server {
    listen 80;

    location /api/ {
      proxy_pass http://public_api_upstream;
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
      proxy_pass http://admin_api_upstream;
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
    }
  }
}
```

### 8.4 `docker-compose.yml`
Services:
- `postgres` (with volume)
- `public_api` depends_on postgres
- `admin_api` depends_on postgres
- `nginx` depends_on both APIs, exposes port 80

Use env vars from `.env`.

### 8.5 `.env.example`
Include:
- `DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/shop`
- `JWT_SECRET=...`
- `ACCESS_TOKEN_TTL_SECONDS=900`
- `REFRESH_TOKEN_TTL_DAYS=30`
- `FRONTEND_BASE_URL=http://localhost`
- `MAIL_MODE=console` (or smtp)
- `SMTP_HOST=...` etc
- `ADMIN_API_KEY=change-me`
- `ENABLE_DEV_ENDPOINTS=true`

---

## 9) Educational “nice to have” (optional, but recommended)
These are optional if time permits; implement only if quick:
- `GET /api/v1/items/facets` → min/max price, tag counts, category counts for UI filters
- “Featured” items: `items.is_featured boolean`
- Simple “recommendations”: `GET /api/v1/items/{slug}/related` (same category/tag)
- Webhook simulation endpoint in admin (teaches integrations)

---

## 10) Acceptance checklist
Cursor implementation is complete when:
- `docker compose up` brings up Postgres + both APIs + Nginx
- Public API accessible via `http://localhost/api/v1/...`
- Admin API accessible via `http://localhost/admin/v1/...` (with API key header)
- Magic-link auth works (console mail mode acceptable)
- Logged-in user can:
  - merge cart
  - like items
  - create an order
  - list order history
- Admin can:
  - create categories/tags/items/variants
  - change order status and see event history

---
