"""Get previous version to the given one."""

from pathlib import Path

import click
import semver


@click.command()
@click.argument("releases_dir", type=click.Path(exists=True))
@click.argument("current_release_dir", type=click.Path(exists=True))
def get_previous_version(releases_dir: str, current_release_dir: str) -> None:
    """Get previous CCMM release directory to CURRENT_RELEASE_DIR in RELEASES_DIR."""

    def convert_to_version(directory: Path) -> tuple[Path, semver.Version, str]:
        """Convert directory name to version components.

        Returns a list of [Path, semantic_version, date]
        """
        x = directory.name.removeprefix("ccmm-")
        with_optional_date = x.split("-", 1)
        if len(with_optional_date) > 1:
            return (
                directory,
                semver.parse_version_info(with_optional_date[0]),
                with_optional_date[1],
            )
        return (
            directory,
            semver.parse_version_info(with_optional_date[0]),
            "1970-01-01",
        )

    all_versions = [
        convert_to_version(d) for d in Path(releases_dir).iterdir() if d.is_dir() and d.name.startswith("ccmm-")
    ]
    current_version = convert_to_version(Path(current_release_dir))

    # versions look line <semantic>[-<date>], we sort them using semver at first
    # and by date secondarily
    if current_version not in all_versions:
        raise ValueError(f"Current release directory {current_release_dir} not found in releases dir {releases_dir}")
    all_versions.sort(key=lambda x: (x[1], x[2]))

    current_index = all_versions.index(current_version)
    if current_index == 0:
        raise ValueError(
            f"Current release directory {current_release_dir} is the first one, no previous version available"
        )
    previous_version = all_versions[current_index - 1][0]
    click.echo(previous_version.relative_to(releases_dir))


if __name__ == "__main__":
    get_previous_version()
