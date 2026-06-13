# Coding Conventions

**Analysis Date:** 2026-06-13

## Naming Patterns

**Files:**
- `snake_case.py` for Python modules (`etl.py`, `quarentena.py`, `app.py`).
- `snake_case.ipynb` for Jupyter notebooks (`analise_manutencao_veiculos.ipynb`).
- `UPPERCASE.md` for major documentation files (`README.md`, `PROJECT.md`).

**Functions:**
- `snake_case` for all functions (`normaliza_texto()`, `carrega_bases()`, `load_all_data()`).
- Use descriptive verbs (`carrega_...`, `normaliza_...`, `enriquece_...`).

**Variables:**
- `snake_case` for standard and dataframe variables (`df_veiculos`, `gasto_total`, `cols_financeiras`).
- `UPPER_SNAKE_CASE` for global configurations, parameters, and constants (`ANO`, `SEP_CSV`, `LIMIAR_ZSCORE`).

**Classes/Types:**
- `PascalCase` if custom classes are added (none currently present).

## Code Style

**Formatting:**
- 4-space indentation for Python code.
- Align long dictionary declarations and comments for improved readability (as seen in `config.py` and `app.py`).
- Use single quotes `'` for dictionary keys and pandas indices, reserving double quotes `"` for user-facing output messages or f-strings.

**Linting:**
- No strict linter enforced; adherence to basic PEP8 styling.

## Import Organization

**Order:**
1. Standard library imports (`sys`, `pathlib`, `unicodedata`, `textwrap`).
2. Data science/visualization packages (`pandas`, `numpy`, `plotly.express`, `plotly.graph_objects`, `streamlit`, `sklearn`).
3. Local application modules (`config`, `etl`, `quarentena`).

**Grouping:**
- Imports grouped neatly with a blank line separating standard library, third-party packages, and local scripts.

**Path Management:**
- Root path adjustments using `sys.path.insert(0, ...)` inside `app.py` to ensure local modules in `src/` can be resolved consistently from different execution contexts.

## Error Handling

**Strategy:** Try-catch wrappers for unstable operations (e.g. HTTP requests) with safe returns.

**Patterns:**
- Always wrap external API calls (`requests.get`) with a timeout (10s/15s) and `verify=False` if SSL verification issues occur.
- Return empty containers or fallback structures on failure to ensure the rest of the application remains functional.
- Use `pd.to_datetime(..., errors='coerce')` or `pd.to_numeric(..., errors='coerce')` to transform unstable columns without throwing exceptions on corrupt values.

## Logging

**Patterns:**
- Use console print statements (`print()`) to output ETL progress to console logs during execution.
- Use Streamlit alert banners (`st.error`, `st.warning`, `st.info`) to present API connectivity issues or empty data warnings directly to the user in the UI.

## Comments

**When to Comment:**
- Explain the logic behind string cleaning operations (e.g., Unicode NFKD normalization details).
- Demarcate key steps in long operations with distinct section markers (e.g., `# ── Carregamento de Dados com Cache ──`).
- Docstrings are recommended on all ETL pipeline functions to document their input parameters and transformations.

## Function Design

**Size:** Keep pipeline functions focused on single responsibilities (e.g., one function for base loading, one for normalizations, one for aditive consolidation).

**Parameters:** Prefer passing pandas DataFrames directly and returning transformed/new DataFrames.

---

*Convention analysis: 2026-06-13*
*Update when patterns change*
