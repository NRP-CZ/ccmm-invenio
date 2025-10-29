"""Diff CCMM schemas between two releases."""

import subprocess
import sys
from pathlib import Path

import click


@click.command()
@click.argument("previous_release_dir", type=click.Path(exists=True))
@click.argument("current_release_dir", type=click.Path(exists=True))
@click.argument("diff_name", type=click.Path(), required=True)
def diff_schemas(previous_release_dir: str, current_release_dir: str, diff_name: str) -> None:
    """Diff CCMM schemas between CURRENT_RELEASE_DIR and the previous release in RELEASES_DIR."""
    previous_release_files = {f.name for f in Path(previous_release_dir).glob("*.xsd")}
    current_release_files = {f.name for f in Path(current_release_dir).glob("*.xsd")}

    diff_lines = [
        "<xml>",
        "<!-- Comparing schemas in directories: -->",
    ]

    diff_lines.extend(
        f"<!-- File {filename} is missing in {current_release_dir} -->"
        for filename in previous_release_files - current_release_files
    )

    diff_lines.extend(
        f"<!-- File {filename} is missing in {previous_release_dir} -->"
        for filename in current_release_files - previous_release_files
    )

    for filename in previous_release_files & current_release_files:
        if (Path(previous_release_dir) / filename).read_text() != (Path(current_release_dir) / filename).read_text():
            diff_lines.append(
                f"<!-- Files {filename} differ between {previous_release_dir} and {current_release_dir} -->",
            )
            # get current python interpreter path
            xmldiff_path = Path(sys.executable).parent / "xmldiff"
            data: str | bytes = subprocess.check_output(  # noqa: S603
                [
                    str(xmldiff_path),
                    str(Path(previous_release_dir) / filename),
                    str(Path(current_release_dir) / filename),
                    "--best-match",
                    "--format",
                    "xml",
                    "-p",
                ],
            )
            # print data indented for better readability
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            diff_lines.extend("  " + line for line in data.splitlines())
            diff_lines.append("<!-- End of differences for file -->")
            diff_lines.append("")
    diff_lines.append("</xml>")

    Path(diff_name).write_text("\n".join(diff_lines))


if __name__ == "__main__":
    diff_schemas()
