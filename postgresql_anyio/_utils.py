import inspect
from enum import Enum, IntEnum
from functools import wraps
from typing import cast

from . import _pgmsg
from ._exceptions import DatabaseError


class PgProtocolFormat(IntEnum):
  TEXT = 0
  BINARY = 1

  _DEFAULT = BINARY

  @staticmethod
  def convert(value):
    if isinstance(value, PgProtocolFormat):
      return value
    elif isinstance(value, str):
      try:
        return PgProtocolFormat[value.upper()]
      except KeyError:
        pass

    raise ValueError(
      "Invalid protocol format value. A PgProtocolFormat value "
      "or its string representation is expected."
    )


class PgIsolationLevel(Enum):
  SERIALIZABLE = 1
  REPEATABLE_READ = 2
  READ_COMMITTED = 3
  READ_UNCOMMITTED = 4

  def __str__(self):
    return self.name.lower().replace("_", " ")


class PgReadWriteMode(Enum):
  READ_WRITE = 1
  READ_ONLY = 2

  def __str__(self):
    return self.name.lower().replace("_", " ")


def get_exc_from_msg(msg, desc_prefix="", desc_suffix=""):
  fields = dict(msg.pairs)

  error_msg = fields.get("M")
  if error_msg is not None:
    error_msg = str(error_msg)
  if error_msg is None:
    error_msg = ""

  severity = fields.get("S")
  if severity is not None:
    severity = str(severity)

  error_msg = desc_prefix + error_msg + desc_suffix

  return DatabaseError(
    error_msg=error_msg,
    severity=severity,
  )


def set_event_when_done(event_name):
  def decorator(method):
    @wraps(method)
    async def async_wrapper(self, *args, **kwargs):
      try:
        return await method(self, *args, **kwargs)
      finally:
        getattr(self, event_name).set()

    @wraps(method)
    async def sync_wrapper(self, *args, **kwargs):
      try:
        return await method(self, *args, **kwargs)
      finally:
        getattr(self, event_name).set()

    if inspect.iscoroutinefunction(method):
      return async_wrapper
    else:
      return sync_wrapper

  return decorator


def get_rowcount(msg):
  """Parses a CommandComplete message and returns a rowcount value in it
  (if any)"""
  assert isinstance(msg, _pgmsg.CommandComplete)

  cmd_tag = cast(bytes, msg.cmd_tag)
  if cmd_tag.startswith(b"SELECT"):
    _, rows = cmd_tag.split(b" ")
    rows = int(rows.decode("ascii"))
  elif cmd_tag.startswith(b"INSERT"):
    _, _, rows = cmd_tag.split(b" ")
    rows = int(rows.decode("ascii"))
  elif cmd_tag.startswith(b"UPDATE"):
    _, rows = cmd_tag.split(b" ")
    rows = int(rows.decode("ascii"))
  else:
    rows = None

  return rows


def chunks(x, n):
  return [x[i : i + n] for i in range(0, len(x), n)]
