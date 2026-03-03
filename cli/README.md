# CLI – Storage Partition Simulator

> **Status:** Planned

A command-line utility for running Azure Storage partition simulations offline, generating reports, and integrating partition analysis into CI/CD pipelines.

## Planned Features

- Run blob, files, and table partition simulations from the terminal
- Output results as JSON, CSV, or Markdown reports
- Accept configuration via YAML/JSON files or CLI flags
- Integrate into CI/CD pipelines to validate partition strategies before deployment
- Support for custom partition key generators

## Technology Options

| Option | Notes |
|--------|-------|
| Python | Rich ecosystem, easy CLI with `click` or `typer` |
| Node.js | Reuse existing JavaScript simulation logic from `simulators/` |
| .NET | Native Azure SDK integration |

## Getting Started (Future)

```bash
# Example (Python)
pip install storage-simulator
storage-sim blob --pattern hash-prefix --count 500000

# Example (Node.js)
npx storage-simulator table --strategy hash-bucket --entities 100000
```

## Contributing

If you'd like to contribute to the CLI, please open an issue to discuss the design approach before submitting a PR.
