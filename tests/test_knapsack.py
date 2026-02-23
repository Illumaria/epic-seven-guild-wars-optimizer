import pytest

from src.knapsack import knapsack, new_knapsack
from src.models import Tower


@pytest.mark.parametrize(
    ["tower_tables", "budget", "expected_result"],
    [
        [
            [
                [
                    (0, "Satellite 1"),
                    (120, "Satellite 1"),
                    (300, "Satellite 1"),
                ],  # 200 HP
                [
                    (0, "Satellite 2"),
                    (120, "Satellite 2"),
                    (300, "Satellite 2"),
                ],  # 200 HP
            ],
            2,
            [(0, ""), (120, "Satellite 1"), (300, "Satellite 1")],
        ],
        [
            [
                [
                    (0, "Satellite 1"),
                    (120, "Satellite 1"),
                    (300, "Satellite 1"),
                ],  # 200 HP
                [
                    (0, "DefenseTower 2"),
                    (120 + 250, "DefenseTower 2"),
                    (120 + 250, "DefenseTower 2"),
                ],  # 120 HP
            ],
            2,
            [
                (0, ""),
                (120 + 250, "DefenseTower 2"),
                (120 + 120 + 250, "DefenseTower 2"),
            ],
        ],
    ],
)
def test_knapsack_works_correctly(
    tower_tables: list[list[tuple[int, str]]],
    budget: int,
    expected_result: list[tuple[int, str]],
) -> None:
    actual_result = knapsack(tower_tables=tower_tables, budget=budget)

    assert actual_result == expected_result


@pytest.mark.parametrize(
    ["towers", "max_tokens", "expected_result"],
    [
        [
            [Tower(max_havoc=300, max_hp=200), Tower(max_havoc=300, max_hp=200)],
            2,
            [
                (0, None),
                (120, Tower(max_havoc=300, max_hp=200)),
                (300, Tower(max_havoc=300, max_hp=200)),
            ],
        ],
        [
            [
                Tower(max_havoc=300, max_hp=200),
                Tower(max_havoc=700, max_hp=450, hp=120),
            ],
            2,
            [
                (0, None),
                (120 + 250, Tower(max_havoc=700, max_hp=450, hp=120)),
                (120 + 120 + 250, Tower(max_havoc=700, max_hp=450, hp=120)),
            ],
        ],
    ],
)
def test_new_knapsack_works_correctly(
    towers: list[Tower],
    max_tokens: int,
    expected_result: list[tuple[int, Tower | None]],
) -> None:
    actual_result = new_knapsack(towers=towers, max_tokens=max_tokens)

    assert actual_result == expected_result
