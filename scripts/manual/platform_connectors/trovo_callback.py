import requests


def make_retry_session():
    # Minimal helper: return a requests-like session
    return requests.Session()


def main():
    # Acquire a session (tests patch make_retry_session to return a fake)
    sess = make_retry_session()
    sess.get('https://example.local/trovo_callback')


if __name__ == '__main__':
    main()
