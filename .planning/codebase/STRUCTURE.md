# Codebase Structure

**Analysis Date:** 2026-06-13

## Directory Layout

```
[project-root]/
├── .agent/               # GSD automation settings, hooks, and skills
├── .planning/            # Project planning context and codebase map
│   └── codebase/         # Stored documentation of codebase state
├── dados/                # Source database tables (CSV format, ¬ delimiter)
├── img/                  # Static image assets for documentation
├── notebook/             # Jupyter notebooks for analytical research
├── output/               # Persisted analytical reports and CSV exports
├── src/                  # Application source files
│   ├── app.py            # Streamlit dashboard and UI rendering
│   ├── config.py         # Project configurations and threshold values
│   ├── etl.py            # Data loading, normalization, and enrichment
│   └── quarentena.py     # Budget triaging and data validation
├── README.md             # Project onboarding and replication guide
├── requirements.md       # Requirements listing and checklist
├── requirements.txt      # Python dependencies manifest
├── runtime.txt           # Environment execution requirement
└── state.md              # Project progress document
```

## Directory Purposes

**.planning/codebase/**
- Purpose: Technical reference documentation of the codebase's current state.
- Contains: `STACK.md`, `INTEGRATIONS.md`, `ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `TESTING.md`, `CONCERNS.md`.

**dados/**
- Purpose: Raw dataset storage.
- Contains: Large CSV tables exported from the TCE-CE database.
- Key files:
  - `veiculos.csv` - Cadastro de veículos.
  - `veiculos_manutencao.csv` - Ordens de serviço de oficina.
  - `veiculos_locados.csv` - Contratos de locação.

**img/**
- Purpose: Static image assets.
- Contains: PNG graphs and dashboard screenshots for the main documentation.

**notebook/**
- Purpose: Interactive prototyping and exploratory data analysis (EDA).
- Key files: `analise_manutencao_veiculos.ipynb` - Initial pipeline test and outlier logic definition.

**output/**
- Purpose: Target folder for exported analytics.
- Contains: Exported Plotly HTML plots and quarentena files.
- Key files: `empenhos_quarentena_critica.csv` - High-risk entries for audit investigation.

**src/**
- Purpose: Main application Python modules.
- Contains: Streamlit frontend, ETL classes, quarentena algorithms, and configuration settings.

## Key File Locations

**Entry Points:**
- [src/app.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/app.py): Streamlit dashboard entry.
- [notebook/analise_manutencao_veiculos.ipynb](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/notebook/analise_manutencao_veiculos.ipynb): Analytical notebook entry.

**Configuration:**
- [src/config.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/config.py): Key settings, constants, and margins.
- [requirements.txt](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/requirements.txt): Python libraries list.
- [runtime.txt](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/runtime.txt): Specifies Python execution environment (3.10.12).

**Core Logic:**
- [src/etl.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/etl.py): Transformation routines.
- [src/quarentena.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/quarentena.py): Budgetary variance checks.

## Naming Conventions

**Files:**
- Snake-case for Python source files (`app.py`, `config.py`, `etl.py`, `quarentena.py`).
- Snake-case for Jupyter notebooks (`analise_manutencao_veiculos.ipynb`).
- Upper-case for root project files (`README.md`, `LICENSE`, `PROJECT.md`).

**Directories:**
- Flat directories in root. Kebab-case or lower-case directories.

## Where to Add New Code

**New Visualizations or UI Elements:**
- Implementation: Modify [src/app.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/app.py).

**New Ingestion / Cleaning Steps:**
- Implementation: Add function/logic in [src/etl.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/etl.py).
- Constants/keys: Update [src/config.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/config.py).

**New Outlier Algorithms or Triaging Rules:**
- Implementation: Add to [src/quarentena.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/quarentena.py) or `load_all_data` in [src/app.py](file:///c:/Users/User/Documents/TI/Python/Analise%20de%20Dados%20de%20Manutencao%20-%20Frota%20Municipal/src/app.py).

## Special Directories

**dados/**
- Committed: No (listed in `.gitignore` due to file size).

**output/**
- Committed: HTML reports are committed as static outputs.

---

*Structure analysis: 2026-06-13*
*Update when directory structure changes*
