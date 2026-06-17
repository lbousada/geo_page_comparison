from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


SF_CLI = Path(
    r"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe"
)
SF_CONFIG_DIR = Path(r"C:\Users\lbousada\.ScreamingFrogSEOSpider")
PAGE_ONLY_CONFIG = SF_CONFIG_DIR / "cc_page_only.seospiderconfig"
SEMANTICS_CONFIG = SF_CONFIG_DIR / "cc_semantics_crawl.seospiderconfig"
NO_RENDER_CONFIG = SF_CONFIG_DIR / "cc_no_render.seospiderconfig"
SF_PROJECT_INSTANCE_DATA = SF_CONFIG_DIR / "ProjectInstanceData"

OUTPUT_DIR = Path(r"C:\Users\lbousada\OneDrive - BHEP\Desktop\GEO")
OUTPUT_FILE_PREFIX = "geo_screamingfrog_audit"

INPUT_URLS = [
    "https://ufred.ca/programs/business/accelerated-mba",
    "https://ivey.uwo.ca/amba",
    "https://smith.queensu.ca/mba_programs/amba/index.php",
    "https://ibu.ca/online-mba",
    "https://online.unb.ca/master-of-business-administration",
    "https://athabascau.ca/programs/summary/master-of-business-administration.html",
    "https://smith.queensu.ca/mba_programs/gomba/landing.php",
]

SEMANTIC_COLUMNS = [
    "Extract embeddings from page content",
    "Closest Semantically Similar Address",
    "Semantic Similarity Score",
    "No. Semantically Similar",
    "Semantic Relevance Score",
]


# Verify exact Screaming Frog export tab names if exports fail:
# "C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe" --help export-tabs
PAGE_ONLY_EXPORT_TABS = "Internal:All"
SEMANTICS_EXPORT_TABS = "Internal:All,Content:Semantically Similar"
NO_RENDER_EXPORT_TABS = "Internal:All"
CRAWL_TIMEOUT_SECONDS = 1800


def terminate_process_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )


