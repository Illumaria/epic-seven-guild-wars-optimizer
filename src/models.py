from math import ceil
from typing import Annotated, Any, Callable, Sequence

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
from src.knapsack import backtrack, knapsack, knapsack_backtrack


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

    def max_havoc_per_tokens_invested(self, max_tokens: int) -> list[int]:
        """
        Compute the maximum havoc achievable from one fortress for each
        token budget from 0 to max_tokens.

        Returns a list `result` where `result[t]` = max havoc with `t` tokens.
        """
        dp, _ = self.dp_and_resolve_allocation(max_tokens)
        return dp

    def per_tower_token_allocation(
        self, max_tokens: int
    ) -> Sequence[tuple[Tower, int]]:
        """
        Given a token budget, return per-tower token allocation that maximizes havoc.
        Returns a list of (tower, tokens_allocated) pairs.
        """
        _, bt = self.dp_and_resolve_allocation(max_tokens)
        return bt(max_tokens)

    def generate_new_alloc(
        self,
        alloc_others: list[int],
        cur_defense_tower_index: int,
        cur_defense_tower_tokens_to_destroy: int,
    ) -> list[tuple[Tower, int]]:
        new_alloc: list[tuple[Tower, int]] = []

        for k, _ in enumerate(self.satellites):
            new_alloc.append((self.satellites[k], alloc_others[k]))

        other_dt_cursor = len(self.satellites)
        for i, _ in enumerate(self.defense_towers):
            if i == cur_defense_tower_index:
                new_alloc.append(
                    (self.defense_towers[i], cur_defense_tower_tokens_to_destroy)
                )
            else:
                new_alloc.append(
                    (self.defense_towers[i], alloc_others[other_dt_cursor])
                )
                other_dt_cursor += 1

        stronghold_alloc = alloc_others[
            len(self.satellites) + len(self.defense_towers) - 1
        ]
        new_alloc.append((self.stronghold, stronghold_alloc))

        return new_alloc

    def dp_and_resolve_allocation(
        self, max_tokens: int
    ) -> tuple[list[int], Callable[[int], Sequence[tuple[Tower, int]]]]:
        """
        Compute the per-fortress DP table and a backtracker callable.

        Returns:
            dp: list[int] where dp[t] = max havoc achievable with t tokens.
            backtracker: callable that takes a specific token budget and returns
                per-tower token allocation that maximizes havoc.

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
            dp, choices = knapsack(
                tower_tables=satellite_havoc_matrix
                + defense_tower_havoc_matrix
                + [stronghold_havoc_vector],
                budget=max_tokens,
            )
            towers = self.satellites + self.defense_towers + [self.stronghold]

            def bt_unlocked(tokens: int) -> Sequence[tuple[Tower, int]]:
                return list(zip(towers, backtrack(choices, tokens)))

            return dp, bt_unlocked

        # ── Case 2: Stronghold locked ──
        # We consider two sub-cases:
        #   A) Don't attack the stronghold at all (treat all towers as independent)
        #   B) Unlock the stronghold via defense tower `j`, then attack it
        #
        # For (B), defense tower j must receive at least `tokens_to_destroy(dt_hps[j])`
        # tokens. The remaining tokens are distributed among stronghold + other towers.

        # Sub-case A: skip stronghold entirely
        dp_a, choices_a = knapsack(
            tower_tables=satellite_havoc_matrix + defense_tower_havoc_matrix,
            budget=max_tokens,
        )

        best: list[int] = dp_a
        # best_unlocker[t] = j means Case B with unlocker j was optimal for budget t;
        # -1 means Case A was optimal.
        best_unlocker: list[int] = [-1] * (max_tokens + 1)
        # choices_per_unlocker[j] = (min_j, choices_j) for each valid unlocker j
        choices_per_unlocker: dict[int, tuple[int, list[list[int]]]] = {}

        # Sub-case B: try each defense tower as the stronghold unlocker
        for j, defense_tower in enumerate(self.defense_towers):
            min_j = defense_tower.tokens_to_destroy
            if min_j > max_tokens:
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

            remaining_budget = max_tokens - min_j
            dp_others, choices_j = knapsack(
                tower_tables=other_tables, budget=remaining_budget
            )
            choices_per_unlocker[j] = (min_j, choices_j)

            defense_tower_j_havoc = defense_tower_havoc_matrix[j][
                min_j
            ]  # havoc from destroying defense tower j

            for t in range(min_j, max_tokens + 1):
                val = defense_tower_j_havoc + dp_others[t - min_j]
                if val > best[t]:
                    best[t] = val
                    best_unlocker[t] = j

        def bt_locked(tokens: int) -> Sequence[tuple[Tower, int]]:
            j = best_unlocker[tokens]
            if j == -1:  # Case A: stronghold skipped
                alloc = backtrack(choices_a, tokens)
                return list(zip(self.satellites + self.defense_towers, alloc)) + [
                    (self.stronghold, 0)
                ]
            # Case B: stronghold unlocked via defense tower j
            min_j, choices_j = choices_per_unlocker[j]
            alloc_others = backtrack(choices_j, tokens - min_j)
            return self.generate_new_alloc(
                alloc_others=alloc_others,
                cur_defense_tower_index=j,
                cur_defense_tower_tokens_to_destroy=min_j,
            )

        return best, bt_locked


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

    def allocate_remaining_tokens(
        self,
    ) -> tuple[int, list[Sequence[tuple[Tower, int]]]]:
        """
        Distribute remaining tokens across fortresses to maximize total havoc.

        Returns (max_havoc, per_fortress_token_allocation).
        """
        per_fortress_dp: list[list[int]] = []
        per_fortress_backtrack: list[Callable[[int], Sequence[tuple[Tower, int]]]] = []
        for fortress in self.fortresses:
            dp, bt = fortress.dp_and_resolve_allocation(
                max_tokens=self.tokens_remaining
            )
            per_fortress_dp.append(dp)
            per_fortress_backtrack.append(bt)

        cross_fortress_dp, per_fortress_alloc = knapsack_backtrack(
            tower_tables=per_fortress_dp, budget=self.tokens_remaining
        )

        per_fortress_tower_alloc: list[Sequence[tuple[Tower, int]]] = [
            backtrack_func(tokens)
            for (tokens, backtrack_func) in zip(
                per_fortress_alloc, per_fortress_backtrack
            )
        ]

        return cross_fortress_dp[self.tokens_remaining], per_fortress_tower_alloc

    def format_attack_order(self) -> str:
        """Format the optimal attack order across all fortresses."""
        max_havoc, per_fortress_tower_alloc = self.allocate_remaining_tokens()

        lines: list[str] = []
        for i, tower_alloc in enumerate(per_fortress_tower_alloc):
            lines.append(f"Fortress {i + 1}:")
            if len(tower_alloc) == 0:
                lines.append("    (no attacks)")
                continue
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
