# External Integrations

**Analysis Date:** 2026-06-13

## APIs & External Services

**Tribunal de Contas do Estado do Ceará (TCE-CE) API:**
- **Municipalities DE-PARA:**
  - Endpoint: `https://api-dados-abertos.tce.ce.gov.br/sim/municipios`
  - Purpose: Convert 3-digit internal municipal codes to 6-digit or 7-digit IBGE codes
  - Client: Python `requests` library
  - Auth: None (Public API)
- **LOA Budget API:**
  - Endpoint: `https://api-dados-abertos.tce.ce.gov.br/sim/orcamento_despesa`
  - Purpose: Fetch 2025 budget allocations for municipal secretariats in real-time
  - Client: Python `requests` library
  - Caching: `@st.cache_data` (TTL of 1 hour) to reduce network requests
  - Auth: None (Public API)

**GeoJSON Service:**
- **Ceará Municipal Map:**
  - Endpoint: `https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-23-mun.json`
  - Purpose: Draw geographical map of Ceará municipalities and map color-coded maintenance expenses
  - Client: Python `requests` library
  - Caching: `@st.cache_data` (permanent cache unless rerun)

## Data Storage

**Local File System (CSVs):**
- **Data Location:** `dados/` directory
- **Files:**
  - `veiculos.csv` - Vehicle registry database
  - `veiculos_manutencao.csv` - Order of Service (OS) and execution database
  - `veiculos_locados.csv` - Lease contracts and conditions
  - `veiculos_cedidos.csv` - Assignment/loan records between municipalities
- **Format:** CSV with custom delimiter `¬`
- **Client:** `pandas.read_csv` with `dtype=str` for ID columns and custom type conversion

## Authentication & Identity

- **Authentication:** None (Open/Public academic project)
- **Token storage:** None

## Monitoring & Observability

- **Logs:** Python stdout/stderr and Streamlit server logs.

## CI/CD & Deployment

- **Hosting:** Local execution (`streamlit run`) or deployment to Streamlit Community Cloud
- **CI Pipeline:** None

## Environment Configuration

- **Development:**
  - Python dependencies configured in `requirements.txt`
  - Data directory `dados/` expected in project root
- **Production:**
  - Same environment as development; requires public internet access for the TCE-CE APIs and GeoJSON download.

## Webhooks & Callbacks

- **Webhooks:** None

---

*Integration audit: 2026-06-13*
*Update when adding/removing external services*
