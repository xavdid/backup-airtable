import json
from pathlib import Path
from typing import Callable, Optional, Protocol, TypedDict
from unittest.mock import patch

import pytest
from click.testing import CliRunner, Result
from pytest_httpx import HTTPXMock

from backup_airtable.cli import build_client, cli, load_all_comments, load_all_records


class TableInfo(TypedDict):
    info: dict
    records: list[dict]


class BaseInfo(TypedDict):
    info: dict
    tables: list[TableInfo]


type BasesFn = Callable[[], list[BaseInfo]]


@pytest.fixture
def get_bases() -> BasesFn:
    """
    This is the full, final representation of the DB dump.
    In a function so other fixtures can modify it safely, but also available directly as a fixture.
    """

    def _build_bases() -> list[BaseInfo]:
        return [
            {
                "info": {
                    "id": "app123",
                    "name": "Base the First",
                    "permissionLevel": "create",
                },
                "tables": [
                    {
                        "info": {
                            "id": "tbl123",
                            "name": "Cool Table",
                            "primaryFieldId": "fld123",
                            "fields": [
                                {
                                    "type": "singleLineText",
                                    "id": "fld123",
                                    "name": "Name",
                                },
                                {
                                    "type": "checkbox",
                                    "options": {
                                        "icon": "check",
                                        "color": "greenBright",
                                    },
                                    "id": "fld456",
                                    "name": "Done?",
                                },
                            ],
                        },
                        "records": [
                            {
                                "id": "rec1",
                                "commentCount": 2,
                                "comments": [
                                    {
                                        "author": {
                                            "email": "email@website.com",
                                            "id": "usrOrn2etJhbw2dem",
                                            "name": "Bruce Wayne",
                                        },
                                        "createdTime": "2025-02-21T08:05:25.000Z",
                                        "id": "comx1KUhmPiHYX10w",
                                        "lastUpdatedTime": None,
                                        "text": "cool comment!",
                                    },
                                    {
                                        "author": {
                                            "email": "email@website.com",
                                            "id": "usrOrn2etJhbw2dem",
                                            "name": "Bruce Wayne",
                                        },
                                        "createdTime": "2025-02-21T08:15:25.000Z",
                                        "id": "comx1KUhmPiHYX11w",
                                        "lastUpdatedTime": None,
                                        "text": "another cool comment!",
                                    },
                                ],
                                "fields": {
                                    "name": "This is the name",
                                    "address": "Address line 1\nAddress line 2",
                                    "weird name: what is this?": "hello",
                                    "size": 441,
                                    "some_checkbox": True,
                                },
                                "createdTime": "2020-04-19T18:50:27.000Z",
                            },
                            {
                                "id": "rec2",
                                "commentCount": 0,
                                "comments": [],
                                "fields": {
                                    "name": "This is the name 2",
                                    "address": "Address line 1\nAddress line 2",
                                    "weird name: what is this?": "there",
                                    "size": 442,
                                    "some_checkbox": False,
                                },
                                "createdTime": "2020-04-18T18:58:27.000Z",
                            },
                        ],
                    },
                    {
                        "info": {
                            "id": "tbl456",
                            "name": "Tough: name? / neat",
                            "primaryFieldId": "fld456",
                            "fields": [
                                {
                                    "type": "singleLineText",
                                    "id": "fld123",
                                    "name": "Name",
                                },
                                {
                                    "type": "checkbox",
                                    "options": {
                                        "icon": "check",
                                        "color": "greenBright",
                                    },
                                    "id": "fld456",
                                    "name": "Done?",
                                },
                            ],
                        },
                        "records": [
                            {
                                "id": "rec1",
                                "commentCount": 0,
                                "comments": [],
                                "fields": {
                                    "name": "This is the name",
                                    "address": "Address line 1\nAddress line 2",
                                    "weird name: what is this?": "hello",
                                    "size": 441,
                                    "some_checkbox": True,
                                },
                                "createdTime": "2020-04-18T18:50:27.000Z",
                            },
                            {
                                "id": "rec2",
                                "commentCount": 0,
                                "comments": [],
                                "fields": {
                                    "name": "This is the name 2",
                                    "address": "Address line 1\nAddress line 2",
                                    "weird name: what is this?": "there",
                                    "size": 442,
                                    "some_checkbox": False,
                                },
                                "createdTime": "2020-04-18T18:58:27.000Z",
                            },
                        ],
                    },
                ],
            },
            {
                "info": {
                    "id": "app123",
                    "name": "Base the Second",
                    "permissionLevel": "create",
                },
                "tables": [
                    {
                        "info": {
                            "id": "tbl789",
                            "name": "Cool Table",
                            "primaryFieldId": "fld123",
                            "fields": [
                                {
                                    "type": "singleLineText",
                                    "id": "fld123",
                                    "name": "Name",
                                },
                                {
                                    "type": "checkbox",
                                    "options": {
                                        "icon": "check",
                                        "color": "greenBright",
                                    },
                                    "id": "fld456",
                                    "name": "Done?",
                                },
                            ],
                        },
                        "records": [
                            {
                                "id": "rec1",
                                "commentCount": 0,
                                "comments": [],
                                "fields": {
                                    "name": "This is the name",
                                    "address": "Address line 1\nAddress line 2",
                                    "weird name: what is this?": "hello",
                                    "size": 441,
                                    "some_checkbox": True,
                                },
                                "createdTime": "2020-04-18T18:50:27.000Z",
                            },
                            {
                                "id": "rec2",
                                "commentCount": 0,
                                "comments": [],
                                "fields": {
                                    "name": "This is the name 2",
                                    "address": "Address line 1\nAddress line 2",
                                    "weird name: what is this?": "there",
                                    "size": 442,
                                    "some_checkbox": False,
                                },
                                "createdTime": "2020-04-18T18:58:27.000Z",
                            },
                        ],
                    },
                ],
            },
        ]

    return _build_bases


