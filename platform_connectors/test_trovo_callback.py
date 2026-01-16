import requests

test_url = "https://mistilled-declan-unendable.ngrok-free.dev/callback?code=test"
headers = {"ngrok-skip-browser-warning": "true"}

response = requests.get(test_url, headers=headers)
print(f"Status code: {response.status_code}")
print(f"Response body: {response.text}")
