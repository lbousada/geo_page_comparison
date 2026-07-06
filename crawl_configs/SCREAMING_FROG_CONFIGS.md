# Screaming Frog Crawl Configurations

This file documents four Screaming Frog SEO Spider configuration files:

- `cc_no_render.seospiderconfig`
- `cc_page_only.seospiderconfig`
- `cc_prompt_semantics.seospiderconfig`
- `cc_semantics_crawl.seospiderconfig`

The configs are Java-serialized Screaming Frog SEO Spider `24.0` config files. This document was updated on 2026-07-06 to include `cc_prompt_semantics.seospiderconfig`.

## Shared Defaults

All four configs share these baseline settings:

- Screaming Frog version: `24.0`
- Robots handling: respect `robots.txt`
- User agent: `Screaming Frog SEO Spider/24.0`
- HTTP version: HTTP/1.1
- Max threads: `3`
- Response timeout: `20` seconds
- Max redirects: `10`
- Max page size: `50,000,000` bytes
- Total crawl limit enabled: `5,000,000` URLs
- No custom URL exclude rules
- No URL rewrite rules
- URLs are not forced lowercase
- Query parameters are not stripped
- Custom link position detection is enabled with these buckets:
  - Head: `/head/`
  - Navigation: `nav`
  - Header: `header`
  - Aside: `aside`
  - Footer: `footer`
  - Content: `/`

All four send these request headers:

- `Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8`
- `Accept-Encoding: gzip`
- `Cache-Control: no-cache`
- `Pragma: no-cache`

## `cc_no_render.seospiderconfig`

### Plain-English Purpose

This is the broad, traditional SEO crawl profile. It uses standard crawling, does not render pages in Chrome, and is configured to collect the normal SEO and technical crawl fields across a broad site scope.

Use this when you want a normal Screaming Frog crawl that follows discovered links, captures resources, and reports standard SEO fields.

### Crawl Mode And Scope

- Crawler mode: `STANDARD`
- JavaScript rendering: off
- Crawl depth limit: enabled
- Depth value: `0`
- Crawl internal links: enabled
- Crawl external links: enabled
- Check links outside the start folder: enabled
- Crawl outside the start folder: enabled
- Search all subdomains: enabled
- Follow internal `nofollow`: disabled
- Follow external `nofollow`: disabled

The broad folder/subdomain settings are important. Even though the depth value is `0`, this profile is otherwise set up with permissive crawl scope. If you raise the crawl depth to `1`, it can crawl one click out broadly across allowed folders and subdomains.

### Resources Crawled And Stored

Enabled:

- CSS
- JavaScript files as resources
- Images
- Iframes
- Canonicals
- Hreflang
- XML sitemaps
- Meta refresh
- SWF
- PDFs
- Internal links
- External links
- Original HTML
- Rendered HTML storage

Disabled:

- Media files
- AMP HTML links
- Mobile alternate links
- `rel="next"` / `rel="prev"`

Note: `CrawlJavaScript` means Screaming Frog crawls JavaScript files as resources. It does not mean the crawler is using rendered mode.

### SEO Extraction

Enabled:

- Page titles
- Meta descriptions
- Meta keywords
- Meta robots
- X-Robots-Tag
- H1
- H2
- Word count
- Text-to-code ratio
- Response time
- Page size
- Last modified
- Indexability
- PDF metadata
- PDF link text
- Forms
- Readability
- JSON-LD
- Microdata
- RDFa
- Google structured data validation
- Schema.org validation

Disabled:

- Cookie extraction
- Image alt text checking

### AI And Embeddings

- OpenAI integration: enabled
- Embeddings: enabled
- Embedding provider: OpenAI
- Embedding model: `text-embedding-3-small`
- Embedding preset: `Extract embeddings from page content`
- Cosine similarity: enabled
- Cosine similarity threshold: `0.9`
- Cosine similarity indexable-only: enabled
- Cosine similarity ignores paginated URLs: enabled
- Low relevance detection: enabled
- Low relevance threshold: `0.4`
- Low relevance indexable-only: enabled

