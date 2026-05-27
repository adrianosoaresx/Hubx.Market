# Public Catalog Partner Onboarding

Version: `2026-05-26`

## Scope

This guide documents the first partner-facing public catalog API surface for one tenant store.

- tenant boundary: each request is resolved by tenant subdomain.
- allowed scope: `read:catalog`.
- allowed resources:
  - `GET /api/v1/catalog/products/`
  - `GET /api/v1/catalog/products/<slug>/`
- read-only only: no cart, checkout, order, customer, payment, inventory mutation or admin operation.
- no billing, quota or commercial plan contract is defined by this guide.

## Authentication

Use the partner API key issued for the tenant and scope `read:catalog`.

```http
Authorization: Bearer <partner_api_key>
```

Rules:

- never share a real key in tickets, docs, screenshots or logs.
- rotate the key if it appears outside the approved secure channel.
- a key without `read:catalog` must be treated as unauthorized for catalog reads.

## Endpoint examples

### List catalog products

```http
GET /api/v1/catalog/products/?page=1&page_size=20
Authorization: Bearer <partner_api_key>
```

Success response shape:

```json
{
  "result": "public-catalog-products-listed",
  "count": 2,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": 10,
      "slug": "basic-shirt",
      "name": "Basic Shirt",
      "brand": "Hubx",
      "category": "Apparel",
      "is_featured": true,
      "status": "active",
      "price": "99.90",
      "compare_price": "",
      "availability": "in_stock",
      "primary_image": {
        "url": "https://cdn.example.test/basic-shirt.jpg",
        "alt": "Basic Shirt"
      },
      "updated_at": "2026-05-26T10:00:00+00:00"
    }
  ]
}
```

### Retrieve product detail

```http
GET /api/v1/catalog/products/basic-shirt/
Authorization: Bearer <partner_api_key>
```

Success response shape:

```json
{
  "result": "public-catalog-product-retrieved",
  "product": {
    "id": 10,
    "slug": "basic-shirt",
    "name": "Basic Shirt",
    "description": "Public product description.",
    "price": "99.90",
    "availability": "in_stock",
    "images": [
      {
        "url": "https://cdn.example.test/basic-shirt.jpg",
        "alt": "Basic Shirt"
      }
    ],
    "variants": [
      {
        "sku": "BASIC-SHIRT-P",
        "price": "99.90",
        "compare_price": "",
        "availability": "in_stock",
        "is_default": true
      }
    ]
  }
}
```

## Error contract

Expected errors:

- `401`: missing, malformed, expired or revoked API key.
- `403`: valid API key without `read:catalog`.
- `404`: endpoint disabled, tenant not found or product slug not found.
- `429`: request blocked by tenant/key rate limit.

Partners should treat unknown `5xx` responses as retryable with backoff.

## Rate limit

Rate limit is enforced per API key and endpoint label.

- list endpoint label: `catalog.products.list`.
- detail endpoint label: `catalog.products.detail`.
- limits are environment-configured and may differ between staging and production.

## Observability

Public endpoint metrics are emitted with low-cardinality labels.

- metric family: `hubx_api_key_public_request_total`.
- expected labels include endpoint and result.
- product slug, SKU, customer data, tenant name or API key material must not be used as metric labels.

## Activation checklist

Before granting partner access:

- confirm tenant subdomain and target environment.
- create or select an API key scoped to `read:catalog`.
- confirm list and detail endpoint feature flags are enabled.
- run a smoke request for list and one known active product slug.
- confirm `401`, `403`, `404` and `429` handling in partner client.
- confirm dashboard/alerts are available for public endpoint traffic.
- share only placeholder-based examples in tickets and documentation.

## Explicit non-goals

- no new public endpoint.
- no admin or `/ops/` endpoint exposure.
- no billing, quota, pricing plan or commercial enforcement.
- no customer, order, payment or raw inventory export.
- no secret, key hash, raw token or real credential in examples.

## Delivery package

Delivery channel:

- approved channel: secure partner onboarding workspace or support ticket with restricted access.
- do not paste credentials into the documentation package.
- share only this versioned guide and tenant-specific activation status.

Documentation owner:

- owner: platform/API operations.
- reviewer: tenant operations owner.
- support contact: platform support queue.

Support handoff:

- support must know the tenant subdomain, target environment and enabled feature flags.
- support may validate status codes and endpoint availability.
- support must not request or store a partner API key in plain text.

Smoke evidence template:

- tenant subdomain confirmed: yes/no.
- list endpoint smoke status: success/failure.
- detail endpoint smoke status: success/failure.
- observed status codes: `200`, `401`, `403`, `404` or `429`.
- dashboard/alert visibility confirmed: yes/no.
- credential exposure check confirmed: yes/no.

Change control:

- update the version date when endpoint shape, error contract or activation checklist changes.
- record any contract change in `DECISIONS.md`.
- keep backwards compatibility notes with the guide version.

No commercial terms:

- this package does not define pricing, quotas, billing, SLA or contractual support terms.

No runtime change:

- this package does not require code deploy, middleware change, authentication change or new endpoint activation.

## Publication evidence

The publication evidence must be recorded separately from credentials and runtime activation.

Required sanitized fields:

- published version.
- approved delivery channel.
- target audience.
- tenant reference.
- publication timestamp.
- evidence reference.

Operational confirmations:

- publication confirmed.
- support notified.
- activation status recorded.
- smoke evidence template attached.
- redaction confirmed.
- no credential shared.
- no runtime activation performed.

Evidence must not include API keys, secrets, hashes, raw tokens, request headers or credential screenshots.

## Activation smoke contract

The first real partner activation smoke must be contracted before execution.

Required sanitized references:

- partner reference.
- tenant reference.
- target environment.
- product slug reference.
- smoke evidence reference.

Scope:

- `GET /api/v1/catalog/products/`.
- `GET /api/v1/catalog/products/<slug>/`.
- scope `read:catalog`.
- tenant subdomain.
- observability check.
- rollback plan.

The smoke contract must document:

- expected status codes.
- redaction plan.
- rollback owner.
- evidence storage reference.
- no new endpoint.
- no commercial terms.
- no runtime change.
- no credential material in the evidence package.
