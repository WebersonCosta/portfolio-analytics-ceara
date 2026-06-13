# Technology Stack

**Analysis Date:** 2026-06-13

## Languages

**Primary:**
- Python 3.10.12 - All application code, ETL pipeline, and dashboard frontend

**Secondary:**
- Markdown - Documentation and requirements

## Runtime

**Environment:**
- Python 3.10.12 (standard interpreter)
- Streamlit local development web server

**Package Manager:**
- pip - Dependencies installed via `requirements.txt`
- Lockfile: None (standard `requirements.txt` only)

## Frameworks

**Core:**
- Streamlit (latest) - Frontend interactive dashboard and page routing
- pandas (latest) - Data manipulation and transformation engine
- scikit-learn (latest) - Machine Learning library (Isolation Forest)
- plotly (latest) - Interactive visualization engine (scatter plots, choropleth map, bar charts, boxplots)

**Testing:**
- None - Currently manually tested

**Build/Dev:**
- Streamlit dev server

## Key Dependencies

**Critical:**
- pandas - Essential for ETL, deduplication, and data transformation
- numpy - Used for vectorized quarentena status selection
- scikit-learn (sklearn.ensemble.IsolationForest) - For unsupervised outlier detection
- streamlit - Web interface and controls
- plotly - Dynamic Plotly charts (express and graph_objects)
- requests - External API communication with TCE-CE

**Infrastructure:**
- Python built-in modules: `unicodedata`, `sys`, `pathlib`, `textwrap`

## Configuration

**Environment:**
- External environment variables: None required
- Hardcoded parameters and thresholds in `src/config.py`

**Build:**
- `requirements.txt` - Python dependencies
- `runtime.txt` - Target Python runtime version

## Platform Requirements

**Development:**
- Windows/macOS/Linux with Python 3.9+ installed
- Internet connection (required to fetch GeoJSON and run TCE-CE API calls on initial load)

**Production:**
- Streamlit deployment target (local dev server or Streamlit Community Cloud)
- Requires internet access for API endpoints

---

*Stack analysis: 2026-06-13*
*Update after major dependency changes*
