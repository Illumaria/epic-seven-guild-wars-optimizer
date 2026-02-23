from heapq import merge
from math import ceil
from pathlib import Path
from typing import Annotated, Any

from prettytable import PrettyTable
from pydantic import BaseModel, Field, NonNegativeInt, NonNegativeFloat, PositiveInt, field_validator, ValidationInfo
from yaml import safe_load


HAVOC_PER_WIN: int = 60
MAX_WINS_PER_TOKEN: int = 2
MAX_DMG_PER_TOKEN: int = HAVOC_PER_WIN * MAX_WINS_PER_TOKEN  # 120


def knapsack(tower_tables: list[list[tuple[int, str]]], budget: int) -> list[tuple[int, str]]:
    """
    Knapsack over a set of independent towers.
    Given a list of towers (each with a havoc table indexed by tokens),
    return dp[t] = max havoc using exactly/up-to t tokens across all towers.
    """
    dp = [(0, "")] * (budget + 1)
    for i, table in enumerate(tower_tables):
        new_dp = [(0, "")] * (budget + 1)
        for t in range(budget + 1):
            # Don't allocate any tokens to this tower
            new_dp[t] = dp[t]
            # Allocate k tokens to this tower
            for k in range(1, t + 1):
                val = dp[t - k][0] + table[k][0]
                if val > new_dp[t][0]:
                    new_dp[t] = (val, table[k][1])
        dp = new_dp
    return dp


class Tower(BaseModel):
    separator: Annotated[str, Field(default="", repr=False, exclude=True)]

    max_hp: PositiveInt
    hp: Annotated[NonNegativeInt, Field(default=None)]
    max_havoc: PositiveInt

    wins_to_destroy: Annotated[NonNegativeInt, Field(default=None, init=False)]
    tokens_to_destroy: Annotated[NonNegativeInt, Field(default=None, init=False)]
    havoc_left: Annotated[NonNegativeInt, Field(default=None, init=False)]
    havoc_left_per_token: Annotated[NonNegativeFloat, Field(default=None, init=False)]

    def model_post_init(self, context: Any) -> None:
        if self.hp is None:
            self.hp = self.max_hp
        
        self.wins_to_destroy = ceil(self.hp / HAVOC_PER_WIN)
        self.tokens_to_destroy = ceil(self.wins_to_destroy / MAX_WINS_PER_TOKEN)
        self.havoc_left = self.max_havoc - self.max_hp + self.hp
        self.havoc_left_per_token = self.havoc_left / self.tokens_to_destroy if self.tokens_to_destroy > 0 else 0

    def is_stronghold(self) -> bool:
        return isinstance(self, Stronghold)

    @property
    def row(self) -> list[str]:
        return [
            f"{self.hp}/{self.max_hp}",
            f"{self.havoc_left}/{self.max_havoc}",
            f"{self.wins_to_destroy}/{self.tokens_to_destroy}",
            f"{self.havoc_left_per_token:.1f}"
        ]

    def __str__(self) -> str:
        return f"{self.__class__.__name__} ({self.hp}/{self.max_hp} HP)"
        # return (
        #     f"{self.separator} HP: {self.hp}/{self.max_hp}, "
        #     f"havoc: {self.havoc_left}/{self.max_havoc}, "
        #     f"wins/tokens to destroy: {self.wins_to_destroy}/{self.tokens_to_destroy}, "
        #     f"havoc left per token: {self.havoc_left_per_token:.1f}"
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


class Satellite(Tower):
    max_havoc: Annotated[PositiveInt, Field(default=300)]
    separator: str = "---"


class DefenseTower(Tower):
    max_havoc: Annotated[PositiveInt, Field(default=700)]
    separator: str = "--"


