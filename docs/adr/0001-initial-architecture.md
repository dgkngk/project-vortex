# ADR-001: Initial Vortex Architecture

## Status
Accepted

## Context
A high-throughput Quantitative Trading System requires isolation of concerns between data extraction, indicator calculation, and strategy validation.

## Decision
We chose an **ETL Pipeline based on the Factory Pattern**:
- **Extractors** pull data from external resources.
- **Transformers** calculate Technical Analysis using pandas and pandas-ta.
- **Loaders** insert the processed dataframe into specific backends (Postgres, InfluxDB, Redis).

## Consequences
**Pros:** 
- Extremely modular; adding a new exchange or Database takes minimal code changes in the core engine.
- Asynchronous tasks allow concurrency despite using Python.

**Cons:** 
- Overhead of passing dictionaries of DataFrames through the pipeline instead of processing simple sequences.
- Slightly higher cognitive complexity for new developers coming to the system.
