import subprocess
import pandas as pd
import re

SF = r"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe"

def crawl_table():
    output = subprocess.run(
        [SF, "--headless", "--list-crawls"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    ).stdout

    uuid_pattern = re.compile(
        r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
        re.I
    )

    print(output.splitlines())

    rows = []

    for line in output.splitlines():
        match = uuid_pattern.search(line)

        if not match:
            continue

        crawl_id = match.group(1)

        urls = re.findall(r'https?://[^\s│]+', line)

        rows.append({
            "database_id": crawl_id,
            "url": urls[0] if len(urls) > 0 else None,
            "name": urls[1] if len(urls) > 1 else None
        })

    df = pd.DataFrame(rows)

    print(df)
    return df

def find_crawl_by_domain(domain: str, df: pd.DataFrame):
    return df.loc[
        df["url"].str.contains(domain, na=False),
        "database_id"
    ].iloc[0]


df = crawl_table()
crawl_id = find_crawl_by_domain("mrshsfishandchips.ca", df)
print(crawl_id)