import requests


def main():
    # Minimal behavior expected by tests: perform a GET and a POST
    requests.get('https://example.local/test')
    requests.post('https://example.local/test', data={'ok': '1'})


if __name__ == '__main__':
    main()
