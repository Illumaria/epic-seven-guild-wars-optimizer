from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Tower


def new_knapsack(
    towers: list[Tower], max_tokens: int
) -> list[tuple[int, Tower | None]]:
    """
    Knapsack over a set of independent towers.
    Given a list of towers, return a list of towers ordered to attack
    for maximum havoc earn.
    """
    dp: list[tuple[int, Tower | None]] = [(0, None) for _ in range(max_tokens + 1)]
    for tower in towers:
        new_dp: list[tuple[int, Tower | None]] = [
            (0, None) for _ in range(max_tokens + 1)
        ]
        table = [tower.havoc(tokens=t) for t in range(max_tokens + 1)]
        for t in range(max_tokens + 1):
            # Don't allocate any tokens to this tower
            new_dp[t] = dp[t]
            # Allocate k tokens to this tower
            for k in range(1, t + 1):
                val = dp[t - k][0] + table[k]
                if val > new_dp[t][0]:
                    new_dp[t] = (val, tower)
        dp = new_dp
    return dp


def backtrack(choices: list[list[int]], budget: int) -> list[int]:
    alloc: list[int] = [0] * len(choices)
    remaining: int = budget
    for i in range(len(choices) - 1, -1, -1):
        alloc[i] = choices[i][remaining]
        remaining -= alloc[i]
    return alloc


def knapsack_backtrack(
    tower_tables: list[list[int]], budget: int
) -> tuple[list[int], list[int]]:
    """
    Knapsack over a set of independent towers with
    per-tower token allocation via backtracking.

    Given a list of towers (each as a havoc table indexed by tokens invested),
    returns (dp_vector, per_tower_token_counts_matrix),
    where dp_vector[t] = max havoc using exactly/up-to t tokens across all towers.
    """
    dp: list[int] = [0] * (budget + 1)
    choices: list[list[int]] = [[0] * (budget + 1) for _ in enumerate(tower_tables)]

    for i, table in enumerate(tower_tables):
        new_dp: list[int] = [0] * (budget + 1)
        for t in range(budget + 1):
            # Don't allocate any tokens to this tower
            new_dp[t] = dp[t]
            choices[i][t] = 0
            # Allocate k tokens to this tower
            for k in range(1, t + 1):
                val = dp[t - k] + table[k]
                if val > new_dp[t]:
                    new_dp[t] = val
                    choices[i][t] = k
        dp = new_dp

    alloc: list[int] = backtrack(choices=choices, budget=budget)

    return dp, alloc
