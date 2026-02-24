import pytest

from src.models import DefenseTower, Satellite, Stronghold


@pytest.fixture
def satellite_80_hp() -> Satellite:
    return Satellite(max_hp=200, hp=80)


@pytest.fixture
def satellite_140_hp() -> Satellite:
    return Satellite(max_hp=200, hp=140)


@pytest.fixture
def defense_tower_330_hp() -> DefenseTower:
    return DefenseTower(max_hp=450, hp=330)


@pytest.fixture
def defense_tower_210_hp() -> DefenseTower:
    return DefenseTower(max_hp=450, hp=210)


@pytest.fixture
def defense_tower_90_hp() -> DefenseTower:
    return DefenseTower(max_hp=450, hp=90)


@pytest.fixture
def defense_tower_0_hp() -> DefenseTower:
    return DefenseTower(max_hp=450, hp=0)


@pytest.fixture
def stronghold_800_hp() -> Stronghold:
    return Stronghold(max_hp=800, hp=800)


@pytest.fixture
def stronghold_680_hp() -> Stronghold:
    return Stronghold(max_hp=800, hp=680)


@pytest.fixture
def stronghold_80_hp() -> Stronghold:
    return Stronghold(max_hp=800, hp=80)
