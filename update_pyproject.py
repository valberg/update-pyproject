"""Script to check if there are updates to the dependencies in the pyproject.toml file."""

import argparse
import json
import tomllib
import urllib.request
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path


@dataclass(kw_only=True)
class Package:
    """Class to represent a package with name, version, and extras."""

    name: str
    version: str | None
    extras: list[str]
    delimiter: str
    latest_version: str | None = field(init=False, default=None)

    @classmethod
    def from_string(cls, string: str) -> "Package":
        """Create a Package object from a string.

        The string can be in the format `package_name[extra1,extra2]==version`.
        """
        # find out what delimiter to use
        possible_delimiters = ("==", ">=", "<=", "~=")

        delimiter: str | None = None

        for possible_delimiter in possible_delimiters:
            if possible_delimiter in string:
                delimiter = possible_delimiter
                break

        if not delimiter:
            delimiter = "=="

        # split the string into package and version delimited by "=="
        package_parts = string.split(delimiter)
        if len(package_parts) > 1:
            package_name, version = package_parts
        else:
            package_name = package_parts[0]
            version = None

        # split the package name into package and extras delimited by "["
        package_name_parts = package_name.split("[")

        extras = []

        if len(package_name_parts) > 1:
            package_name, extras = package_name_parts
            # remove the "]" from the extras
            extras = extras[:-1].split(",")
        return cls(name=package_name, version=version, extras=extras, delimiter=delimiter)

    def get_latest_version(self) -> str:
        """Get the latest version of the package from PyPI."""
        package_path = f"https://pypi.org/pypi/{self.name}/json"
        response = urllib.request.urlopen(package_path)  # noqa: S310
        # turn response into dictionary
        response_dict = json.loads(response.read())
        return response_dict["info"]["version"]

    def has_newer_version(self) -> bool:
        """Check if the package has a newer version available."""
        if not self.version:
            return True
        self.latest_version = self.get_latest_version()
        return self.latest_version != self.version

    def __str__(self) -> str:
        """Return the package string."""
        extras_string = ""
        if self.extras:
            extras_string = f"[{','.join(self.extras)}]"
        return f"{self.name}{extras_string}{self.delimiter}{self.version}"

    def updated_string(self) -> str:
        """Return the package string with the latest version."""
        extras_string = ""
        if self.extras:
            extras_string = f"[{','.join(self.extras)}]"
        return f"{self.name}{extras_string}=={self.latest_version}"


def check_for_updates(*, pyproject_path: Path, update_file: bool = False) -> None:
    """Check if there are updates to the dependencies in the pyproject.toml file."""
    updated = False
    with pyproject_path.open() as pyproject_file:
        pyproject_content = pyproject_file.read()
        pyproject = tomllib.loads(pyproject_content)

        # validate that the pyproject.toml file has the expected structure
        if "project" not in pyproject or "dependencies" not in pyproject["project"]:
            print("Invalid pyproject.toml file.")
            return

        packages = []

        for package_string in pyproject["project"]["dependencies"]:
            package = Package.from_string(package_string)
            packages.append(package)

        for package in packages:
            if package.has_newer_version():
                print(
                    f"Newer version of {package.name} available: "
                    f"{package.latest_version} (currently {package.version})",
                )
                # update the version in the pyproject.toml file
                pyproject_content = pyproject_content.replace(str(package), package.updated_string())
                updated = True

    if updated:
        if update_file:
            print("Updating pyproject.toml file...")
            with pyproject_path.open("w") as pyproject_file:
                pyproject_file.write(pyproject_content)
        else:
            print("Run with --update/-u to update the pyproject.toml file.")
    else:
        print("No updates found.")


def main() -> None:
    """Run the script."""
    parser = argparse.ArgumentParser(
        description="Check for updates to dependencies in pyproject.toml.",
    )

    parser.add_argument(
        "-p",
        "--path",
        type=Path,
        default="pyproject.toml",
        help="Path to the pyproject.toml file.",
    )

    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="Update the pyproject.toml file with the latest versions.",
    )

    args = parser.parse_args()
    check_for_updates(pyproject_path=args.path, update_file=args.update)


if __name__ == "__main__":
    main()
