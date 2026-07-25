"""Generate a VAPID keypair for Web Push.

Run once, then paste the printed values into backend/.env:

    python -m backend.scripts.generate_vapid_keys

The private key stays on the server; the public key is what the browser uses as
its ``applicationServerKey`` when subscribing (the app exposes it via
GET /api/push/vapid-public-key). Both are raw EC P-256 keys, base64url-encoded —
the format pywebpush and the browser PushManager expect.
"""
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_keypair() -> tuple[str, str]:
    """Return (private_key_b64url, public_key_b64url) for a fresh P-256 key."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_scalar = private_key.private_numbers().private_value.to_bytes(32, "big")
    public_point = private_key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    return _b64url(private_scalar), _b64url(public_point)


def main() -> None:
    private_key, public_key = generate_keypair()
    print("# Add these to backend/.env (keep the private key secret):")
    print(f"VAPID_PRIVATE_KEY={private_key}")
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print("VAPID_SUBJECT=mailto:you@example.com")


if __name__ == "__main__":
    main()
