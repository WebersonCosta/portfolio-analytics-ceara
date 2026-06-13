# Codebase Concerns

**Analysis Date:** 2026-06-13

## Tech Debt

**Omission of Final Service Providers (Monopolistic Intermediaries):**
- Issue: Large transaction volumes (e.g., R$ 8.0M in Caucaia) are billed directly to fleet management intermediaries (e.g., *7SERV GESTAO DE BENEFICIOS LTDA*), which obscures the actual workshops doing the work.
- Files: [src/etl.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/etl.py) (master name mapping) and [src/app.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/app.py) (Top 10 Prestadores query).
- Impact: Transparency is compromised, hiding the actual local workshops receiving public money.
- Fix approach: Request subcontractor receipt details or cross-reference secondary invoice registries if available in the SIM database.

**Zero Automated Testing:**
- Issue: No unit or integration testing framework is configured.
- Files: Project root and [src/](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/).
- Impact: Refactoring the ETL logic (such as text normalizations or currency formatting) can introduce silent regressions in financial values or dashboard calculations.
- Fix approach: Implement a simple test suite using `pytest` to validate `etl.py` sanitization and `quarentena.py` filtering.

## Known Bugs

- None currently identified.

## Security Considerations

**API calls ignore SSL validation:**
- Risk: In `etl.py` and `app.py`, requests to the TCE-CE endpoints use `verify=False`. This makes the application vulnerable to man-in-the-middle (MITM) attacks when retrieving municipality budgets.
- Files: [src/etl.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/etl.py) (line 282) and [src/app.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/app.py) (line 438).
- Current mitigation: None (relying on public, non-sensitive endpoints).
- Recommendations: Install proper CA root certificates and configure `requests` to verify HTTPS signatures properly.

## Performance Bottlenecks

**Synchronous Network Dependencies:**
- Problem: The dashboard downloads the Ceará GeoJSON raw file (approx. 1MB) and contacts the TCE-CE API synchronously on initial launch or cache expiry.
- File: [src/app.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/app.py) (lines 38-55 and 434-445).
- Measurement: 3.5s to 5.0s load time on standard connections. The map fails entirely if raw.githubusercontent.com is blocked or the TCE-CE API is offline.
- Cause: Synchronous `requests.get` blocks rendering.
- Improvement path: Download the Ceará GeoJSON file and store it locally inside `dados/` or `src/assets/`. Cache LOA budget data in a local SQLite file instead of purely in-memory.

## Fragile Areas

**Unicode Normalization NFKD:**
- File: [src/etl.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/etl.py) (lines 20-31).
- Why fragile: Resolving name mismatches between databases relies entirely on a custom string sanitization function. If a municipality name changes or is mistyped with a new character style, database joins might silently fail or discard records.
- Test coverage: No tests.

## Scaling Limits

**Pandas In-Memory Processing:**
- Current capacity: Handles ~50k OS records easily.
- Limit: Will experience significant slowdowns if dataset sizes grow above 500k rows (due to multiple serial merges and groupbys).
- Symptoms: Dashboard lags for several seconds on filter selection.
- Scaling path: Migrate the ETL transformation pipeline to SQLite or DuckDB, querying pre-aggregated records rather than computing them on the fly.

## Dependencies at Risk

- None.

## Missing Critical Features

**Lack of Persistent Local Database:**
- Problem: The ETL pipeline runs in memory on every application startup.
- Workaround: Caching using Streamlit's `@st.cache_data`.
- Blocks: Prevents historic comparison across multiple years without loading gigabytes of raw CSV data.
- Implementation complexity: Medium (requires writing a lightweight SQLite database generator script).

---

*Concerns audit: 2026-06-13*
*Update as issues are fixed or new ones discovered*
