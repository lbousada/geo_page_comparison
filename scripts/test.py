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
            "--crawl", url,
            "--output-folder", str(tmp_path),
            "--export-tabs", "Images:All,Internal:All,Page Titles:All,Content:Semantically Similar", 
            "--overwrite",
        ]

        subprocess.run(cmd, check=True)

        return {
            csv_file.stem: pd.read_csv(csv_file)
            for csv_file in tmp_path.rglob("*.csv")
        }


def print_csv_names(dataframes: dict[str, pd.DataFrame]) -> None:
    if not dataframes:
        print("No CSV files were exported.")
        return

    print("Exported CSV files:")
    for csv_name, dataframe in dataframes.items():
        print(f"=== {csv_name} ===")
        print(dataframe.to_string(index=False))


dfs = run_crawl("https://wolfenergymuskoka.ca/")
print_csv_names(dfs)


#print the average length of each page title in characters
for csv_name, dataframe in dfs.items():
    if "page_titles_all" in csv_name:
        print(csv_name)
        print(f"Average length: {dataframe['Title 1'].str.len().mean()}")