@pytest.fixture
def bases(get_bases) -> list[BaseInfo]:
    return get_bases()


@pytest.fixture
def mock_bases(httpx_mock, bases):
    httpx_mock.add_response(
        url="https://api.airtable.com/v0/meta/bases",
        match_headers={
            "Authorization": "Bearer pat123.456",
            "user-agent": "backup-airtable",
        },
        json={"bases": [b["info"] for b in bases]},
    )


@pytest.fixture
def mock_tables(httpx_mock: HTTPXMock, bases, mock_bases):  # noqa: ARG001
    for b in bases:
        httpx_mock.add_response(
            url=f"https://api.airtable.com/v0/meta/bases/{b['info']['id']}/tables",
            match_headers={"Authorization": "Bearer pat123.456"},
            json={"tables": [t["info"] for t in b["tables"]]},
        )


@pytest.fixture
def mock_records(httpx_mock, mock_tables, get_bases: BasesFn):  # noqa: ARG001
    def mock_calls(ignored_tables: Optional[list[str]] = None, with_comments=False):
        if ignored_tables is None:
            ignored_tables = []
        for b in get_bases():
            for t in b["tables"]:
                if t["info"]["id"] in ignored_tables:
                    continue

                records = []

                for r in t["records"]:
                    # comments[] are _never_ in the root response, but may be fetched and merged later
                    comments = r.pop("comments")
                    if with_comments and comments:
                        httpx_mock.add_response(
                            url=f"https://api.airtable.com/v0/{b['info']['id']}/{t['info']['id']}/{r['id']}/comments",
                            match_headers={"Authorization": "Bearer pat123.456"},
                            json={"comments": list(reversed(comments))},
                        )
                    records.append(r)

                httpx_mock.add_response(
                    url=f"https://api.airtable.com/v0/{b['info']['id']}/{t['info']['id']}?recordMetadata=commentCount",
                    match_headers={"Authorization": "Bearer pat123.456"},
                    json={"records": t["records"]},
                )

    return mock_calls


