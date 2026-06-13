# Testing Patterns

**Analysis Date:** 2026-06-13

## Test Framework

**Runner:**
- None - There is currently no automated testing framework (like PyTest or unittest) configured in the codebase.

**Assertion Library:**
- None.

**Run Commands:**
- Automated test commands do not exist.
- Manual execution of the Streamlit dashboard:
```bash
python -m streamlit run src/app.py
```

## Test File Organization

- No automated test files exist (e.g., `test_*.py` or `*_test.py`).

## Test Structure

- Verification is performed manually by checking data consistency and interface output.

## Mocking

- Currently, mocking is not implemented. Real datasets are loaded from the `dados/` directory, and live APIs are queried directly.
- Fallback mock data structures (empty DataFrames with correct schemas) are returned when the TCE-CE API is unreachable.

## Fixtures and Factories

- No test fixtures or mock factories are defined.

## Coverage

- Coverage metrics are not tracked.

## Test Types

**Manual Exploratory Testing:**
- The Jupyter notebook [analise_manutencao_veiculos.ipynb](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/notebook/analise_manutencao_veiculos.ipynb) serves as the primary sandbox environment where new data transformation functions and outlier logic are tested and visualised before incorporation into the `src/` modules.

**Visual Dashboard Verification:**
- After modifying the ETL pipeline or Streamlit code, developers run the application locally and check:
  - If KPIs load correctly without syntax or runtime errors.
  - If the interactive map filters and color-scales map correctly.
  - If selecting a specific municipality updates secondary components re-actively.
  - If API fallbacks trigger gracefully when offline.

---

*Testing analysis: 2026-06-13*
*Update when test patterns change*