class Stronghold(Tower):
    max_havoc: Annotated[PositiveInt, Field(default=1300)]
    separator: str = "-"


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
        table.field_names = ["HP", "Havoc", "Wins/tokens to destroy", "Havoc left per token"]

        table.add_row(row=self.stronghold.row,divider=True)
        table.add_rows([tower.row for tower in self.defense_towers], divider=True)
        table.add_rows([tower.row for tower in self.satellites], divider=True)

        return table.get_string()

    # @property
    # def attack_targets(self) -> list[Tower]:
    #     sorted_towers = sorted(self.towers, key=lambda x: x.havoc_left_per_token, reverse=True)

    #     stronghold_index = sorted_towers.index(self.stronghold)
    #     defense_towers_indices = [sorted_towers.index(tower) for tower in self.defense_towers]
    #     if not self.is_stronghold_unlocked and stronghold_index < min(defense_towers_indices):
    #         min_defense_towers_index = min(defense_towers_indices)
    #         sorted_towers[min_defense_towers_index], sorted_towers[stronghold_index] = sorted_towers[stronghold_index], sorted_towers[min_defense_towers_index]

    #     return sorted_towers

    @property
    def attack_targets(self) -> list[Tower]:
        towers_copy = self.towers.copy()

        stronghold_index = towers_copy.index(self.stronghold)
        defense_towers_indices = [towers_copy.index(tower) for tower in self.defense_towers]


        if not self.is_stronghold_unlocked and stronghold_index < min(defense_towers_indices):
            min_defense_towers_index = min(defense_towers_indices)
            towers_copy[min_defense_towers_index].havoc_left_per_token = (towers_copy[min_defense_towers_index].havoc_left + towers_copy[stronghold_index].max_havoc) / towers_copy[min_defense_towers_index].tokens_to_destroy

        sorted_towers = sorted(towers_copy, key=lambda x: x.havoc_left_per_token, reverse=True)

        return sorted_towers
    
    def dp(self, max_tokens: int) -> list[tuple[int, str]]:
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
        # ── Precompute per-tower havoc tables ──
        # satellite_havoc_matrix[i][t] = havoc from allocating t tokens to satellite i
        satellite_havoc_matrix: list[list[tuple[int, str]]] = []
        for _, tower in enumerate(self.satellites):
            row = [(tower.havoc(tokens=t), str(tower)) for t in range(max_tokens + 1)]
            satellite_havoc_matrix.append(row)

        # defense_tower_havoc_matrix[i][t] = havoc from allocating t tokens to defense tower i
        defense_tower_havoc_matrix: list[list[tuple[int, str]]] = []
        for _, tower in enumerate(self.defense_towers):
            row = [(tower.havoc(tokens=t), str(tower)) for t in range(max_tokens + 1)]
            defense_tower_havoc_matrix.append(row)

        # stronghold_havoc_vector[t] = havoc from allocating t tokens to stronghold
        stronghold_havoc_vector: list[tuple[int, str]] = [(self.stronghold.havoc(tokens=t), str(self.stronghold)) for t in range(max_tokens + 1)]

        # ── Case 1: Stronghold already unlocked ──
        # All towers are independent; just knapsack over everything.
        if self.is_stronghold_unlocked:
            all_tables = satellite_havoc_matrix + defense_tower_havoc_matrix + [stronghold_havoc_vector]
            dp = knapsack(all_tables, max_tokens)
            return dp

        # ── Case 2: Stronghold locked ──
        # We consider two sub-cases:
        #   A) Don't attack the stronghold at all (treat all towers as independent)
        #   B) Unlock the stronghold via defense tower `j`, then attack it
        #
        # For (B), defense tower j must receive at least `tokens_to_destroy(dt_hps[j])`
        # tokens. The remaining tokens are distributed among stronghold + other towers.

        # Sub-case A: no stronghold, all towers independent
        no_stronghold_tables = satellite_havoc_matrix + defense_tower_havoc_matrix
        dp_no_stronghold = knapsack(tower_tables=no_stronghold_tables, budget=max_tokens)

        best = list(dp_no_stronghold)

        # Sub-case B: for each defense tower as potential unlocker
        for j, defense_tower in enumerate(self.defense_towers):
            min_defense_tower_tokens = defense_tower.tokens_to_destroy
            if min_defense_tower_tokens > max_tokens:
                continue  # can't even destroy this defense tower

            defense_tower_j_havoc = defense_tower_havoc_matrix[j][min_defense_tower_tokens][0]  # havoc from destroying defense tower j

            # Remaining towers: satellites + other defense towers (not j) + stronghold
            other_tables = list(satellite_havoc_matrix)
            for i, _ in enumerate(self.defense_towers):
                if i != j:
                    other_tables.append(defense_tower_havoc_matrix[i])
            other_tables.append(stronghold_havoc_vector)

            remaining_budget = max_tokens - min_defense_tower_tokens
            dp_others = knapsack(tower_tables=other_tables, budget=remaining_budget)

            for t in range(max_tokens + 1):
                if t < min_defense_tower_tokens:
                    continue
                val, name = defense_tower_j_havoc + dp_others[t - min_defense_tower_tokens][0], dp_others[t - min_defense_tower_tokens][1]
                if val > best[t][0]:
                    best[t] = (val, name)

        return best


