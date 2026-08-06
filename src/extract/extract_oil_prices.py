from loguru import logger

from src.api.oil_price_api import OilPriceAPI
from src.utils.file_manager import save_json
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")

class OilPriceExtractor:

    def __init__(self):
        self.api = OilPriceAPI()


    def execute(self):

        logger.info("Starting Oil Price Extraction")

        data = self.api.get(
            endpoint="petroleum/pri/spt/data/"
        )

        save_json(
            data,
            f"data/raw//oil_prices/oil_prices_{today}.json"
        )

        logger.success(
            "Oil Price Extraction completed"
        )


def main():

    extractor = OilPriceExtractor()
    extractor.execute()


if __name__ == "__main__":
    main()