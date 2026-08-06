from datetime import datetime, timezone
from pathlib import Path
import shutil

from loguru import logger

from src.config.config import RAW_RIG_COUNT_FOLDER


SOURCE_FOLDER = (
    RAW_RIG_COUNT_FOLDER
    / "manual"
)

BRONZE_FOLDER = (
    RAW_RIG_COUNT_FOLDER
    / "bronze"
)


class RigCountExtractor:
    """
    Ingest a manually downloaded Baker Hughes workbook
    into the Bronze data layer.
    """

    SUPPORTED_EXTENSIONS = {
        ".xlsx",
        ".xls",
        ".csv",
    }

    def get_latest_source_file(self) -> Path:
        if not SOURCE_FOLDER.exists():
            raise FileNotFoundError(
                f"Source folder not found: "
                f"{SOURCE_FOLDER.resolve()}"
            )

        files = [
            file
            for file in SOURCE_FOLDER.iterdir()
            if (
                file.is_file()
                and file.suffix.lower()
                in self.SUPPORTED_EXTENSIONS
            )
        ]

        if not files:
            raise FileNotFoundError(
                "No rig-count Excel or CSV files found in "
                f"{SOURCE_FOLDER.resolve()}"
            )

        return max(
            files,
            key=lambda file: file.stat().st_mtime,
        )

    def save_bronze_copy(
        self,
        source_file: Path,
    ) -> Path:
        ingestion_time = datetime.now(
            timezone.utc
        )

        partition_folder = (
            BRONZE_FOLDER
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
            / (
                f"baker_hughes_rig_count_"
                f"{timestamp}"
                f"{source_file.suffix.lower()}"
            )
        )

        shutil.copy2(
            source_file,
            output_file,
        )

        logger.success(
            "Rig-count Bronze file saved: {}",
            output_file,
        )

        return output_file

    def execute(self) -> Path:
        logger.info(
            "Starting Baker Hughes rig-count ingestion"
        )

        source_file = (
            self.get_latest_source_file()
        )

        logger.info(
            "Selected source file: {}",
            source_file,
        )

        return self.save_bronze_copy(
            source_file
        )


def main() -> None:
    extractor = RigCountExtractor()
    extractor.execute()


if __name__ == "__main__":
    main()