from collections import namedtuple
from datetime import date, datetime, time, timedelta, timezone
from ipaddress import (
    IPv4Address,
    IPv4Network,
    IPv6Address,
    IPv6Network,
    ip_address,
    ip_network,
)

import anyio
from pytest import raises

import pganyio


async def test_null_char_in_query(conn):
    with raises(pganyio.ProgrammingError):
        await conn.execute("foo \x00 bar")


async def test_empty_query(conn):
    results = await conn.execute("")
    assert results == []
    assert conn.rowcount is None


async def test_null(conn):
    await conn.execute("create table foobar (foo int, bar int)")
    await conn.execute("insert into foobar (foo) values ($1)", 1900)
    await conn.execute("insert into foobar (bar) values ($1)", 1800)
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [(1900, None), (None, 1800)]


async def test_null_param(conn):
    await conn.execute("create table foobar (foo int, bar int)")
    await conn.execute("insert into foobar (foo, bar) values ($1, $2)", 1900, None)
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 1
    assert results == [(1900, None)]


async def test_float4(conn):
    await conn.execute("create table foobar (foo float4)")
    await conn.execute("insert into foobar (foo) values ($1)", 4.25)
    await conn.execute("insert into foobar (foo) values ($1)", 18.5)
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [(4.25,), (18.5,)]


async def test_float8(conn):
    await conn.execute("create table foobar (foo float8)")
    await conn.execute("insert into foobar (foo) values ($1)", 4.25)
    await conn.execute("insert into foobar (foo) values ($1)", 18.5)
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [(4.25,), (18.5,)]


async def test_int2(conn):
    await conn.execute("create table foobar (foo int2)")
    await conn.execute("insert into foobar (foo) values ($1)", 1000)
    await conn.execute("insert into foobar (foo) values ($1)", -32768)
    await conn.execute("insert into foobar (foo) values ($1)", 32767)
    await conn.execute("insert into foobar (foo) values ($1)", 0)
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 4
    assert results == [(1000,), (-32768,), (32767,), (0,)]


async def test_int2_out_of_range_inline_value(conn):
    await conn.execute("create table foobar (foo int2)")

    # overflow of parameters directly mentioned in the query will be
    # detected by the backend
    with raises(pganyio.DatabaseError):
        await conn.execute("insert into foobar (foo) values (33000)")


async def test_int2_out_of_range_param(conn):
    await conn.execute("create table foobar (foo int2)")

    # parameter overflow should be detected while encoding the value
    with raises(OverflowError):
        await conn.execute("insert into foobar (foo) values ($1)", 33000)


async def test_int4(conn):
    await conn.execute("create table foobar (foo int4)")
    await conn.execute("insert into foobar (foo) values ($1)", 1000)
    await conn.execute("insert into foobar (foo) values ($1)", -2147483648)
    await conn.execute("insert into foobar (foo) values ($1)", 2147483647)
    await conn.execute("insert into foobar (foo) values ($1)", 0)
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 4
    assert results == [(1000,), (-2147483648,), (2147483647,), (0,)]


async def test_int4_out_of_range_inline_value(conn):
    await conn.execute("create table foobar (foo int4)")

    # overflow of parameters directly mentioned in the query will be
    # detected by the backend
    with raises(pganyio.DatabaseError):
        await conn.execute("insert into foobar (foo) values (2147483648)")


async def test_int4_out_of_range_in_param(conn):
    await conn.execute("create table foobar (foo int4)")

    # parameter overflow should be detected while encoding the value
    with raises(OverflowError):
        await conn.execute("insert into foobar (foo) values ($1)", 2147483648)


async def test_int8(conn):
    await conn.execute("create table foobar (foo int8)")
    await conn.execute("insert into foobar (foo) values ($1)", 1000)
    await conn.execute("insert into foobar (foo) values ($1)", -9223372036854775808)
    await conn.execute("insert into foobar (foo) values ($1)", 9223372036854775807)
    await conn.execute("insert into foobar (foo) values ($1)", 0)
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 4
    assert results == [(1000,), (-9223372036854775808,), (9223372036854775807,), (0,)]


