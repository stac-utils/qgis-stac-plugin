# -*- coding: utf-8 -*-
""" QGIS STAC plugin admin operations

"""

import os

import configparser
import datetime as dt
import re
import shlex
import shutil
import subprocess
import typing
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx
import toml
import typer

LOCAL_ROOT_DIR = Path(__file__).parent.resolve()
SRC_NAME = "qgis_stac"
PACKAGE_NAME = SRC_NAME.replace("_", "")
TEST_FILES = [
    "test",
    "test_suite.py",
    "docker-compose.yml",
    "scripts"
]
app = typer.Typer()


@dataclass
class GithubRelease:
    """
    Class for defining plugin releases details.
    """
    pre_release: bool
    tag_name: str
    url: str
    published_at: dt.datetime


@app.callback()
def main(
        context: typer.Context,
        verbose: bool = False,
        qgis_profile: str = "default"):
    """Performs various development-oriented tasks for this plugin

    :param context: Application context
    :type context: typer.Context

    :param verbose: Boolean value to whether more details should be displayed
    :type verbose: bool

    :param qgis_profile: QGIS user profile to be used when operating in
            QGIS application
    :type qgis_profile: str

    """
    context.obj = {
        "verbose": verbose,
        "qgis_profile": qgis_profile,
    }


@app.command()
def install(
        context: typer.Context,
        build_src: bool = True
):
    """Deploys plugin to QGIS plugins directory

    :param context: Application context
    :type context: typer.Context

    :param build_src: Whether to build plugin files from source
    :type build_src: bool
    """
    _log("Uninstalling...", context=context)
    uninstall(context)
    _log("Building...", context=context)

    built_directory = build(context, clean=True) \
        if build_src else LOCAL_ROOT_DIR / "build" / SRC_NAME

    root_directory = Path.home() / \
                     f".local/share/QGIS/QGIS3/profiles/" \
                     f"{context.obj['qgis_profile']}"

    base_target_directory = root_directory / "python/plugins" / SRC_NAME
    _log(f"Copying built plugin to {base_target_directory}...", context=context)
    shutil.copytree(built_directory, base_target_directory)
    _log(
        f"Installed {str(built_directory)!r}"
        f" into {str(base_target_directory)!r}",
        context=context)


@app.command()
def symlink(
        context: typer.Context
):
    """Create a plugin symlink to QGIS plugins directory

    :param context: Application context
    :type context: typer.Context
    """

    build_path = LOCAL_ROOT_DIR / "build" / SRC_NAME

    root_directory = Path.home() / \
                     f".local/share/QGIS/QGIS3/profiles/" \
                     f"{context.obj['qgis_profile']}"

    destination_path = root_directory / "python/plugins" / SRC_NAME

    if not os.path.islink(destination_path):
        os.symlink(build_path, destination_path)
    else:
        _log(f"Symlink already exists, skipping creation.", context=context)


@app.command()
def uninstall(context: typer.Context):
    """Removes the plugin from QGIS plugins directory

    :param context: Application context
    :type context: typer.Context
    """
    root_directory = Path.home() / \
                     f".local/share/QGIS/QGIS3/profiles/" \
                     f"{context.obj['qgis_profile']}"
    base_target_directory = root_directory / "python/plugins" / SRC_NAME
    shutil.rmtree(str(base_target_directory), ignore_errors=True)
    _log(f"Removed {str(base_target_directory)!r}", context=context)


@app.command()
def generate_zip(
        context: typer.Context,
        output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "dist"):
    """ Generates plugin zip folder, that can be used to installed the
        plugin in QGIS

    :param context: Application context
    :type context: typer.Context

    :param output_directory: Directory where the zip folder will be saved.
    :type context: Path
    """
    build_dir = build(context)
    metadata = _get_metadata()
    output_directory.mkdir(parents=True, exist_ok=True)
    zip_path = output_directory / f'{SRC_NAME}.{metadata["version"]}.zip'
    with zipfile.ZipFile(zip_path, "w") as fh:
        _add_to_zip(build_dir, fh, arc_path_base=build_dir.parent)
    typer.echo(f"zip generated at {str(zip_path)!r}")
    return zip_path


@app.command()
def build(
        context: typer.Context,
        output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build" / SRC_NAME,
        clean: bool = True,
        tests: bool = False
) -> Path:
    """ Builds plugin directory for use in QGIS application.

    :param context: Application context
    :type context: typer.Context

    :param output_directory: Build output directory plugin where
            files will be saved.
    :type output_directory: Path

    :param clean: Whether current build directory files should be removed,
            before writing new files.
    :type clean: bool

    :param tests: Flag to indicate whether to include test related files.
    :type tests: bool

    :returns: Build directory path.
    :rtype: Path
    """
    if clean:
        shutil.rmtree(str(output_directory), ignore_errors=True)
    output_directory.mkdir(parents=True, exist_ok=True)
    copy_source_files(output_directory, tests=tests)
    icon_path = copy_icon(output_directory)
    if icon_path is None:
        _log("Could not copy icon", context=context)
    compile_resources(context, output_directory)
    generate_metadata(context, output_directory)
    return output_directory


