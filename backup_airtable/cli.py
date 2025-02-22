import json
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Protocol, TypedDict

import click
import httpx
from httpx import HTTPError, HTTPStatusError

# airtable occasionally has read timeouts when doing a big export
# see https://github.com/simonw/airtable-export/pull/14
timeout = httpx.Timeout(5, read=60)
http_client = httpx.Client(timeout=timeout)
# Rate limit is 5req / s. With some overhead for connection time, this is ~ as fast as we can go without hitting limits.
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


class FetchFn(Protocol):
    def __call__(
        self, path: str, params: Optional[dict[str, str]] = None, /
    ) -> Any: ...


fetch_fn = Callable[[str, Optional[dict[str, str]]], Any]


def build_client(airtable_token: str) -> FetchFn:
    def _api_request(api_path: str, params: Optional[dict[str, str]] = None):
        assert api_path.startswith("/")
        assert "api.airtable.com" not in api_path

        try:
            response = http_client.get(
                f"https://api.airtable.com/v0{api_path}",
                headers={
                    "Authorization": f"Bearer {airtable_token}",
                    "user-agent": "backup-airtable",
                },
                # remove `None` keys from params dict to make calling this easier
                params={k: v for k, v in (params or {}).items() if v is not None},
            )
            response.raise_for_status()
            return response.json()

        except HTTPError as e:
            print("\n")

            message = f"{str(e)}\n"

            # permissions issue would be the trickiest to catch, so flag those especially
            if isinstance(e, HTTPStatusError) and e.response.status_code == 403:
                message += "\nHINT: Ensure your token has the correct permissions!\n"

            raise click.ClickException(message)

    return _api_request


def load_all_items(
    fetch: FetchFn, base_id: str, table_id: str, record_id: Optional[str] = None
) -> Iterable:
    first = True  # no do...while, but can't set `offset` to something because it gets passed to airtable
    offset = None
    while first or offset:
        first = False
        path = f"/{base_id}/{table_id}"

        if record_id:
            path += f"/{record_id}/comments"

        data = fetch(
            path,
            {"offset": offset, "recordMetadata": None if record_id else "commentCount"},
        )
        print(".", end="", flush=True)  # little progress bar-type thing
        offset = data.get("offset")
        # TODO: decouple this from record_id? or split out to separate functions?
        yield from data["comments" if record_id else "records"]
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
    "--ignore-table",
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
@click.option(
    "--include-comments",
    help="Whether to include row comments in the backup. May slow down the backup considerably if many rows have backups.",
    is_flag=True,
)
def cli(
    backup_directory: Path,
    ignore_table: tuple[str],
    airtable_token: str,
    include_comments: bool,
):
    "Save data from Airtable to a series of local JSON files / folders"

    fetch = build_client(airtable_token)

    print(f"Backing up to {backup_directory}")
    print("Fetching bases...", end="", flush=True)

    base_response: BaseResponse = fetch("/meta/bases")
    bases = base_response["bases"]
    num_bases = len(bases)

    print(f" done! Found {num_bases}")

    for base_index, base in enumerate(bases):
        print(f"  ({base_index + 1}/{num_bases}) Fetching info for: {base['name']}")

        base_directory = backup_directory / normalize_name(base["name"])

        table_response: TableResponse = fetch(f"/meta/bases/{base['id']}/tables")
        tables = table_response["tables"]
        num_tables = len(tables)
        for table_index, table in enumerate(tables):
            if table["id"] in ignore_table:
                print(
                    f"    ({table_index + 1}/{num_tables}) Skipping table: {table['name']}"
                )
                continue

            print(f"    ({table_index + 1}/{num_tables}) Saving table: {table['name']}")

            table_directory = base_directory / normalize_name(table["name"])
            table_directory.mkdir(parents=True, exist_ok=True)

            write_json(table_directory, "schema", table)

            print("      loading records", end="", flush=True)
            records = sorted(
                load_all_items(fetch, base["id"], table["id"]),
                key=lambda r: r["createdTime"],
            )

            if include_comments:
                # only log if we're fetching any comments for this table
                if num_records_with_comments := sum(
                    1 for r in records if r.get("commentCount")
                ):
                    print(
                        f"\n      loading comments for {num_records_with_comments} record(s)",
                        end="",
                        flush=True,
                    )
                else:
                    print("\n      no comments for this table", flush=True, end="")

                # but, always add the empty lists
                for record in records:
                    comments = []
                    if record.get("commentCount"):
                        comments = sorted(
                            load_all_items(
                                fetch, base["id"], table["id"], record["id"]
                            ),
                            key=lambda r: r["createdTime"],
                        )
                    record["comments"] = comments

            write_json(table_directory, "records", records)
            print("\n      wrote records.json")
