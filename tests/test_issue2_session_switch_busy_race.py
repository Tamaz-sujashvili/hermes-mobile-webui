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


def test_loadSession_snapshots_live_turn_before_wiping_message_pane():
    body = _function_body(SESSIONS_SRC, "async function loadSession(")

    snap_pos = body.find("snapshotLiveTurnHtmlForSession(currentSid)")
    wipe_pos = body.find('_msgInner.innerHTML=\'<div style="display:flex')
    assert snap_pos != -1, "loadSession must snapshot the outgoing live turn before switching"
    assert wipe_pos != -1, "loadSession must still show the loading placeholder on switch"
    assert snap_pos < wipe_pos, "snapshot must run before msgInner is replaced"


def test_loadSession_restores_live_turn_ui_for_active_stream_paths():
    body = _function_body(SESSIONS_SRC, "async function loadSession(")

    assert "function _restoreActiveStreamLiveUi(" in SESSIONS_SRC
    restore_helper = _function_body(SESSIONS_SRC, "function _restoreActiveStreamLiveUi(")
    assert "restoreLiveTurnHtmlForSession" in restore_helper
    assert "appendThinking()" in restore_helper
    assert body.count("_restoreActiveStreamLiveUi(sid)") >= 2, (
        "both INFLIGHT and active_stream_id load paths must restore live UI"
    )


def test_live_activity_group_seeds_turn_timer_from_pending_started_at():
    ui_src = (REPO / "static" / "ui.js").read_text(encoding="utf-8")
    body = _function_body(ui_src, "function ensureActivityGroup(")
    assert "pending_started_at" in body
    assert 'data-turn-started-at' in body
