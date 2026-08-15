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

The alignment is provisional. It groups adjacent Chinese and English segments by cumulative character mass and bounded 1:1, 1:2, 2:1, 2:2, 1:3, and 3:1 moves. It is meant to produce a complete editable edition, not a final scholarly alignment.

Correct alignments in `data/alignment.jsonl` or improve `scripts/build.py`, then regenerate with `make data`.

## Source Profiles

The TeX source profiles are functional now:

- `\eA{...}` and `\zA{...}` mark the provisional Author profile.
- `\eR{...}` and `\zR{...}` mark the provisional Redactor / editor / continuation profile.

This first pass marks chapters 1-80 as Author and chapters 81-120 as Redactor to visualize the traditional authorship/editorial problem cautiously.
