from __future__ import annotations

import json
import math
import os
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime
from http.client import HTTPSConnection
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

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
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
PROMPT = "I want to become a therapist, but don't have a lot of money or time. How can I earn an accredited graduate degree at my own pace online. I live in Ontario."
EMBEDDING_MODEL = "text-embedding-3-small"
RELEVANT_CHUNK_THRESHOLD = 0.75

INPUT_URLS = [
    "https://adler.ca/academic-calendar/academic-calendar/academic-programs/transitional-equivalency-program-teq",

]

SEMANTIC_COLUMNS = [
    "Extract embeddings from page content",
    "Closest Semantically Similar Address",
    "Semantic Similarity Score",
    "No. Semantically Similar",
    "Semantic Relevance Score",
]
REDIRECT_COLUMNS = [
    "Redirect URL",
]
CANONICAL_COLUMNS = [
    "Canonical Link Element 1",
]
DUPLICATE_TITLE_COLUMNS = [
    "Title 2",
    "Title 2 Length",
    "Title 2 Pixel Width",
    "H1-2",
    "H1-2 Length",
]


# Verify exact Screaming Frog export tab names if exports fail:
# "C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe" --help export-tabs
PAGE_ONLY_EXPORT_TABS = "Internal:All"
SEMANTICS_EXPORT_TABS = "Internal:All,Content:Semantically Similar"
NO_RENDER_EXPORT_TABS = "Internal:All"
CRAWL_TIMEOUT_SECONDS = 1800
MAX_PAGE_ONLY_RESOLUTION_CRAWLS = 3


def terminate_process_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )


def load_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_openai_api_key() -> str:
    load_env_file()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your_openai_api_key_here":
        raise RuntimeError(
            f"Set OPENAI_API_KEY in {ENV_FILE} before running embedding scoring."
        )
    return api_key


