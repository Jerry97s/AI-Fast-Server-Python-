from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

_LAST_SENT_AT = 0.0
_LAST_SIGNATURE = ""


def _now() -> float:
    return time.time()


def _redact(text: str) -> str:
    # 최소한의 비밀값 마스킹 (키가 로그에 섞여 들어오는 경우 방어)
    if not text:
        return text
    key = os.getenv("OPENAI_API_KEY")
    if key:
        text = text.replace(key, "[REDACTED_OPENAI_API_KEY]")
    return text


def send_slack_error(
    *,
    title: str,
    text: str,
    signature: str = "",
    cooldown_seconds: int | None = None,
) -> bool:
    """
    Slack으로 에러 알림을 보낸다.

    환경 변수:
      - (방식 A) Incoming Webhook
        - SLACK_WEBHOOK_URL
      - (방식 B) Bot token + Channel ID (특정 채널 전송)
        - SLACK_BOT_TOKEN (xoxb-...)
        - SLACK_CHANNEL_ID (예: C0123...)
      - SLACK_NOTIFY_COOLDOWN_SECONDS (기본 60)
    """
    global _LAST_SENT_AT, _LAST_SIGNATURE

    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    bot_token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    channel_id = os.getenv("SLACK_CHANNEL_ID", "").strip()
    if not webhook and not (bot_token and channel_id):
        return False

    cooldown = cooldown_seconds
    if cooldown is None:
        try:
            cooldown = int(os.getenv("SLACK_NOTIFY_COOLDOWN_SECONDS", "60"))
        except Exception:
            cooldown = 60

    sig = signature.strip() or (title + "|" + str(len(text)))
    t = _now()
    if (t - _LAST_SENT_AT) < max(0, cooldown) and sig == _LAST_SIGNATURE:
        return False

    safe_title = _redact(title)[:200]
    safe_text = _redact(text)[:3500]  # 슬랙 메시지 길이 과도 방지

    # 우선순위: Webhook > Bot token
    if webhook:
        payload = {"text": f"*{safe_title}*\n```{safe_text}```"}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                ok = 200 <= getattr(resp, "status", 0) < 300
        except Exception:
            return False
        if not ok:
            return False
    else:
        # chat.postMessage
        payload = {
            "channel": channel_id,
            "text": f"*{safe_title}*\n```{safe_text}```",
            "mrkdwn": True,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {bot_token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                ok = 200 <= getattr(resp, "status", 0) < 300
        except Exception:
            return False
        if not ok:
            return False
        try:
            parsed = json.loads(body)
            if not bool(parsed.get("ok")):
                return False
        except Exception:
            return False

    _LAST_SENT_AT = t
    _LAST_SIGNATURE = sig
    return True
