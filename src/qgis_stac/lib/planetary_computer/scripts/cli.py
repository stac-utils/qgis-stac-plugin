from pathlib import Path
import click


@click.group(help="Microsoft Planetary Computer CLI")
def app() -> None:
    """Click group for planetarycomputer subcommands"""
    pass


@app.command()
@click.option(
    "--subscription_key",
    prompt="Please enter your API subscription key",
    help="Your API subscription key",
)
def configure(subscription_key: str) -> None:
    """Configure the planetarycomputer library"""
    settings_dir = Path("~/.planetarycomputer").expanduser()
    settings_dir.mkdir(exist_ok=True)
    with (settings_dir / "settings.env").open(mode="w") as settings_file:
        settings_file.write(f"PC_SDK_SUBSCRIPTION_KEY={subscription_key}\n")
