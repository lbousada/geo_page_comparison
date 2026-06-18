from __future__ import annotations

import json

from geo_screamingfrog_audit import scorePagesAgainstPrompt


def main() -> int:
    prompt_embedding = [1.0, 0.0, 0.0]
    pages = [
        {
            "Address": "https://example.com/mba",
            "Extract embeddings from page content": json.dumps([0.9, 0.1, 0.0]),
            "Passage Embeddings 1": json.dumps(
                {
                    "success": True,
                    "model": "text-embedding-3-small",
                    "totalChunks": 3,
                    "chunks": [
                        {
                            "text": "MBA programs in Canada overview.",
                            "index": 0,
                            "metadata": {"elementType": "p", "textLength": 32},
                            "embedding": [0.95, 0.05, 0.0],
                            "embeddingModel": "text-embedding-3-small",
                        },
                        {
                            "text": "Tuition and admissions details.",
                            "index": 1,
                            "metadata": {"elementType": "p", "textLength": 31},
                            "embedding": [0.3, 0.7, 0.0],
                            "embeddingModel": "text-embedding-3-small",
                        },
                        {
                            "text": "Career outcomes for graduates.",
                            "index": 2,
                            "metadata": {"elementType": "h2", "textLength": 30},
                            "embedding": [0.8, 0.2, 0.0],
                            "embeddingModel": "text-embedding-3-small",
                        },
                    ],
                }
            ),
        }
    ]

    scored_pages = scorePagesAgainstPrompt(
        prompt_embedding,
        pages,
        {"relevant_chunk_threshold": 0.75},
    )
    for page in scored_pages:
        print(json.dumps(page, indent=2, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
