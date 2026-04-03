from k6.backends.embedded import _split_stream_buffer


def test_split_stream_buffer_keeps_carriage_return_information() -> None:
    lines, remainder = _split_stream_buffer("default [ 10% ]\rdefault [ 11% ]\n")

    assert lines == [("default [ 10% ]", True), ("default [ 11% ]", False)]
    assert remainder == ""


def test_split_stream_buffer_returns_remainder_for_incomplete_line() -> None:
    lines, remainder = _split_stream_buffer("line one\npartial")

    assert lines == [("line one", False)]
    assert remainder == "partial"