@app.command()
def copy_icon(
        output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build/temp",
) -> Path:
    """ Copies the plugin intended icon to the specified output
        directory.

    :param output_directory: Output directory where the icon will be saved.
    :type output_directory: Path

    :returns: Icon output directory path.
    :rtype: Path
    """

    metadata = _get_metadata()
    icon_path = LOCAL_ROOT_DIR / "resources" / metadata["icon"]
    if icon_path.is_file():
        target_path = output_directory / icon_path.name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(icon_path, target_path)
        result = target_path
    else:
        result = None
    return result


@app.command()
def copy_source_files(
        output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build/temp",
        tests: bool = False
):
    """ Copies the plugin source files to the specified output
            directory.

    :param output_directory: Output directory where the icon will be saved.
    :type output_directory: Path

    :param tests: Flag to indicate whether to include test related files.
    :type tests: bool

    """
    output_directory.mkdir(parents=True, exist_ok=True)
    for child in (LOCAL_ROOT_DIR / "src" / SRC_NAME).iterdir():
        if child.name != "__pycache__":
            target_path = output_directory / child.name
            handler = shutil.copytree if child.is_dir() else shutil.copy
            handler(str(child.resolve()), str(target_path))
    if tests:
        for child in LOCAL_ROOT_DIR.iterdir():
            if child.name in TEST_FILES:
                target_path = output_directory / child.name
                handler = shutil.copytree if child.is_dir() else shutil.copy
                handler(str(child.resolve()), str(target_path))


@app.command()
def compile_resources(
        context: typer.Context,
        output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build/temp",
):
    """ Compiles plugin resources using the pyrcc package

    :param context: Application context
    :type context: typer.Context

    :param output_directory: Output directory where the resources will be saved.
    :type output_directory: Path
    """
    resources_path = LOCAL_ROOT_DIR / "resources" / "resources.qrc"
    target_path = output_directory / "resources.py"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _log(f"compile_resources target_path: {target_path}", context=context)
    subprocess.run(shlex.split(f"pyrcc5 -o {target_path} {resources_path}"))


@app.command()
def generate_metadata(
        context: typer.Context,
        output_directory: typing.Optional[Path] = LOCAL_ROOT_DIR / "build/temp",
):
    """ Generates plugin metadata file using settings defined in the
        project configuration file 'pyproject.toml'

    :param context: Application context
    :type context: typer.Context

    :param output_directory: Output directory where the metadata.txt file will be saved.
    :type output_directory: Path
    """
    metadata = _get_metadata()
    target_path = output_directory / "metadata.txt"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _log(f"generate_metadata target_path: {target_path}", context=context)
    config = configparser.ConfigParser()
    # do not modify case of parameters, as per
    # https://docs.python.org/3/library/configparser.html#customizing-parser-behaviour
    config.optionxform = lambda option: option
    config["general"] = metadata
    with target_path.open(mode="w") as fh:
        config.write(fh)


@app.command()
def generate_plugin_repo_xml(
        context: typer.Context,
):
    """ Generates the plugin repository xml file, from which users
        can use to install the plugin in QGIS.

    :param context: Application context
    :type context: typer.Context
   """
    repo_base_dir = LOCAL_ROOT_DIR / "docs" / "repository"
    repo_base_dir.mkdir(parents=True, exist_ok=True)
    metadata = _get_metadata()
    fragment_template = """
            <pyqgis_plugin name="{name}" version="{version}">
                <description><![CDATA[{description}]]></description>
                <about><![CDATA[{about}]]></about>
                <version>{version}</version>
                <qgis_minimum_version>{qgis_minimum_version}</qgis_minimum_version>
                <homepage><![CDATA[{homepage}]]></homepage>
                <file_name>{filename}</file_name>
                <icon>{icon}</icon>
                <author_name><![CDATA[{author}]]></author_name>
                <download_url>{download_url}</download_url>
                <update_date>{update_date}</update_date>
                <experimental>{experimental}</experimental>
                <deprecated>{deprecated}</deprecated>
                <tracker><![CDATA[{tracker}]]></tracker>
                <repository><![CDATA[{repository}]]></repository>
                <tags><![CDATA[{tags}]]></tags>
                <server>False</server>
            </pyqgis_plugin>
    """.strip()
    contents = "<?xml version = '1.0' encoding = 'UTF-8'?>\n<plugins>"
    all_releases = _get_existing_releases(context=context)
    _log(f"Found {len(all_releases)} release(s)...", context=context)
    for release in [r for r in _get_latest_releases(all_releases) if r is not None]:
        tag_name = release.tag_name
        _log(f"Processing release {tag_name}...", context=context)
        fragment = fragment_template.format(
            name=metadata.get("name"),
            version=tag_name.replace("v", ""),
            description=metadata.get("description"),
            about=metadata.get("about"),
            qgis_minimum_version=metadata.get("qgisMinimumVersion"),
            homepage=metadata.get("homepage"),
            filename=release.url.rpartition("/")[-1],
            icon=metadata.get("icon", ""),
            author=metadata.get("author"),
            download_url=release.url,
            update_date=release.published_at,
            experimental=release.pre_release,
            deprecated=metadata.get("deprecated"),
            tracker=metadata.get("tracker"),
            repository=metadata.get("repository"),
            tags=metadata.get("tags"),
        )
        contents = "\n".join((contents, fragment))
    contents = "\n".join((contents, "</plugins>"))
    repo_index = repo_base_dir / "plugins.xml"
    repo_index.write_text(contents, encoding="utf-8")
    _log(f"Plugin repo XML file saved at {repo_index}", context=context)


