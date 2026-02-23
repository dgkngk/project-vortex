# Engineering Guidelines

## Naming Conventions
- **Functions, variables, test cases, and test files:** Use `snake_case`.
- **Classes and class file names:** Use `PascalCase` (e.g., `BaseController.py`, `class Portfolio`).
- **Enums:** Use `ALL_CAPS_SNAKE_CASE`. They don't always need to be in their own class.
- **Files:** All file names must be `PascalCase` unless they are `__init__.py` or `test_*` files.

## Architectural Patterns
The project follows a highly modular architecture based on **Base Classes** and **Factory Patterns**, especially within the ETL and Backtesting modules.

### ETL Pipeline
- **Controllers:** Orchestrate the flow (Extraction -> Transformation -> Loading).
- **Extractors:** Handle raw data fetching from external APIs (Binance, CoinGecko, Polygon).
- **Transformers:** Clean and reshape raw data into internal formats.
- **Loaders:** Save transformed data into appropriate storage tiers.
- **Factories:** Centralized creation of components based on Enums.

### Backtesting
- **Event-Driven:** Uses `Position`, `Order`, `Fill`, and `Portfolio` classes to simulate real market interactions.
- **Vectorized:** Uses Pandas for rapid bulk calculation of strategies over historical data.

## Logging Standards
- All components should use the `VortexLogger` found in `backend/core/VortexLogger.py`.
- Logs are stored in the `./.logs` directory.
- Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, `EXCEPTION`.
- Default format: `%(asctime)-15s %(levelname)s > %(module)s: %(message)s`.

## Testing Standards
- **Framework:** `pytest`.
- **Markers:**
    - `@pytest.mark.unit`: Fast unit tests with mocks.
    - `@pytest.mark.contract`: Tests that hit real external APIs.
    - `@pytest.mark.slow`: Long-running integration or performance tests.
- **naming:** Test files must start with `test_`.
- **reproduction:** Bug fixes must include a reproduction test case.

## Development Workflow
1. **Research:** Map codebase, validate assumptions, and reproduce issues.
2. **Strategy:** Formulate a grounded plan and share a summary.
3. **Execution:** Plan -> Act -> Validate. Surgical changes with automated verification.

## Documentation
- **Diagrams:** Use **PlantUML** for all architectural and flow diagrams.
- **Code Comments:** Focus on explaining the algorithm itself. Avoid deductions or thought chains in comments.
- **Markdown:** All documentation and project descriptions should be in Markdown format.
