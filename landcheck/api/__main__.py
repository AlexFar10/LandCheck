"""Production entry point: binds 0.0.0.0:${PORT:-3000} (PRD Section 11.4)."""

import uvicorn

from landcheck.api.config import get_settings


def main() -> None:
    uvicorn.run("landcheck.api.main:app", host="0.0.0.0", port=get_settings().port)


if __name__ == "__main__":
    main()
