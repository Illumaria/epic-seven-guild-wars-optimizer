import pytest

from src.knapsack import knapsack, knapsack_backtrack, new_knapsack
from src.models import Tower


@pytest.mark.parametrize(
    ["tower_tables", "budget", "expected_result"],
    [
        [
            [
                [
                    0,
                    120,
                    300,
                ],  # 200 HP
                [
                    0,
                    120,
                    300,
                ],  # 200 HP
            ],
            2,
            [0, 120, 300],
        ],
        [
            [
                [
                    0,
                    120,
                    300,
                ],  # 200 HP
                [
                    0,
                    120 + 250,
                    120 + 250,
                ],  # 120 HP
            ],
            2,
            [
                0,
                120 + 250,
                120 + 120 + 250,
            ],
        ],
    ],
)
def test_knapsack_works_correctly(
    tower_tables: list[list[int]],
    budget: int,
    expected_result: list[int],
) -> None:
    actual_result, _ = knapsack(tower_tables=tower_tables, budget=budget)

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


def test_knapsack_backtrack_with_empty_tower_tables_list() -> None:
    max_tokens: int = 4
    expected_result: tuple[list[int], list[int]] = ([0] * (max_tokens + 1), [])

    actual_result = knapsack_backtrack(tower_tables=[], budget=max_tokens)

    assert actual_result == expected_result
