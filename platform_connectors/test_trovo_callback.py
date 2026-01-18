import requests
from core.logger import get_logger

logger = get_logger(__name__)

test_url = "https://mistilled-declan-unendable.ngrok-free.dev/callback?code=test"
headers = {"ngrok-skip-browser-warning": "true"}

response = requests.get(test_url, headers=headers)
logger.info(f"Status code: {response.status_code}")
logger.debug(f"Response body: {response.text}")
