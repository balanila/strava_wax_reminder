from __future__ import annotations

from app.config import Config


def main() -> None:
    config = Config.from_env()
    config.state_path.parent.mkdir(parents=True, exist_ok=True)
    if not config.state_path.parent.exists():
        raise SystemExit(1)


if __name__ == "__main__":
    main()

