from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Tower


def knapsack(tower_tables: list[list[int]], budget: int) -> list[int]:
    """
    Knapsack over a set of independent towers.
    Given a list of towers (each with a havoc table indexed by invested tokens),
    return dp[t] = max havoc using exactly/up-to t tokens across all towers.
    """
    dp = [0] * (budget + 1)
    for table in tower_tables:
        new_dp = [0] * (budget + 1)
        for t in range(budget + 1):
            # Don't allocate any tokens to this tower
            new_dp[t] = dp[t]
            # Allocate k tokens to this tower
            for k in range(1, t + 1):
                val = dp[t - k] + table[k]
                if val > new_dp[t]:
                    new_dp[t] = val
        dp = new_dp
    return dp


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


def knapsack_backtrack(
    tower_tables: list[list[tuple[int, str]]], budget: int
) -> tuple[list[tuple[int, str]], list[int]]:
    """
    Same as knapsack but also returns per-tower token allocation via backtracking.
    Returns (dp_table, per_tower_token_counts).
    """
    n = len(tower_tables)
    if n == 0:
        return [(0, "")] * (budget + 1), []

    dp = [(0, "")] * (budget + 1)
    choices = [[0] * (budget + 1) for _ in range(n)]

    for i, table in enumerate(tower_tables):
        new_dp = [(0, "")] * (budget + 1)
        for t in range(budget + 1):
            new_dp[t] = dp[t]
            choices[i][t] = 0
            for k in range(1, t + 1):
                val = dp[t - k][0] + table[k][0]
                if val > new_dp[t][0]:
                    new_dp[t] = (val, table[k][1])
                    choices[i][t] = k
        dp = new_dp

    alloc = [0] * n
    remaining = budget
    for i in range(n - 1, -1, -1):
        alloc[i] = choices[i][remaining]
        remaining -= alloc[i]

    return dp, alloc
