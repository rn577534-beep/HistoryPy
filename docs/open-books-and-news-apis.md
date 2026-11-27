# Open books, historical collections, and news discovery

HistoryPy integrates with public catalog/search APIs. These integrations retrieve
bibliographic or article metadata and source URLs; they do not mirror entire
libraries, scrape provider websites, or copy full copyrighted books/news stories.

## Built-in book and cultural-heritage providers

| Provider | Access | What HistoryPy retrieves | Important conditions |
|---|---|---|---|
| Project Gutenberg via Gutendex | No API key | Ebook ID, title, author, subjects, language, landing-page URL | Gutenberg ebooks are generally public domain in the US; verify the individual work and the user's jurisdiction before downloading/reuse |
| Open Library | No API key | Work ID, title, author, first publication year, subjects, language | Use cache and identified User-Agent; default 1 request/second, identified 3 requests/second; do not use live API for bulk ingestion |
| Internet Archive | No API key | Item identifier, title, creator, date, metadata URL | Metadata search is not a blanket license to download/reuse an item; inspect item-level rights and access status |
| Library of Congress | No API key | Catalog metadata and record URL | Check item-level rights and access statements |
| Europeana | Free API key | Cultural-heritage record metadata, creator, date, rights statement | Read the record-level rights field; each contributing institution may have different terms |
| Smithsonian Open Access | API key | Collection metadata and item link | CC0 status is item/media-specific; inspect the item's usage/access fields |
| Harvard Art Museums | API key | Object metadata | Non-commercial terms and quota/caching restrictions apply; not a general book library |

## News discovery providers

| Provider | Access | What HistoryPy retrieves | Important conditions |
|---|---|---|---|
| GDELT DOC 2.0 | No API key | Recent article title, publisher domain, URL, language, country, seen date | Rolling recent-news index; rate limited; original publisher retains article rights |
| The Guardian Open Platform | Free developer key for eligible non-commercial use | Article title, URL, date, byline, short trail text | Developer tier: non-commercial, up to 1 request/second and 500 requests/day; commercial use requires a commercial agreement |

## Example: discover books

\`\`\`python
from historypy import GutendexSearch, OpenLibrarySearch

gutenberg = GutendexSearch()
for book in gutenberg.iter_search("early Islamic history", max_records=500):
    print(book.title, book.creator, book.url, book.license)

open_library = OpenLibrarySearch()
for book in open_library.search("early Islamic history", limit=20):
    print(book.title, book.creator, book.url)
\`\`\`

The iter_search method is an explicit, bounded pagination workflow. Its default ceiling is
1,000 results, and callers can raise it to at most 10,000. This is a discovery
tool, not a promise that every result is open access or downloadable. Open
Library's live API must not be used for bulk metadata harvesting; use its
official monthly data dumps for bulk research datasets.

## Example: search news

\`\`\`python
from historypy import GDELTNewsSearch

news = GDELTNewsSearch().search(
    "historical archaeology",
    timespan="7d",
    limit=25,
)
for article in news:
    print(article.title, article.creator, article.url)
\`\`\`

The optional Guardian provider requires a key:

\`\`\`bash
export GUARDIAN_API_KEY="your-key"
\`\`\`

\`\`\`python
from historypy import GuardianNewsSearch

articles = GuardianNewsSearch().search("archaeology", limit=10)
\`\`\`

## Federated cross-checking

\`\`\`python
from historypy import (
    GDELTNewsSearch,
    GutendexSearch,
    InternetArchiveSearch,
    OpenLibrarySearch,
    cross_verify_claim,
)

report = cross_verify_claim(
    dataset,
    claim_id="claim-001",
    providers=[
        OpenLibrarySearch(),
        GutendexSearch(),
        InternetArchiveSearch(),
        GDELTNewsSearch(),
    ],
    limit_per_provider=10,
)
print(report.candidate_count)
print(report.provider_report.failures)
print(report.duplicate_candidates)
print(report.metadata_conflicts)
\`\`\`

Search candidates are never automatically linked as supporting evidence. A
catalog hit may be a derivative record, a later reprint, an inaccurate record,
or the same original report indexed by multiple services. Inspect provenance
and the underlying source before adding an EvidenceLink. Multiple providers
do not automatically mean multiple independent sources.

## Live source and quotation checks

\`\`\`python
from historypy import verify_source_urls

report = verify_source_urls(dataset, claim_id="claim-001")
for result in report.results:
    print(
        result.source_id,
        result.status,
        result.http_status,
        result.quotation_status,
        result.checked_url,
    )
\`\`\`

The verifier checks only HTTP(S) reachability and exact quotation presence
after case-folding and whitespace normalization. It is bounded to 2 MB per
response by default and inspects HTML/plain text only. It rejects local/private
network destinations. A quote not found may reflect a paywall, changed page,
OCR/translation difference, or an incorrect quotation; a quote found does not
prove authenticity or context.

## Claim documentation assessment

\`\`\`python
from historypy import analyze_claim_confidence

assessment = analyze_claim_confidence(dataset, "claim-001")
print(assessment.documentation_score)
print(assessment.documentation_band)
print(assessment.evidence_status)
print(assessment.source_independence_status)
print(assessment.limitations)
\`\`\`

The 0-100 score is a documentation-completeness heuristic, not a probability
that the historical claim is true. It combines citation traceability (50%),
locator coverage (30%), and capped source count (20%). It does not reward
unknown independence as corroboration. Read the component fields and
limitations; do not report this number as a truth confidence percentage.

## Rights, privacy, and operational safeguards

- Store metadata, short permitted snippets, and stable links; do not mirror
  entire copyrighted books or news articles.
- A free API key does not grant a right to republish the provider's content.
- Check record-level rights, jurisdiction, API terms, quotas, attribution, and
  cache rules before downloading or redistributing any full text.
- Keep API keys in environment variables; never commit keys to the repository.
- Cache provider responses and use bounded pagination. Do not send high-volume
  single-record requests to a public service.
- Provider errors are returned per provider; an incomplete search is not proof
  that no relevant sources exist.

## Official provider documentation

- Open Library APIs and usage/rate limits: https://openlibrary.org/developers/api
- Open Library Search API: https://openlibrary.org/dev/docs/api/search
- Project Gutenberg catalog, OPDS, and machine-readable metadata: https://www.gutenberg.org/ebooks/offline_catalogs.html
- Gutendex API: https://gutendex.com/
- Internet Archive item search APIs: https://doc-tools.readthedocs.io/en/ia-test-gsod/item-search-apis.html
- Internet Archive search and full-text overview: https://archivesupport.zendesk.com/hc/en-us/articles/360018359991-Search-A-Basic-Guide
- GDELT Project data and APIs: https://www.gdeltproject.org/data.html
- The Guardian Open Platform access tiers: https://open-platform.theguardian.com/access/
- The Guardian API documentation: https://open-platform.theguardian.com/documentation/