async def test_int8_out_of_range_inline_value(conn):
    await conn.execute("create table foobar (foo int8)")

    # overflow of parameters directly mentioned in the query will be
    # detected by the backend
    with raises(pganyio.DatabaseError):
        await conn.execute("insert into foobar (foo) values (9223372036854775808)")


async def test_int8_out_of_range_param(conn):
    await conn.execute("create table foobar (foo int8)")

    # overflow of parameters directly mentioned in the query will be
    # detected by the backend
    with raises(OverflowError):
        await conn.execute("insert into foobar (foo) values ($1)", 9223372036854775808)


async def test_bool(conn):
    await conn.execute("create table foobar (foo bool)")
    await conn.execute("insert into foobar (foo) values ($1)", True)
    await conn.execute("insert into foobar (foo) values ($1)", False)
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [(True,), (False,)]


async def test_bytea(conn):
    await conn.execute("create table foobar (foo bytea)")
    await conn.execute("insert into foobar (foo) values ($1)", b"\x00\x01\x02")
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 1
    assert results == [(b"\x00\x01\x02",)]


async def test_text(conn):
    await conn.execute("create table foobar (foo text)")
    await conn.execute("insert into foobar (foo) values ($1)", "fooobaar")
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 1
    assert results == [("fooobaar",)]


async def test_json(conn):
    await conn.execute("create table foobar (foo json)")
    await conn.execute("insert into foobar (foo) values ($1)", {})
    await conn.execute("insert into foobar (foo) values ($1)", [])
    await conn.execute(
        "insert into foobar (foo) values ($1)", {"foo": [10], "bar": 1.5}
    )
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 3
    assert results == [
        ({},),
        ([],),
        ({"foo": [10], "bar": 1.5},),
    ]


async def test_jsonb(conn):
    await conn.execute("create table foobar (foo jsonb)")
    await conn.execute("insert into foobar (foo) values ($1)", {})
    await conn.execute("insert into foobar (foo) values ($1)", [])
    await conn.execute(
        "insert into foobar (foo) values ($1)", {"foo": [10], "bar": 1.5}
    )
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 3
    assert results == [
        ({},),
        ([],),
        ({"foo": [10], "bar": 1.5},),
    ]


async def test_inet(conn):
    await conn.execute("create table foobar (foo inet)")
    await conn.execute(
        "insert into foobar (foo) values ($1)", ip_address("192.168.1.100")
    )
    await conn.execute("insert into foobar (foo) values ($1)", ip_address("::2"))
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [
        (IPv4Address("192.168.1.100"),),
        (IPv6Address("::2"),),
    ]


async def test_cidr(conn):
    await conn.execute("create table foobar (foo cidr)")
    await conn.execute(
        "insert into foobar (foo) values ($1)", ip_network("192.168.0.0/16")
    )
    await conn.execute("insert into foobar (foo) values ($1)", ip_network("::/8"))
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [
        (IPv4Network("192.168.0.0/16"),),
        (IPv6Network("::/8"),),
    ]


async def test_char(conn):
    await conn.execute("create table foobar (foo char)")
    await conn.execute("insert into foobar (foo) values ($1)", "X")
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 1
    assert results == [
        ("X",),
    ]


async def test_varchar(conn):
    await conn.execute("create table foobar (foo varchar)")
    await conn.execute("insert into foobar (foo) values ($1)", "abc")
    await conn.execute("insert into foobar (foo) values ($1)", "xyzabc")
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [
        ("abc",),
        ("xyzabc",),
    ]


async def test_date(conn):
    await conn.execute("create table foobar (foo date)")
    await conn.execute("insert into foobar (foo) values ($1)", date(2022, 10, 19))
    await conn.execute("insert into foobar (foo) values ($1)", date(1954, 1, 2))
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [
        (date(2022, 10, 19),),
        (date(1954, 1, 2),),
    ]


async def test_time(conn):
    await conn.execute("create table foobar (foo time)")
    await conn.execute("insert into foobar (foo) values ($1)", time(0, 0, 1))
    await conn.execute("insert into foobar (foo) values ($1)", time(18, 19, 44))
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [
        (time(0, 0, 1),),
        (time(18, 19, 44),),
    ]


