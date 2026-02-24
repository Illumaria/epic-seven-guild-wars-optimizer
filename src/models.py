from math import ceil
from typing import Annotated, Any

from prettytable import PrettyTable
from pydantic import (
    BaseModel,
    Field,
    NonNegativeInt,
    PositiveInt,
    field_validator,
    ValidationInfo,
)

from src.constants import MAX_DMG_PER_TOKEN
from src.knapsack import backtrack, knapsack_backtrack


class Tower(BaseModel):
    max_hp: PositiveInt
    max_havoc: PositiveInt
    hp: Annotated[NonNegativeInt, Field(default=None)]

    tokens_to_destroy: Annotated[NonNegativeInt, Field(default=None, init=False)]
    havoc_left: Annotated[NonNegativeInt, Field(default=None, init=False)]

    def model_post_init(self, context: Any) -> None:
        if self.hp is None:
            self.hp = self.max_hp

        self.tokens_to_destroy = ceil(self.hp / MAX_DMG_PER_TOKEN)
        self.havoc_left = self.max_havoc - self.max_hp + self.hp

    def is_stronghold(self) -> bool:
        return isinstance(self, Stronghold)

    @property
    def row(self) -> list[str]:
        return [
            f"{self.hp}/{self.max_hp}",
            f"{self.havoc_left}/{self.max_havoc}",
            f"{self.tokens_to_destroy}",
        ]

    def __str__(self) -> str:
        return f"{self.__class__.__name__} ({self.hp}/{self.max_hp} HP)"
        # return (
        #     f"HP: {self.hp}/{self.max_hp}, "
        #     f"havoc: {self.havoc_left}/{self.max_havoc}, "
        #     f"tokens to destroy: {self.tokens_to_destroy}"
        # )

    def __repr__(self) -> str:
        return super().__repr__()

    def havoc(self, tokens: int) -> int:
        """
        Havoc earned from allocating `tokens` tokens to a single tower.
        Assumes all wins.

        - If total damage >= hp: tower destroyed → earn full havoc_left
        - Otherwise: earn damage dealt (tokens * 120), no destruction bonus
        """
        if self.hp <= 0 or self.havoc_left <= 0:
            return 0
        damage = tokens * MAX_DMG_PER_TOKEN
        if damage >= self.hp:
            return self.havoc_left
        return damage  # partial damage, no bonus

    def format_attacks(self, tokens: int) -> list[str]:
        """Format the sequence of attack lines for a single tower."""
        if tokens <= 0 or self.hp <= 0:
            return []

        lines = []
        current_hp = self.hp
        for _ in range(tokens):
            if current_hp <= 0:
                break
            hp_before = current_hp
            current_hp -= MAX_DMG_PER_TOKEN
            if current_hp <= 0:
                lines.append(
                    f"    {self.__class__.__name__} ({hp_before}/{self.max_hp} HP) -> {self.havoc_left} havoc (destroyed)"
                )
            else:
                lines.append(
                    f"    {self.__class__.__name__} ({hp_before}/{self.max_hp} HP) -> {MAX_DMG_PER_TOKEN} havoc"
                )
        return lines


class Satellite(Tower):
    max_havoc: Annotated[PositiveInt, Field(default=300)]


class DefenseTower(Tower):
    max_havoc: Annotated[PositiveInt, Field(default=700)]


class Stronghold(Tower):
    max_havoc: Annotated[PositiveInt, Field(default=1300)]


