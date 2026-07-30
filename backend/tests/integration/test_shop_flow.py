"""Integration: admin creates catalog, customer orders it (COD). Requires PostgreSQL."""
import pytest

from ._helpers import auth_header, grant_super_admin, login

pytestmark = pytest.mark.integration


async def test_catalog_cart_order_flow(client, _engine):
    # --- bootstrap an admin ---
    admin = await login(client, _engine, "+919000000200")
    await grant_super_admin(_engine, admin["user"]["id"])
    admin = await login(client, _engine, "+919000000200")  # re-login to pick up role
    ah = auth_header(admin["access_token"])

    # --- create category + product + variant ---
    cat = await client.post("/admin/categories", headers=ah,
                            json={"name": "Chicken", "slug": "chicken-int"})
    assert cat.status_code in (200, 201), cat.text

    prod = await client.post("/admin/products", headers=ah,
                             json={"name": "Curry Cut", "slug": "curry-cut-int",
                                   "category_id": cat.json()["id"]})
    assert prod.status_code in (200, 201), prod.text
    pid = prod.json()["id"]

    var = await client.post(f"/admin/products/{pid}/variants", headers=ah,
                            json={"name": "1 kg", "price_amount": 26000, "initial_quantity": 50})
    assert var.status_code in (200, 201), var.text
    variant_id = var.json()["id"]

    # --- customer adds to cart ---
    cust = await login(client, _engine, "+919000000201")
    ch = auth_header(cust["access_token"])
    add = await client.post("/cart/items", headers=ch,
                            json={"variant_id": variant_id, "quantity": 2})
    assert add.status_code == 200, add.text
    quote = add.json()["quote"]
    assert quote["subtotal"] == 52000

    # --- customer needs an address, then places a COD order ---
    addr = await client.post("/me/addresses", headers=ch,
                             json={"line1": "12 MG Road", "city": "Agra", "pincode": "282001"})
    assert addr.status_code == 201, addr.text
    order = await client.post("/orders", headers={**ch, "Idempotency-Key": "int-key-1"},
                              json={"address_id": addr.json()["id"], "payment_method": "cod"})
    assert order.status_code == 201, order.text
    o = order.json()["order"]
    assert o["status"] == "accepted"          # COD auto-accepts
    assert o["grand_total"] == 52000 + o["shipping_total"] + o["tax_total"]

    # --- idempotency: same key returns the same order ---
    again = await client.post("/orders", headers={**ch, "Idempotency-Key": "int-key-1"},
                              json={"address_id": addr.json()["id"], "payment_method": "cod"})
    assert again.status_code in (200, 201)
    assert again.json()["order"]["order_number"] == o["order_number"]


async def test_admin_dashboard_requires_permission(client, _engine):
    cust = await login(client, _engine, "+919000000202")
    r = await client.get("/admin/dashboard", headers=auth_header(cust["access_token"]))
    assert r.status_code == 403   # plain customer lacks analytics.read
