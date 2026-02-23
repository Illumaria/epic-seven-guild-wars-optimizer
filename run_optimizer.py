from pathlib import Path

from yaml import safe_load

from src.constants import MAX_DMG_PER_TOKEN
from src.models import Config, DefenseTower, Guild, Satellite, Stronghold, Tower


_TOWER_DISPLAY_NAMES: dict[type, str] = {
    DefenseTower: "Defense tower",
    Stronghold: "Stronghold",
    Satellite: "Satellite",
}


def _format_tower_attacks(tower: Tower, tokens: int) -> list[str]:
    """Format the sequence of attack lines for a single tower."""
    if tokens == 0 or tower.hp <= 0:
        return []
    name = _TOWER_DISPLAY_NAMES.get(type(tower), tower.__class__.__name__)
    lines = []
    current_hp = tower.hp
    for _ in range(tokens):
        if current_hp <= 0:
            break
        hp_before = current_hp
        damage = min(MAX_DMG_PER_TOKEN, current_hp)
        current_hp -= damage
        if current_hp <= 0:
            lines.append(f"    {name} ({hp_before}/{tower.max_hp} HP) -> {tower.havoc_left} havoc (destroyed)")
        else:
            lines.append(f"    {name} ({hp_before}/{tower.max_hp} HP) -> {damage} havoc")
    return lines


def format_attack_order(guild: Guild) -> str:
    """Format the optimal attack order across all fortresses."""
    (max_havoc, _), per_fortress_alloc = guild.optimal_allocation()
    lines: list[str] = []
    for i, (fortress, tokens) in enumerate(zip(guild.fortresses, per_fortress_alloc)):
        lines.append(f"Fortress {i + 1}:")
        if tokens == 0:
            lines.append("    (no attacks)")
            continue
        tower_alloc = fortress.resolve_allocation(tokens)
        # Display: defense towers first, then stronghold, then satellites
        ordered = (
            [(t, n) for t, n in tower_alloc if isinstance(t, DefenseTower)] +
            [(t, n) for t, n in tower_alloc if isinstance(t, Stronghold)] +
            [(t, n) for t, n in tower_alloc if isinstance(t, Satellite)]
        )
        for tower, tower_tokens in ordered:
            lines.extend(_format_tower_attacks(tower, tower_tokens))
    lines.append(f"\nTotal: {max_havoc} havoc")
    return "\n".join(lines)


def load_config(config_path: Path) -> Config:
    with open(config_path, "r") as f:
        config_yaml = safe_load(f)
        config = Config.model_validate(obj=config_yaml)
    return config


def main() -> None:
    config = load_config(config_path=Path("./config.yaml"))

    print(format_attack_order(config.guild_a))


if __name__ == "__main__":
    main()
