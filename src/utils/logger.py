from loguru import logger

logger.add("logs/pipeline.log",
	rotation="10 MB",
	retention="30 days",
	level="INFO")
