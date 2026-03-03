# Azure Storage Partition Strategy Simulator

Interactive, zero-install browser tools that let you **see** how Azure Storage partition behaviour affects your application — before a single byte hits production.

## The Problem

Storage throttling is the silent killer of cloud applications. Azure Storage partitions data across servers to scale horizontally, but every partition server has hard throughput ceilings:

| Service | Per-Partition Limit | Account Limit |
|---------|-------------------|---------------|
| **Table Storage** | ~2,000 ops/sec | 20,000 ops/sec |
| **Blob Storage** | ~20,000 req/sec (before auto-split) | 20,000 req/sec ingress |
| **Azure Files** | Tier-dependent IOPS & throughput | Per-share provisioned limits |

When your data or access patterns accidentally funnel traffic to a single partition — a **hot partition** — Azure returns HTTP 503 (Server Busy) and your application grinds to a halt. Retry storms amplify the problem, upstream services time out, and you're in a full outage.

The brutal part: **you won't catch this in dev or staging.** It only surfaces at production scale, and the fix is a schema/naming redesign — the most expensive kind of change.

## What These Simulators Do

| Simulator | Core Question It Answers |
|---|---|
| **[Blob Storage](https://vikasrajput.github.io/storage-simulator/simulators/blob-partition-simulator.html)** | *Will my blob naming pattern create a hot partition server?* — Compares 6 naming strategies, visualizes partition spread, flags throttling risk. |
| **[Table Storage](https://vikasrajput.github.io/storage-simulator/simulators/table-partition-simulator.html)** | *Will my PartitionKey strategy bottleneck under load?* — Simulates 6 key strategies, models entity distribution, detects when any partition exceeds 2,000 ops/sec. |
| **[Azure Files](https://vikasrajput.github.io/storage-simulator/simulators/files-partition-simulator.html)** | *Is my file share configuration sized correctly?* — Models IOPS, throughput, and capacity against tier limits with visual gauges. |

Each simulator validates inputs against real Azure service limits, produces interactive visualizations, and generates actionable recommendations specific to your configuration.

## Why This Matters for Engineering Teams

- **Shift-left on performance design.** Partition strategy is a day-zero architecture decision that's expensive to change later. Validate a design in 30 seconds instead of discovering problems in production.
- **Zero friction.** No build step, no dependencies, no cost, no Azure account needed. Open the HTML in a browser or use [GitHub Pages](https://vikasrajput.github.io/storage-simulator/simulators/).
- **Prevent the costliest outage pattern.** A 30-second simulation before deployment prevents a multi-hour throttling incident in production.
- **Eliminate tribal knowledge.** The difference between `0001.json` (hot-partition anti-pattern) and `a3f_0001.json` (excellent distribution) is one line of code — but knowing *which* line requires deep Azure internals. The simulators encode that expertise into a self-service tool any engineer can use.
- **Quantify risk in architecture reviews.** Run the simulator with your actual parameters (entity count, ops/sec, time span) and get a concrete answer instead of debating in a design doc.

## Project Structure

```
storage-simulator/
├── simulators/                        # Interactive web-based partition simulators
│   ├── index.html                     # Hub page – links to all simulators
│   ├── blob-partition-simulator.html  # Blob Storage naming & partition simulator
│   ├── files-partition-simulator.html # Azure Files performance & tier simulator
│   └── table-partition-simulator.html # Table Storage PartitionKey simulator
├── cli/                               # CLI application / utility (future)
│   └── README.md
├── demo/                              # Demos for AI and analytical workloads
│   └── README.md
└── README.md
```

## Simulators

Open the simulators directly via **GitHub Pages**:

| Simulator | Description |
|-----------|-------------|
| [Hub Page](https://vikasrajput.github.io/storage-simulator/simulators/) | Overview & quick decision guide |
| [Blob Storage](https://vikasrajput.github.io/storage-simulator/simulators/blob-partition-simulator.html) | Naming patterns, partition spread, hot-spot detection |
| [Azure Files](https://vikasrajput.github.io/storage-simulator/simulators/files-partition-simulator.html) | Tier limits, IOPS/throughput gauges, share planning |
| [Table Storage](https://vikasrajput.github.io/storage-simulator/simulators/table-partition-simulator.html) | PartitionKey strategies, entity distribution, query patterns |

> **Tip:** Enable GitHub Pages (source: root `/`) on this repo to serve the simulators at the URLs above.

## CLI (Planned)

A command-line utility for running partition simulations, generating reports, and integrating into CI/CD pipelines. See [cli/README.md](abc/act/apply/code/storage-simulator/cli/README.md).

## Demo (Planned)

End-to-end demos showcasing storage partition strategies with AI and analytical workloads. See [demo/README.md](abc/act/apply/code/storage-simulator/demo/README.md).

## Getting Started

1. Clone this repository.
2. Open any simulator HTML file directly in a browser — no build step required.
3. Or enable GitHub Pages on this repo and access them via the URLs above.

## Contributing

1. Fork the repo and create a feature branch.
2. Add or modify simulators under `simulators/`.
3. For CLI work, develop under `cli/`.
4. For demos, add under `demo/`.
5. Submit a pull request.

## License

See [LICENSE](LICENSE) if applicable.
