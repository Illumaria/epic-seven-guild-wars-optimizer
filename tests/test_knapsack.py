import pytest

from src.knapsack import knapsack, knapsack_backtrack


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


def test_knapsack_backtrack_with_empty_tower_tables_list() -> None:
    max_tokens: int = 4
    expected_result: tuple[list[int], list[int]] = ([0] * (max_tokens + 1), [])

    actual_result = knapsack_backtrack(tower_tables=[], budget=max_tokens)

    assert actual_result == expected_result
