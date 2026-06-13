# Architecture

**Analysis Date:** 2026-06-13

## Pattern Overview

**Overall:** Modularized Python Data Application & Streamlit Dashboard

**Key Characteristics:**
- **Pipeline-Driven:** Batch processing of local CSV files through a sequential ETL pipeline.
- **Reactive UI:** Streamlit-driven event loop that redraws visualizations dynamically based on user selections/filters.
- **Heuristics + ML Outliers:** Uses statistical limits (IQR, Z-Score) and Machine Learning (Isolation Forest) to evaluate data anomalies.
- **Resilient APIs:** Calls external government APIs (TCE-CE) with fallback logic to prevent app failures.

## Layers

**Presentation Layer:**
- Purpose: Render dashboard UI, filters, tabs, KPIs, maps, and interactive charts.
- Contains: Streamlit components, Plotly visualization logic, and reactive filtering.
- Location: [app.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/app.py)
- Depends on: ETL Layer, Quarentena Layer, and Config Layer.

**ETL (Extract, Transform, Load) Layer:**
- Purpose: Read raw files, normalize text and document IDs, standardise names, and enrich fields.
- Contains: Sane text normalisation, document formatting, aditive deduplication, and IBGE mapping logic.
- Location: [etl.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/etl.py)
- Depends on: Config Layer.

**Triaging / Quality Layer:**
- Purpose: Assess budget discrepancies and place high-variance entries into quarentena or investigation buckets.
- Contains: Agrupamento by NE, divergence calculation, and vectorized status assignments.
- Location: [quarentena.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/quarentena.py)
- Depends on: Config Layer.

**Configuration Layer:**
- Purpose: Store all thresholds, parameters, priorities, and static dictionaries.
- Contains: Z-Score thresholds, IQR multiplier, contamination parameters, date bounds, file mapping.
- Location: [config.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/config.py)
- Used by: All layers.

## Data Flow

**ETL and Dashboard Bootstrapping Flow:**

1. User starts dashboard (`streamlit run src/app.py`).
2. Dashboard calls `load_all_data()` which is decorated with `@st.cache_data`.
3. `load_all_data` executes:
   - `carrega_bases()`: Reads `veiculos`, `veiculos_manutencao`, `veiculos_locados`, `veiculos_cedidos` using delimiter `¬`.
   - `normaliza_bases()`: Sane cleans text fields (NFKD Unicode normalization), formats CNPJs/CPFs, converts currencies (e.g. `1.000,50` to `1000.50`), and maps master names.
   - `enriquece_veiculos()`: Calculates ages and maps real situation statuses (Em Operação, Sucata, Ocioso, etc.).
   - `enriquece_locados()`: Deduplicates aditivos by month/vehicle to prevent double-counting.
   - `deduplica_os()`: Deduplicates orders of service at the `cd_municipio`, `cd_renavam_vm`, `nu_ordem_servico_vma` level.
   - `enriquece_manutencoes()`: Detects description irregularities (short text, multiple vehicles in one OS description).
   - `aplica_quarentena()`: Validates that the sum of OS costs matches the empenho value. Separates data into `df_valido`, `df_investigacao`, and `df_quarentena`.
   - `carrega_de_para_ibge()`: Contacts TCE-CE API for IBGE code mapping.
   - Outliers logic: Computes Isolation Forest, IQR boundaries, Z-Scores on `df_valido`, calculating an accumulated suspicion score (0 to 3) for each OS.
4. If a specific municipality is selected in the Sidebar:
   - DataFrames are sliced (`df[df['nm_municipio'] == selection]`).
   - Indicators and visualizations (Plotly) are updated reactively.
   - Budget LOA details for the specific municipality are requested from the TCE-CE API (cached for 1h).

**State Management:**
- Stateless server execution. State is held in Streamlit's reactive session cache.
- Hard file output generated only in the exploratory notebook stage (in `output/` folder).

## Key Abstractions

**ETL Pipeline Functions:**
- Purpose: Structured modular functions for specific sanitizing tasks.
- Examples: `normaliza_texto()`, `enriquece_veiculos()`, `deduplica_os()`.

**Outlier Classifiers:**
- Purpose: Multi-model evaluation of a single numeric column (`vl_total_servicos_vma`).
- Example: Combination of statistical (Z-Score, IQR) and Machine Learning (Isolation Forest) flags.

## Entry Points

**Streamlit Dashboard:**
- Location: [app.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/app.py)
- Triggers: Execution of `streamlit run src/app.py`.
- Responsibilities: Main UI layout, rendering elements, reactive filtering, network integrations.

**Exploratory Notebook:**
- Location: `notebook/analise_manutencao_veiculos.ipynb`
- Triggers: Jupyter execution.
- Responsibilities: Initial model design, algorithm prototyping, and HTML report exports.

## Error Handling

**Strategy:** Fail-safe default returns for external network endpoints.

**Patterns:**
- `carrega_de_para_ibge()` and `carregar_orcamento_tce()` wrap `requests.get` inside try-catch blocks. If a request times out (10s/15s) or fails, an empty DataFrame is returned, allowing the application to display a warning but continue running without crashing.
- Float conversions use `errors='coerce'` and fallback to fillna values.

## Cross-Cutting Concerns

**Caching:**
- `@st.cache_data` caches GeoJSON downloads, main ETL dataset loading, and API query results to optimize execution speed.

**Text Normalization:**
- Custom ASCII text mapping applied consistently across all datasets to resolve accentuation mismatch in database joins.

---

*Architecture analysis: 2026-06-13*
*Update when major patterns change*
