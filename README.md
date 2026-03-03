# Azure Storage Partition Strategy Simulator

Storage Simulator and Utilities with Demos for AI and Analytical Workloads.

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

A command-line utility for running partition simulations, generating reports, and integrating into CI/CD pipelines. See [cli/README.md](cli/README.md).

## Demo (Planned)

End-to-end demos showcasing storage partition strategies with AI and analytical workloads. See [demo/README.md](demo/README.md).

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