### Other Integrations

Disabled:

- GA4
- Universal Analytics
- Google Search Console
- GSC URL Inspection
- PageSpeed
- Ahrefs
- Majestic
- Moz
- Anthropic
- Gemini
- Ollama

## `cc_page_only.seospiderconfig`

### Plain-English Purpose

This is the rendered page-quality and feature-extraction profile. It renders pages, keeps the broad crawl/resource settings from the normal SEO crawl, and adds custom JavaScript checks that inspect rendered DOM features.

Use this when you want Screaming Frog to render a page and collect page-level signals such as author presence, methodology language, schema counts, heading counts, semantic passage extraction, and image-alt gaps.

### Crawl Mode And Scope

- Crawler mode: `RENDER`
- JavaScript rendering: on
- Crawl depth limit: enabled
- Depth value: `0`
- Crawl internal links: enabled
- Crawl external links: enabled
- Check links outside the start folder: enabled
- Crawl outside the start folder: enabled
- Search all subdomains: enabled
- Follow internal `nofollow`: disabled
- Follow external `nofollow`: disabled

The depth value of `0` makes this effectively page-only unless you change the depth. It can see and store links, but depth `0` prevents crawling out to those links.

### Resources Crawled And Stored

Enabled:

- CSS
- JavaScript files as resources
- Images
- Iframes
- Canonicals
- Hreflang
- XML sitemaps
- Meta refresh
- SWF
- PDFs
- Internal links
- External links
- Original HTML
- Rendered HTML storage

Disabled:

- Media files
- AMP HTML links
- Mobile alternate links
- `rel="next"` / `rel="prev"`

### SEO Extraction

Enabled:

- Page titles
- Meta descriptions
- Meta keywords
- Meta robots
- X-Robots-Tag
- H1
- H2
- Word count
- Text-to-code ratio
- Response time
- Page size
- Last modified
- Indexability
- PDF metadata
- PDF link text
- Forms
- Readability
- JSON-LD
- Microdata
- RDFa
- Google structured data validation
- Schema.org validation

Disabled:

- Cookie extraction
- Image alt text checking through the built-in content setting

### Custom JavaScript Checks

This config contains `26` custom JavaScript snippets. They run against `text/html` pages and return data back to Screaming Frog.

Presence checks:

- Contains Author
- Contains Methodology
- Contains Published Date
- Contains Updated Date

Structure and schema counts:

- Count Article Schema
- Count Article Tags
- Count BreadcrumbList
- Count Bullets
- Count Definition
- Count FAQ
- Count FAQ Schema
- Count Footer Tags
- Count H1
- Count H2
- Count H3
- Count Header Tags
- Count Main Tags
- Count Nav Tags
- Count Org Schema
- Count Product Schema
- Count Section Tags
- Count Table
- Count Tags

Content quality checks:

- Words per Paragraph
- Missing Image Alt Tags

Semantic extraction:

- Passage Embeddings

The `Passage Embeddings` custom JavaScript snippet chunks rendered page content into semantic passages and calls OpenAI's embeddings API from inside the rendered page context.

### Security Note

The `Passage Embeddings` JavaScript snippet uses a dummy OpenAI key placeholder in the tracked Screaming Frog configuration. Keep real API keys in `.env` or inject them locally before running; do not commit exported configs that contain live keys.

### AI And Embeddings

- OpenAI integration: enabled
- OpenAI preset: `Extract embeddings from page content`
- OpenAI model: `text-embedding-3-small`
- Screaming Frog embeddings feature: disabled
- Cosine similarity: disabled
- Low relevance detection: disabled

This config has OpenAI enabled, but Screaming Frog's native embeddings analysis is off. The important semantic behavior in this config comes from the custom `Passage Embeddings` JavaScript snippet, not the native embeddings feature.

