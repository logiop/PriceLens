from app.analytics import market_stats, repricing_recommendation
from app.collector import (
    _extract_jsonld_price,
    _extract_regex_price,
    _parse_amount,
)
from app.models import Product
from app.rate_limit import SlidingWindowLimiter
from app.security import hash_password, verify_password


class _EmptySession:
    """Minimal Session stub: no price points exist."""

    def exec(self, *_args, **_kwargs):
        class _Result:
            def all(self):
                return []

            def first(self):
                return None

        return _Result()


def test_password_hash_roundtrip():
    stored = hash_password("super-secret-123")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("super-secret-123", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("super-secret-123", "garbage")


def test_parse_amount_formats():
    assert _parse_amount("1.234,56") == 1234.56
    assert _parse_amount("99.99") == 99.99
    assert _parse_amount("€ 1 234,56") == 1234.56
    assert _parse_amount("1,234.56") == 1234.56
    assert _parse_amount("") is None
    assert _parse_amount("nope") is None


def test_extract_jsonld_price():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "Product", "offers": {"price": "199.90", "priceCurrency": "EUR"}}
    </script></head></html>
    """
    assert _extract_jsonld_price(html) == 199.9


def test_extract_jsonld_invalid():
    assert _extract_jsonld_price("<html><body>no ld+json here</body></html>") is None


def test_extract_regex_price():
    assert _extract_regex_price("Prezzo: € 1.299,00", r"[€$£]\s*([0-9][0-9.,]*)") == 1299.0
    assert _extract_regex_price("nessun prezzo", r"[€$£]\s*([0-9][0-9.,]*)") is None


def test_rate_limiter_blocks_after_limit():
    limiter = SlidingWindowLimiter(window=60)
    for _ in range(3):
        allowed, _retry = limiter.allow("k", 3)
        assert allowed
    allowed, retry = limiter.allow("k", 3)
    assert not allowed
    assert retry >= 1


def _product(cost=100.0, price=150.0, msrp=200.0, map_price=120.0, strategy="margin_protected"):
    return Product(
        id=1,
        team_id=1,
        sku="X",
        name="Test",
        brand="B",
        category="C",
        cost_price=cost,
        current_price=price,
        msrp=msrp,
        map_price=map_price,
        strategy=strategy,
    )


def test_repricing_floor_is_map_when_higher():
    # floor = max(map_price, cost*1.15) = max(120, 115) = 120
    rec = repricing_recommendation(_EmptySession(), _product(cost=100.0, price=150.0, map_price=120.0))
    assert rec.floor == 120.0
    assert rec.suggested_price >= rec.floor


def test_repricing_floor_is_margin_when_higher():
    # cost=100, min_margin=15% -> 115; map=110 -> floor 115
    rec = repricing_recommendation(_EmptySession(), _product(cost=100.0, price=150.0, map_price=110.0))
    assert rec.floor == 115.0


def test_repricing_ceiling_msrp():
    rec = repricing_recommendation(_EmptySession(), _product(price=150.0, msrp=200.0))
    assert rec.ceiling == 200.0
    assert rec.suggested_price <= 200.0


def test_market_stats_empty():
    stats = market_stats(_EmptySession(), _product())
    assert stats["min_price"] is None
    assert stats["position"] is None
