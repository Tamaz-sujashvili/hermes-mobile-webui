"""Regression coverage for #2 session-switch busy-state race.

Switching from a streaming session to an idle one must clear S.busy before the
async _ensureMessagesLoaded gap. Otherwise _isSessionLocallyStreaming() treats
the newly opened session as locally streaming while messages are still loading.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SESSIONS_SRC = (REPO / "static" / "sessions.js").read_text(encoding="utf-8")


def _function_body(src: str, signature: str) -> str:
    start = src.find(signature)
    assert start != -1, f"missing {signature}"
    brace = src.find("{", start)
    assert brace != -1, f"missing opening brace for {signature}"
    depth = 0
    for i in range(brace, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[brace + 1 : i]
    raise AssertionError(f"could not extract function body for {signature}")


def test_loadSession_clears_busy_before_async_message_load_when_server_idle():
    body = _function_body(SESSIONS_SRC, "async function loadSession(")

    idle_reset = body.find("if(!activeStreamId){")
    assert idle_reset != -1, "loadSession must gate idle cleanup on missing active_stream_id"
    idle_block = body[idle_reset : idle_reset + 500]
    assert "S.busy=false" in idle_block, "idle switch must clear S.busy immediately"
    assert "S.activeStreamId=null" in idle_block, "idle switch must clear S.activeStreamId immediately"

    ensure_load = body.find("await _ensureMessagesLoaded(sid)")
    assert ensure_load != -1, "loadSession must still lazy-load messages for idle sessions"
    assert idle_reset < ensure_load, (
        "S.busy must be cleared before _ensureMessagesLoaded so session-list polling "
        "during the async gap does not mark the new session as locally streaming"
    )
