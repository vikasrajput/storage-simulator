"""Blob Storage analyzer – samples blob names and evaluates partition spread."""

from __future__ import annotations

from collections import Counter
from typing import Optional

from storage_assess.analyzers.base import (
    SectionFindings,
    classify_naming_pattern,
    compute_distribution_stats,
)

# Azure Blob limits
ACCOUNT_MAX_RPS = 20_000
PARTITION_RANGE_WARN_THRESHOLD = 2  # fewer distinct prefix buckets = risky


class BlobAnalyzer:
    """Analyze blob naming patterns across containers in a storage account."""

    def __init__(
        self,
        connection_string: Optional[str],
        account_name: Optional[str],
        credential,
        sample_size: int = 500,
    ):
        self._conn_str = connection_string
        self._account_name = account_name
        self._credential = credential
        self._sample_size = sample_size

    # ----- public -----
    def analyze(self) -> SectionFindings:
        findings = SectionFindings()

        try:
            client = self._build_client()
        except Exception as exc:
            findings.critical("Connection failed", str(exc))
            return findings

        containers = self._list_containers(client, findings)
        if not containers:
            findings.info("No containers", "The storage account has no blob containers.")
            findings.summary = "No blob containers found."
            return findings

        total_sampled = 0
        all_pattern_counts: Counter = Counter()
        all_prefix_buckets: Counter = Counter()

        for cname in containers:
            blobs = self._sample_blobs(client, cname)
            total_sampled += len(blobs)

            if not blobs:
                findings.info(f"Container '{cname}'", "Empty – no blobs to assess.")
                continue

            # Classify naming patterns
            pattern_counts: Counter = Counter()
            prefix_buckets: Counter = Counter()

            for bname in blobs:
                pattern = classify_naming_pattern(bname)
                pattern_counts[pattern] += 1
                # Bucket by first 3 chars (Azure's partition-range proxy)
                prefix = bname[:3].lower() if len(bname) >= 3 else bname.lower()
                prefix_buckets[prefix] += 1

            all_pattern_counts += pattern_counts
            all_prefix_buckets += prefix_buckets

            dominant_pattern, dominant_count = pattern_counts.most_common(1)[0]
            pct = round(dominant_count / len(blobs) * 100, 1)

            stats = compute_distribution_stats(dict(prefix_buckets))

            # ---- Per-container findings ----
            findings.info(
                f"Container '{cname}' – {len(blobs)} blobs sampled",
                f"Dominant naming pattern: **{dominant_pattern}** ({pct}%).  "
                f"Unique prefix buckets: {stats['bucket_count']}, "
                f"skew ratio: {stats['skew_ratio']}×.",
                **stats,
            )

            self._evaluate_container(findings, cname, dominant_pattern,
                                     pct, stats, len(blobs))

        # ---- Account-level summary ----
        if all_prefix_buckets:
            acct_stats = compute_distribution_stats(dict(all_prefix_buckets))
            self._evaluate_account(findings, acct_stats, all_pattern_counts,
                                   total_sampled, len(containers))

        return findings

    # ----- private helpers -----
    def _build_client(self):
        from azure.storage.blob import BlobServiceClient

        if self._conn_str:
            return BlobServiceClient.from_connection_string(self._conn_str)
        url = f"https://{self._account_name}.blob.core.windows.net"
        return BlobServiceClient(url, credential=self._credential)

    def _list_containers(self, client, findings: SectionFindings):
        try:
            return [c.name for c in client.list_containers()]
        except Exception as exc:
            findings.warn("Could not list containers", str(exc))
            return []

    def _sample_blobs(self, client, container_name: str):
        try:
            container = client.get_container_client(container_name)
            names = []
            for blob in container.list_blobs():
                names.append(blob.name)
                if len(names) >= self._sample_size:
                    break
            return names
        except Exception:
            return []

    # ---- evaluation logic ----
    def _evaluate_container(self, findings, cname, pattern, pct, stats, count):
        """Add warnings / recommendations for a single container."""

        # Sequential naming is the #1 anti-pattern
        if pattern == "sequential" and pct > 50:
            findings.critical(
                f"Container '{cname}': Sequential naming detected",
                f"{pct}% of sampled blobs use sequential numeric names. "
                "This concentrates all writes on a single partition range and "
                "limits throughput.  Prepend a 3–6 character hash to each blob "
                "name (e.g., a3f_0001.json) for even distribution.",
            )

        # Timestamp prefix clusters today's writes
        if pattern == "timestamp-prefix" and pct > 50:
            findings.warn(
                f"Container '{cname}': Timestamp-prefixed names",
                f"{pct}% of blobs start with a date/timestamp prefix. "
                "Today's partition range receives all current writes. "
                "Consider hash-prefix or reverse-timestamp patterns to "
                "spread load.",
            )

        # Low bucket diversity
        if stats["bucket_count"] <= PARTITION_RANGE_WARN_THRESHOLD and count > 10:
            findings.warn(
                f"Container '{cname}': Low prefix diversity",
                f"Only {stats['bucket_count']} distinct 3-char prefixes across "
                f"{count} blobs.  Azure cannot partition-balance effectively "
                "with so few prefix ranges.",
            )

        # High skew
        if stats["skew_ratio"] > 5 and stats["bucket_count"] > 2:
            findings.warn(
                f"Container '{cname}': Uneven prefix distribution",
                f"Skew ratio {stats['skew_ratio']}× — the largest prefix "
                f"bucket has {stats['max_count']} blobs vs. average "
                f"{stats['avg_count']}.  This may cause hot-partition "
                "throttling under load.",
            )

        # Good patterns
        if pattern in ("hash-prefix", "guid-prefix") and pct > 50:
            findings.ok(
                f"Container '{cname}': Good naming pattern",
                f"{pct}% of blobs use {pattern}, which distributes "
                "evenly across partition ranges.",
            )

    def _evaluate_account(self, findings, stats, pattern_counts,
                          total_sampled, container_count):
        """Account-wide summary."""
        dominant, dom_count = pattern_counts.most_common(1)[0]
        pct = round(dom_count / total_sampled * 100, 1) if total_sampled else 0

        health = "GOOD" if stats["skew_ratio"] < 3 and stats["bucket_count"] > 5 else \
                 "FAIR" if stats["skew_ratio"] < 10 else "POOR"

        findings.summary = (
            f"Assessed {total_sampled} blobs across {container_count} container(s).  "
            f"Dominant naming: {dominant} ({pct}%).  "
            f"Prefix diversity: {stats['bucket_count']} buckets, "
            f"skew {stats['skew_ratio']}×.  "
            f"Overall partition health: **{health}**."
        )

        if health == "POOR":
            findings.overall_health = findings.overall_health  # keep worst
            findings.warn(
                "Account-wide: Poor partition spread",
                f"Only {stats['bucket_count']} distinct prefix buckets with "
                f"skew ratio {stats['skew_ratio']}×.  High risk of throttling "
                "at scale.  Review naming conventions.",
            )
        elif health == "GOOD":
            findings.ok(
                "Account-wide: Healthy partition spread",
                f"{stats['bucket_count']} prefix buckets with low skew "
                f"({stats['skew_ratio']}×).  Naming patterns support "
                "scalable throughput.",
            )
