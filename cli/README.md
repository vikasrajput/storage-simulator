# Storage Assess CLI

A command-line tool that connects to a live Azure Storage account, samples blob names, file share configurations, and table PartitionKeys, then reports whether the partition strategy is healthy and provides actionable recommendations.

## Quick Start

```bash
cd cli
pip install -r requirements.txt

# Using a connection string
python -m storage_assess all -c "DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"

# Using DefaultAzureCredential (az login)
python -m storage_assess all -a mystorageaccount
```

## Commands

| Command | Description |
|---------|-------------|
| `all`   | Assess **all** storage types (blob, files, table) |
| `blob`  | Assess Blob Storage naming patterns and partition spread |
| `files` | Assess Azure Files share tier, provisioned IOPS/throughput |
| `table` | Assess Table Storage PartitionKey distribution |

## Options

| Flag | Short | Env Var | Description |
|------|-------|---------|-------------|
| `--connection-string` | `-c` | `AZURE_STORAGE_CONNECTION_STRING` | Storage account connection string |
| `--account-name` | `-a` | `AZURE_STORAGE_ACCOUNT` | Account name (uses DefaultAzureCredential) |
| `--sample-size` | `-n` | — | Max items to sample per container/table/share (default: 500) |
| `--output` | `-o` | — | Output format: `text` (rich tables) or `json` |

## Examples

```bash
# Assess only blob containers
python -m storage_assess blob -a mystorageaccount

# Assess table storage with larger sample and JSON output
python -m storage_assess table -a mystorageaccount -n 2000 -o json

# Assess files with connection string from env var
export AZURE_STORAGE_CONNECTION_STRING="..."
python -m storage_assess files
```

## What It Checks

### Blob Storage
- Naming patterns (sequential, timestamp-prefix, hash-prefix, GUID, category-date)
- Prefix diversity (3-char bucket distribution)
- Skew ratio and hot-partition risk
- Container strategy recommendations

### Azure Files
- Tier and provisioned size vs. IOPS/throughput limits
- NFS protocol on non-Premium tier
- Under-provisioned Premium shares
- File count and listing performance concerns

### Table Storage
- PartitionKey strategy classification (date, category, GUID, hash-bucket, sequential, composite)
- Partition count and distribution uniformity
- Skew ratio and hot-partition detection
- Batch operation compatibility

## Project Structure

```
cli/
├── requirements.txt
├── README.md
└── storage_assess/
    ├── __init__.py
    ├── __main__.py          # python -m entry point
    ├── cli.py               # Click CLI commands
    ├── report.py            # Rich text / JSON output
    └── analyzers/
        ├── __init__.py
        ├── base.py          # Shared types & distribution math
        ├── blob_analyzer.py
        ├── files_analyzer.py
        └── table_analyzer.py
```

## Authentication

The CLI supports two authentication methods:

1. **Connection string** (`-c`): Includes account key, works out of the box.
2. **Account name** (`-a`): Uses `DefaultAzureCredential` from azure-identity. Run `az login` first, or configure a service principal.

## Contributing

See the root [README](abc/act/apply/code/storage-simulator/README.md) for contribution guidelines.