@pytest.fixture
def bases_no_comments(get_bases: BasesFn):
    bases = get_bases()

    for b in bases:
        for t in b["tables"]:
            for r in t["records"]:
                r.pop("comments")

    return bases


class InvokeFn(Protocol):
    def __call__(
        self,
        args: Optional[list[str]] = None,
        *,
        expected_status=0,
        backup_dir: Optional[list[str]] = None,
    ) -> Result: ...


@pytest.fixture
def invoke(tmp_path, monkeypatch) -> InvokeFn:
    def _run(
        args: Optional[list[str]] = None,
        expected_status=0,
        backup_dir: Optional[list[str]] = None,
    ):
        if args is None:
            args = []
        # use a list here so we can disappear it with an unpack
        if backup_dir is None:
            backup_dir = [str(tmp_path)]

        runner = CliRunner()

        monkeypatch.chdir(tmp_path)

        # write to tmp_path directly so we don't have to get the subfolder in tests
        result = runner.invoke(
            cli, [*backup_dir, *args], env={"AIRTABLE_TOKEN": "pat123.456"}
        )

        if result.exit_code != expected_status:
            # much easier to debug this way
            print(result.output)

        assert result.exit_code == expected_status

        return result

    return _run


def test_version(invoke: InvokeFn):
    result = invoke(["--version"])
    assert result.output.startswith("cli, version ")


def test_full_backup(
    tmp_path, mock_records, bases_no_comments: list[BaseInfo], invoke: InvokeFn
):
    mock_records()
    invoke()

    assert (
        json.loads(
            Path(tmp_path, "Base the First", "Cool Table", "schema.json").read_text()
        )
        == bases_no_comments[0]["tables"][0]["info"]
    )
    assert json.loads(
        Path(tmp_path, "Base the First", "Cool Table", "records.json").read_text()
    ) == [
        bases_no_comments[0]["tables"][0]["records"][1],
        bases_no_comments[0]["tables"][0]["records"][0],
    ]  # sorted by creation date
    assert (
        json.loads(
            Path(
                tmp_path, "Base the First", "Tough- name? | neat", "schema.json"
            ).read_text()
        )
        == bases_no_comments[0]["tables"][1]["info"]
    )
    assert (
        json.loads(
            Path(tmp_path, "Base the Second", "Cool Table", "schema.json").read_text()
        )
        == bases_no_comments[1]["tables"][0]["info"]
    )
    assert (
        json.loads(
            Path(tmp_path, "Base the Second", "Cool Table", "records.json").read_text()
        )
        == bases_no_comments[1]["tables"][0]["records"]
    )


def test_full_backup_with_comments(tmp_path, mock_records, bases, invoke: InvokeFn):
    mock_records(with_comments=True)

    invoke(["--include-comments"])

    assert json.loads(
        Path(tmp_path, "Base the First", "Cool Table", "records.json").read_text()
    ) == [
        bases[0]["tables"][0]["records"][1],
        bases[0]["tables"][0]["records"][0],
    ]  # sorted by creation date

    assert bases[0]["tables"][0]["records"][0]["comments"] == [
        {
            "author": {
                "email": "email@website.com",
                "id": "usrOrn2etJhbw2dem",
                "name": "Bruce Wayne",
            },
            "createdTime": "2025-02-21T08:05:25.000Z",
            "id": "comx1KUhmPiHYX10w",
            "lastUpdatedTime": None,
            "text": "cool comment!",
        },
        {
            "author": {
                "email": "email@website.com",
                "id": "usrOrn2etJhbw2dem",
                "name": "Bruce Wayne",
            },
            "createdTime": "2025-02-21T08:15:25.000Z",
            "id": "comx1KUhmPiHYX11w",
            "lastUpdatedTime": None,
            "text": "another cool comment!",
        },
    ]


