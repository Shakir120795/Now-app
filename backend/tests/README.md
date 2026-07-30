# Tests

## Pure unit tests (no dependencies beyond the app package)
Fast, deterministic, no DB. Cover the money/logic cores:
- `test_pricing.py` — the cart pricing engine (coupons, membership, tax, shipping, wallet)
- `test_order_lifecycle.py` — the order status state machine
- `test_payment_signatures.py` — Razorpay/PhonePe signature verification
- `test_pagination.py` — pagination math

```bash
pytest tests/test_pricing.py tests/test_order_lifecycle.py \
       tests/test_payment_signatures.py tests/test_pagination.py -q
```

## Integration tests (require PostgreSQL)
Spin up infra, point `TEST_DATABASE_URL` at a disposable database, then run the
`integration` marker. These exercise real HTTP flows against the ASGI app.

```bash
docker compose up -d db redis
createdb -h localhost -U luxe luxe_test          # or let conftest recreate the schema
export TEST_DATABASE_URL=postgresql+asyncpg://luxe:luxe@localhost:5432/luxe_test
pytest -m integration -q
```

Covered flows:
- `test_auth_flow.py` — health, guest login, OTP login, refresh **rotation + reuse detection**.
- `test_shop_flow.py` — admin creates category→product→variant; customer adds to cart,
  places a COD order (idempotent), and RBAC blocks a customer from the admin dashboard.

## Everything
```bash
pytest -q            # runs pure + integration (integration needs the DB up)
```
