import pytest

from app.cli import fts_rebuild


def test_parse_args_requires_scope_negative():
    with pytest.raises(SystemExit):
        fts_rebuild.parse_args([])


def test_parse_args_tenant_positive():
    args = fts_rebuild.parse_args(["--tenant", "11111111-1111-1111-1111-111111111111"])
    assert args.tenant == "11111111-1111-1111-1111-111111111111"
    assert not args.all_tenants


def test_main_calls_rebuild(monkeypatch):
    called = {}

    def fake_rebuild(tenant_id=None, all_tenants=False):
        called["tenant_id"] = tenant_id
        called["all_tenants"] = all_tenants
        return 3

    monkeypatch.setattr(fts_rebuild, "rebuild_fts", fake_rebuild)
    rc = fts_rebuild.main(["--all"])
    assert rc == 0
    assert called == {"tenant_id": None, "all_tenants": True}