def run_sf_crawl(
    url: str,
    config_path: Path,
    output_dir: Path,
    export_tabs: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(SF_CLI),
        "--headless",
        "--crawl",
        url,
        "--config",
        str(config_path),
        "--output-folder",
        str(output_dir),
        "--export-format",
        "csv",
        "--export-tabs",
        export_tabs,
        "--overwrite",
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        stdout, stderr = process.communicate(timeout=CRAWL_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        terminate_process_tree(process.pid)
        stdout, stderr = process.communicate()
        raise TimeoutError(
            f"Screaming Frog crawl timed out after {CRAWL_TIMEOUT_SECONDS} seconds. "
            f"Output:\n{stdout[-4000:]}\n{stderr[-4000:]}"
        ) from exc
    except KeyboardInterrupt:
        terminate_process_tree(process.pid)
        raise

    if process.returncode != 0:
        raise subprocess.CalledProcessError(
            process.returncode,
            cmd,
            output=stdout,
            stderr=stderr,
        )

    if stdout:
        print(stdout[-2000:], flush=True)


def find_export_file(output_dir: Path, keywords: Iterable[str]) -> Path:
    csv_files = sorted(output_dir.rglob("*.csv"))
    lowered_keywords = [keyword.lower() for keyword in keywords]

    for csv_file in csv_files:
        name = csv_file.stem.lower()
        if all(keyword in name for keyword in lowered_keywords):
            return csv_file

    available = ", ".join(str(csv_file.relative_to(output_dir)) for csv_file in csv_files)
    raise FileNotFoundError(
        f"No export CSV matching {list(keywords)} found in {output_dir}. "
        f"Available CSVs: {available or 'none'}"
    )


def load_internal_export(output_dir: Path) -> pd.DataFrame:
    return pd.read_csv(find_export_file(output_dir, ["internal"]), encoding="utf-8-sig")


def normalise_url(url: str) -> str:
    return str(url).strip().rstrip("/").lower()


def select_input_url_row(dataframe: pd.DataFrame, input_url: str) -> pd.DataFrame:
    if "Address" not in dataframe.columns:
        raise KeyError("Expected export to include an 'Address' column.")

    exact_match = dataframe.loc[dataframe["Address"].astype(str).str.strip().eq(input_url)]
    if not exact_match.empty:
        return exact_match.head(1).copy()

    normalised_input = normalise_url(input_url)
    normalised_match = dataframe.loc[
        dataframe["Address"].astype(str).map(normalise_url).eq(normalised_input)
    ]
    if not normalised_match.empty:
        return normalised_match.head(1).copy()

    raise ValueError(f"No row found for input URL: {input_url}")


def drop_columns_case_insensitive(
    dataframe: pd.DataFrame,
    columns_to_drop: Iterable[str],
) -> pd.DataFrame:
    drop_lookup = {column.lower() for column in columns_to_drop}
    existing_columns_to_drop = [
        column for column in dataframe.columns if column.lower() in drop_lookup
    ]
    return dataframe.drop(columns=existing_columns_to_drop, errors="ignore")


def single_row_dict(dataframe: pd.DataFrame) -> dict[str, object]:
    if dataframe.empty:
        return {}
    return dataframe.iloc[0].to_dict()


def get_first_existing_value(row: dict[str, object], column_names: Iterable[str]) -> object:
    lower_to_actual = {str(column).lower(): column for column in row}
    for column_name in column_names:
        actual_column = lower_to_actual.get(column_name.lower())
        if actual_column is not None:
            return row.get(actual_column)
    return pd.NA


def merge_page_semantics_and_no_render(
    page_df: pd.DataFrame,
    semantics_df: pd.DataFrame,
    no_render_df: pd.DataFrame,
) -> dict[str, object]:
    page_without_semantics = drop_columns_case_insensitive(page_df, SEMANTIC_COLUMNS)
    merged = single_row_dict(page_without_semantics)

    semantics_row = single_row_dict(semantics_df)
    for column in SEMANTIC_COLUMNS:
        merged[column] = get_first_existing_value(semantics_row, [column])

    no_render_row = single_row_dict(no_render_df)
    merged["Word Count - Rendering Off"] = get_first_existing_value(
        no_render_row,
        ["Word Count"],
    )

    return merged


def snapshot_screamingfrog_project_instances() -> set[str]:
    if not SF_PROJECT_INSTANCE_DATA.exists():
        return set()
    return {path.name for path in SF_PROJECT_INSTANCE_DATA.iterdir() if path.is_dir()}


def remove_path_if_possible(path: Path) -> None:
    def retry_readonly(function: object, failed_path: str, exc: BaseException) -> None:
        try:
            os.chmod(failed_path, stat.S_IWRITE)
            function(failed_path)  # type: ignore[operator]
        except OSError as retry_exc:
            print(f"Warning: could not remove {failed_path}: {retry_exc}")

    try:
        if path.is_dir():
            shutil.rmtree(path, onexc=retry_readonly)
        else:
            path.unlink()
    except OSError as exc:
        print(f"Warning: could not remove {path}: {exc}")


def cleanup_screamingfrog_crawl_if_possible(
    before_snapshot: set[str] | None = None,
) -> None:
    if before_snapshot is None or not SF_PROJECT_INSTANCE_DATA.exists():
        return

    for path in SF_PROJECT_INSTANCE_DATA.iterdir():
        if path.name in before_snapshot or not path.is_dir():
            continue

        remove_path_if_possible(path)


def prepare_final_output_folder() -> None:
    # Do not delete existing files in GEO. Temporary exports live in
    # TemporaryDirectory, and Screaming Frog crawl data cleanup is handled
    # separately under the Screaming Frog data folder.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_timestamped_output_file() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return OUTPUT_DIR / f"{OUTPUT_FILE_PREFIX}_{timestamp}.xlsx"


def process_url(url: str) -> dict[str, object]:
    before_snapshot = snapshot_screamingfrog_project_instances()

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            page_output = tmp_path / "page_only"
            semantics_output = tmp_path / "semantics"
            no_render_output = tmp_path / "no_render"

            print(f"Running Page Only crawl for {url}")
            run_sf_crawl(url, PAGE_ONLY_CONFIG, page_output, PAGE_ONLY_EXPORT_TABS)
            page_internal_df = select_input_url_row(load_internal_export(page_output), url)

            print(f"Running Semantics crawl for {url}")
            run_sf_crawl(url, SEMANTICS_CONFIG, semantics_output, SEMANTICS_EXPORT_TABS)
            semantics_internal_df = select_input_url_row(
                load_internal_export(semantics_output),
                url,
            )

            print(f"Running Rendering Off crawl for {url}")
            run_sf_crawl(url, NO_RENDER_CONFIG, no_render_output, NO_RENDER_EXPORT_TABS)
            no_render_internal_df = select_input_url_row(
                load_internal_export(no_render_output),
                url,
            )

            merged = merge_page_semantics_and_no_render(
                page_internal_df,
                semantics_internal_df,
                no_render_internal_df,
            )
            merged["Input URL"] = url
            merged["Error"] = pd.NA
            return merged
    except subprocess.CalledProcessError as exc:
        output = "\n".join(part for part in [exc.stdout, exc.stderr] if part)
        return {
            "Input URL": url,
            "Error": f"Screaming Frog failed with exit code {exc.returncode}: {output[-4000:]}",
        }
    except Exception as exc:
        return {
            "Input URL": url,
            "Error": str(exc),
        }
    finally:
        cleanup_screamingfrog_crawl_if_possible(before_snapshot)


def order_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    preferred_first = [
        "Input URL",
        "Address",
        "Missing Alt Image Count",
        *SEMANTIC_COLUMNS,
        "Word Count - Rendering Off",
        "Error",
    ]
    existing_first = [column for column in preferred_first if column in dataframe.columns]
    remaining = [column for column in dataframe.columns if column not in existing_first]
    return dataframe.loc[:, existing_first + remaining]


def main() -> int:
    for path in [SF_CLI, PAGE_ONLY_CONFIG, SEMANTICS_CONFIG, NO_RENDER_CONFIG]:
        if not path.exists():
            raise FileNotFoundError(f"Required path does not exist: {path}")

    prepare_final_output_folder()

    rows = [process_url(url) for url in INPUT_URLS]
    final_df = order_columns(pd.DataFrame(rows))
    output_file = get_timestamped_output_file()

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        final_df.to_excel(writer, sheet_name="Audit", index=False)

    print(f"Saved final audit: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
