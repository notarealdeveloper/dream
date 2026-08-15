MAIN := master
PDF := $(MAIN).pdf
BUILD := build
CACHE := $(BUILD)/texmf-var
LATEX := lualatex
LATEXFLAGS := -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=$(BUILD)

TEX_SOURCES := $(shell find . -path './build' -prune -o -name '*.tex' -print)

export TEXMFVAR = $(CACHE)

.PHONY: all pdf data align tex validate clean distclean

all: pdf

pdf: data $(PDF)

data align tex validate:
	python3 scripts/build.py

$(PDF): $(TEX_SOURCES)
	@mkdir -p "$(BUILD)" "$(CACHE)" "$(BUILD)/01-book-one" "$(BUILD)/02-book-two"
	$(LATEX) $(LATEXFLAGS) "$(MAIN).tex"
	@if grep -q 'Rerun to get' "$(BUILD)/$(MAIN).log"; then \
		$(LATEX) $(LATEXFLAGS) "$(MAIN).tex"; \
	fi
	cp "$(BUILD)/$(MAIN).pdf" .

clean:
	rm -rf "$(BUILD)"

distclean: clean
	rm -f "$(PDF)"
