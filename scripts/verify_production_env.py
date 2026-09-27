from __future__ import annotations

import os
import sys
from urllib.parse import urlparse


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing")
    return value


def main() -> int:
    try:
        required("DATABASE_URL")
        required("BOB_API_KEY")
        bob_base = required("BOB_BASE_URL")
        bob_endpoint = required("BOB_ENDPOINT")
        required("OPENAI_API_KEY")

        if os.getenv("DEV_MODE", "").strip().lower() != "false":
            raise ValueError("DEV_MODE must be false")
        if os.getenv("MOCK_BOB", "").strip().lower() != "false":
            raise ValueError("MOCK_BOB must be false")
        if os.getenv("LOCAL_EMBEDDINGS", "").strip().lower() != "false":
            raise ValueError("LOCAL_EMBEDDINGS must be false")
        if os.getenv("BOB_LOG_EXCHANGES", "false").strip().lower() != "false":
            raise ValueError("BOB_LOG_EXCHANGES must be false")

        cors = [item.strip() for item in os.getenv("CORS_ORIGINS", "").split(",") if item.strip()]
        if not cors or "*" in cors:
            raise ValueError("CORS_ORIGINS must contain explicit origins")
        for origin in cors:
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                raise ValueError("CORS_ORIGINS contains an invalid origin")

        parsed_bob = urlparse(bob_base)
        if parsed_bob.scheme != "https" or not parsed_bob.netloc or parsed_bob.query or parsed_bob.fragment:
            raise ValueError("BOB_BASE_URL must be HTTPS and contain no query or fragment")
        if not bob_endpoint.startswith("/"):
            raise ValueError("BOB_ENDPOINT must start with '/'")

        private_enabled = os.getenv("ALLOW_PRIVATE_REPOS", "false").strip().lower() == "true"
        if private_enabled and not os.getenv("GITHUB_TOKEN", "").strip():
            raise ValueError("GITHUB_TOKEN is required when ALLOW_PRIVATE_REPOS=true")
        if not private_enabled:
            # The token is allowed to exist in the deployment secret store but is
            # deliberately ignored by the application while this switch is false.
            print("Private repository access: disabled")
        else:
            print("Private repository access: enabled")
    except ValueError as exc:
        print(f"Production environment check FAILED: {exc}", file=sys.stderr)
        return 1

    print("Production environment contract PASS (secret values were not displayed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
