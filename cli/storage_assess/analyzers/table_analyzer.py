"""Table Storage analyzer – evaluates PartitionKey distribution and strategy."""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from storage_assess.analyzers.base import (
    SectionFindings,
    compute_distribution_stats,
)

# Azure Table limits
PARTITION_OPS_LIMIT = 2_000   # ops/sec per partition
TABLE_OPS_LIMIT = 20_000      # ops/sec per table / account


class TableAnalyzer:
    """Analyze Table Storage PartitionKey patterns and distribution."""

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

    def analyze(self) -> SectionFindings:
        findings = SectionFindings()

        try:
            client = self._build_client()
        except Exception as exc:
            findings.critical("Connection failed", str(exc))
            return findings

        tables = self._list_tables(client, findings)
        if not tables:
            findings.info("No tables", "The storage account has no Table Storage tables.")
            findings.summary = "No tables found."
            return findings

        total_sampled = 0
        all_pk_counts: Counter = Counter()
        all_strategy_counts: Counter = Counter()

        for tname in tables:
            entities = self._sample_entities(client, tname)
            total_sampled += len(entities)

            if not entities:
                findings.info(f"Table '{tname}'", "Empty – no entities to assess.")
                continue

            pk_counts: Counter = Counter()
            strategy_counts: Counter = Counter()

            for pk in entities:
                pk_counts[pk] += 1
                strategy = self._classify_pk_strategy(pk)
                strategy_counts[strategy] += 1

            all_pk_counts += pk_counts
            all_strategy_counts += strategy_counts

            stats = compute_distribution_stats(dict(pk_counts))
            dominant_strat, dom_count = strategy_counts.most_common(1)[0]
            pct = round(dom_count / len(entities) * 100, 1)

            findings.info(
                f"Table '{tname}' – {len(entities)} entities sampled",
                f"Unique partitions: {stats['bucket_count']}, "
                f"dominant strategy: **{dominant_strat}** ({pct}%), "
                f"skew ratio: {stats['skew_ratio']}×.",
                **stats,
            )

            self._evaluate_table(findings, tname, stats, dominant_strat,
                                 pct, len(entities))

        # Account summary
        if all_pk_counts:
            acct_stats = compute_distribution_stats(dict(all_pk_counts))
            self._account_summary(findings, acct_stats, all_strategy_counts,
                                  total_sampled, len(tables))

        return findings

    # ---- private helpers ----
    def _build_client(self):
        from azure.data.tables import TableServiceClient

        if self._conn_str:
            return TableServiceClient.from_connection_string(self._conn_str)
        url = f"https://{self._account_name}.table.core.windows.net"
        return TableServiceClient(url, credential=self._credential)

    def _list_tables(self, client, findings: SectionFindings):
        try:
            return [t.name for t in client.list_tables()]
        except Exception as exc:
            findings.warn("Could not list tables", str(exc))
            return []

    def _sample_entities(self, client, table_name: str):
        """Return a list of PartitionKey values from sampled entities."""
        try:
            table = client.get_table_client(table_name)
            pks = []
            for entity in table.list_entities(results_per_page=self._sample_size):
                pks.append(entity["PartitionKey"])
                if len(pks) >= self._sample_size:
                    break
            return pks
        except Exception:
            return []

    @staticmethod
    def _classify_pk_strategy(pk: str) -> str:
        """Heuristic to identify the PartitionKey strategy."""
        if not pk:
            return "empty"

        # GUID
        if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", pk, re.I):
            return "unique-guid"

        # Date-based (yyyy-MM-dd or yyyyMMdd or Day_NNNN)
        if re.match(r"^\d{4}[-/]?\d{2}[-/]?\d{2}$", pk):
            return "date-day"
        if re.match(r"^\d{4}[-/]?\d{2}$", pk):
            return "date-month"

        # Hash-bucket (Bucket_NNN or numeric-only small range)
        if re.match(r"^(bucket|hash|shard)[_-]?\d+$", pk, re.I):
            return "hash-bucket"

        # Purely numeric / sequential
        if re.match(r"^\d+$", pk):
            return "sequential-numeric"

        # Composite (contains two segments with separator)
        if re.search(r"[_|:]{2}|__", pk):
            return "composite"

        # Category-like (short alphanumeric, no date)
        if re.match(r"^[A-Za-z][\w-]{0,30}$", pk):
            return "category"

        return "other"

    def _evaluate_table(self, findings, tname, stats, strategy, pct, count):
        """Per-table findings."""

        # Single partition – all entities share one PK
        if stats["bucket_count"] == 1 and count > 10:
            findings.critical(
                f"Table '{tname}': Single partition",
                "All sampled entities share one PartitionKey. This creates a "
                "hard scalability ceiling of ~2,000 ops/sec. Use a partitioning "
                "strategy (date, category, hash-bucket) to distribute load.",
            )

        # Very few partitions
        elif stats["bucket_count"] <= 3 and count > 50:
            findings.warn(
                f"Table '{tname}': Very few partitions ({stats['bucket_count']})",
                "Limited partition diversity restricts throughput. Consider "
                "a composite key or hash-bucket strategy to spread entities.",
            )

        # High skew
        if stats["skew_ratio"] > 10 and stats["bucket_count"] > 1:
            findings.warn(
                f"Table '{tname}': Highly skewed distribution",
                f"Largest partition has {stats['skew_ratio']}× the average "
                f"entity count ({stats['max_count']:,} vs avg {stats['avg_count']:,}). "
                "This partition will become a hot spot under load.",
            )
        elif stats["skew_ratio"] > 5 and stats["bucket_count"] > 1:
            findings.warn(
                f"Table '{tname}': Moderate skew",
                f"Skew ratio {stats['skew_ratio']}× indicates uneven "
                "distribution. Monitor for throttling at scale.",
            )

        # Sequential numeric keys
        if strategy == "sequential-numeric" and pct > 50:
            findings.warn(
                f"Table '{tname}': Sequential numeric PartitionKeys",
                "Sequential numbers create hot append partitions and prevent "
                "Azure from distributing load. Consider date-based, composite, "
                "or hash-bucket strategies.",
            )

        # Unique GUID keys – good distribution but no batch ops
        if strategy == "unique-guid" and pct > 50:
            findings.info(
                f"Table '{tname}': GUID PartitionKeys",
                "Every entity gets its own partition — excellent for write "
                "parallelism, but Entity Group Transactions (batch) are "
                "impossible and partition-scoped queries won't help.",
            )

        # Good distribution
        if (stats["bucket_count"] > 10 and stats["skew_ratio"] < 3
                and strategy not in ("sequential-numeric", "empty")):
            findings.ok(
                f"Table '{tname}': Healthy partition distribution",
                f"{stats['bucket_count']} unique partitions with low skew "
                f"({stats['skew_ratio']}×). Strategy '{strategy}' supports "
                "scalable throughput.",
            )

    def _account_summary(self, findings, stats, strategy_counts,
                         total_sampled, table_count):
        dominant, dom_count = strategy_counts.most_common(1)[0]
        pct = round(dom_count / total_sampled * 100, 1) if total_sampled else 0

        health = (
            "GOOD" if stats["skew_ratio"] < 3 and stats["bucket_count"] > 10 else
            "FAIR" if stats["skew_ratio"] < 10 else
            "POOR"
        )

        findings.summary = (
            f"Assessed {total_sampled} entities across {table_count} table(s).  "
            f"Unique partitions: {stats['bucket_count']}, "
            f"dominant strategy: {dominant} ({pct}%).  "
            f"Skew ratio: {stats['skew_ratio']}×.  "
            f"Overall partition health: **{health}**."
        )
