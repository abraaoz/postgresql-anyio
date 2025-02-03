# PostgreSQL AnyIO

`postgresql-anyio` is an [AnyIO](https://anyio.readthedocs.io/) ([asyncio](https://docs.python.org/3/library/asyncio.html) or [trio](https://trio.readthedocs.io/) backend) PostgreSQL client library.

It's a slighty modified version of the amazing library [pgtrio](https://github.com/elektito/pgtrio) created by [Mostafa Razavi](https://elektito.com/).

## Tests

1. Start a localhost PostgreSQL instance on port 5432 (default).

2. Check if `pg_ctl` is on PATH.

3. Run `./test.sh`

## Usage

Install with `poetry add git+https://github.com/abraaoz/postgresql-anyio.git#main`

Use as [pgtrio README.md](https://github.com/elektito/pgtrio/blob/master/README.md), but:

| Find:          | Replace with:                                                         |
|----------------|-----------------------------------------------------------------------|
| import pgtrio  | import postgresql_anyio                                               |
| import trio    | import anyio                                                          |
| trio.run(main) | anyio.run(main, backend="trio") or anyio.run(main, backend="asyncio") |