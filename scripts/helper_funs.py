import subprocess
import pandas as pd
import re

SF = r"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe"
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


def parse_table_row(line: str) -> dict[str, str] | None:
    if "║" not in line or "│" not in line:
        return None

    table_line = line.split("INFO  -", 1)[-1].strip()
    cells = [cell.strip() for cell in table_line.strip("║").split("│")]

    if len(cells) < 3 or not UUID_PATTERN.match(cells[0]):
        return None

    return {
        "database_id": cells[0],
        "name": cells[1],
        "url": cells[2],
    }


def crawl_table():
    output = subprocess.run(
        [SF, "--headless", "--list-crawls"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    ).stdout

    rows = []

    for line in output.splitlines():
        row = parse_table_row(line)
        if row:
            rows.append(row)

    df = pd.DataFrame(rows)

    print(df.to_string(index=False))
    return df

def find_crawl_by_domain(domain: str, df: pd.DataFrame):
    return df.loc[
        df["url"].str.contains(domain, na=False),
        "database_id"
    ].iloc[0]


