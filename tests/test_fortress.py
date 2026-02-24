from src.models import DefenseTower, Fortress, Satellite, Stronghold, Tower


def test_fortress_with_locked_stronghold_per_tower_token_allocation(
    defense_tower_90_hp: DefenseTower,
    defense_tower_330_hp: DefenseTower,
    satellite_80_hp: Satellite,
    satellite_140_hp: Satellite,
    stronghold_800_hp: Stronghold,
) -> None:
    fortress = Fortress(
        stronghold=stronghold_800_hp,
        defense_towers=[
            defense_tower_90_hp,
            defense_tower_330_hp,
        ],
        satellites=[
            satellite_80_hp,
            satellite_140_hp,
        ],
    )

    assert fortress.is_stronghold_unlocked is False

    expected_result: list[tuple[Tower, int]] = [
        (satellite_80_hp, 1),
        (satellite_140_hp, 1),
        (defense_tower_90_hp, 1),
        (defense_tower_330_hp, 0),
        (stronghold_800_hp, 0),
    ]
    actual_result: list[tuple[Tower, int]] = fortress.per_tower_token_allocation(
        max_tokens=3
    )
    assert actual_result == expected_result


def test_fortress_with_unlocked_stronghold_per_tower_token_allocation(
    defense_tower_0_hp: DefenseTower,
    defense_tower_330_hp: DefenseTower,
    satellite_80_hp: Satellite,
    satellite_140_hp: Satellite,
    stronghold_800_hp: Stronghold,
) -> None:
    fortress = Fortress(
        stronghold=stronghold_800_hp,
        defense_towers=[
            defense_tower_0_hp,
            defense_tower_330_hp,
        ],
        satellites=[
            satellite_80_hp,
            satellite_140_hp,
        ],
    )

    assert fortress.is_stronghold_unlocked is True

    expected_result: list[tuple[Tower, int]] = [
        (satellite_80_hp, 0),
        (satellite_140_hp, 0),
        (defense_tower_0_hp, 0),
        (defense_tower_330_hp, 3),
        (stronghold_800_hp, 0),
    ]
    actual_result: list[tuple[Tower, int]] = fortress.per_tower_token_allocation(
        max_tokens=3
    )
    assert actual_result == expected_result
