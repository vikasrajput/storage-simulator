"""Azure Files analyzer – evaluates share configuration against performance limits."""

from __future__ import annotations

from typing import Optional

from storage_assess.analyzers.base import SectionFindings


# Azure Files per-share limits (approximate)
TIER_LIMITS = {
    "Premium": {
        "baseline_iops": 3_000,
        "iops_per_gib": 1,
        "max_iops": 100_000,
        "baseline_throughput_mibs": 100,
        "throughput_per_gib": 0.04,
        "max_throughput_mibs": 10_240,
    },
    "TransactionOptimized": {
        "baseline_iops": 10_000,
        "iops_per_gib": 0,
        "max_iops": 10_000,
        "baseline_throughput_mibs": 300,
        "throughput_per_gib": 0,
        "max_throughput_mibs": 300,
    },
    "Hot": {
        "baseline_iops": 10_000,
        "iops_per_gib": 0,
        "max_iops": 10_000,
        "baseline_throughput_mibs": 300,
        "throughput_per_gib": 0,
        "max_throughput_mibs": 300,
    },
    "Cool": {
        "baseline_iops": 10_000,
        "iops_per_gib": 0,
        "max_iops": 10_000,
        "baseline_throughput_mibs": 300,
        "throughput_per_gib": 0,
        "max_throughput_mibs": 300,
    },
}

MAX_CONNECTIONS_PER_SHARE = 10_000


class FilesAnalyzer:
    """Analyze Azure Files shares – tier, capacity, provisioned limits."""

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

        shares = self._list_shares(client, findings)
        if not shares:
            findings.info("No file shares", "The storage account has no Azure File shares.")
            findings.summary = "No Azure File shares found."
            return findings

        total_provisioned_gib = 0
        share_details = []

        for share_info in shares:
            name = share_info["name"]
            quota_gib = share_info.get("quota_gib", 0)
            tier = share_info.get("tier", "Unknown")
            protocol = share_info.get("protocol", "SMB")

            total_provisioned_gib += quota_gib

            limits = self._compute_limits(tier, quota_gib)
            sd = {
                "name": name,
                "tier": tier,
                "protocol": protocol,
                "quota_gib": quota_gib,
                **limits,
            }
            share_details.append(sd)

            # Per-share assessment
            findings.info(
                f"Share '{name}' ({tier}, {protocol})",
                f"Provisioned: {quota_gib} GiB  |  "
                f"IOPS limit: {limits['prov_iops']:,}  |  "
                f"Throughput: {limits['prov_throughput_mibs']:.0f} MiB/s",
                **sd,
            )

            self._evaluate_share(findings, sd)

        # File count sampling
        for share_info in shares:
            file_count = self._count_files(client, share_info["name"])
            if file_count is not None:
                if file_count > 1_000_000:
                    findings.warn(
                        f"Share '{share_info['name']}': High file count",
                        f"~{file_count:,}+ files detected (sampled). "
                        "Large directories degrade listing performance. "
                        "Consider flatter structures or splitting across shares.",
                    )

        # Account summary
        self._account_summary(findings, share_details, total_provisioned_gib)
        return findings

    # ---- private helpers ----
    def _build_client(self):
        from azure.storage.fileshare import ShareServiceClient

        if self._conn_str:
            return ShareServiceClient.from_connection_string(self._conn_str)
        url = f"https://{self._account_name}.file.core.windows.net"
        return ShareServiceClient(url, credential=self._credential)

    def _list_shares(self, client, findings: SectionFindings):
        try:
            result = []
            for s in client.list_shares(include_metadata=True):
                tier = "Unknown"
                # The access_tier property is available on premium / v2 shares
                if hasattr(s, "access_tier") and s.access_tier:
                    tier = s.access_tier
                elif s.metadata and s.metadata.get("AccessTier"):
                    tier = s.metadata["AccessTier"]

                protocol = "SMB"
                if hasattr(s, "protocols") and s.protocols:
                    protocol = s.protocols
                elif hasattr(s, "enabled_protocols") and s.enabled_protocols:
                    protocol = s.enabled_protocols

                result.append({
                    "name": s.name,
                    "quota_gib": s.quota or 0,
                    "tier": tier,
                    "protocol": str(protocol),
                })
            return result
        except Exception as exc:
            findings.warn("Could not list shares", str(exc))
            return []

    def _count_files(self, client, share_name: str):
        """Sample file listing to estimate file count."""
        try:
            share = client.get_share_client(share_name)
            root = share.get_directory_client("")
            count = 0
            for _ in root.list_directories_and_files():
                count += 1
                if count >= self._sample_size:
                    break
            return count
        except Exception:
            return None

    @staticmethod
    def _compute_limits(tier: str, quota_gib: int) -> dict:
        """Compute provisioned IOPS and throughput based on tier + size."""
        tl = TIER_LIMITS.get(tier, TIER_LIMITS.get("Hot", {}))
        if not tl:
            return {"prov_iops": 0, "prov_throughput_mibs": 0}

        iops = min(
            tl["max_iops"],
            tl["baseline_iops"] + int(tl["iops_per_gib"] * quota_gib),
        )
        tp = min(
            tl["max_throughput_mibs"],
            tl["baseline_throughput_mibs"] + tl["throughput_per_gib"] * quota_gib,
        )
        return {"prov_iops": iops, "prov_throughput_mibs": round(tp, 1)}

    def _evaluate_share(self, findings, sd):
        """Per-share recommendations."""
        tier = sd["tier"]
        quota = sd["quota_gib"]
        name = sd["name"]

        # Very small Premium share – under-provisioned IOPS
        if tier == "Premium" and quota < 256:
            findings.warn(
                f"Share '{name}': Small Premium share",
                f"Only {quota} GiB provisioned.  Premium IOPS = 3,000 + 1×GiB. "
                "Consider increasing provisioned size to unlock more IOPS, "
                "even if you don't need the space.",
            )

        # NFS on non-Premium
        if "nfs" in sd["protocol"].lower() and tier != "Premium":
            findings.critical(
                f"Share '{name}': NFS on non-Premium tier",
                "NFS 4.1 is only supported on Premium (SSD) tier. "
                "This share may not function correctly.",
            )

        # Cool tier with high IOPS potential
        if tier == "Cool":
            findings.info(
                f"Share '{name}': Cool tier",
                "Cool tier has lower storage costs but higher per-transaction "
                "costs.  Best for infrequent-access / archive workloads.",
            )

        # Good Premium config
        if tier == "Premium" and quota >= 1024:
            findings.ok(
                f"Share '{name}': Well-provisioned Premium share",
                f"{quota} GiB gives {sd['prov_iops']:,} IOPS and "
                f"{sd['prov_throughput_mibs']:.0f} MiB/s throughput.  "
                "Enable SMB Multichannel for maximum single-client performance.",
            )

    def _account_summary(self, findings, share_details, total_gib):
        share_count = len(share_details)
        tiers = set(sd["tier"] for sd in share_details)
        total_iops = sum(sd["prov_iops"] for sd in share_details)

        findings.summary = (
            f"Assessed {share_count} file share(s), "
            f"total provisioned: {total_gib:,} GiB.  "
            f"Tiers: {', '.join(tiers)}.  "
            f"Aggregate IOPS capacity: {total_iops:,}."
        )

        if share_count == 1 and total_gib > 5120:
            findings.warn(
                "Single large share",
                f"All {total_gib:,} GiB on one share.  Consider splitting "
                "across multiple shares for workload isolation and independent "
                "IOPS limits.",
            )
