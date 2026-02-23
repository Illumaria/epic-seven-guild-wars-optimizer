import pytest

from src.knapsack import knapsack


@pytest.mark.parametrize(
    ["tower_tables", "budget", "expected_result"],
    [[
        [
            [(0, "Tower 1"), (120, "Tower 1"), (300, "Tower 1")],
            [(0, "Tower 2"), (120, "Tower 2"), (300, "Tower 2")],
        ],
        2,
        [(0, ""), (120, "Tower 1"), (300, "Tower 1")],
    ]],
)
def test_knapsack_works_correctly(tower_tables: list[list[tuple[int, str]]], budget: int, expected_result: list[tuple[int, str]]) -> None:
    actual_result = knapsack(tower_tables=tower_tables, budget=budget)

    assert actual_result == expected_result
