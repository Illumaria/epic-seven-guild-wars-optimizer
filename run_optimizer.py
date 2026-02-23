from pathlib import Path

from yaml import safe_load

from src.models import Config, DefenseTower, Guild, Satellite, Stronghold


def load_config(config_path: Path) -> Config:
    with open(config_path, "r") as f:
        config_yaml = safe_load(f)
        config = Config.model_validate(obj=config_yaml)
    return config


def main() -> None:
    config = load_config(config_path=Path("./config.yaml"))

    print(config.guild_a.format_attack_order())


if __name__ == "__main__":
    main()