def get_prompt_embedding(prompt: str = PROMPT) -> list[float]:
    payload = json.dumps({"model": EMBEDDING_MODEL, "input": prompt})
    connection = HTTPSConnection("api.openai.com", timeout=60)

    try:
        connection.request(
            "POST",
            "/v1/embeddings",
            body=payload,
            headers={
                "Authorization": f"Bearer {get_openai_api_key()}",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        response_body = response.read().decode("utf-8", errors="replace")
    finally:
        connection.close()

    if response.status >= 400:
        raise RuntimeError(f"OpenAI embeddings request failed: {response_body}")

    data = json.loads(response_body)
    return parseEmbedding(data["data"][0]["embedding"])


def run_sf_crawl(
    url: str,
    config_path: Path,
    output_dir: Path,
    export_tabs: str,
    timeout_seconds: int = CRAWL_TIMEOUT_SECONDS,
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

    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )

    if result.stdout:
        print(result.stdout[-2000:], flush=True)


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


def normalize_url(url: str) -> str:
    raw_url = str(url).strip()
    if not raw_url:
        return ""

    parsed = urlsplit(raw_url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def url_without_http_scheme(url: str) -> str:
    parsed = urlsplit(normalize_url(url))
    if parsed.scheme in {"http", "https"}:
        return urlunsplit(("", parsed.netloc, parsed.path, parsed.query, ""))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def urls_match(a: str, b: str) -> bool:
    normalized_a = normalize_url(a)
    normalized_b = normalize_url(b)

    if not normalized_a or not normalized_b:
        return False

    if normalized_a == normalized_b:
        return True

    return url_without_http_scheme(normalized_a) == url_without_http_scheme(normalized_b)


def urls_differ_for_rerun(a: str, b: str) -> bool:
    return normalize_url(a) != normalize_url(b)


def find_row_by_url(dataframe: pd.DataFrame, url: str) -> pd.DataFrame:
    if "Address" not in dataframe.columns:
        raise KeyError("Expected export to include an 'Address' column.")

    matches = dataframe.loc[
        dataframe["Address"].astype(str).map(lambda address: urls_match(address, url))
    ]
    if not matches.empty:
        return matches.head(1).copy()

    raise ValueError(f"No row found for URL: {url}")


def is_blank(value: object) -> bool:
    if value is None or value is pd.NA:
        return True

    cleaned_value = str(value).strip()
    return cleaned_value == "" or cleaned_value.lower() in {"nan", "nat", "<na>"}


def get_first_existing_value(row: dict[str, object], column_names: Iterable[str]) -> object:
    lower_to_actual = {str(column).lower(): column for column in row}
    for column_name in column_names:
        actual_column = lower_to_actual.get(column_name.lower())
        if actual_column is not None:
            value = row.get(actual_column)
            if not is_blank(value):
                return value
    return pd.NA


def get_status_code(row: dict[str, object]) -> int | None:
    status_code = get_first_existing_value(row, ["Status Code", "Status"])
    if is_blank(status_code):
        return None

    match = str(status_code).strip()[:3]
    if match.isdigit():
        return int(match)

    return None


def parseEmbedding(value: object) -> list[float]:
    if is_blank(value):
        raise ValueError("Embedding value is missing.")

    parsed_value = value
    if isinstance(value, str):
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = parse_comma_separated_embedding(value)

    if isinstance(parsed_value, dict):
        if "embedding" in parsed_value:
            parsed_value = parsed_value["embedding"]
        elif "data" in parsed_value and isinstance(parsed_value["data"], list):
            parsed_value = parsed_value["data"][0].get("embedding")

    if not isinstance(parsed_value, list):
        raise ValueError("Embedding value is not a JSON array.")

    vector: list[float] = []
    for item in parsed_value:
        if not isinstance(item, (int, float)) or isinstance(item, bool):
            raise ValueError("Embedding array contains a non-numeric value.")
        if not math.isfinite(float(item)):
            raise ValueError("Embedding array contains a non-finite value.")
        vector.append(float(item))

    if not vector:
        raise ValueError("Embedding array is empty.")

    return vector


def parse_comma_separated_embedding(value: str) -> list[float]:
    cleaned_value = value.strip().strip("[]")
    if not cleaned_value:
        raise ValueError("Embedding value is empty.")

    vector: list[float] = []
    for index, part in enumerate(cleaned_value.split(",")):
        cleaned_part = part.strip()
        if not cleaned_part:
            continue

        try:
            number = float(cleaned_part)
        except ValueError as exc:
            raise ValueError(
                f"Embedding value is neither valid JSON nor a comma-separated "
                f"numeric vector; invalid item at position {index}."
            ) from exc

        if not math.isfinite(number):
            raise ValueError("Embedding array contains a non-finite value.")
        vector.append(number)

    if not vector:
        raise ValueError("Embedding array is empty.")

    return vector


def validate_same_dimensions(a: list[float], b: list[float]) -> None:
    if len(a) != len(b):
        raise ValueError(f"Embedding dimension mismatch: {len(a)} vs {len(b)}.")


def cosineSimilarity(a: list[float], b: list[float]) -> float:
    validate_same_dimensions(a, b)
    dot_product = sum(a_value * b_value for a_value, b_value in zip(a, b))
    norm_a = math.sqrt(sum(a_value * a_value for a_value in a))
    norm_b = math.sqrt(sum(b_value * b_value for b_value in b))

    if norm_a == 0 or norm_b == 0:
        raise ValueError("Cannot compute cosine similarity for a zero vector.")

    return dot_product / (norm_a * norm_b)


def extractChunkEmbeddings(
    passageEmbeddingsField: object,
) -> tuple[list[tuple[list[float], str]], list[str]]:
    warnings: list[str] = []
    if is_blank(passageEmbeddingsField):
        return [], ["Passage Embeddings 1 is missing."]

    parsed_value = passageEmbeddingsField
    if isinstance(passageEmbeddingsField, str):
        try:
            parsed_value = json.loads(passageEmbeddingsField)
        except json.JSONDecodeError as exc:
            raise ValueError("Passage Embeddings 1 is not valid JSON.") from exc

    if not isinstance(parsed_value, dict):
        raise ValueError("Passage Embeddings 1 must be a JSON object.")

    chunks = parsed_value.get("chunks")
    if not isinstance(chunks, list):
        raise ValueError("Passage Embeddings 1 does not contain a chunks array.")

    chunk_embeddings: list[tuple[list[float], str]] = []
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            warnings.append(f"Chunk {index} is not an object.")
            continue

        try:
            chunk_text = ""
            if not is_blank(chunk.get("text")):
                chunk_text = str(chunk.get("text")).strip()
            chunk_embeddings.append((parseEmbedding(chunk.get("embedding")), chunk_text))
        except ValueError as exc:
            warnings.append(f"Chunk {index} embedding invalid: {exc}")

    if not chunk_embeddings:
        warnings.append("No valid chunk embeddings were found.")

    return chunk_embeddings, warnings


def scorePageAgainstPrompt(
    promptEmbedding: list[float],
    page: dict[str, object],
    threshold: float = RELEVANT_CHUNK_THRESHOLD,
) -> dict[str, object]:
    scores: dict[str, object] = {
        "page_similarity": pd.NA,
        "max_chunk_similarity": pd.NA,
        "max_chunk_content": pd.NA,
        "avg_top_3_chunk_similarity": pd.NA,
        "relevant_chunk_count": pd.NA,
        "embedding_similarity_warning": pd.NA,
        "embedding_similarity_error": pd.NA,
    }
    warnings: list[str] = []

    try:
        page_embedding = parseEmbedding(
            get_first_existing_value(page, ["Extract embeddings from page content"])
        )
        scores["page_similarity"] = cosineSimilarity(promptEmbedding, page_embedding)
    except ValueError as exc:
        warnings.append(f"Page embedding invalid: {exc}")

    try:
        chunk_embeddings, chunk_warnings = extractChunkEmbeddings(
            get_first_existing_value(page, ["Passage Embeddings 1"])
        )
        warnings.extend(chunk_warnings)

        chunk_similarities = sorted(
            (
                (cosineSimilarity(promptEmbedding, chunk_embedding), chunk_text)
                for chunk_embedding, chunk_text in chunk_embeddings
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        if chunk_similarities:
            top_3 = [similarity for similarity, _ in chunk_similarities[:3]]
            scores["max_chunk_similarity"] = chunk_similarities[0][0]
            scores["max_chunk_content"] = chunk_similarities[0][1] or pd.NA
            scores["avg_top_3_chunk_similarity"] = sum(top_3) / len(top_3)
            scores["relevant_chunk_count"] = sum(
                similarity >= threshold for similarity, _ in chunk_similarities
            )
    except ValueError as exc:
        warnings.append(f"Chunk embeddings invalid: {exc}")

    if warnings:
        scores["embedding_similarity_warning"] = " | ".join(warnings)

    return scores


def scorePagesAgainstPrompt(
    promptEmbedding: list[float],
    pages: list[dict[str, object]],
    options: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    threshold_value = (options or {}).get(
        "relevant_chunk_threshold",
        RELEVANT_CHUNK_THRESHOLD,
    )
    threshold = float(str(threshold_value))
    scored_pages: list[dict[str, object]] = []

    for page in pages:
        scored_page = dict(page)
        try:
            scored_page.update(scorePageAgainstPrompt(promptEmbedding, page, threshold))
        except Exception as exc:
            scored_page.update(
                {
                    "page_similarity": pd.NA,
                    "max_chunk_similarity": pd.NA,
                    "max_chunk_content": pd.NA,
                    "avg_top_3_chunk_similarity": pd.NA,
                    "relevant_chunk_count": pd.NA,
                    "embedding_similarity_warning": pd.NA,
                    "embedding_similarity_error": str(exc),
                }
            )
        scored_pages.append(scored_page)

    return scored_pages


def resolve_from_page_only_crawl(
    input_url: str,
    page_only_internal_df: pd.DataFrame,
) -> dict[str, object]:
    warning = ""
    try:
        input_row_df = find_row_by_url(page_only_internal_df, input_url)
    except ValueError:
        if len(page_only_internal_df) == 1:
            input_row_df = page_only_internal_df.head(1).copy()
            warning = (
                "Input URL was not found in the Address column; using the only "
                "Internal row from the page-only crawl for resolution."
            )
        else:
            raise

    row = single_row_dict(input_row_df)
    indexability = str(get_first_existing_value(row, ["Indexability"])).strip()
    indexability_status = str(
        get_first_existing_value(row, ["Indexability Status"])
    ).strip()
    redirect_target = get_first_existing_value(row, REDIRECT_COLUMNS)
    canonical_target = get_first_existing_value(row, CANONICAL_COLUMNS)
    resolved_url = input_url
    resolution_method = "input"

    if indexability.casefold() == "indexable":
        resolved_url = input_url
        resolution_method = "input"
    elif indexability_status.casefold() == "canonicalised":
        if is_blank(canonical_target):
            warning = "Input URL is Canonicalised, but Canonical Link Element 1 is blank."
        else:
            resolved_url = str(canonical_target).strip()
            resolution_method = "canonical"
    elif indexability_status.casefold() == "redirected":
        if is_blank(redirect_target):
            warning = "Input URL is Redirected, but Redirect URL is blank."
        else:
            resolved_url = str(redirect_target).strip()
            resolution_method = "redirect"
    elif indexability.casefold() == "non-indexable":
        warning = (
            f"Input URL is Non-Indexable with Indexability Status "
            f"'{indexability_status or 'blank'}'; using input URL."
        )

    return {
        "input_url": input_url,
        "resolved_url": resolved_url,
        "resolution_method": resolution_method,
        "redirect_target": redirect_target,
        "canonical_target": canonical_target,
        "should_rerun_page_only": urls_differ_for_rerun(input_url, resolved_url),
        "warning": warning or pd.NA,
    }


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


def merge_page_semantics_and_no_render(
    page_df: pd.DataFrame,
    semantics_df: pd.DataFrame,
    no_render_df: pd.DataFrame,
    resolved_url: str,
) -> dict[str, object]:
    columns_to_drop = [*SEMANTIC_COLUMNS, *DUPLICATE_TITLE_COLUMNS]
    page_without_semantics = drop_columns_case_insensitive(page_df, columns_to_drop)
    merged = single_row_dict(page_without_semantics)
    merged.update(extract_semantic_metrics(semantics_df, resolved_url))
    merged.update(extract_no_render_word_count(no_render_df, resolved_url))

    return merged


def extract_semantic_metrics(
    semantic_internal_df: pd.DataFrame,
    resolved_url: str,
) -> dict[str, object]:
    semantic_row = single_row_dict(find_row_by_url(semantic_internal_df, resolved_url))
    metrics: dict[str, object] = {}
    for column in SEMANTIC_COLUMNS:
        metrics[column] = get_first_existing_value(semantic_row, [column])
    return metrics


def extract_no_render_word_count(
    no_render_internal_df: pd.DataFrame,
    resolved_url: str,
) -> dict[str, object]:
    no_render_row = single_row_dict(find_row_by_url(no_render_internal_df, resolved_url))
    return {
        "Word Count - Rendering Off": get_first_existing_value(
        no_render_row,
        ["Word Count"],
        )
    }


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


def resolve_page_only_chain(
    input_url: str,
    tmp_path: Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    current_url = input_url
    warnings: list[str] = []
    history: list[str] = []
    last_resolution: dict[str, object] | None = None
    last_internal_df: pd.DataFrame | None = None

    for attempt in range(1, MAX_PAGE_ONLY_RESOLUTION_CRAWLS + 1):
        page_output = tmp_path / f"page_only_{attempt}"
        print(
            f"Running Page Only resolution crawl {attempt}/"
            f"{MAX_PAGE_ONLY_RESOLUTION_CRAWLS} for {current_url}"
        )
        run_sf_crawl(current_url, PAGE_ONLY_CONFIG, page_output, PAGE_ONLY_EXPORT_TABS)

        last_internal_df = load_internal_export(page_output)
        resolution = resolve_from_page_only_crawl(current_url, last_internal_df)
        last_resolution = resolution

        if not is_blank(resolution["warning"]):
            warnings.append(str(resolution["warning"]))

        resolved_url = str(resolution["resolved_url"])
        resolution_method = str(resolution["resolution_method"])
        history.append(f"{current_url} -> {resolved_url} ({resolution_method})")

        if resolution_method == "input":
            page_internal_df = find_row_by_url(last_internal_df, current_url)
            resolution["input_url"] = input_url
            resolution["resolved_url"] = current_url
            resolution["resolution_chain"] = " | ".join(history)
            resolution["warning"] = " | ".join(warnings) if warnings else pd.NA
            return page_internal_df, resolution

        if attempt == MAX_PAGE_ONLY_RESOLUTION_CRAWLS:
            warnings.append(
                "Maximum page-only resolution crawls reached before an indexable URL "
                "was found."
            )
            page_internal_df = find_row_by_url(last_internal_df, current_url)
            resolution["input_url"] = input_url
            resolution["resolved_url"] = current_url
            resolution["resolution_chain"] = " | ".join(history)
            resolution["warning"] = " | ".join(warnings)
            return page_internal_df, resolution

        current_url = resolved_url

    raise RuntimeError("Page-only resolution chain ended unexpectedly.")


def process_url(url: str) -> dict[str, object]:
    before_snapshot = snapshot_screamingfrog_project_instances()

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            semantics_output = tmp_path / "semantics"
            no_render_output = tmp_path / "no_render"

            page_internal_df, resolution = resolve_page_only_chain(url, tmp_path)
            resolved_url = str(resolution["resolved_url"])

            print(f"Running Semantics crawl for {resolved_url}")
            run_sf_crawl(
                resolved_url,
                SEMANTICS_CONFIG,
                semantics_output,
                SEMANTICS_EXPORT_TABS,
            )
            semantics_internal_df = load_internal_export(semantics_output)

            print(f"Running Rendering Off crawl for {resolved_url}")
            run_sf_crawl(
                resolved_url,
                NO_RENDER_CONFIG,
                no_render_output,
                NO_RENDER_EXPORT_TABS,
            )
            no_render_internal_df = load_internal_export(no_render_output)

            merged = merge_page_semantics_and_no_render(
                page_internal_df,
                semantics_internal_df,
                no_render_internal_df,
                resolved_url,
            )
            merged["Input URL"] = url
            merged["Resolved URL"] = resolved_url
            merged["Resolution Method"] = resolution["resolution_method"]
            merged["Redirect Target"] = resolution["redirect_target"]
            merged["Canonical Target"] = resolution["canonical_target"]
            merged["Resolution Chain"] = resolution["resolution_chain"]
            merged["Error"] = pd.NA
            merged["Warning"] = resolution["warning"]
            return merged
    except subprocess.CalledProcessError as exc:
        output = "\n".join(part for part in [exc.stdout, exc.stderr] if part)
        return {
            "Input URL": url,
            "Resolved URL": pd.NA,
            "Resolution Method": pd.NA,
            "Redirect Target": pd.NA,
            "Canonical Target": pd.NA,
            "Error": f"Screaming Frog failed with exit code {exc.returncode}: {output[-4000:]}",
            "Warning": pd.NA,
        }
    except Exception as exc:
        return {
            "Input URL": url,
            "Resolved URL": pd.NA,
            "Resolution Method": pd.NA,
            "Redirect Target": pd.NA,
            "Canonical Target": pd.NA,
            "Error": str(exc),
            "Warning": pd.NA,
        }
    finally:
        cleanup_screamingfrog_crawl_if_possible(before_snapshot)


def order_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    preferred_first = [
        "Input URL",
        "Resolved URL",
        "Resolution Method",
        "Redirect Target",
        "Canonical Target",
        "Resolution Chain",
        "Address",
        "Missing Alt Image Count",
        "page_similarity",
        "max_chunk_similarity",
        "max_chunk_content",
        "avg_top_3_chunk_similarity",
        "relevant_chunk_count",
        "embedding_similarity_warning",
        "embedding_similarity_error",
        *SEMANTIC_COLUMNS,
        "Word Count - Rendering Off",
        "Error",
        "Warning",
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
    prompt_embedding = get_prompt_embedding(PROMPT)
    scored_rows = scorePagesAgainstPrompt(prompt_embedding, rows)
    final_df = order_columns(pd.DataFrame(scored_rows))
    output_file = get_timestamped_output_file()

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        final_df.to_excel(writer, sheet_name="Audit", index=False)

    print(f"Saved final audit: {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
