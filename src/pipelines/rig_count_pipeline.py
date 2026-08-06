from loguru import logger

from src.extract.extract_rig_count import (
    RigCountExtractor,
)
from src.transform.transform_rig_count import (
    RigCountTransformer,
)
from src.warehouse.rig_pipeline import (
    run_rig_warehouse_pipeline,
)


def run_rig_count_pipeline() -> None:
    logger.info(
        "Starting complete Baker Hughes rig-count pipeline"
    )

    extractor = RigCountExtractor()
    extractor.execute()

    transformer = RigCountTransformer()
    transformer.execute()

    run_rig_warehouse_pipeline()

    logger.success(
        "Complete Baker Hughes rig-count pipeline finished"
    )


def main() -> None:
    run_rig_count_pipeline()


if __name__ == "__main__":
    main()