class Fortress(BaseModel):
    stronghold: Stronghold
    defense_towers: Annotated[list[DefenseTower], Field(min_length=2, max_length=2)]
    satellites: Annotated[list[Satellite], Field(min_length=0, max_length=7)]

    @property
    def is_stronghold_unlocked(self) -> bool:
        return any(tower.hp == 0 for tower in self.defense_towers)

    @property
    def towers(self) -> list[Tower]:
        towers = []
        towers.append(self.stronghold)
        for tower in self.defense_towers:
            towers.append(tower)
        for tower in self.satellites:
            towers.append(tower)
        return towers

    def __str__(self) -> str:
        table = PrettyTable()
        table.field_names = [
            "HP",
            "Havoc",
            "Tokens to destroy",
        ]

        table.add_row(row=self.stronghold.row, divider=True)
        table.add_rows([tower.row for tower in self.defense_towers], divider=True)
        table.add_rows([tower.row for tower in self.satellites], divider=True)

        return table.get_string()

    def dp(self, max_tokens: int) -> list[int]:
        """
        Compute the maximum havoc achievable from one fortress for each
        token budget from 0 to max_tokens.

        Returns a list `result` where `result[t]` = max havoc with `t` tokens.

        Stronghold lock rule: stronghold can only receive tokens if at least
        one defense tower is fully destroyed (enough tokens allocated to it).

        Strategy:
        We enumerate all valid allocation patterns and pick the best.

        For independent towers (satellites + defense towers that are NOT
        being used to unlock the stronghold), we use a knapsack DP.

        For the stronghold unlock path, we try each defense tower as the
        "unlocker" and compute the joint allocation.
        """
        # ── Precompute per-tower havoc matrices ──
        # satellite_havoc_matrix[i][t] = havoc from allocating t tokens to satellite i
        satellite_havoc_matrix: list[list[int]] = [
            [tower.havoc(tokens=t) for t in range(max_tokens + 1)]
            for tower in self.satellites
        ]

        # defense_tower_havoc_matrix[i][t] = havoc from allocating t tokens to defense tower i
        defense_tower_havoc_matrix: list[list[int]] = [
            [tower.havoc(tokens=t) for t in range(max_tokens + 1)]
            for tower in self.defense_towers
        ]

        # stronghold_havoc_vector[t] = havoc from allocating t tokens to stronghold
        stronghold_havoc_vector: list[int] = [
            self.stronghold.havoc(tokens=t) for t in range(max_tokens + 1)
        ]

        # ── Case 1: Stronghold already unlocked ──
        # All towers are independent; just knapsack over everything.
        if self.is_stronghold_unlocked:
            dp, _ = knapsack_backtrack(
                tower_tables=satellite_havoc_matrix
                + defense_tower_havoc_matrix
                + [stronghold_havoc_vector],
                budget=max_tokens,
            )
            return dp

        # ── Case 2: Stronghold locked ──
        # We consider two sub-cases:
        #   A) Don't attack the stronghold at all (treat all towers as independent)
        #   B) Unlock the stronghold via defense tower `j`, then attack it
        #
        # For (B), defense tower j must receive at least `tokens_to_destroy(dt_hps[j])`
        # tokens. The remaining tokens are distributed among stronghold + other towers.

        # Sub-case A: skip stronghold entirely
        dp_no_stronghold, _ = knapsack_backtrack(
            tower_tables=satellite_havoc_matrix + defense_tower_havoc_matrix,
            budget=max_tokens,
        )

        best: list[int] = dp_no_stronghold

        # Sub-case B: try each defense tower as the stronghold unlocker
        for j, defense_tower in enumerate(self.defense_towers):
            min_defense_tower_tokens = defense_tower.tokens_to_destroy
            if min_defense_tower_tokens > max_tokens:
                continue  # can't even destroy this defense tower

            # Remaining towers: satellites + other defense towers (not j) + stronghold
            other_defense_tower_matrix = [
                defense_tower_havoc_matrix[i]
                for i, _ in enumerate(self.defense_towers)
                if i != j
            ]
            other_tables = (
                satellite_havoc_matrix
                + other_defense_tower_matrix
                + [stronghold_havoc_vector]
            )

            remaining_budget = max_tokens - min_defense_tower_tokens
            dp_others, _ = knapsack_backtrack(
                tower_tables=other_tables, budget=remaining_budget
            )

            defense_tower_j_havoc = defense_tower_havoc_matrix[j][
                min_defense_tower_tokens
            ]  # havoc from destroying defense tower j

            for t in range(min_defense_tower_tokens, max_tokens + 1):
                val = defense_tower_j_havoc + dp_others[t - min_defense_tower_tokens]
                if val > best[t]:
                    best[t] = val

        return best

    def resolve_allocation(self, max_tokens: int) -> list[tuple[Tower, int]]:
        """
        Given a token budget, return per-tower token allocation that maximizes havoc.
        Mirrors the logic of dp() but with backtracking to recover the allocation.
        Returns a list of (tower, tokens_allocated) pairs.
        """
        # ── Precompute per-tower havoc matrices ──
        # satellite_havoc_matrix[i][t] = havoc from allocating t tokens to satellite i
        satellite_havoc_matrix: list[list[int]] = [
            [tower.havoc(tokens=t) for t in range(max_tokens + 1)]
            for tower in self.satellites
        ]

        # defense_tower_havoc_matrix[i][t] = havoc from allocating t tokens to defense tower i
        defense_tower_havoc_matrix: list[list[int]] = [
            [tower.havoc(tokens=t) for t in range(max_tokens + 1)]
            for tower in self.defense_towers
        ]

        # stronghold_havoc_vector[t] = havoc from allocating t tokens to stronghold
        stronghold_havoc_vector: list[int] = [
            self.stronghold.havoc(tokens=t) for t in range(max_tokens + 1)
        ]

        # ── Case 1: Stronghold already unlocked ──
        # All towers are independent; just knapsack over everything.
        if self.is_stronghold_unlocked:
            _, alloc = knapsack_backtrack(
                tower_tables=satellite_havoc_matrix
                + defense_tower_havoc_matrix
                + [stronghold_havoc_vector],
                budget=max_tokens,
            )
            return list(
                zip(self.satellites + self.defense_towers + [self.stronghold], alloc)
            )

        # ── Case 2: Stronghold locked ──
        # We consider two sub-cases:
        #   A) Don't attack the stronghold at all (treat all towers as independent)
        #   B) Unlock the stronghold via defense tower `j`, then attack it
        #
        # For (B), defense tower j must receive at least `tokens_to_destroy(dt_hps[j])`
        # tokens. The remaining tokens are distributed among stronghold + other towers.

        # Sub-case A: skip stronghold entirely
        dp_no_stronghold, alloc_no_stronghold = knapsack_backtrack(
            tower_tables=satellite_havoc_matrix + defense_tower_havoc_matrix,
            budget=max_tokens,
        )

        best_val: int = dp_no_stronghold[max_tokens]
        best_alloc: list[tuple[Tower, int]] = list(
            zip(self.satellites + self.defense_towers, alloc_no_stronghold)
        ) + [(self.stronghold, 0)]

        # Sub-case B: try each defense tower as the stronghold unlocker
        for j, defense_tower in enumerate(self.defense_towers):
            min_defense_tower_tokens = defense_tower.tokens_to_destroy
            if min_defense_tower_tokens > max_tokens:
                continue  # can't even destroy this defense tower

            # Remaining towers: satellites + other defense towers (not j) + stronghold
            other_defense_tower_matrix = [
                defense_tower_havoc_matrix[i]
                for i, _ in enumerate(self.defense_towers)
                if i != j
            ]
            other_tables = (
                satellite_havoc_matrix
                + other_defense_tower_matrix
                + [stronghold_havoc_vector]
            )

            remaining_budget = max_tokens - min_defense_tower_tokens
            dp_others, alloc_others = knapsack_backtrack(
                tower_tables=other_tables, budget=remaining_budget
            )

            total_val = (
                defense_tower.havoc(min_defense_tower_tokens)
                + dp_others[remaining_budget]
            )
            if total_val > best_val:
                best_val = total_val
                new_alloc: list[tuple[Tower, int]] = []
                for k, _ in enumerate(self.satellites):
                    new_alloc.append((self.satellites[k], alloc_others[k]))
                other_dt_cursor = len(self.satellites)
                for i, _ in enumerate(self.defense_towers):
                    if i == j:
                        new_alloc.append(
                            (self.defense_towers[i], min_defense_tower_tokens)
                        )
                    else:
                        new_alloc.append(
                            (self.defense_towers[i], alloc_others[other_dt_cursor])
                        )
                        other_dt_cursor += 1
                stronghold_alloc = alloc_others[
                    len(self.satellites) + len(other_defense_tower_matrix)
                ]
                new_alloc.append((self.stronghold, stronghold_alloc))
                best_alloc = new_alloc

        return best_alloc

    def dp_and_resolve_allocation(
        self, max_tokens: int
    ) -> tuple[list[int], list[tuple[Tower, int]]]:
        """
        TODO: combine docstrings from dp() and resolve_allocation() properly.
        Returns:
            dp: a list where `dp[t]` = max havoc with `t` tokens.
            alloc: a list of (tower, tokens_allocated) pairs.
        """
        # ── Precompute per-tower havoc matrices ──
        # satellite_havoc_matrix[i][t] = havoc from allocating t tokens to satellite i
        satellite_havoc_matrix: list[list[int]] = [
            [tower.havoc(tokens=t) for t in range(max_tokens + 1)]
            for tower in self.satellites
        ]

        # defense_tower_havoc_matrix[i][t] = havoc from allocating t tokens to defense tower i
        defense_tower_havoc_matrix: list[list[int]] = [
            [tower.havoc(tokens=t) for t in range(max_tokens + 1)]
            for tower in self.defense_towers
        ]

        # stronghold_havoc_vector[t] = havoc from allocating t tokens to stronghold
        stronghold_havoc_vector: list[int] = [
            self.stronghold.havoc(tokens=t) for t in range(max_tokens + 1)
        ]

        # ── Case 1: Stronghold already unlocked ──
        # All towers are independent; just knapsack over everything.
        if self.is_stronghold_unlocked:
            dp, alloc = knapsack_backtrack(
                tower_tables=satellite_havoc_matrix
                + defense_tower_havoc_matrix
                + [stronghold_havoc_vector],
                budget=max_tokens,
            )
            return dp, list(
                zip(self.satellites + self.defense_towers + [self.stronghold], alloc)
            )

        # ── Case 2: Stronghold locked ──
        # We consider two sub-cases:
        #   A) Don't attack the stronghold at all (treat all towers as independent)
        #   B) Unlock the stronghold via defense tower `j`, then attack it
        #
        # For (B), defense tower j must receive at least `tokens_to_destroy(dt_hps[j])`
        # tokens. The remaining tokens are distributed among stronghold + other towers.

        # Sub-case A: skip stronghold entirely
        dp_no_stronghold, _ = knapsack_backtrack(
            tower_tables=satellite_havoc_matrix + defense_tower_havoc_matrix,
            budget=max_tokens,
        )

        best: list[int] = dp_no_stronghold

        # Sub-case B: try each defense tower as the stronghold unlocker
        for j, defense_tower in enumerate(self.defense_towers):
            min_defense_tower_tokens = defense_tower.tokens_to_destroy
            if min_defense_tower_tokens > max_tokens:
                continue  # can't even destroy this defense tower

            # Remaining towers: satellites + other defense towers (not j) + stronghold
            other_defense_tower_matrix = [
                defense_tower_havoc_matrix[i]
                for i, _ in enumerate(self.defense_towers)
                if i != j
            ]
            other_tables = (
                satellite_havoc_matrix
                + other_defense_tower_matrix
                + [stronghold_havoc_vector]
            )

            remaining_budget = max_tokens - min_defense_tower_tokens
            dp_others, _ = knapsack_backtrack(
                tower_tables=other_tables, budget=remaining_budget
            )

            defense_tower_j_havoc = defense_tower_havoc_matrix[j][
                min_defense_tower_tokens
            ]  # havoc from destroying defense tower j

            for t in range(min_defense_tower_tokens, max_tokens + 1):
                val = defense_tower_j_havoc + dp_others[t - min_defense_tower_tokens]
                if val > best[t]:
                    best[t] = val

        return best


