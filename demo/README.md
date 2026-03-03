# Demo – Storage Partition Strategy Demos

> **Status:** Planned

End-to-end demonstrations showcasing Azure Storage partition strategies applied to real-world AI and analytical workloads.

## Planned Demos

| Demo | Description |
|------|-------------|
| IoT Telemetry Ingestion | High-volume blob ingestion with hash-prefix naming for even partition distribution |
| Log Analytics Pipeline | Table Storage with composite PartitionKey for time-series log data |
| ML Training Data Lake | Azure Files Premium with NFS for large-model training workloads |
| Event-Driven Processing | Blob trigger + partition-aware naming for serverless pipelines |

## Structure (Future)

```
demo/
├── iot-telemetry/
│   ├── README.md
│   ├── setup.sh
│   └── src/
├── log-analytics/
│   ├── README.md
│   └── src/
├── ml-data-lake/
│   ├── README.md
│   └── src/
└── event-processing/
    ├── README.md
    └── src/
```

## Contributing

If you'd like to add a demo, please open an issue describing the scenario and the partition strategy it demonstrates.
