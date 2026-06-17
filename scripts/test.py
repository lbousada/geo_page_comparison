import subprocess
import tempfile
from pathlib import Path

import pandas as pd

SF_CLI = r"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe"


def run_crawl(url: str) -> dict[str, pd.DataFrame]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        cmd = [
            SF_CLI,
            "--headless",
            "--load-crawl", "de396f5b-4386-44fe-ad2a-55a9c2116543",
            "--output-folder", str(tmp_path),
            "--export-tabs", "Images:All",
            "--overwrite",
        ]

        subprocess.run(cmd, check=True)

        return {
            csv_file.stem: pd.read_csv(csv_file)
            for csv_file in tmp_path.rglob("*.csv")
        }


def print_image_urls(dataframes: dict[str, pd.DataFrame]) -> None:
    image_exports = {
        name: dataframe
        for name, dataframe in dataframes.items()
        if "image" in name.lower()
    }

    if not image_exports:
        print("No image export CSV was found.")
        print(f"Available CSVs: {', '.join(dataframes) or 'none'}")
        return

    for csv_name, dataframe in image_exports.items():
        print(f"\n=== {csv_name} ({len(dataframe)} images) ===")
        if dataframe.empty:
            print("No images found.")
            continue

        url_column = "Address" if "Address" in dataframe.columns else dataframe.columns[0]
        for image_url in dataframe[url_column].dropna():
            print(image_url)


dfs = run_crawl("https://mrshsfishandchips.ca/")
print_image_urls(dfs)