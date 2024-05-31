from harp.commandline.server import ServerOptions


def test_default():
    options = ServerOptions(options=(), files=(), enable=(), disable=(), reset=False)
    assert options.as_list() == []


def test_applications():
    options = ServerOptions(options=(), files=(), enable=("foo", "bar"), disable=("baz", "blurp"), reset=False)
    assert options.as_list() == ["--enable foo", "--enable bar", "--disable baz", "--disable blurp"]


def test_reset():
    options = ServerOptions(options=(), files=(), enable=(), disable=(), reset=True)
    assert options.as_list() == [
        "--set storage.drop_tables=true",
    ]
