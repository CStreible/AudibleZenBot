import requests
from core.logger import get_logger
try:
	from core.http_session import make_retry_session
except Exception:
	make_retry_session = None

logger = get_logger(__name__)


def main():
	test_url = "https://mistilled-declan-unendable.ngrok-free.dev/callback?code=test"
	headers = {"ngrok-skip-browser-warning": "true"}

	session = make_retry_session() if make_retry_session else requests.Session()
	try:
		response = session.get(test_url, headers=headers, timeout=10)
		logger.info(f"Status code: {response.status_code}")
		logger.debug(f"Response body: {response.text}")
	except requests.exceptions.RequestException as e:
		logger.exception(f"Network error hitting test URL: {e}")


if __name__ == '__main__':
	main()
