"""Pure-schema tests (no DB/network). Run: pytest -q."""
import uuid

import pytest
from pydantic import ValidationError

from app.features.auth.schemas import OtpRequestIn, TokenPair, UserOut
from app.features.catalog.schemas import CategoryOut, ProductCard


def test_otp_request_accepts_valid_phone():
    assert OtpRequestIn(phone="+919876543210").phone == "+919876543210"


def test_otp_request_rejects_bad_phone():
    with pytest.raises(ValidationError):
        OtpRequestIn(phone="not-a-phone")


def test_token_pair_shape():
    u = UserOut(
        id=uuid.uuid4(), phone="+91999", email=None, full_name="A",
        is_guest=False, referral_code="ABC123", default_locale="en",
        roles=["customer"], permissions=[],
    )
    tp = TokenPair(access_token="a", refresh_token="b", user=u)
    assert tp.token_type == "bearer"


def test_category_tree_is_recursive():
    root = CategoryOut(id=uuid.uuid4(), name="Food", slug="food")
    child = CategoryOut(id=uuid.uuid4(), name="Pizza", slug="pizza")
    root.children.append(child)
    assert root.children[0].slug == "pizza"


def test_product_card_price_minor_units():
    card = ProductCard(
        id=uuid.uuid4(), name="Margherita", slug="marg", short_description=None,
        brand=None, is_veg=True, rating_avg=4.5, rating_count=10, price_from=29900,
    )
    assert card.price_from == 29900  # ₹299.00 in paise
