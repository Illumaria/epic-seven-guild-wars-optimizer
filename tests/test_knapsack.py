import pytest

from run_opimizer import Satellite


@pytest.fixture
def satellite() -> Satellite:
    return Satellite(max_hp=200, max_havoc=300, hp=140)


def test_satellite_is_created_correctly(satellite: Satellite) -> None:
    assert satellite.havoc_left_per_token > 0
