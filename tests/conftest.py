import os
import shutil
import subprocess
from tempfile import TemporaryDirectory, mkstemp

import pytest

import postgresql_anyio

pg_ctl = None

pytestmark = pytest.mark.anyio


# run each async test two times, one for each backend
@pytest.fixture(
  params=[
    pytest.param("trio", id="trio"),
    pytest.param("asyncio", id="asyncio"),
  ]
)
def anyio_backend(request):
  return request.param


@pytest.fixture(scope="session")
def postgres_socket_file():
  global pg_ctl
  if not pg_ctl:
    pg_ctl = find_pg_ctl()

  with TemporaryDirectory() as data_dir:
    # use the same directory for both data and the unix socket
    socket_dir = data_dir

    _, log_file = mkstemp(suffix=".log")

    init_cmd = [
      pg_ctl,
      "init",
      "-D",
      data_dir,
      "-l",
      log_file,
    ]

    sudo_prefix = []
    if os.getuid() == 0:
      # pg_ctl refuses to run as root

      # make sure the log file is owned by the postgres user
      chown_cmd = ["/bin/chown", "postgres:postgres", data_dir, "-R"]
      proc = subprocess.run(chown_cmd, capture_output=True)
      if proc.returncode:
        raise RuntimeError(
          f"Could not chown the data directory "
          f"(exit code={proc.returncode})\n"
          f"stdout:\n{proc.stderr.decode()}\n\n"
          f"stderr:\n{proc.stderr.decode()}"
        )

      # make sure the log file is owned by the postgres user
      chown_cmd = ["/bin/chown", "postgres:postgres", log_file]
      proc = subprocess.run(chown_cmd, capture_output=True)
      if proc.returncode:
        raise RuntimeError(
          f"Could not chown the log file "
          f"(exit code={proc.returncode})\n"
          f"stdout:\n{proc.stderr.decode()}\n\n"
          f"stderr:\n{proc.stderr.decode()}"
        )

      # run pg_ctl as the postgres user
      sudo_prefix = ["sudo", "-u", "postgres"]

    proc = subprocess.run(sudo_prefix + init_cmd, capture_output=True)
    if proc.returncode:
      raise RuntimeError(
        f"Could not initilize a PostgreSQL data directory "
        f"(exit code={proc.returncode}). Check the log file: "
        f"{log_file}\nstdout:\n{proc.stdout.decode()}\n\n"
        f"stderr:\n{proc.stderr.decode()}"
      )

    pg_options = f'-F -c listen_addresses="" -c unix_socket_directories={socket_dir} '
    start_cmd = [
      pg_ctl,
      "-D",
      data_dir,
      "-l",
      log_file,
      "-m",
      "immediate",
      "start",
      "-o",
      pg_options,
    ]

    proc = subprocess.run(sudo_prefix + start_cmd, capture_output=True)
    if proc.returncode:
      raise RuntimeError(
        f"Could not start PostgreSQL (exit code="
        f"{proc.returncode}). Check the log file: {log_file}"
        f"\nstdout:\n{proc.stdout.decode()}\n\n"
        f"stderr:\n{proc.stderr.decode()}"
      )

    try:
      yield f"{data_dir}/.s.PGSQL.5432"
    finally:
      stop_cmd = [
        pg_ctl,
        "-D",
        data_dir,
        "-l",
        log_file,
        "-m",
        "immediate",
        "stop",
        "-o",
        pg_options,
      ]

      proc = subprocess.run(sudo_prefix + stop_cmd, capture_output=True)
      if proc.returncode:
        raise RuntimeError(
          f"Could not stop PostgreSQL (exit code="
          f"{proc.returncode}).\nstdout:\n{proc.stdout.decode()}"
          f"\n\nstderr:\n{proc.stderr.decode()}"
        )

      os.unlink(log_file)

    try:
      os.unlink(log_file)
    except FileNotFoundError:
      pass


@pytest.fixture(params=["binary", "text"])
async def conn(postgres_socket_file, request):
  fmt = request.param

  username = None
  if os.getuid() == 0:
    # no root role, so use postgres
    username = "postgres"

  async with postgresql_anyio.connect(
    "postgres",
    username=username,
    protocol_format=fmt,
    unix_socket_path=postgres_socket_file,
  ) as conn:
    await cleanup_existing_test_db(conn)
    await conn.execute("create database testdb")

  async with postgresql_anyio.connect(
    "testdb",
    username=username,
    protocol_format=fmt,
    unix_socket_path=postgres_socket_file,
  ) as conn:
    # owner check won't work in tests, because fixtures are not
    # created in the same task as the test function
    conn._disable_owner_check = True

    yield conn


@pytest.fixture(params=["binary", "text"])
async def pool(postgres_socket_file, request):
  fmt = request.param

  username = None
  if os.getuid() == 0:
    # no root role, so use postgres
    username = "postgres"

  async with postgresql_anyio.connect(
    "postgres",
    username=username,
    protocol_format=fmt,
    unix_socket_path=postgres_socket_file,
  ) as conn:
    await cleanup_existing_test_db(conn)
    await conn.execute("create database testdb")

  def conn_init(conn):
    # owner check won't work in tests, because fixtures are not
    # created in the same task as the test function
    conn._disable_owner_check = True

  async with postgresql_anyio.create_pool(
    "testdb",
    username=username,
    protocol_format=fmt,
    pool_conn_init=conn_init,
    unix_socket_path=postgres_socket_file,
  ) as pool:
    yield pool


def find_pg_ctl():
  pg_ctl = shutil.which("pg_ctl")
  if not pg_ctl:
    raise RuntimeError("pg_ctl not found at PATH.")

  return str(pg_ctl)


async def cleanup_existing_test_db(conn):
  results = await conn.execute("select 1 from pg_database where datname = 'testdb'")
  if len(results) == 0:
    return

  await conn.execute("drop database testdb")
