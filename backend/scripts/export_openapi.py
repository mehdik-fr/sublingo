import json
import sys
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
REPOSITORY_DIRECTORY = BACKEND_DIRECTORY.parent
OUTPUT_PATH = REPOSITORY_DIRECTORY / "contracts" / "openapi.json"

sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.main import app  # noqa: E402


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Exported OpenAPI contract to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
