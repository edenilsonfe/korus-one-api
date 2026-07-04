"""Shared HTTP helpers for payment gateways."""

from typing import Any

import httpx

from app.billing.errors import PaymentGatewayError


async def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, url, headers=headers, json=json_body)

    if response.status_code >= 400:
        detail = response.text[:500] if response.text else response.reason_phrase
        raise PaymentGatewayError(
            f"Gateway HTTP {response.status_code}: {detail}",
            status_code=response.status_code,
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise PaymentGatewayError("Gateway returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise PaymentGatewayError("Gateway returned unexpected payload shape")
    return data
