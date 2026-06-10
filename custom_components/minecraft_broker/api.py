"""Client for the Minecraft control broker.

Builds the broker's required envelope — bearer token + HMAC-SHA256 signature over a
timestamp + nonce + body hash — using only the standard library, then POSTs over the
Home Assistant aiohttp session. The signing helpers are deliberately dependency-free
so they can be unit-tested offline against the broker's own verifier
(broker/shared/auth.py). See docs/automation/API.md for the contract.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any
from urllib.parse import urlsplit


class BrokerError(Exception):
    """Base error for broker calls."""


class BrokerConnectionError(BrokerError):
    """Network/transport failure reaching the broker."""


class BrokerAuthError(BrokerError):
    """Broker rejected our credentials/signature (HTTP 401)."""


class BrokerValidationError(BrokerError):
    """Broker rejected the request payload (HTTP 400)."""


class BrokerRateLimitError(BrokerError):
    """Broker rate limit hit (HTTP 429)."""


def build_signed_request(
    url: str,
    action: str,
    instance: str | None,
    bearer_token: str,
    hmac_key: str,
    now: float | None = None,
) -> tuple[bytes, dict[str, str]]:
    """Return ``(body_bytes, headers)`` for a signed broker request.

    Pure standard library; safe to call from a worker thread.
    """
    body_obj: dict[str, Any] = {"action": action, "request_id": str(uuid.uuid4())}
    if instance:
        body_obj["instance"] = instance
    body = json.dumps(body_obj, separators=(",", ":")).encode("utf-8")

    ts = str(int(time.time() if now is None else now))
    nonce = str(uuid.uuid4())
    path = urlsplit(url).path or "/api/control"
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join(["POST", path, ts, nonce, body_hash])
    signature = hmac.new(
        hmac_key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }
    return body, headers


class BrokerClient:
    """Async wrapper that signs and sends control requests."""

    def __init__(
        self,
        session: Any,
        url: str,
        bearer_token: str,
        hmac_key: str,
        timeout: float = 120.0,
    ) -> None:
        self._session = session
        self._url = url
        self._bearer_token = bearer_token
        self._hmac_key = hmac_key
        self._timeout = timeout

    async def async_call(self, action: str, instance: str | None = None) -> dict:
        """Sign and POST a control request; return the parsed JSON response.

        Raises a :class:`BrokerError` subclass on auth/validation/rate-limit/transport
        failure.
        """
        # Imported lazily so the signing helpers above stay dependency-free.
        import aiohttp

        body, headers = build_signed_request(
            self._url, action, instance, self._bearer_token, self._hmac_key
        )

        try:
            async with self._session.post(
                self._url,
                data=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as resp:
                text = await resp.text()
                status = resp.status
        except aiohttp.ClientError as err:
            raise BrokerConnectionError(str(err)) from err
        except TimeoutError as err:
            raise BrokerConnectionError("broker request timed out") from err

        if status == 200:
            try:
                return json.loads(text)
            except json.JSONDecodeError as err:
                raise BrokerError(f"broker returned non-JSON 200: {text[:200]}") from err

        message = _extract_message(text)
        if status == 401:
            raise BrokerAuthError(message)
        if status == 400:
            raise BrokerValidationError(message)
        if status == 429:
            raise BrokerRateLimitError(message)
        raise BrokerError(f"broker error {status}: {message}")


def _extract_message(text: str) -> str:
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("message"):
            return str(data["message"])
    except json.JSONDecodeError:
        pass
    return text[:200] or "unknown broker error"
