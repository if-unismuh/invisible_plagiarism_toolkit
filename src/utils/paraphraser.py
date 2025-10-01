from __future__ import annotations

import random
import re
from typing import Dict, List

__all__ = ["paraphrase_text"]

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])", re.UNICODE)
CLAUSE_SPLIT_RE = re.compile(r",\s*")
WORD_RE = re.compile(r"\w+", re.UNICODE)


def paraphrase_text(
    text: str,
    synonyms_map: Dict[str, List[str]] | None,
    phrase_map: Dict[str, List[str]] | None,
    replacement_rate: float,
    clause_swap_rate: float = 0.25,
) -> str:
    if not text or replacement_rate <= 0:
        return text

    sentences = SENTENCE_SPLIT_RE.split(text)
    if len(sentences) == 1:
        sentences = [text]

    processed = [_paraphrase_sentence(sentence, synonyms_map, phrase_map, replacement_rate, clause_swap_rate)
                 for sentence in sentences]
    return rebuild_text(text, processed)


def _paraphrase_sentence(
    sentence: str,
    synonyms_map: Dict[str, List[str]] | None,
    phrase_map: Dict[str, List[str]] | None,
    replacement_rate: float,
    clause_swap_rate: float,
) -> str:
    if not sentence.strip():
        return sentence

    ending = ''
    if sentence and sentence[-1] in '.!?':
        ending = sentence[-1]
        core = sentence[:-1]
    else:
        core = sentence

    core = _apply_phrase_replacements(core, phrase_map)
    core = _apply_synonym_swaps(core, synonyms_map, replacement_rate)
    core = _maybe_swap_clauses(core, clause_swap_rate)
    return core.strip() + ending


def _apply_phrase_replacements(sentence: str, phrase_map: Dict[str, List[str]] | None) -> str:
    if not phrase_map:
        return sentence

    result = sentence
    for phrase, alternatives in phrase_map.items():
        if not alternatives:
            continue
        pattern = re.compile(rf"(?i)(?<!\w){re.escape(phrase)}(?!\w)")

        def _repl(match: re.Match[str]) -> str:
            replacement = random.choice(alternatives)
            matched_text = match.group(0)
            if matched_text.isupper():
                return replacement.upper()
            if matched_text[0].isupper():
                return replacement.capitalize()
            return replacement

        result = pattern.sub(_repl, result)
    return result


def _apply_synonym_swaps(sentence: str, synonyms_map: Dict[str, List[str]] | None, replacement_rate: float) -> str:
    if not synonyms_map or replacement_rate <= 0:
        return sentence

    tokens = re.findall(r"\w+|\s+|[^\w\s]", sentence, flags=re.UNICODE)
    if not tokens:
        return sentence

    result_tokens: List[str] = []
    for token in tokens:
        if WORD_RE.fullmatch(token):
            lower = token.lower()
            synonyms = synonyms_map.get(lower)
            if synonyms and random.random() < replacement_rate:
                replacement = random.choice(synonyms)
                if token.isupper():
                    replacement = replacement.upper()
                elif token[0].isupper():
                    replacement = replacement.capitalize()
                result_tokens.append(replacement)
            else:
                result_tokens.append(token)
        else:
            result_tokens.append(token)
    return ''.join(result_tokens)


def _maybe_swap_clauses(sentence: str, clause_swap_rate: float) -> str:
    if clause_swap_rate <= 0:
        return sentence

    clauses = CLAUSE_SPLIT_RE.split(sentence)
    if len(clauses) < 2:
        return sentence

    cleaned = [c.strip() for c in clauses if c.strip()]
    if len(cleaned) < 2:
        return sentence

    if random.random() >= clause_swap_rate:
        return sentence

    first, *rest = cleaned
    reordered = rest + [first]
    # Maintain punctuation by joining with comma and space
    return ', '.join(reordered)


def rebuild_text(original: str, sentences: List[str]) -> str:
    stripped = [s.strip() for s in sentences if s.strip()]
    if not stripped:
        return original
    rebuilt = ' '.join(stripped)
    if original.endswith((' ', '\t', '\n')):
        rebuilt += ' '
    return rebuilt
