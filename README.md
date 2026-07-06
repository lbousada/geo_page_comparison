# GEO Page Comparison

This repo audits how well pages align with AI-search prompts. It combines Screaming Frog crawls, OpenAI embeddings, prompt/fanout inputs, and optional Semrush backlink lookups to produce Excel files for GEO and semantic-content analysis.

The main workflow is `scripts/geo_screamingfrog_audit.py`. A lighter prompt-only workflow is available in `scripts/just_prompt_comparison.py`.

## What This Repo Does

- Crawls URLs with Screaming Frog using repo-stored crawl configs.
- Resolves redirected or canonicalized URLs before scoring the final page.
- Extracts structural page data such as titles, headings, schema counts, image-alt gaps, and rendered/no-render word-count differences.
- Compares prompt embeddings against page-level and passage-level embeddings.
- Aggregates fanout-query similarity for each prompt.
- Optionally scrapes Semrush backlink/referring-domain counts through Selenium.
- Writes Excel outputs for review.

## Repo Structure

```text
.
├── crawl_configs/
│   ├── cc_no_render.seospiderconfig
│   ├── cc_page_only.seospiderconfig
│   ├── cc_prompt_semantics.seospiderconfig
│   ├── cc_semantics_crawl.seospiderconfig
│   └── SCREAMING_FROG_CONFIGS.md
├── raw_inputs/
│   ├── Fanout_Queries - Master.csv
│   ├── Fanout_Queries - Sample.csv
│   ├── Losing_URLs - Master.csv
│   ├── Losing_URLs - Sample.csv
│   └── Prompt_Names.csv
├── scripts/
│   ├── geo_screamingfrog_audit.py
│   ├── just_prompt_comparison.py
│   ├── backlink_getter.py
│   └── list_screaming_frog_crawls.py
├── urls_and_fanout_getter/
│   ├── Losing Prompts.sql
│   ├── Losing Prompts.ipynb
│   ├── Fanout Queries.ipynb
│   └── RUN_THESE_IN_DB
└── FIELD_DICTIONARY.md
```

## Requirements

- Windows.
- Python 3.12+ recommended.
- Screaming Frog SEO Spider installed with CLI access.
  - Current scripts expect:
    `C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe`
- Screaming Frog license/configuration capable of running the included crawl configs.
- Chrome installed for Selenium/Semrush backlink collection.
- Python packages:
  - `pandas`
  - `openpyxl`
  - `selenium`

Install Python dependencies with:

```powershell
pip install pandas openpyxl selenium
```

## Environment Variables

Create a `.env` file in the repo root. It is ignored by git.

```env
OPENAI_API_KEY=your_openai_key
SEMRUSH_USERNAME=your_semrush_email
SEMRUSH_PASSWORD=your_semrush_password
```

`OPENAI_API_KEY` is required for embedding scoring. `SEMRUSH_USERNAME` and `SEMRUSH_PASSWORD` are required if you want the main audit to collect Semrush referring-domain counts.

Security note: the tracked Screaming Frog custom JavaScript configs should contain only dummy OpenAI key placeholders. Keep real keys in `.env` or inject them locally before running, and see `crawl_configs/SCREAMING_FROG_CONFIGS.md` before sharing any `.seospiderconfig` files.

## Input Files

The scripts are driven by CSV files in `raw_inputs/`. Keep the existing column names and layout. You can replace the data, but do not rename headers unless you also update the script constants.

### URL Inputs

Default for `geo_screamingfrog_audit.py`:

```python
URLS_CSV = Path("raw_inputs/Losing_URLs - Sample.csv")
```

Expected core columns:

- `prompt`
- `url`

The current sample also includes columns such as `classification`, `title`, `retrievals`, and `citation_rate`.

### Fanout Query Inputs

Default for `geo_screamingfrog_audit.py`:

```python
FANOUT_QUERIES_CSV = Path("raw_inputs/Fanout_Queries - Sample.csv")
```

Expected core columns:

- `Prompt`
- `Query`

The file can also include model/date columns. The script uses fanout queries to compare page content against the search-query variants associated with a prompt.

### Prompt Name Inputs

Default for `geo_screamingfrog_audit.py`:

```python
PROMPT_NAMES_CSV = Path("raw_inputs/Prompt_Names.csv")
```

Expected columns:

- `Prompt No`
- `content`

This maps full prompt text to a readable prompt name used in output filenames.

### Prompt-Only Inputs

Default for `just_prompt_comparison.py`:

```python
INPUT_URLS_CSV = Path("raw_inputs/Losing_URLs - Master.csv")
```

Expected core columns:

- `prompt`
- `url`

