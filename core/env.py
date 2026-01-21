"""Environment helpers for AudibleZenBot.

Provide a small centralized API to determine whether the process is
running in CI/test mode or production. This helps keep environment
checks consistent across the codebase and makes switching modes
simpler.
"""
import os


def is_ci() -> bool:
    """Return True when running in CI/test mode via legacy env var."""
    return os.environ.get('AUDIBLEZENBOT_CI', '') == '1'


def env() -> str:
    """Return the explicit environment string if provided.

    Recognized values: 'test', 'production'.
    """
    return os.environ.get('AUDIBLEZENBOT_ENV', '').lower()


def is_test() -> bool:
    """Return True when running tests or when explicit test env requested."""
    return is_ci() or env() == 'test'


def is_production() -> bool:
    """Return True when running in production mode (default)."""
    return not is_test()