@lru_cache()
def _get_metadata() -> typing.Dict:
    """ Reads the metadata properties from the
        project configuration file 'pyproject.toml'

    :return: plugin metadata
    :type: Dict
    """
    pyproject_path = LOCAL_ROOT_DIR / "pyproject.toml"
    with pyproject_path.open("r") as fh:
        conf = toml.load(fh)
    poetry_conf = conf["tool"]["poetry"]
    raw_author_list = poetry_conf["authors"][0].split("<")
    author = raw_author_list[0].strip()
    email = raw_author_list[-1].replace(">", "")
    metadata = conf["tool"]["qgis-plugin"]["metadata"].copy()

    metadata.update(
        {
            "author": author,
            "email": email,
            "description": poetry_conf["description"],
            "version": poetry_conf["version"],
            "tags": ", ".join(metadata.get("tags", [])),
            "changelog": _changelog(),
        }
    )
    return metadata


def _changelog() -> str:
    """ Reads the changelog content from a config file.

    :returns: Plugin changelog
    :type: str
    """
    path = LOCAL_ROOT_DIR / "docs/plugin/changelog.txt"

    with path.open() as fh:
        changelog_file = fh.read()

    return changelog_file


def _add_to_zip(
        directory: Path,
        zip_handler: zipfile.ZipFile,
        arc_path_base: Path):
    """ Adds to files inside the passed directory to the zip file.

    :param directory: Directory with files that are to be zipped.
    :type directory: Path

    :param zip_handler: Plugin zip file
    :type zip_handler: ZipFile

    :param arc_path_base: Parent directory of the input files directory.
    :type arc_path_base: Path
    """
    for item in directory.iterdir():
        if item.is_file():
            zip_handler.write(item, arcname=str(
                item.relative_to(arc_path_base)))
        else:
            _add_to_zip(item, zip_handler, arc_path_base)


def _log(
        msg,
        *args,
        context: typing.Optional[typer.Context] = None,
        **kwargs):
    """ Logs the message into the terminal.
    :param msg: Directory with files that are to be zipped.
    :type msg: str

    :param context: Application context
    :type context: typer.Context
    """
    if context is not None:
        context_user_data = context.obj or {}
        verbose = context_user_data.get("verbose", True)
    else:
        verbose = True
    if verbose:
        typer.echo(msg, *args, **kwargs)


def _get_existing_releases(
        context: typing.Optional = None,
) -> typing.List[GithubRelease]:
    """ Gets the existing plugin releases in  available in the Github repository.

    :param context: Application context
    :type context: typer.Context

    :returns: List of github releases
    :rtype: List[GithubRelease]
    """
    base_url = "https://api.github.com/repos/" \
               "stac-utils/qgis-stac-plugin/releases"
    response = httpx.get(base_url)
    result = []
    if response.status_code == 200:
        payload = response.json()
        for release in payload:
            for asset in release["assets"]:
                if asset.get("content_type") == "application/zip":
                    zip_download_url = asset.get("browser_download_url")
                    break
            else:
                zip_download_url = None
            _log(f"zip_download_url: {zip_download_url}", context=context)
            if zip_download_url is not None:
                result.append(
                    GithubRelease(
                        pre_release=release.get("prerelease", True),
                        tag_name=release.get("tag_name"),
                        url=zip_download_url,
                        published_at=dt.datetime.strptime(
                            release["published_at"], "%Y-%m-%dT%H:%M:%SZ"
                        ),
                    )
                )
    return result


def _get_latest_releases(
        current_releases: typing.List[GithubRelease],
) -> typing.Tuple[
    typing.Optional[GithubRelease],
    typing.Optional[GithubRelease]]:
    """ Searches for the latest plugin releases from the Github plugin releases.

    :param current_releases: Existing plugin releases
     available in the Github repository.
    :type current_releases: list

    :returns: Tuple containing the latest stable and experimental releases
    :rtype: tuple
    """
    latest_experimental = None
    latest_stable = None
    for release in current_releases:
        if release.pre_release:
            if latest_experimental is not None:
                if release.published_at > latest_experimental.published_at:
                    latest_experimental = release
            else:
                latest_experimental = release
        else:
            if latest_stable is not None:
                if release.published_at > latest_stable.published_at:
                    latest_stable = release
            else:
                latest_stable = release
    return latest_stable, latest_experimental


if __name__ == "__main__":
    app()
