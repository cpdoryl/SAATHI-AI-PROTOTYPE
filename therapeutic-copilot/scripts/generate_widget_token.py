"""
SAATHI AI — Widget Token Generator
Generates a secure widget_token for a new tenant.

Usage:
  python scripts/generate_widget_token.py --tenant-name "My Clinic"
"""
import secrets
import argparse


def generate_token(prefix: str = "saathi") -> str:
    """Generate a secure 32-character widget token."""
    return f"{prefix}_{secrets.token_urlsafe(24)}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-name", default="My Clinic")
    args = parser.parse_args()

    token = generate_token()
    print(f"Tenant: {args.tenant_name}")
    print(f"Widget Token: {token}")
    print(f"\nEmbed script:")
    print(f'<script src="https://api.saathi-ai.com/api/v1/widget/bundle.js" data-token="{token}"></script>')