def test_skipping_tables(tmp_path, mock_records, bases_no_comments, invoke: InvokeFn):
    mock_records(["tbl123", "tbl789"])
    invoke(
        [
            "--ignore-table",
            "tbl123",
            "--ignore-table",
            "tbl789",
        ]
    )

    assert not Path(tmp_path, "Base the First", "Cool Table").exists()
    assert (
        json.loads(
            Path(
                tmp_path, "Base the First", "Tough- name? | neat", "schema.json"
            ).read_text()
        )
        == bases_no_comments[0]["tables"][1]["info"]
    )
    assert (
        json.loads(
            Path(
                tmp_path, "Base the First", "Tough- name? | neat", "records.json"
            ).read_text()
        )
        == bases_no_comments[0]["tables"][1]["records"]
    )
    assert not Path(tmp_path, "Base the Second", "Cool Table").exists()


@pytest.mark.freeze_time("2024-04-24")
def test_default_path(tmp_path, mock_records, invoke: InvokeFn):
    mock_records()
    invoke(backup_dir=[])  # use the CLI's default location

    assert Path(tmp_path, "airtable-backup-2024-04-24").exists()


def test_airtable_export_401_error(httpx_mock, invoke: InvokeFn):
    httpx_mock.add_response(status_code=401)
    result = invoke(expected_status=1)
    assert result.exit_code == 1
    assert "401 Unauthorized" in result.output
    assert "HINT: Ensure" not in result.output


def test_airtable_bad_permissions(httpx_mock, invoke: InvokeFn):
    httpx_mock.add_response(status_code=403)
    result = invoke(expected_status=1)
    assert result.exit_code == 1
    assert "403 Forbidden" in result.output
    assert "HINT: Ensure" in result.output


@patch("backup_airtable.cli.REQUEST_DELAY", new=0)
class TestPagination:
    def test_paging_records(self, httpx_mock: HTTPXMock):
        headers = {
            "Authorization": "Bearer pat456.789",
            "user-agent": "backup-airtable",
        }

        httpx_mock.add_response(
            url="https://api.airtable.com/v0/app123/tbl123?recordMetadata=commentCount",
            json={"records": [{"id": 1}], "offset": "abc/123"},
            match_headers=headers,
        )
        httpx_mock.add_response(
            url="https://api.airtable.com/v0/app123/tbl123?recordMetadata=commentCount&offset=abc%2F123",
            json={"records": [{"id": 2}], "offset": "abc/456"},
            match_headers=headers,
        )
        httpx_mock.add_response(
            url="https://api.airtable.com/v0/app123/tbl123?recordMetadata=commentCount&offset=abc%2F456",
            # last page no offset
            json={"records": [{"id": 3}]},
            match_headers=headers,
        )

        fetch = build_client("pat456.789")
        records = load_all_records(fetch, "app123", "tbl123")
        assert list(records) == [{"id": 1}, {"id": 2}, {"id": 3}]

    def test_paging_comments(self, httpx_mock: HTTPXMock):
        headers = {
            "Authorization": "Bearer pat456.789",
            "user-agent": "backup-airtable",
        }

        httpx_mock.add_response(
            url="https://api.airtable.com/v0/app123/tbl123/rec123/comments",
            json={"comments": [{"id": 1}], "offset": "abc/123"},
            match_headers=headers,
        )
        httpx_mock.add_response(
            url="https://api.airtable.com/v0/app123/tbl123/rec123/comments?offset=abc%2F123",
            json={"comments": [{"id": 2}], "offset": "abc/456"},
            match_headers=headers,
        )
        httpx_mock.add_response(
            url="https://api.airtable.com/v0/app123/tbl123/rec123/comments?offset=abc%2F456",
            # last page no offset
            json={"comments": [{"id": 3}]},
            match_headers=headers,
        )

        fetch = build_client("pat456.789")
        comments = load_all_comments(fetch, "app123", "tbl123", "rec123")
        assert list(comments) == [{"id": 1}, {"id": 2}, {"id": 3}]
