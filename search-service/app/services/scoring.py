"""Shared fuzzy matching helpers for search ranking."""

import re


def normalize_text(value: str | None) -> str:
    """Normalize text for case-insensitive fuzzy comparison.
    
    Args:
        value (str | None): Parameter value.
    
    Returns:
        str: Text for case-insensitive fuzzy comparison.
    """
    return " ".join((value or "").strip().lower().split())


def tokenize(value: str | None) -> list[str]:
    """Tokenize normalized text into alphanumeric words.
    
    Args:
        value (str | None): Parameter value.
    
    Returns:
        list[str]: Result of the operation.
    """
    normalized = normalize_text(value)
    if not normalized:
        return []
    return re.findall(r"[a-z0-9]+", normalized)


def char_ngrams(value: str | None, n: int = 3) -> set[str]:
    """Build character n-grams from normalized text.
    
    Args:
        value (str | None): Parameter value.
        n (int): Parameter n.
    
    Returns:
        set[str]: Character n-grams from normalized text.
    """
    normalized = normalize_text(value)
    if not normalized:
        return set()
    if len(normalized) < n:
        return {normalized}
    return {normalized[index : index + n] for index in range(len(normalized) - n + 1)}


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    """Compute Jaccard similarity score for two token sets.
    
    Args:
        left (set[str]): Parameter left.
        right (set[str]): Parameter right.
    
    Returns:
        float: Jaccard similarity score for two token sets.
    """
    if not left or not right:
        return 0.0
    union_size = len(left.union(right))
    if union_size == 0:
        return 0.0
    return len(left.intersection(right)) / union_size


def fuzzy_similarity(query: str, candidate: str | None) -> float:
    """Compute weighted fuzzy similarity between query and candidate text.
    
    Args:
        query (str): Search query string.
        candidate (str | None): Parameter candidate.
    
    Returns:
        float: Weighted fuzzy similarity between query and candidate text.
    """
    normalized_query = normalize_text(query)
    normalized_candidate = normalize_text(candidate)
    if not normalized_query or not normalized_candidate:
        return 0.0

    if normalized_query == normalized_candidate:
        return 1.0

    if normalized_candidate.startswith(normalized_query):
        exact_signal = 0.93
    elif normalized_query in normalized_candidate:
        exact_signal = 0.82
    else:
        exact_signal = 0.0

    query_tokens = set(tokenize(normalized_query))
    candidate_tokens = set(tokenize(normalized_candidate))
    if query_tokens and candidate_tokens:
        overlap_ratio = len(query_tokens.intersection(candidate_tokens)) / len(query_tokens)
        prefix_hits = sum(
            1
            for token in query_tokens
            if any(candidate_token.startswith(token) for candidate_token in candidate_tokens)
        )
        prefix_ratio = prefix_hits / len(query_tokens)
        token_signal = max(overlap_ratio, 0.9 * prefix_ratio)
    else:
        token_signal = 0.0

    ngram_signal = jaccard_similarity(char_ngrams(normalized_query), char_ngrams(normalized_candidate))
    return max(exact_signal, (token_signal * 0.62) + (ngram_signal * 0.38))
