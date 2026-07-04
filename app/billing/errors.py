"""Billing gateway errors."""


class PaymentGatewayError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class PaymentGatewayConfigError(PaymentGatewayError):
    """Missing or invalid gateway configuration."""