async def test_timestamp(conn):
    await conn.execute("create table foobar (foo timestamp)")
    await conn.execute(
        "insert into foobar (foo) values ($1)", datetime(2022, 4, 18, 1, 31, 43, 646120)
    )
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 1
    assert results == [
        (datetime(2022, 4, 18, 1, 31, 43, 646120),),
    ]


async def test_timestamptz(conn):
    await conn.execute("create table foobar (foo timestamptz)")
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        datetime(
            2022,
            4,
            18,
            1,
            31,
            43,
            646120,
            tzinfo=timezone(timedelta(hours=2, minutes=30)),
        ),
    )
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 1
    assert results == [
        (
            datetime(
                2022,
                4,
                18,
                1,
                31,
                43,
                646120,
                tzinfo=timezone(timedelta(hours=2, minutes=30)),
            ),
        ),
    ]


async def test_interval(conn):
    await conn.execute("create table foobar (foo interval)")
    await conn.execute(
        "insert into foobar (foo) values ($1)", timedelta(hours=2, minutes=30)
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)", timedelta(days=41, hours=82, minutes=30)
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        timedelta(days=41, hours=82, minutes=30, seconds=7),
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        timedelta(days=41 + 100 * 365, hours=82, minutes=30, seconds=7),
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        timedelta(days=41 + 300 * 365, hours=82, minutes=30, seconds=7),
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)", timedelta(days=100 * 365)
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        timedelta(days=100 * 365, microseconds=2),
    )
    await conn.execute("insert into foobar (foo) values ($1)", timedelta(days=1 * 365))
    await conn.execute("insert into foobar (foo) values ($1)", timedelta(days=-1 * 365))
    await conn.execute(
        "insert into foobar (foo) values ($1)", timedelta(days=-1 * 365, seconds=2)
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)", timedelta(days=2 * 365, seconds=-2)
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        timedelta(days=3 * 365 + 1 * 30 + 1, hours=4, minutes=47, seconds=58),
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        timedelta(days=9 * 365 + 1 * 30 + 1, hours=4, minutes=47, seconds=58),
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        timedelta(days=9 * 365 + 9 * 30 + 1, hours=4, minutes=47, seconds=58),
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        timedelta(days=9 * 365 + 9 * 30 + 1, hours=-5, minutes=-4, seconds=-2),
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)", timedelta(days=1, microseconds=2100)
    )
    await conn.execute("insert into foobar (foo) values ($1)", timedelta(days=21))
    await conn.execute("insert into foobar (foo) values ($1)", timedelta(days=2107))
    await conn.execute("insert into foobar (foo) values ($1)", timedelta(hours=-10))
    await conn.execute("insert into foobar (foo) values ($1)", timedelta(hours=10))
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 20
    assert results == [
        (timedelta(hours=2, minutes=30),),
        (timedelta(days=41, hours=82, minutes=30),),
        (timedelta(days=41, hours=82, minutes=30, seconds=7),),
        (timedelta(days=41 + 100 * 365, hours=82, minutes=30, seconds=7),),
        (timedelta(days=41 + 300 * 365, hours=82, minutes=30, seconds=7),),
        (timedelta(days=100 * 365),),
        (timedelta(days=100 * 365, microseconds=2),),
        (timedelta(days=1 * 365),),
        (timedelta(days=-1 * 365),),
        (timedelta(days=-1 * 365, seconds=2),),
        (timedelta(days=2 * 365, seconds=-2),),
        (timedelta(days=3 * 365 + 1 * 30 + 1, hours=4, minutes=47, seconds=58),),
        (timedelta(days=9 * 365 + 1 * 30 + 1, hours=4, minutes=47, seconds=58),),
        (timedelta(days=9 * 365 + 9 * 30 + 1, hours=4, minutes=47, seconds=58),),
        (timedelta(days=9 * 365 + 9 * 30 + 1, hours=-5, minutes=-4, seconds=-2),),
        (timedelta(days=1, microseconds=2100),),
        (timedelta(days=21),),
        (timedelta(days=2107),),
        (timedelta(hours=-10),),
        (timedelta(hours=10),),
    ]


