"""Base classes and shared types used by all analyzers."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class Severity(str, Enum):
    """Severity levels for findings."""

    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Finding:
    """A single assessment finding."""

    title: str
    detail: str
    severity: Severity = Severity.INFO
    data: Dict | None = None  # optional raw metrics


@dataclass
class SectionFindings:
    """Collection of findings for one storage type."""

    summary: str = ""
    overall_health: Severity = Severity.OK
    findings: List[Finding] = field(default_factory=list)

    # ---- helpers ----
    def ok(self, title: str, detail: str, **kw):
        self.findings.append(Finding(title, detail, Severity.OK, kw or None))

    def info(self, title: str, detail: str, **kw):
        self.findings.append(Finding(title, detail, Severity.INFO, kw or None))

    def warn(self, title: str, detail: str, **kw):
        self.findings.append(Finding(title, detail, Severity.WARNING, kw or None))
        if self.overall_health.value < Severity.WARNING.value:
            self.overall_health = Severity.WARNING

    def critical(self, title: str, detail: str, **kw):
        self.findings.append(Finding(title, detail, Severity.CRITICAL, kw or None))
        self.overall_health = Severity.CRITICAL


# ---------------------------------------------------------------------------
# Partition-distribution utilities
# ---------------------------------------------------------------------------

def compute_distribution_stats(bucket_counts: Dict[str, int]) -> Dict:
    """Compute skew / uniformity metrics from a dict of {key: count}.

    Returns dict with keys:
        total_items, bucket_count, max_count, min_count, avg_count,
        std_dev, coefficient_of_variation, skew_ratio
    """
    if not bucket_counts:
        return {
            "total_items": 0, "bucket_count": 0,
            "max_count": 0, "min_count": 0, "avg_count": 0,
            "std_dev": 0, "coefficient_of_variation": 0, "skew_ratio": 0,
        }

    values = list(bucket_counts.values())
    n = len(values)
    total = sum(values)
    avg = total / n
    max_c = max(values)
    min_c = min(values)
    variance = sum((v - avg) ** 2 for v in values) / n
    std_dev = math.sqrt(variance)
    cv = (std_dev / avg) if avg else 0
    skew = (max_c / avg) if avg else 0

    return {
        "total_items": total,
        "bucket_count": n,
        "max_count": max_c,
        "min_count": min_c,
        "avg_count": round(avg, 1),
        "std_dev": round(std_dev, 1),
        "coefficient_of_variation": round(cv, 3),
        "skew_ratio": round(skew, 2),
    }


def classify_naming_pattern(name: str) -> str:
    """Heuristic classification of a blob/file name into a naming pattern."""
    import re

    if not name:
        return "unknown"

    # GUID prefix:  xxxxxxxx-xxxx-... or hex(8)/...
    if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", name, re.I):
        return "guid-prefix"

    # Hash prefix: 2-6 hex chars followed by _ or /
    if re.match(r"^[0-9a-f]{2,6}[_/]", name, re.I):
        return "hash-prefix"

    # Reverse timestamp (large digit string)
    if re.match(r"^\d{10,}_", name):
        return "reverse-timestamp"

    # Timestamp prefix: yyyy-MM-dd or yyyyMMdd
    if re.match(r"^\d{4}[-/]?\d{2}[-/]?\d{2}", name):
        return "timestamp-prefix"

    # Category/date path:  word/yyyy/MM/...
    if re.match(r"^[a-zA-Z]+/\d{4}/\d{2}", name):
        return "category-date"

    # Purely sequential numbers
    if re.match(r"^\d+\.", name):
        return "sequential"

    return "other"
