"""Pure pagination helper tests."""
from app.core.pagination import PageParams, build_page


def test_offset_and_limit():
    p = PageParams(page=3, page_size=20)
    assert p.offset == 40
    assert p.limit == 20


def test_build_page_total_pages():
    page = build_page(items=[1, 2, 3], total=137, params=PageParams(page=1, page_size=20))
    assert page.meta.total == 137
    assert page.meta.total_pages == 7   # ceil(137/20)
    assert page.data == [1, 2, 3]


def test_build_page_exact_multiple():
    page = build_page(items=[], total=40, params=PageParams(page=2, page_size=20))
    assert page.meta.total_pages == 2
