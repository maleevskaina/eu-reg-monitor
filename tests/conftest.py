from pathlib import Path

import pytest

from regmon.config import load_rules, load_sources

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def sources():
    return load_sources()


@pytest.fixture
def rules():
    return load_rules()