async def test_timetz(conn):
    await conn.execute("create table foobar (foo timetz)")
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        time(0, 0, 1, tzinfo=timezone(timedelta(hours=2))),
    )
    await conn.execute(
        "insert into foobar (foo) values ($1)",
        time(18, 19, 44, tzinfo=timezone(timedelta(hours=2))),
    )
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 2
    assert results == [
        (time(0, 0, 1, tzinfo=timezone(timedelta(hours=2))),),
        (time(18, 19, 44, tzinfo=timezone(timedelta(hours=2))),),
    ]


async def test_multiple_params(conn):
    await conn.execute(
        "create table foobar (foo int2, bar text, spam jsonb, eggs float)"
    )
    await conn.execute(
        "insert into foobar (foo, bar, eggs) values ($1, $2, $3)",
        101,
        "foobar",
        2500.25,
    )
    results = await conn.execute("select * from foobar")
    assert conn.rowcount == 1
    assert results == [
        (101, "foobar", None, 2500.25),
    ]


async def test_wrong_param_type(conn):
    await conn.execute(
        "create table foobar (foo int2, bar text, spam jsonb, eggs float)"
    )
    with raises(TypeError):
        await conn.execute(
            "insert into foobar (foo, bar, eggs) values ($1, $2, $3)",
            101,
            "foobar",
            object(),
        )


async def test_closed(conn):
    conn.close()
    with raises(pganyio.ProgrammingError):
        await conn.execute("select 1")


async def test_ownership(conn):
    # this is set in the fixture, but now we flip it back for this
    # test
    conn._disable_owner_check = False

    async def perform():
        with raises(pganyio.InterfaceError):
            await conn.execute("select 1")

    async with anyio.create_task_group() as nursery:
        nursery.start_soon(perform)


async def test_rowcount(conn):
    await conn.execute("create table foobar (foo int)")
    await conn.execute("insert into foobar (foo) values (10), (20), (30)")
    assert conn.rowcount == 3
    await conn.execute("update foobar set foo = foobar.foo + 1 where foo >= 20")
    assert conn.rowcount == 2


async def test_array(conn):
    await conn.execute("create table foobar (foo int[])")
    await conn.execute("insert into foobar (foo) values ('{1,2,3}'::int[])")
    results = await conn.execute("select * from foobar")
    assert results == [([1, 2, 3],)]


async def test_array_with_quote(conn):
    await conn.execute("create table foobar (foo text[])")
    await conn.execute(
        r"""
        insert into foobar (foo)
        values ('{"foo", "aaa\"aaa"}'::text[])
        """
    )
    results = await conn.execute("select * from foobar")
    assert results == [(["foo", 'aaa"aaa'],)]


async def test_array_empty(conn):
    await conn.execute("create table foobar (foo int[])")
    await conn.execute("insert into foobar (foo) values ('{}'::int[])")
    results = await conn.execute("select * from foobar")
    assert results == [([],)]


async def test_array_multidim1(conn):
    await conn.execute("create table foobar (foo int[][])")
    await conn.execute("insert into foobar (foo) values ('{{1,2,3},{4,5,6}}'::int[])")
    results = await conn.execute("select * from foobar")
    assert results == [([[1, 2, 3], [4, 5, 6]],)]


async def test_array_multidim2(conn):
    results = await conn.execute(
        "select '{{{1,2},{3,4},{5,6}},{{7,8},{9,10},{11,12}}}'::int[][][]"
    )
    assert results == [([[[1, 2], [3, 4], [5, 6]], [[7, 8], [9, 10], [11, 12]]],)]


async def test_array_multidim3(conn):
    results = await conn.execute("select '{{{{1,2},{3,4},{5,6}}}}'::int[]")
    assert results == [([[[[1, 2], [3, 4], [5, 6]]]],)]


async def test_array_non_list(conn):
    await conn.execute("create table foobar (foo int[])")
    with raises(TypeError):
        await conn.execute("insert into foobar (foo) values ($1)", 10)


