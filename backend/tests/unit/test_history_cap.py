"""T123: Unit test for context history capping."""
from app.models.schemas import cap_context, ContextMessage, ChatRequest


def _make_messages(n: int) -> list[ContextMessage]:
    return [ContextMessage(role="user" if i % 2 == 0 else "assistant", content=f"msg {i}") for i in range(n)]


def test_cap_to_15_from_50():
    msgs = _make_messages(50)
    result = cap_context(msgs)
    assert len(result) == 15
    assert result[0].content == "msg 35"
    assert result[-1].content == "msg 49"


def test_cap_preserves_under_limit():
    msgs = _make_messages(10)
    result = cap_context(msgs)
    assert len(result) == 10


def test_cap_exact_15():
    msgs = _make_messages(15)
    result = cap_context(msgs)
    assert len(result) == 15


def test_cap_none_returns_none():
    assert cap_context(None) is None


def test_cap_empty_returns_empty():
    assert cap_context([]) == []


def test_cap_custom_limit():
    msgs = _make_messages(20)
    result = cap_context(msgs, max_n=5)
    assert len(result) == 5
    assert result[0].content == "msg 15"


def test_chat_request_validator_caps():
    """Pydantic validator on ChatRequest should cap context."""
    msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(30)]
    req = ChatRequest(message="hello", context=msgs)
    assert len(req.context) == 15
    assert req.context[-1].content == "msg 29"
