import json
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, TypedDict
from urllib.parse import urlencode

import click
import httpx
from httpx import HTTPError

# airtable occasionally has read timeouts when doing a big export
# see https://github.com/simonw/airtable-export/pull/14
timeout = httpx.Timeout(5, read=60)
http_client = httpx.Client(timeout=timeout)
REQUEST_DELAY = 0.2


class Base(TypedDict):
    id: str
    name: str
    permissionLevel: str


class BaseResponse(TypedDict):
    bases: list[Base]


class Table(TypedDict):
    id: str
    name: str
    primaryFieldId: str
    fields: list[dict]  # don't need the details here


class TableResponse(TypedDict):
    tables: list[Table]


# make an airtable name appropriate for a filepath
def normalize_name(s: str) -> str:
    return s.replace(":", "-").replace("/", "|")


def write_json(folder: Path, filename: str, data):
    (folder / f"{filename}.json").write_text(json.dumps(data, indent=2, sort_keys=True))


fetch_fn = Callable[[str], Any]


def build_client(airtable_token: str) -> fetch_fn:
    def _api_request(api_path: str):
        assert api_path.startswith("/")
        assert "api.airtable.com" not in api_path

        try:
            response = http_client.get(
                f"https://api.airtable.com/v0{api_path}",
                headers={
                    "Authorization": f"Bearer {airtable_token}",
                    "user-agent": "backup-airtable",
                },
            )
            response.raise_for_status()
        except HTTPError as e:
            raise click.ClickException(str(e))

        return response.json()

    return _api_request


def load_all_records(fetch: fetch_fn, base_id: str, table_id: str) -> Iterable:
    first = True
    offset = None
    while first or offset:
        first = False
        path = f"/{base_id}/{table_id}"
        if offset:
            path += "?" + urlencode({"offset": offset})

        data = fetch(path)
        print(".", end="", flush=True)  # little progress bar-type thing
        offset = data.get("offset")
        yield from data["records"]
        if offset:
            time.sleep(REQUEST_DELAY)


@click.command()
@click.version_option()
@click.argument(
    "backup_directory",
    type=click.Path(
        file_okay=False, dir_okay=True, allow_dash=False, writable=True, path_type=Path
    ),
    default=lambda: Path.cwd() / f"airtable-backup-{date.today()}",
)
@click.option(
    "--ignore_table",
    type=str,
    multiple=True,
    help="Table id(s) to ignore when backing up.",
)
@click.option(
    "--airtable-token",
    envvar="AIRTABLE_TOKEN",
    help="Airtable Access Token",
    required=True,
)
def cli(backup_directory: Path, ignore_table: tuple[str], airtable_token: str):
    "Save data from Airtable to a series of local JSON files / folders"
    fetch = build_client(airtable_token)

    print(f"Backing up to {backup_directory}")
    print("Fetching bases...", end="", flush=True)

    base_response: BaseResponse = fetch("/meta/bases")
    bases = base_response["bases"]
    num_bases = len(bases)

    print(f" done! Found {num_bases}")

    for base_index, base in enumerate(bases):
        print(f"  ({base_index+1}/{num_bases}) Fetching info for: {base["name"]}")

        base_directory = backup_directory / normalize_name(base["name"])

        table_response: TableResponse = fetch(f"/meta/bases/{base["id"]}/tables")
        tables = table_response["tables"]
        num_tables = len(tables)
        for table_index, table in enumerate(tables):
            if table["id"] in ignore_table:
                print(
                    f'    ({table_index+1}/{num_tables}) Skipping table: {table["name"]}'
                )
                continue

            print(f'    ({table_index+1}/{num_tables}) Saving table: {table["name"]}')

            table_directory = base_directory / normalize_name(table["name"])
            table_directory.mkdir(parents=True, exist_ok=True)

            write_json(table_directory, "schema", table)

            print("      loading records", end="", flush=True)
            records = sorted(
                load_all_records(fetch, base["id"], table["id"]),
                key=lambda r: r["createdTime"],
            )
            write_json(table_directory, "records", records)
            print("\n      wrote records.json")
