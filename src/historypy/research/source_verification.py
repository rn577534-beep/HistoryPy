"""Bounded live verification of recorded source URLs and exact quotations.

This checks HTTP reachability and exact text presence only. It cannot
authenticate a document, prove authorship, validate a citation's context, or
establish historical truth.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)

from historypy.core.dataset import HistoricalDataset


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def _validate_public_http_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute HTTP(S) source URLs are supported")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost"} or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal hosts are not allowed")
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            addresses = [
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            ]
        except OSError as exc:
            raise ValueError(f"Could not resolve source host: {exc}") from exc
    if not addresses or any(
        address.is_private or address.is_loopback or address.is_link_local
        or address.is_reserved or address.is_multicast or address.is_unspecified
        for address in addresses
    ):
        raise ValueError("Private, local, or reserved network destinations are not allowed")


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_public_http_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True, slots=True)
class SourceVerificationResult:
    source_id: str
    url: str
    status: str
    http_status: int | None
    content_type: str | None
    quotation_status: str
    checked_url: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SourceVerificationReport:
    results: tuple[SourceVerificationResult, ...]

    @property
    def reachable_count(self) -> int:
        return sum(item.status == "reachable" for item in self.results)

    @property
    def quotation_match_count(self) -> int:
        return sum(item.quotation_status == "found" for item in self.results)

    @property
    def failed_count(self) -> int:
        return sum(item.status in {"http_error", "request_error", "unsafe_url"} for item in self.results)


def _normalized_quote(value: str) -> str:
    return " ".join(value.casefold().split())


def _fetch_source(source_id: str, url: str, quotations: tuple[str, ...], *,
                  timeout: float, max_bytes: int) -> SourceVerificationResult:
    try:
        _validate_public_http_url(url)
        request = Request(url, headers={
            "Accept": "text/html, text/plain;q=0.9",
            "User-Agent": "HistoryPy/1.1 (+https://github.com/rn577534-beep/HistoryPy)",
        })
        opener = build_opener(_SafeRedirectHandler())
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            body = response.read(max_bytes + 1)
            final_url = response.geturl()
        if len(body) > max_bytes:
            return SourceVerificationResult(
                source_id, url, "too_large", status, content_type, "not_checked",
                final_url, f"Response exceeded the {max_bytes}-byte limit",
            )
        if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
            return SourceVerificationResult(
                source_id, url, "reachable", status, content_type, "unsupported",
                final_url, "Only HTML and plain-text pages are checked for quotations",
            )
        text = body.decode("utf-8", errors="replace")
        if content_type != "text/plain":
            parser = _TextExtractor()
            parser.feed(text)
            text = parser.text()
        normalized = _normalized_quote(text)
        quote_states = [
            _normalized_quote(quote) in normalized
            for quote in quotations if quote and quote.strip()
        ]
        quote_status = (
            "not_provided" if not quote_states
            else "found" if all(quote_states)
            else "not_found"
        )
        return SourceVerificationResult(
            source_id, url, "reachable", status, content_type, quote_status, final_url,
        )
    except ValueError as exc:
        return SourceVerificationResult(
            source_id, url, "unsafe_url", None, None, "not_checked", error=str(exc),
        )
    except HTTPError as exc:
        return SourceVerificationResult(
            source_id, url, "http_error", exc.code, None, "not_checked", error=str(exc),
        )
    except (URLError, TimeoutError, OSError) as exc:
        return SourceVerificationResult(
            source_id, url, "request_error", None, None, "not_checked", error=str(exc),
        )


def verify_source_urls(
    dataset: HistoricalDataset,
    claim_id: str | None = None,
    *,
    timeout: float = 10.0,
    max_bytes: int = 2_000_000,
) -> SourceVerificationReport:
    """Check source URL reachability and exact recorded quotations.

    One request is made per unique source. Only HTML/plain-text responses up
    to max_bytes are inspected. Quote matching is exact after case-folding and
    whitespace normalization; it is not fuzzy or semantic matching.
    """
    dataset.require_valid()
    if claim_id is not None and claim_id not in {item.id for item in dataset.claims}:
        raise KeyError(f"Unknown claim id: {claim_id}")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("timeout must be a positive number")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")

    source_ids = {
        link.source_id for link in dataset.evidence
        if claim_id is None or link.claim_id == claim_id
    }
    source_map = {source.id: source for source in dataset.sources}
    results = []
    for source_id in sorted(source_ids):
        source = source_map[source_id]
        if not source.url:
            results.append(SourceVerificationResult(
                source_id, "", "missing_url", None, None, "not_checked",
                error="No URL is recorded for this source",
            ))
            continue
        quotes = tuple(
            link.quotation for link in dataset.evidence
            if link.source_id == source_id
            and (claim_id is None or link.claim_id == claim_id)
            and link.quotation
        )
        results.append(_fetch_source(
            source_id, source.url, quotes, timeout=float(timeout), max_bytes=max_bytes,
        ))
    return SourceVerificationReport(tuple(results))


__all__ = [
    "SourceVerificationReport", "SourceVerificationResult", "verify_source_urls",
]
