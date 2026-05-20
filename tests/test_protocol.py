from messenger.protocol import decode_message, encode_message


def test_encode_decode_roundtrip():
    raw = encode_message("MESSAGE", {"From": "alice"}, "hello")
    message = decode_message(raw)

    assert message.method == "MESSAGE"
    assert message.headers["From"] == "alice"
    assert message.body == "hello"