## Crawl Configs

All Screaming Frog configs now live in `crawl_configs/` and are referenced from the repo, not from an absolute user profile path.

- `cc_no_render.seospiderconfig`: standard no-render SEO crawl.
- `cc_page_only.seospiderconfig`: rendered page-quality crawl with custom DOM checks.
- `cc_semantics_crawl.seospiderconfig`: rendered depth-1 semantic crawl.
- `cc_prompt_semantics.seospiderconfig`: rendered page-only passage-embedding crawl.

For detailed settings and intended use, read:

```text
crawl_configs/SCREAMING_FROG_CONFIGS.md
```

## Main Script: Full GEO Audit

Run:

```powershell
python scripts\geo_screamingfrog_audit.py
```

What it does:

1. Reads URL, fanout-query, and prompt-name CSVs.
2. Opens/logs into Semrush through Selenium if credentials are available.
3. For each prompt, crawls each URL with the page-only rendered config.
4. Resolves redirects and canonicals up to `MAX_PAGE_ONLY_RESOLUTION_CRAWLS`.
5. Runs semantic and no-render Screaming Frog crawls against the resolved URL.
6. Scores prompt/page and fanout/page semantic similarity.
7. Adds Semrush referring-domain counts when available.
8. Writes one Excel file per prompt.

Default output folder:

```text
C:\Users\lbousada\OneDrive - BHEP\Desktop\GEO\GEO Levers Data
```

Output filenames are timestamped and based on the prompt name from `Prompt_Names.csv`.

Important: `backlink_getter.py` uses Selenium because the Semrush Pro tier does not expose backlink data through the API. It will open a Chrome browser window. After it opens, do not interact with the browser window. Minimize it and let it run in the background.

## Prompt-Only Script

Run:

```powershell
python scripts\just_prompt_comparison.py
```

This script performs prompt-to-page semantic comparison only. It does not use fanout queries and writes one combined Excel file instead of one file per prompt.

Default output folder:

```text
C:\Users\lbousada\OneDrive - BHEP\Desktop\GEO
```

Default output prefix:

```text
master_prompt_similarity
```

## Generating New Input Data

Use the files in `urls_and_fanout_getter/` to create or refresh the input CSVs:

- `Losing Prompts.sql`: query for prompts where the target brand is not the visibility leader.
- `Losing Prompts.ipynb`: workflow for prompt data.
- `Fanout Queries.ipynb`: workflow for fanout-query data.
- `RUN_THESE_IN_DB`: brief process note.

When refreshing inputs, preserve the CSV schemas used by the scripts. Change row data, not header names or expected cell locations.

## Output Fields

See `FIELD_DICTIONARY.md` for the main audit output fields. It explains:

- URL resolution fields.
- Screaming Frog page metrics.
- Semantic similarity fields.
- Prompt similarity fields.
- No-render comparison fields.
- Error and warning fields.
- Embedding field shapes.

## Common Configuration Changes

Edit constants near the top of the scripts when changing inputs or output paths:

```python
URLS_CSV = Path("raw_inputs/Losing_URLs - Sample.csv")
FANOUT_QUERIES_CSV = Path("raw_inputs/Fanout_Queries - Sample.csv")
PROMPT_NAMES_CSV = Path("raw_inputs/Prompt_Names.csv")
OUTPUT_DIR = Path(...)
```

For the prompt-only script:

```python
INPUT_URLS_CSV = Path("raw_inputs/Losing_URLs - Master.csv")
OUTPUT_DIR = Path(...)
```

If Screaming Frog is installed somewhere else, update `SF_CLI` in both main scripts.

## Troubleshooting

- If Screaming Frog exports fail, verify available export tabs:

  ```powershell
  "C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe" --help export-tabs
  ```

- If a crawl sees outlinks but does not follow them, check the config's crawl depth and scope settings in `crawl_configs/SCREAMING_FROG_CONFIGS.md`.
- If OpenAI scoring fails, verify `OPENAI_API_KEY` is present in `.env`.
- If Semrush backlink counts are `0`, check Semrush credentials, account access, and whether Selenium successfully logged in.
- If Selenium opens a browser, do not use that browser during the run.
- If output files are missing expected columns, confirm the relevant Screaming Frog config still exports those fields.

## Development Notes

- The scripts clean up temporary Screaming Frog crawl data under the local Screaming Frog `ProjectInstanceData` folder after crawls.
- The repo-stored crawl configs are separate from Screaming Frog runtime data.
- The scripts continue row-by-row where possible and record row-level `Error` or `Warning` values in the output.
- `just_prompt_comparison.py` writes progress after each row so partial results are preserved during longer runs.