class Guild(BaseModel):
    name: Annotated[str, Field(default="Guild Name")]
    current_havoc: Annotated[NonNegativeInt, Field(default=0)]
    tokens_remaining: Annotated[NonNegativeInt, Field(default=0)]
    max_stronghold_hp: Annotated[PositiveInt, Field(default=800)]
    max_defense_tower_hp: Annotated[PositiveInt, Field(default=450)]
    max_satellite_hp: Annotated[PositiveInt, Field(default=200)]
    fortresses: Annotated[list[Fortress], Field(min_length=3, max_length=3)]

    @field_validator('fortresses', mode='before')
    def inject_max_hp_into_fortresses(cls, value: list, info: ValidationInfo) -> list:
        # Check if 'value' is a list and 'max_stronghold_hp' is in the input data (info.data)
        if isinstance(value, list):
            for fortress in value:
                if "max_stronghold_hp" in info.data and not fortress.get("stronghold", {}).get("max_hp"):
                    fortress["stronghold"]["max_hp"] = info.data['max_stronghold_hp']
                for defense_tower in fortress["defense_towers"]:
                    if "max_defense_tower_hp" in info.data and not defense_tower.get("max_hp"):
                        defense_tower["max_hp"] = info.data['max_defense_tower_hp']
                for satellite in fortress["satellites"]:
                    if "max_satellite_hp" in info.data and not satellite.get("max_hp"):
                        satellite["max_hp"] = info.data['max_satellite_hp']
        return value

    @property
    def towers(self) -> list[Tower]:
        towers = []
        for fortress in self.fortresses:
            towers.extend(fortress.towers)
        return towers

    @property
    def attack_targets(self) -> list[Tower]:
        # recalculated_havoc_left_per_token: dict[Tower, float] = {}

        # for fortress in self.fortresses:
        #     for tower in fortress.towers:
        #         recalculated_havoc_left_per_token[tower] = tower.havoc_left_per_token
        #     if not fortress.is_stronghold_unlocked:
        all_attack_targets = [fortress.attack_targets for fortress in self.fortresses]
        return list(merge(*all_attack_targets, key=lambda x: x.havoc_left_per_token, reverse=True))
    
    def optimal_allocation(self) -> tuple[tuple[int, str], list[int]]:
        """
        Distribute tokens across fortresses to maximize total havoc.

        Returns (max_havoc, per_fortress_token_allocation).
        """
        # Compute per-fortress DP tables
        fort_dps: list[list[tuple[int, str]]] = []
        for fortress in self.fortresses:
            dp = fortress.dp(max_tokens=self.tokens_remaining)
            fort_dps.append(dp)

        # Cross-fortress knapsack
        dp: list[tuple[int, str]] = [(0, "")] * (self.tokens_remaining + 1)
        # For backtracking allocations
        alloc: list[list[int]] = [[0] * (self.tokens_remaining + 1) for _ in enumerate(self.fortresses)]

        for i, _ in enumerate(self.fortresses):
            new_dp = [(0, "")] * (self.tokens_remaining + 1)
            for t in range(self.tokens_remaining + 1):
                new_dp[t] = dp[t]  # allocate 0 to fortress i
                alloc[i][t] = 0
                for k in range(1, t + 1):
                    val, name = dp[t - k][0] + fort_dps[i][k][0], f"Fortress {i}: {fort_dps[i][k][1]}"
                    if val > new_dp[t][0]:
                        new_dp[t] = (val, name)
                        alloc[i][t] = k
            dp = new_dp

        # Backtrack to find per-fortress allocation
        result_alloc = [0] * len(self.fortresses)
        remaining = self.tokens_remaining
        for i in range(len(self.fortresses) - 1, -1, -1):
            result_alloc[i] = alloc[i][remaining]
            remaining -= result_alloc[i]

        print(f"{dp = }")
        print(f"{alloc = }")
        print(f"Attack order: {[x[1] for x in dp[:self.tokens_remaining]]}")

        return dp[self.tokens_remaining], result_alloc


class Config(BaseModel):
    guild_a: Guild
    guild_b: Guild


def load_config(config_path: Path) -> Config:
    with open(config_path, "r") as f:
        config_yaml = safe_load(f)
        config = Config.model_validate(obj=config_yaml)
    return config


def main() -> None:
    config = load_config(config_path=Path("./config.yaml"))

    print(config.guild_a.optimal_allocation())


if __name__ == "__main__":
    main()
