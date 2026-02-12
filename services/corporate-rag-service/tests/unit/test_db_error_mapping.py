from types import SimpleNamespace

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.exc import IntegrityError

from app.db.errors import DatabaseOperationError
from app.db.repositories import _commit_or_raise


class FailingDB:
    def __init__(self, sqlstate: str):
        self.sqlstate = sqlstate
        self.rolled_back = False

    def commit(self):
        orig = SimpleNamespace(sqlstate=self.sqlstate)
        raise IntegrityError("stmt", {}, orig)

    def rollback(self):
        self.rolled_back = True


def test_commit_or_raise_maps_unique_violation():
    db = FailingDB("23505")
    with pytest.raises(DatabaseOperationError) as exc:
        _commit_or_raise(db)
    assert db.rolled_back is True
    assert exc.value.error_code == "unique_violation"
    assert exc.value.retryable is False


def test_commit_or_raise_maps_deadlock_as_retryable():
    db = FailingDB("40P01")
    with pytest.raises(DatabaseOperationError) as exc:
        _commit_or_raise(db)
    assert exc.value.error_code == "deadlock_detected"
    assert exc.value.retryable is True
