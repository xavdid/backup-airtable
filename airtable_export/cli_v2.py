import json
import time
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlencode

import click
import httpx
from httpx import HTTPError

# airtable occasionally has read timeouts when doing a big export
# see https://github.com/simonw/airtable-export/pull/14
timeout = httpx.Timeout(5, read=60)
http_client = httpx.Client(timeout=timeout)


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


@click.command()
@click.version_option()
@click.argument(
    "backup_directory",
    type=click.Path(
        file_okay=False, dir_okay=True, allow_dash=False, writable=True, path_type=Path
    ),
    required=False,
    default=Path.cwd(),
    # help="Root of the backup directory. Each base will get its own subfolder.",
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

    def _api_request(api_path: str):
        assert api_path.startswith("/")
        assert "api.airtable.com" not in api_path

        try:
            response = http_client.get(
                f"https://api.airtable.com/v0{api_path}",
                headers={"Authorization": f"Bearer {airtable_token}"},
            )
            response.raise_for_status()
        except HTTPError as e:
            raise click.ClickException(str(e))

        return response.json()

    def all_records(base_id: str, table_id: str, sleep: float = 0.2):
        first = True
        offset = None
        while first or offset:
            first = False
            path = f"/{base_id}/{table_id}"
            if offset:
                path += "?" + urlencode({"offset": offset})

            data = _api_request(path)
            print(".", end="", flush=True)  # little progress bar-type thing
            offset = data.get("offset")
            yield from data["records"]
            if offset and sleep:
                time.sleep(sleep)

    base_response: BaseResponse = _api_request("/meta/bases")
    bases = base_response["bases"]
    num_bases = len(bases)

    print("Loading bases...")
    for base_index, base in enumerate(bases):
        print(f"  ({base_index+1}/{num_bases}) Fetching info for: {base["name"]}")

        base_path = backup_directory / normalize_name(base["name"])

        table_response: TableResponse = _api_request(f"/meta/bases/{base["id"]}/tables")
        tables = table_response["tables"]
        num_tables = len(tables)
        for table_index, table in enumerate(tables):
            print(f'    ({table_index+1}/{num_tables}) Saving table: {table["name"]}')

            table_path = base_path / normalize_name(table["name"])
            table_path.mkdir(parents=True, exist_ok=True)

            write_json(table_path, "schema", table)

            print("      loading records", end="", flush=True)
            records = list(all_records(base["id"], table["id"]))
            write_json(table_path, "records", records)
            print("\n      wrote records.json")