### Other Integrations

Disabled:

- GA4
- Universal Analytics
- Google Search Console
- GSC URL Inspection
- PageSpeed
- Ahrefs
- Majestic
- Moz
- Anthropic
- Gemini
- Ollama

## `cc_prompt_semantics.seospiderconfig`

### Plain-English Purpose

This is the rendered prompt-semantics extraction profile. It renders only the input URL, does not crawl outlinks, and runs a custom `Passage Embeddings` JavaScript snippet against the rendered page.

Use this when you want page-level semantic passage extraction for a specific prompt/page comparison workflow, not a site crawl.

### Crawl Mode And Scope

- Crawler mode: `RENDER`
- JavaScript rendering: on
- Crawl depth limit: enabled
- Depth value: `0`
- Crawl internal links: disabled
- Store internal links: disabled
- Crawl external links: disabled
- Store external links: disabled
- Check links outside the start folder: disabled
- Crawl outside the start folder: disabled
- Search all subdomains: disabled
- Follow internal `nofollow`: disabled
- Follow external `nofollow`: disabled

This is intentionally the most constrained crawl profile. It can render the input page, but it is not configured to follow discovered links.

### Resources Crawled And Stored

Enabled:

- JavaScript files as resources
- Canonicals
- Rendered HTML storage
- JavaScript storage
- Canonical storage

Disabled:

- Internal links
- External links
- Original HTML storage
- CSS
- Images
- Iframes
- Hreflang
- XML sitemaps
- Meta refresh
- PDFs
- SWF
- Media files
- AMP HTML links
- Mobile alternate links
- `rel="next"` / `rel="prev"`

### SEO Extraction

Most standard SEO extraction is disabled:

- Page titles
- Meta descriptions
- Meta keywords
- Meta robots
- X-Robots-Tag
- H1
- H2
- Word count
- Text-to-code ratio
- Response time
- Page size
- Last modified
- PDF metadata
- PDF link text
- Cookies
- Readability
- JSON-LD extraction
- Microdata extraction
- RDFa extraction

Still enabled:

- Indexability extraction
- Form extraction
- Google structured data validation
- Schema.org validation

### Custom JavaScript Checks

This config contains `1` custom JavaScript snippet:

- Passage Embeddings

The snippet chunks rendered page content into semantic passages and calls OpenAI's embeddings API from inside the rendered page context.

### Security Note

The `Passage Embeddings` JavaScript snippet uses a dummy OpenAI key placeholder in the tracked Screaming Frog configuration. Keep real API keys in `.env` or inject them locally before running; do not commit exported configs that contain live keys.

### AI And Embeddings

- OpenAI integration: enabled
- OpenAI prompt count: `1`
- Embedding provider: OpenAI
- Screaming Frog embeddings feature: enabled
- Cosine similarity: disabled
- Low relevance detection: disabled
- Cosine similarity threshold setting: `0.9`
- Low relevance threshold setting: `0.4`

The important semantic behavior in this config comes from the custom `Passage Embeddings` JavaScript snippet. Screaming Frog's embeddings feature is enabled, but similarity and low-relevance analysis are disabled.

### Other Integrations

Disabled:

- GA4
- Universal Analytics
- Google Search Console
- GSC URL Inspection
- PageSpeed
- Ahrefs
- Majestic
- Moz
- Anthropic
- Gemini
- Ollama

## `cc_semantics_crawl.seospiderconfig`

### Plain-English Purpose

This is the rendered semantic crawl profile. It renders pages, crawls internal links to depth `1`, avoids most technical SEO/resource collection, and uses Screaming Frog's native OpenAI embeddings workflow.

Use this when you want a lightweight rendered crawl for semantic similarity and low-relevance analysis across a shallow set of pages.

### Crawl Mode And Scope

