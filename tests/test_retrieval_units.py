"""Offline tests for extraction repair, tokenization and chunk packing."""

from relay.corpus.chunk import ChunkingSpec, estimate_tokens
from relay.corpus.extract import TextBlock, is_heading, repair_split_caps
from relay.corpus.chunk import chunk_paper
from relay.retrieval.index import tokenize


def test_repair_split_caps_rejoins_heading_word() -> None:
    assert repair_split_caps("4.1 T ext data") == "4.1 Text data"
    assert repair_split_caps("6.4 Identification: W atermarking") == (
        "6.4 Identification: Watermarking"
    )


def test_repair_split_caps_leaves_real_articles_alone() -> None:
    assert repair_split_caps("A model of the relay") == "A model of the relay"


def test_heading_with_split_caps_is_detected() -> None:
    assert is_heading("6.1 T oxicity analysis", "Moshi") == ("6.1", "Toxicity analysis")


def test_heading_rejects_table_row() -> None:
    assert is_heading("R VQGAN 24kHz 75Hz 1.5kbps - 1.74 2.74 31.3±1.3", "Moshi") is None


def test_heading_rejects_numbered_question() -> None:
    assert is_heading("1. How does our model behave in terms of producing toxic content?", "x") is None


def test_tokenizer_merges_split_caps_so_text_matches() -> None:
    document = tokenize("5.1 T ext Language Modeling")
    query = tokenize("text language modeling")
    assert "text" in document
    assert set(query) <= set(document)


def test_tokenizer_drops_stopwords_but_keeps_math_variables() -> None:
    assert tokenize("the a of the") == []
    assert tokenize("d k 8 heads") == ["d", "k", "8", "heads"]


def test_estimate_tokens_rounds_up() -> None:
    assert estimate_tokens("x" * 40) == 10
    assert estimate_tokens("") == 1


def test_chunks_stay_inside_their_section_and_pages() -> None:
    blocks = [
        TextBlock("3.2", "Attention", 4, ("word " * 120,)),
        TextBlock("3.2", "Attention", 5, ("word " * 120,)),
        TextBlock("3.3", "Feed-Forward", 5, ("other " * 40,)),
    ]
    chunks = chunk_paper(
        blocks,
        paper_key="attention",
        title="Attention Is All You Need",
        arxiv_id="1706.03762",
        version=7,
        spec=ChunkingSpec(chunk_tokens=100, overlap_tokens=20),
    )
    assert len(chunks) >= 3
    assert all(chunk.section_title in {"Attention", "Feed-Forward"} for chunk in chunks)
    assert chunks[0].paper_key == "attention"
    assert chunks[0].page_start == 4
    assert {chunk.section_title for chunk in chunks} == {"Attention", "Feed-Forward"}


def test_overlap_carries_context_into_next_chunk() -> None:
    blocks = [TextBlock("1", "Intro", 1, tuple(f"line{i} " * 20 for i in range(12)))]
    chunks = chunk_paper(
        blocks,
        paper_key="p",
        title="t",
        arxiv_id="1234.56789",
        version=1,
        spec=ChunkingSpec(chunk_tokens=120, overlap_tokens=40),
    )
    assert len(chunks) > 1
    first_tail = chunks[0].text.split()[-5:]
    assert any(word in chunks[1].text for word in first_tail)
