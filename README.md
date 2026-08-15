# We the Nameless: Dream of the Red Chamber

This repository is a first-pass We the Nameless edition of *Dream of the Red Chamber* / *Honglou Meng* / *Shi Tou Ji*.

It is modeled on the local `BIBLE/` reference project, but the root project is independently buildable. The extracted pieces are the page geometry, title/frontmatter identity, source-profile highlighting, and side-by-side verse system.

## Sources

Chinese uses `zh/github-huangtuzhi/chapter-1` through `chapter-120`, selected because it is already a complete 120-chapter corpus with clean chapter files.

English uses the checked-in H. Bencraft Joly Project Gutenberg files under `en/bencraft/`. Those files currently contain chapters 1-56; chapters after that are represented with Chinese text and explicit source-missing English placeholders. No missing English has been translated or invented.

## Generation

Run:

```sh
make data
make
```

`scripts/build.py` parses both source corpora, segments Chinese on sentence punctuation, segments English with a lightweight abbreviation-aware splitter, and produces monotonic verse-like alignment records in `data/alignment.jsonl`.

Chinese `。` is the preferred prose verse boundary. The aligner keeps Chinese sentence units short by default and lets each Chinese verse absorb the best nearby English span. The English side may therefore contain a fragment, a full sentence, several fragments, or no clean English unit when the sources do not line up neatly.

The alignment is provisional. It uses a monotonic dynamic-programming pass over Chinese sentence units and neighboring English spans, with cumulative position, length balance, and a small curated name/term table as signals. It is meant to produce a complete editable edition, not a final scholarly alignment.

Correct alignments in `data/alignment.jsonl` or improve `scripts/build.py`, then regenerate with `make data`.

Run regression checks with:

```sh
make check
```

The pytest suite in `tests/` checks source preservation, monotonic source spans, short Chinese verse boundaries, chapter boundary anchors, and curated bilingual anchors. Add a known-good correspondence by extending the anchor tables in `tests/test_alignment.py` after confirming the Chinese and English wording in the source files.

## Source Profiles

The TeX source profiles are functional now:

- `\eA{...}` and `\zA{...}` mark the provisional Author profile.
- `\eR{...}` and `\zR{...}` mark the provisional Redactor / editor / continuation profile.

This first pass marks chapters 1-80 as Author and chapters 81-120 as Redactor to visualize the traditional authorship/editorial problem cautiously.
