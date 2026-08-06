import requests
from src.config.config import EIA_API_KEY


class OilPriceAPI:

    BASE_URL = "https://api.eia.gov/v2/"


    def get(self, endpoint, params=None):

        url = self.BASE_URL + endpoint

        default_params = {
            "api_key": EIA_API_KEY,
            "data[0]": "value",
            "frequency": "daily"
        }

        if params:
            default_params.update(params)

        response = requests.get(
            url,
            params=default_params
        )

        response.raise_for_status()

        return response.json()