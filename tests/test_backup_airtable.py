import json
from pathlib import Path
from typing import Optional, TypedDict
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from pytest_httpx import HTTPXMock

from backup_airtable.cli import build_client, cli, load_all_records


class TableInfo(TypedDict):
    info: dict
    records: list[dict]


class BaseInfo(TypedDict):
    info: dict
    tables: list[TableInfo]


BASES: list[BaseInfo] = [
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
                            "options": {"icon": "check", "color": "greenBright"},
                            "id": "fld456",
                            "name": "Done?",
                        },
                    ],
                },
                "records": [
                    {
                        "id": "rec1",
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
                            "options": {"icon": "check", "color": "greenBright"},
                            "id": "fld456",
                            "name": "Done?",
                        },
                    ],
                },
                "records": [
                    {
                        "id": "rec1",
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
                            "options": {"icon": "check", "color": "greenBright"},
                            "id": "fld456",
                            "name": "Done?",
                        },
                    ],
                },
                "records": [
                    {
                        "id": "rec1",
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


@pytest.fixture
def mock_bases(httpx_mock):
    httpx_mock.add_response(
        url="https://api.airtable.com/v0/meta/bases",
        match_headers={
            "Authorization": "Bearer pat123.456",
            "user-agent": "backup-airtable",
        },
        json={"bases": [b["info"] for b in BASES]},
    )


@pytest.fixture
def mock_tables(httpx_mock: HTTPXMock):
    for b in BASES:
        httpx_mock.add_response(
            url=f"https://api.airtable.com/v0/meta/bases/{b['info']['id']}/tables",
            match_headers={"Authorization": "Bearer pat123.456"},
            json={"tables": [t["info"] for t in b["tables"]]},
        )


@pytest.fixture
def mock_records(httpx_mock):
    def mock_calls(ignored_tables: Optional[list[str]] = None):
        if ignored_tables is None:
            ignored_tables = []
        for b in BASES:
            for t in b["tables"]:
                if t["info"]["id"] in ignored_tables:
                    continue
                httpx_mock.add_response(
                    url=f"https://api.airtable.com/v0/{b['info']['id']}/{t['info']['id']}",
                    match_headers={"Authorization": "Bearer pat123.456"},
                    json={"records": t["records"]},
                )

    return mock_calls


def test_version():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["--version"])
        assert 0 == result.exit_code
        assert result.output.startswith("cli, version ")


def test_full_backup(tmpdir, mock_bases, mock_tables, mock_records):
    mock_records()

    runner = CliRunner()
    result = runner.invoke(cli, [str(tmpdir)], env={"AIRTABLE_TOKEN": "pat123.456"})
    assert result.exit_code == 0

    assert (
        json.loads(
            Path(tmpdir / "Base the First" / "Cool Table" / "schema.json").read_text()
        )
        == BASES[0]["tables"][0]["info"]
    )
    assert json.loads(
        Path(tmpdir / "Base the First" / "Cool Table" / "records.json").read_text()
    ) == [
        BASES[0]["tables"][0]["records"][1],
        BASES[0]["tables"][0]["records"][0],
    ]  # sorted by creation date
    assert (
        json.loads(
            Path(
                tmpdir / "Base the First" / "Tough- name? | neat" / "schema.json"
            ).read_text()
        )
        == BASES[0]["tables"][1]["info"]
    )
    assert (
        json.loads(
            Path(tmpdir / "Base the Second" / "Cool Table" / "schema.json").read_text()
        )
        == BASES[1]["tables"][0]["info"]
    )
    assert (
        json.loads(
            Path(tmpdir / "Base the Second" / "Cool Table" / "records.json").read_text()
        )
        == BASES[1]["tables"][0]["records"]
    )


def test_skipping_tables(tmpdir, mock_bases, mock_tables, mock_records):
    mock_records(["tbl123", "tbl789"])

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            str(tmpdir),
            "--airtable-token",
            "pat123.456",
            "--ignore_table",
            "tbl123",
            "--ignore_table",
            "tbl789",
        ],
    )
    assert result.exit_code == 0

    assert not Path(tmpdir / "Base the First" / "Cool Table").exists()
    assert (
        json.loads(
            Path(
                tmpdir / "Base the First" / "Tough- name? | neat" / "schema.json"
            ).read_text()
        )
        == BASES[0]["tables"][1]["info"]
    )
    assert (
        json.loads(
            Path(
                tmpdir / "Base the First" / "Tough- name? | neat" / "records.json"
            ).read_text()
        )
        == BASES[0]["tables"][1]["records"]
    )
    assert not Path(tmpdir / "Base the Second" / "Cool Table").exists()


@pytest.mark.freeze_time("2024-04-24")
def test_default_path(tmpdir, mock_bases, mock_tables, mock_records):
    mock_records()
    runner = CliRunner()
    with runner.isolated_filesystem(str(tmpdir)) as wd:
        result = runner.invoke(cli, env={"AIRTABLE_TOKEN": "pat123.456"})
        assert result.exit_code == 0

        assert Path(wd, "airtable-backup-2024-04-24").exists()


def test_airtable_export_401_error(httpx_mock):
    httpx_mock.add_response(status_code=401)
    runner = CliRunner()
    result = runner.invoke(cli, ["--airtable-token", "pat123.456"])
    assert result.exit_code == 1
    assert "401 Unauthorized" in result.output


@patch("backup_airtable.cli.REQUEST_DELAY", new=0)
class TestPagination:
    def test_paging(self, httpx_mock: HTTPXMock):
        headers = {
            "Authorization": "Bearer pat456.789",
            "user-agent": "backup-airtable",
        }
        httpx_mock.add_response(
            url="https://api.airtable.com/v0/app123/tbl123",
            json={"records": [{"id": 1}], "offset": "abc/123"},
            match_headers=headers,
        )
        httpx_mock.add_response(
            url="https://api.airtable.com/v0/app123/tbl123?offset=abc%2F123",
            json={"records": [{"id": 2}], "offset": "abc/456"},
            match_headers=headers,
        )
        # last page no offset
        httpx_mock.add_response(
            url="https://api.airtable.com/v0/app123/tbl123?offset=abc%2F456",
            json={"records": [{"id": 3}]},
            match_headers=headers,
        )

        fetch = build_client("pat456.789")
        records = load_all_records(fetch, "app123", "tbl123")
        assert list(records) == [{"id": 1}, {"id": 2}, {"id": 3}]
