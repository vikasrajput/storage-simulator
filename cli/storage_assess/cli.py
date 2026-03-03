"""CLI entry-point using Click."""

import click
from storage_assess import __version__


@click.group()
@click.version_option(__version__, prog_name="storage-assess")
def main():
    """Assess Azure Storage account partition strategies.

    Connects to a live storage account (via connection string or
    DefaultAzureCredential) and analyzes naming patterns, partition
    key distribution, and share configuration to provide
    actionable recommendations.
    """


# ---------------------------------------------------------------------------
# Common options shared by sub-commands
# ---------------------------------------------------------------------------
_common_options = [
    click.option(
        "--connection-string", "-c",
        envvar="AZURE_STORAGE_CONNECTION_STRING",
        default=None,
        help="Storage account connection string.  "
             "Falls back to AZURE_STORAGE_CONNECTION_STRING env var.",
    ),
    click.option(
        "--account-name", "-a",
        envvar="AZURE_STORAGE_ACCOUNT",
        default=None,
        help="Storage account name (uses DefaultAzureCredential).  "
             "Falls back to AZURE_STORAGE_ACCOUNT env var.",
    ),
    click.option(
        "--sample-size", "-n",
        default=500,
        show_default=True,
        type=int,
        help="Max items to sample per container/table/share.",
    ),
    click.option(
        "--output", "-o",
        type=click.Choice(["text", "json"], case_sensitive=False),
        default="text",
        show_default=True,
        help="Output format.",
    ),
]


def add_common_options(func):
    """Decorator that attaches the shared options to a command."""
    for option in reversed(_common_options):
        func = option(func)
    return func


def _resolve_credentials(connection_string, account_name):
    """Return (connection_string | None, account_name | None, credential | None)."""
    if connection_string:
        return connection_string, None, None
    if account_name:
        from azure.identity import DefaultAzureCredential
        return None, account_name, DefaultAzureCredential()
    raise click.UsageError(
        "Provide --connection-string / -c  OR  --account-name / -a  "
        "(or set AZURE_STORAGE_CONNECTION_STRING / AZURE_STORAGE_ACCOUNT)."
    )


# ---------------------------------------------------------------------------
# assess all
# ---------------------------------------------------------------------------
@main.command("all")
@add_common_options
def assess_all(connection_string, account_name, sample_size, output):
    """Assess all storage types (blob, files, table)."""
    conn_str, acct, cred = _resolve_credentials(connection_string, account_name)
    from storage_assess.report import Report

    report = Report(output_format=output)
    _run_blob(conn_str, acct, cred, sample_size, report)
    _run_files(conn_str, acct, cred, sample_size, report)
    _run_table(conn_str, acct, cred, sample_size, report)
    report.print()


# ---------------------------------------------------------------------------
# assess blob
# ---------------------------------------------------------------------------
@main.command("blob")
@add_common_options
def assess_blob(connection_string, account_name, sample_size, output):
    """Assess Blob Storage partition strategy."""
    conn_str, acct, cred = _resolve_credentials(connection_string, account_name)
    from storage_assess.report import Report

    report = Report(output_format=output)
    _run_blob(conn_str, acct, cred, sample_size, report)
    report.print()


# ---------------------------------------------------------------------------
# assess files
# ---------------------------------------------------------------------------
@main.command("files")
@add_common_options
def assess_files(connection_string, account_name, sample_size, output):
    """Assess Azure Files share configuration."""
    conn_str, acct, cred = _resolve_credentials(connection_string, account_name)
    from storage_assess.report import Report

    report = Report(output_format=output)
    _run_files(conn_str, acct, cred, sample_size, report)
    report.print()


# ---------------------------------------------------------------------------
# assess table
# ---------------------------------------------------------------------------
@main.command("table")
@add_common_options
def assess_table(connection_string, account_name, sample_size, output):
    """Assess Table Storage partition-key strategy."""
    conn_str, acct, cred = _resolve_credentials(connection_string, account_name)
    from storage_assess.report import Report

    report = Report(output_format=output)
    _run_table(conn_str, acct, cred, sample_size, report)
    report.print()


# ---------------------------------------------------------------------------
# Internal runners
# ---------------------------------------------------------------------------
def _run_blob(conn_str, acct, cred, sample_size, report):
    from storage_assess.analyzers.blob_analyzer import BlobAnalyzer

    analyzer = BlobAnalyzer(conn_str, acct, cred, sample_size)
    findings = analyzer.analyze()
    report.add_section("Blob Storage", findings)


def _run_files(conn_str, acct, cred, sample_size, report):
    from storage_assess.analyzers.files_analyzer import FilesAnalyzer

    analyzer = FilesAnalyzer(conn_str, acct, cred, sample_size)
    findings = analyzer.analyze()
    report.add_section("Azure Files", findings)


def _run_table(conn_str, acct, cred, sample_size, report):
    from storage_assess.analyzers.table_analyzer import TableAnalyzer

    analyzer = TableAnalyzer(conn_str, acct, cred, sample_size)
    findings = analyzer.analyze()
    report.add_section("Table Storage", findings)
