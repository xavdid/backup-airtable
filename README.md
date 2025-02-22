# backup-airtable

Export your [Airtable](https://airtable.com/) data to JSON files. It exports both the table's schema and the records.

## Installation

The easiest way to run this is using [pipx](https://pypa.github.io/pipx/):

```shell
pipx install backup-airtable
```

<!-- You can also use brew:

```shell
brew install ...
``` -->

## Usage

Once [authenticated](#authentication), running `backup-airtable` will immediately start downloading data. There are a few available options (viewable via `backup-airtable --help`):

```
Usage: backup-airtable [OPTIONS] [BACKUP_DIRECTORY]

  Save data from Airtable to a series of local JSON files / folders

Options:
  --version              Show the version and exit.
  --ignore-table TEXT    Table id(s) to ignore when backing up.
  --airtable-token TEXT  Airtable Access Token  [required]
  --include-comments     Whether to include row comments in the backup. May
                         slow down the backup considerably if many rows have
                         backups.
  --help                 Show this message and exit.
```

You'll likely only need `ignore-table` (which you can specify multiple times) to ignore specific tables from bases you otherwise want to include.

### Examples

- `backup-airtable`
- `backup-airtable --include-comments`
- `backup-airtable some_backup_folder`
- `backup_airtable --ignore-table tbl123 --ignore-table tbl456`

## Authentication

You need to create a [personal access token](https://airtable.com/developers/web/guides/personal-access-tokens) to use this tool. It has the format `pat123.456`. They can be created at https://airtable.com/create/tokens.

Ensure it has the following scopes:

- `data.records:read`
- `schema.bases:read`
- if you're going to export comments (see [comments](#comments)):
  - `data.recordComments:read`

You can give it access to as many or as few bases as you'd like. Everything the token has access to will be backed up.

### Supplying the Key

You can make the key available in the environment as `AIRTABLE_TOKEN` or via the `--airtable-token` flag:

- `AIRTABLE_TOKEN=pat123.456 backup-airtable`
- `backup-airtable --airtable-token pat123.456`

## Exported Data Format

This tool creates folders for each base, each containing `records.json` and `schema.json`:

```
. (backup_directory)
├── videogames/
│   ├── games/
│   │   ├── schema.json
│   │   └── records.json
│   └── playthroughs/
│       ├── schema.json
│       └── records.json
└── tv/
    ├── shows/
    │   ├── schema.json
    │   └── records.json
    ├── seasons/
    │   ├── schema.json
    │   └── records.json
    └── watches/
        ├── schema.json
        └── records.json
```

The contents of each file is the raw API response for [the table's schema](https://airtable.com/developers/web/api/get-base-schema) (which includes formula definitions):

```json
{
  "fields": [
    {
      "id": "fldAReWzcSCy8lR6S",
      "name": "Name",
      "type": "singleLineText"
    },
    {
      "id": "fldapjPtWVGLeVEz6",
      "name": "Style",
      "options": {
        "choices": [
          {
            "color": "redLight2",
            "id": "selpGtES7bVHWFO68",
            "name": "Competitive"
          },
          {
            "color": "blueLight2",
            "id": "sel176WltZzGmNl3l",
            "name": "Cooperative"
          }
        ]
      },
      "type": "singleSelect"
    },
    {
      "id": "fldpMVjIrO1QjFeAy",
      "name": "Is Available?",
      "options": {
        "formula": "AND(IF({fldGC6t3qWTFCESvA}, {fldGC6t3qWTFCESvA}<={fld4hmOueoB5ah8Io}, 1), {fld4gls5vBed7NBOP} = 0)",
        "isValid": true,
        "referencedFieldIds": [
          "fldGC6t3qWTFCESvA",
          "fld4hmOueoB5ah8Io",
          "fld4gls5vBed7NBOP"
        ],
        "result": {
          "options": {
            "precision": 0
          },
          "type": "number"
        }
      },
      "type": "formula"
    }
  ],
  "id": "tblvcNVpUk07pRxUQ",
  "name": "Games",
  "primaryFieldId": "fldAReWzcSCy8lR6S",
  "views": [
    {
      "id": "viw2PrDfjQquMoTKb",
      "name": "Main View",
      "type": "grid"
    },
    {
      "id": "viweVcA0peE3M3zag",
      "name": "Add a New Game",
      "type": "form"
    }
  ]
}
```

and the [records themselves](https://airtable.com/developers/web/api/list-records):

```json
[
  {
    "commentCount": 0,
    "createdTime": "2017-09-19T06:21:48.000Z",
    "fields": {
      "Name": "Libertalia: Winds of Galecrest",
      "Style": "Competitive",
      "Is Available?": 1
    },
    "id": "rec0wIiSnMutUfoTY"
  },
  {
    "commentCount": 0,
    "createdTime": "2023-09-19T06:20:20.000Z",
    "fields": {
      "Name": "Hanabi",
      "Style": "Cooperative",
      "Is Available?": 0
    },
    "id": "rec48RFqGw8hAmZFY"
  }
]
```

### Comments

Each row in Airtable can have comments, but downloading them takes an extra API call _per row_. For bases with lots of rows with comments, this can dramatically slow down the backup.

Comments will be included, oldest to newest, on each row:

```json
  {
    "commentCount": 1,
    "comments": [
      {
        "author": {
          "email": "email@website.com",
          "id": "usrOrn2etJhbw2dem",
          "name": "Bruce Wayne"
        },
        "createdTime": "2025-02-21T08:05:25.000Z",
        "id": "comx1KUhmPiHYX10w",
        "lastUpdatedTime": null,
        "text": "cool comment!"
      }
    ],
    "createdTime": "2021-05-24T04:19:13.000Z",
    "fields": {
      "Name": "Vantage",
      "Style": "Cooperative",
      "Is Available?": 0
    },
    "id": "recKPmZ4DkjYyFrV4"
  },
```

## Differences from Upstream

This was originally forked from [simonw/airtable-export](https://github.com/simonw/airtable-export) and has since diverged. In the interest of simplicity & my own needs, I:

- made `backup_directory` optional; it defaults to `./airtable-backup-<ISO_DATE>`
- removed `ndjson`, `yaml`, and `sqlite` options; it always outputs formatted JSON
- removed `base_id`; it pulls every base the auth token has access to
- removed `user-agent` option for simplicity (though would be open to re-adding it later, if needed). It makes calls as default of `backup-airtable`
- removed `schema` option; it always dumps the schema
- removed `http-read-timeout`; it defaults to a high-enough value of 60 seconds
- it doesn't flatten the record. the top level keys are `id`, `createdTime`, and `fields`

## Development

This project uses [just](https://github.com/casey/just) for running tasks. First, create a virtualenv:

```shell
python -m venv .venv
source .venv/bin/activate
```

Then run `just install` to install the project and its development dependencies. At that point, the `backup-airtable` will be available. Run `just` to see all the available commands.
