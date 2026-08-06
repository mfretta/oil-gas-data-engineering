from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from loguru import logger


def save_bronze_json(
    payload: dict[str, Any],
    root_folder: Path,
    filename_prefix: str,
    ingestion_time: datetime | None = None,
) -> Path:
    """
    Save an API payload as a date-partitioned Bronze JSON file.

    The payload is first written to a temporary file and then
    renamed, which helps prevent incomplete files from being
    treated as successful ingestions.
    """

    if ingestion_time is None:
        ingestion_time = datetime.now(timezone.utc)

    root_folder = Path(root_folder)

    partition_folder = (
        root_folder
        / ingestion_time.strftime("%Y-%m-%d")
    )

    partition_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = ingestion_time.strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = (
        partition_folder
        / f"{filename_prefix}_{timestamp}.json"
    )

    temporary_file = output_file.with_suffix(
        ".json.tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    temporary_file.replace(output_file)

    logger.success(
        "Bronze JSON saved: {}",
        output_file,
    )

    return output_file