class Guild(BaseModel):
    name: Annotated[str, Field(default="Guild Name")]
    current_havoc: Annotated[NonNegativeInt, Field(default=0)]
    tokens_remaining: Annotated[NonNegativeInt, Field(default=0)]
    max_stronghold_hp: Annotated[PositiveInt, Field(default=800)]
    max_defense_tower_hp: Annotated[PositiveInt, Field(default=450)]
    max_satellite_hp: Annotated[PositiveInt, Field(default=200)]
    fortresses: Annotated[list[Fortress], Field(min_length=3, max_length=3)]

    @field_validator("fortresses", mode="before")
    def inject_max_hp_into_fortresses(cls, value: list, info: ValidationInfo) -> list:
        # Check if 'value' is a list and 'max_stronghold_hp' is in the input data (info.data)
        if isinstance(value, list):
            for fortress in value:
                if "max_stronghold_hp" in info.data and not fortress.get(
                    "stronghold", {}
                ).get("max_hp"):
                    fortress["stronghold"]["max_hp"] = info.data["max_stronghold_hp"]
                for defense_tower in fortress["defense_towers"]:
                    if "max_defense_tower_hp" in info.data and not defense_tower.get(
                        "max_hp"
                    ):
                        defense_tower["max_hp"] = info.data["max_defense_tower_hp"]
                for satellite in fortress["satellites"]:
                    if "max_satellite_hp" in info.data and not satellite.get("max_hp"):
                        satellite["max_hp"] = info.data["max_satellite_hp"]
        return value

    @property
    def towers(self) -> list[Tower]:
        towers = []
        for fortress in self.fortresses:
            towers.extend(fortress.towers)
        return towers

    def allocate_remaining_tokens(self) -> tuple[int, list[int]]:
        """
        Distribute remaining tokens across fortresses to maximize total havoc.

        Returns (max_havoc, per_fortress_token_allocation).
        """
        # Compute per-fortress DP tables
        per_fortress_dp: list[list[int]] = [
            fortress.dp(max_tokens=self.tokens_remaining)
            for fortress in self.fortresses
        ]

        # Compute cross-fortress DP tables
        cross_fortress_dp, cross_fortress_alloc = knapsack_backtrack(
            tower_tables=per_fortress_dp, budget=self.tokens_remaining
        )

        return cross_fortress_dp[self.tokens_remaining], cross_fortress_alloc

    def format_attack_order(self) -> str:
        """Format the optimal attack order across all fortresses."""
        max_havoc, per_fortress_alloc = self.allocate_remaining_tokens()
        lines: list[str] = []
        for i, (fortress, tokens) in enumerate(
            zip(self.fortresses, per_fortress_alloc)
        ):
            lines.append(f"Fortress {i + 1}:")
            if tokens == 0:
                lines.append("    (no attacks)")
                continue
            tower_alloc = fortress.resolve_allocation(tokens)
            # Display: defense towers first, then stronghold, then satellites
            ordered = (
                [(t, n) for t, n in tower_alloc if isinstance(t, DefenseTower)]
                + [(t, n) for t, n in tower_alloc if isinstance(t, Stronghold)]
                + [(t, n) for t, n in tower_alloc if isinstance(t, Satellite)]
            )
            for tower, tower_tokens in ordered:
                lines.extend(tower.format_attacks(tokens=tower_tokens))
        lines.append(f"\nTotal: {self.current_havoc + max_havoc} havoc")
        return "\n".join(lines)


class Config(BaseModel):
    guild_a: Guild
    guild_b: Guild