- Crawler mode: `RENDER`
- JavaScript rendering: on
- Crawl depth limit: enabled
- Depth value: `1`
- Crawl internal links: enabled
- Crawl external links: disabled
- Check links outside the start folder: enabled
- Crawl outside the start folder: enabled
- Search all subdomains: enabled
- Follow internal `nofollow`: disabled
- Follow external `nofollow`: disabled

This current version is broader than the earlier version discussed in chat. It now allows crawling outside the start folder and across subdomains, while still only crawling internal links and only to depth `1`.

### Resources Crawled And Stored

Enabled:

- Internal links
- Original HTML
- Rendered HTML

Disabled:

- External links
- CSS
- JavaScript files as resources
- Images
- Iframes
- Canonicals
- Hreflang
- XML sitemaps
- Meta refresh
- PDFs
- SWF
- Media files
- AMP HTML links
- Mobile alternate links
- `rel="next"` / `rel="prev"`

### SEO Extraction

Most standard SEO extraction is disabled:

- Page titles
- Meta descriptions
- Meta keywords
- Meta robots
- X-Robots-Tag
- H1
- H2
- Word count
- Text-to-code ratio
- Response time
- Page size
- Last modified
- Indexability
- PDF metadata
- PDF link text
- Forms
- Cookies
- Readability
- JSON-LD extraction
- Microdata extraction
- RDFa extraction

Google structured data validation and Schema.org validation remain enabled, but the structured data extraction flags are off.

### AI And Embeddings

- OpenAI integration: enabled
- Embeddings: enabled
- Embedding provider: OpenAI
- Embedding model: `text-embedding-3-small`
- Embedding preset: `Extract embeddings from page content`
- Cosine similarity: enabled
- Cosine similarity threshold: `0.9`
- Cosine similarity indexable-only: enabled
- Cosine similarity ignores paginated URLs: enabled
- Low relevance detection: enabled
- Low relevance threshold: `0.4`
- Low relevance indexable-only: enabled

### Other Integrations

Disabled:

- GA4
- Universal Analytics
- Google Search Console
- GSC URL Inspection
- PageSpeed
- Ahrefs
- Majestic
- Moz
- Anthropic
- Gemini
- Ollama

## How To Choose

Use `cc_no_render` when you need a broad technical SEO crawl without rendering. It is the best baseline for normal Screaming Frog exports, issue discovery, and link/resource crawling.

Use `cc_page_only` when you need a rendered single-page or page-set audit with custom DOM checks. Keep depth at `0` for a page-only test, or raise the depth if you intentionally want it to crawl onward.

Use `cc_prompt_semantics` when you need rendered passage embeddings for only the input page. It is the best fit for prompt-to-page semantic comparison where the script handles similarity scoring outside Screaming Frog.

Use `cc_semantics_crawl` when you need rendered semantic analysis across the input page and one internal click level, with native Screaming Frog embeddings enabled and most normal SEO extraction turned off.

## Important Difference Summary

`cc_no_render` and `cc_page_only` are broad SEO-style configs. They crawl resources, collect standard SEO fields, and allow broad folder/subdomain scope. Their main difference is rendering: `cc_no_render` is `STANDARD`, while `cc_page_only` is `RENDER` and adds custom JavaScript checks.

`cc_prompt_semantics` is a rendered, page-only semantic extraction config. It does not crawl internal or external links, and its main output comes from the custom `Passage Embeddings` JavaScript snippet.

`cc_semantics_crawl` is much leaner. It renders pages and follows internal links to depth `1`, but it intentionally disables most resource crawling and SEO extraction so the crawl is focused on rendered content and embeddings.

The depth settings are also different:

- `cc_no_render`: depth limit enabled, value `0`
- `cc_page_only`: depth limit enabled, value `0`
- `cc_prompt_semantics`: depth limit enabled, value `0`
- `cc_semantics_crawl`: depth limit enabled, value `1`

If a config sees outlinks but does not crawl them, check both the crawl depth and the scope controls: outside-start-folder, all-subdomains, external-link crawling, and nofollow handling.
