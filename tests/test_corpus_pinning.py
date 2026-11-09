"""Offline tests for the corpus pinning logic."""

from relay.config import PaperSpec
from relay.corpus.fetch import parse_version_marker


def test_marker_found_with_class_suffix() -> None:
    text = "Provided proper attribution... arXiv:1706.03762v7 [cs.CL] 5 Jun 2017"
    assert parse_version_marker(text) == ("1706.03762", 7)


def test_marker_found_with_irregular_whitespace() -> None:
    text = "arXiv:  2507.07955v2\n[cs.LG] 10 Jul 2025"
    assert parse_version_marker(text) == ("2507.07955", 2)


def test_marker_absent_returns_none() -> None:
    assert parse_version_marker("no identifier on this page") is None


def test_spec_builds_pinned_url_and_filename() -> None:
    spec = PaperSpec(key="moshi", arxiv_id="2410.00037", version=1, title="Moshi")
    assert spec.filename == "2410.00037v1.pdf"
    assert spec.url == "https://arxiv.org/pdf/2410.00037v1"