async def test_array_dim_check1(conn):
    await conn.execute("create table foobar (foo int[][])")
    with raises(ValueError):
        # sub arrays should be the same length
        await conn.execute(
            "insert into foobar (foo) values ($1)",
            [[1, 2], [1]],
        )


async def test_array_dim_check2(conn):
    await conn.execute("create table foobar (foo int[])")
    with raises(ValueError):
        await conn.execute(
            "insert into foobar (foo) values ($1)",
            [[[1, 2], [3, 4]], [5, 6]],
        )


async def test_array_dim_check3(conn):
    await conn.execute("create table foobar (foo int[][])")
    with raises(ValueError):
        # sub arrays should be the same length; postgres would
        # actually accept this (at least postgres 12), but it would
        # then insert an empty array. probably a bug.
        await conn.execute(
            "insert into foobar (foo) values ($1)",
            [[[1, 2]], [1]],
        )


async def test_array_dim_check4(conn):
    await conn.execute("create table foobar (foo int[])")
    with raises(ValueError):
        # postgres does not accept empty sub-arrays
        await conn.execute(
            "insert into foobar (foo) values ($1)",
            [[]],
        )


async def test_array_dim_check5(conn):
    await conn.execute("create table foobar (foo int[][])")
    with raises(ValueError):
        # each level should either be all other arrays, or all
        # non-array values
        await conn.execute(
            "insert into foobar (foo) values ($1)",
            [1, [1, 2]],
        )


async def test_array_insert(conn):
    await conn.execute("create table foobar (foo int[])")
    await conn.execute("insert into foobar (foo) values ($1)", [10, 20, 30])
    results = await conn.execute("select * from foobar")
    assert results == [([10, 20, 30],)]


async def test_array_insert_empty(conn):
    await conn.execute("create table foobar (foo int[])")
    await conn.execute("insert into foobar (foo) values ($1)", [])
    results = await conn.execute("select * from foobar")
    assert results == [([],)]


async def test_array_param(conn):
    await conn.execute("create table foobar (foo int)")
    await conn.execute("insert into foobar (foo) values (1), (2), (3)")
    results = await conn.execute("select * from foobar where foo = any($1)", [1, 3])
    assert results == [(1,), (3,)]


async def test_array_special_chars_encode(conn):
    await conn.execute("create table foobar (foo text[])")
    await conn.execute(
        "insert into foobar (foo) values ($1)", ['xx"yy', "xx,yy", "x{}y", 'a\\"\\']
    )
    results = await conn.execute("select * from foobar")
    assert results == [(['xx"yy', "xx,yy", "x{}y", 'a\\"\\'],)]


async def test_array_with_null(conn):
    await conn.execute("create table foobar (foo int[])")
    await conn.execute("insert into foobar (foo) values ($1)", [1, 2, None, 3, 4])
    results = await conn.execute("select * from foobar")
    assert results == [([1, 2, None, 3, 4],)]


async def test_array_with_null_string(conn):
    await conn.execute("create table foobar (foo text[])")
    await conn.execute(
        "insert into foobar (foo) values ($1)", ["foo", None, "NULL", "bar"]
    )
    results = await conn.execute("select * from foobar")
    assert results == [(["foo", None, "NULL", "bar"],)]


async def test_tuple_class_when_execute(conn):
    await conn.execute("create table foobar (foo int, bar text)")
    await conn.execute("insert into foobar (foo, bar) values (100, 'abc')")

    FoobarTuple = namedtuple("FoobarTuple", ["foo", "bar"])
    results = await conn.execute("select * from foobar", tuple_class=FoobarTuple)
    assert results == [(100, "abc")]
    assert isinstance(results[0], FoobarTuple)


async def test_tuple_class_per_connection(conn):
    FoobarTuple = namedtuple("FoobarTuple", ["foo", "bar"])
    conn.tuple_class = FoobarTuple
    await conn.execute("create table foobar (foo int, bar text)")
    await conn.execute("insert into foobar (foo, bar) values (100, 'abc')")

    results = await conn.execute("select * from foobar")
    assert results == [(100, "abc")]
    assert isinstance(results[0], FoobarTuple)
