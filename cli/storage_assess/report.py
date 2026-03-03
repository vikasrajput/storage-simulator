"""Report formatter – renders findings as rich text or JSON."""

from __future__ import annotations

import json
from typing import Dict, List

from storage_assess.analyzers.base import SectionFindings, Severity


_SEVERITY_ICON = {
    Severity.OK: "\u2705",        # ✅
    Severity.INFO: "\u2139\ufe0f",  # ℹ️
    Severity.WARNING: "\u26a0\ufe0f",  # ⚠️
    Severity.CRITICAL: "\U0001f6a8",   # 🚨
}

_SEVERITY_COLOR = {
    Severity.OK: "green",
    Severity.INFO: "cyan",
    Severity.WARNING: "yellow",
    Severity.CRITICAL: "red",
}


class Report:
    """Collects SectionFindings and renders them."""

    def __init__(self, output_format: str = "text"):
        self._format = output_format.lower()
        self._sections: List[Dict] = []

    def add_section(self, title: str, findings: SectionFindings):
        self._sections.append({"title": title, "findings": findings})

    def print(self):
        if self._format == "json":
            self._print_json()
        else:
            self._print_text()

    # ---- text (rich) output ----
    def _print_text(self):
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text

            console = Console()
            self._print_rich(console)
        except ImportError:
            # Fallback to plain text if rich is not installed
            self._print_plain()

    def _print_rich(self, console):
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console.print()
        console.print(
            Panel.fit(
                "[bold]Storage Account Partition Assessment[/bold]",
                border_style="blue",
            )
        )
        console.print()

        for sec in self._sections:
            title = sec["title"]
            f: SectionFindings = sec["findings"]

            health_color = _SEVERITY_COLOR.get(f.overall_health, "white")
            console.print(
                f"[bold underline]{title}[/bold underline]  "
                f"[{health_color}]{f.overall_health.value.upper()}[/{health_color}]"
            )

            if f.summary:
                console.print(f"  {f.summary}")
            console.print()

            if f.findings:
                table = Table(show_header=True, header_style="bold", expand=True)
                table.add_column("", width=3, no_wrap=True)
                table.add_column("Finding", ratio=2)
                table.add_column("Detail", ratio=5)

                for finding in f.findings:
                    icon = _SEVERITY_ICON.get(finding.severity, " ")
                    color = _SEVERITY_COLOR.get(finding.severity, "white")
                    table.add_row(
                        icon,
                        Text(finding.title, style=f"bold {color}"),
                        finding.detail,
                    )

                console.print(table)
            console.print()

    def _print_plain(self):
        """Plain-text fallback without rich."""
        print()
        print("=" * 60)
        print("  Storage Account Partition Assessment")
        print("=" * 60)

        for sec in self._sections:
            title = sec["title"]
            f: SectionFindings = sec["findings"]

            print()
            print(f"--- {title} [{f.overall_health.value.upper()}] ---")
            if f.summary:
                print(f"  {f.summary}")
            print()

            for finding in f.findings:
                icon = _SEVERITY_ICON.get(finding.severity, " ")
                print(f"  {icon} {finding.title}")
                print(f"     {finding.detail}")
                print()

    # ---- JSON output ----
    def _print_json(self):
        output = []
        for sec in self._sections:
            f: SectionFindings = sec["findings"]
            output.append({
                "section": sec["title"],
                "overall_health": f.overall_health.value,
                "summary": f.summary,
                "findings": [
                    {
                        "severity": fd.severity.value,
                        "title": fd.title,
                        "detail": fd.detail,
                        "data": fd.data,
                    }
                    for fd in f.findings
                ],
            })
        print(json.dumps(output, indent=2, default=str))
