# pyright: reportAttributeAccessIssue=none
from unittest.mock import patch

import anyio
import pytest

import postgresql_anyio

pytestmark = pytest.mark.anyio


class MockConnection:
  def __init__(self, *args, **kwargs):
    self.args = args
    self.kwargs = kwargs

    self._is_ready = True
    self._is_ready_cv = anyio.Condition()

  async def _run(self):
    async with self._is_ready_cv:
      self._is_ready_cv.notify_all()

  def close(self):
    pass


async def test_connect_simple():
  with patch("postgresql_anyio._connection.Connection", MockConnection):
    async with postgresql_anyio.connect("postgresql:///foodb") as conn:
      assert conn.kwargs.get("username") is None
      assert conn.kwargs.get("password") is None
      assert conn.kwargs.get("host") is None
      assert conn.kwargs.get("port") is None
      assert conn.args == ("foodb",)


async def test_connect_complex():
  with patch("postgresql_anyio._connection.Connection", MockConnection):
    url = "postgresql://user:pwd@localhost:15432/foodb"
    async with postgresql_anyio.connect(url) as conn:
      assert conn.kwargs.get("username") == "user"
      assert conn.kwargs.get("password") == "pwd"
      assert conn.kwargs.get("host") == "localhost"
      assert conn.kwargs.get("port") == 15432
      assert conn.args == ("foodb",)


async def test_connect_no_url():
  with patch("postgresql_anyio._connection.Connection", MockConnection):
    _url = "postgresql://user:pwd@localhost:15432/foodb"
    async with postgresql_anyio.connect("foodb") as conn:
      assert conn.kwargs.get("username") is None
      assert conn.kwargs.get("password") is None
      assert conn.kwargs.get("host") is None
      assert conn.kwargs.get("port") is None
      assert conn.args == ("foodb",)
