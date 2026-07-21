"""Client IP derivation from X-Forwarded-For (trusted proxy hops, not leftmost)."""

from types import SimpleNamespace

from app.core.client_ip import get_client_ip


def _request(*, host: str | None = "10.0.0.1", xff: str | None = None):
    headers = {}
    if xff is not None:
        headers["x-forwarded-for"] = xff
    client = SimpleNamespace(host=host) if host is not None else None
    return SimpleNamespace(headers=headers, client=client)


def test_no_xff_returns_peer_host():
    req = _request(host="10.0.0.1", xff=None)
    assert get_client_ip(req, trusted_proxy_count=1) == "10.0.0.1"


def test_no_xff_and_no_peer_returns_default():
    req = _request(host=None, xff=None)
    assert get_client_ip(req, trusted_proxy_count=1) == "unknown"
    assert get_client_ip(req, trusted_proxy_count=1, default="127.0.0.1") == "127.0.0.1"


def test_xff_two_hops_n1_picks_left_of_last_not_blind_leftmost_of_longer_chain():
    # client=203.0.113.10, immediate proxy=198.51.100.1
    req = _request(host="198.51.100.1", xff="203.0.113.10, 198.51.100.1")
    assert get_client_ip(req, trusted_proxy_count=1) == "203.0.113.10"

    # Forged leftmost must not win when there are enough hops for N=1:
    # hops = [evil, real-client, proxy] → index len-1-1 = real-client
    req_spoof = _request(
        host="192.0.2.60",
        xff="203.0.113.10, 198.51.100.1, 192.0.2.60",
    )
    assert get_client_ip(req_spoof, trusted_proxy_count=1) == "198.51.100.1"
    assert get_client_ip(req_spoof, trusted_proxy_count=1) != "203.0.113.10"


def test_single_forged_xff_hop_falls_back_to_peer():
    # N=1 needs a hop left of the last; a lone XFF value is not enough → peer.
    req = _request(host="198.51.100.1", xff="203.0.113.10")
    assert get_client_ip(req, trusted_proxy_count=1) == "198.51.100.1"


def test_invalid_xff_hop_falls_back_to_peer():
    req = _request(host="198.51.100.1", xff="not-an-ip, 198.51.100.1")
    assert get_client_ip(req, trusted_proxy_count=1) == "198.51.100.1"


def test_ipv6_client_hop():
    req = _request(
        host="198.51.100.1",
        xff="2001:db8::1, 198.51.100.1",
    )
    assert get_client_ip(req, trusted_proxy_count=1) == "2001:db8::1"
