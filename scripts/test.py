import subprocess
import tempfile
from pathlib import Path

import pandas as pd

SF_CLI = r"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe"
SF_CONFIG = r"C:\Users\lbousada\.ScreamingFrogSEOSpider\cc_page_only.seospiderconfig"


def run_crawl(url: str) -> pd.DataFrame:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        cmd = [
            SF_CLI,
            "--headless",
            "--crawl", url,
            "--config", SF_CONFIG,
            "--output-folder", str(tmp_path),
            "--export-tabs", "Internal:All",
            "--overwrite",
        ]

        subprocess.run(cmd, check=True)

        csv_files = list(tmp_path.rglob("*.csv"))
        internal_csv = next(
            (csv_file for csv_file in csv_files if "internal" in csv_file.stem.lower()),
            None,
        )

        if internal_csv is None:
            exported = ", ".join(csv_file.name for csv_file in csv_files) or "none"
            raise FileNotFoundError(f"No internal URLs CSV was exported. Found: {exported}")

        return pd.read_csv(internal_csv)


def print_internal_urls(dataframe: pd.DataFrame) -> None:
    print(f"Internal URLs ({len(dataframe)} rows):")
    print(dataframe.to_string(index=False))


def print_seed_url_row(dataframe: pd.DataFrame, seed_url: str) -> None:
    if "Address" not in dataframe.columns:
        raise KeyError("Expected the Internal export to include an 'Address' column.")

    seed_row = dataframe.loc[dataframe["Address"].eq(seed_url)]

    if seed_row.empty:
        print(f"No row found for seed URL: {seed_url}")
        return

    print(f"Seed URL row for {seed_url}:")
    print(seed_row.to_string(index=False))


seed_url = "https://wolfenergymuskoka.ca/"
df = run_crawl(seed_url)
print_seed_url_row(df, seed_url)