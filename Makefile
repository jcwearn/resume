# Resume build. See README.md.

VARIANT   ?= default
MAX_PAGES ?= 2
NAME      := jackson-wearn-resume

PY        := uv run --quiet python
VARIANTS  := $(sort $(notdir $(basename $(wildcard variants/*.yaml))))

# XeTeX stamps a creation date into the PDF, so an unpinned build is never
# byte-identical twice. Pinning SOURCE_DATE_EPOCH to the last commit that
# touched a build input makes output reproducible: the PDF changes only when
# something it's derived from changes. That's what lets CI commit rebuilt PDFs
# without looping, and what keeps a local `make` from producing a spurious diff.
# Falls back to a fixed epoch outside a git checkout (git exits 0 with empty
# output there, so a shell `||` would not catch it).
GIT_EPOCH := $(shell git log -1 --format=%ct -- content templates render.py 2>/dev/null)
SOURCE_DATE_EPOCH ?= $(or $(GIT_EPOCH),1700000000)
export SOURCE_DATE_EPOCH

# The default variant is the canonical resume, so it keeps the bare filename.
SUFFIX    := $(if $(filter default,$(VARIANT)),,-$(VARIANT))
OUTFILE   := out/$(NAME)$(SUFFIX).pdf

.PHONY: resume all check ats watch clean help

resume:
	@$(PY) render.py --variant $(VARIANT)
	@tectonic -X compile build/resume-$(VARIANT).tex \
		--outdir build --keep-intermediates --keep-logs
	@mkdir -p out
	@cp build/resume-$(VARIANT).pdf $(OUTFILE)
	@echo "built $(OUTFILE)"

all:
	@for v in $(VARIANTS); do $(MAKE) --no-print-directory resume VARIANT=$$v || exit 1; done

# Page count comes from the LastPage label the lastpage package writes into the
# .aux, so this needs no PDF tooling beyond what already built the document.
check: all
	@fail=0; \
	for v in $(VARIANTS); do \
		pages=$$(sed -n 's/.*newlabel{LastPage}{{}*{\([0-9][0-9]*\)}.*/\1/p' build/resume-$$v.aux | tail -1); \
		if [ -z "$$pages" ]; then \
			echo "FAIL $$v: could not determine page count"; fail=1; \
		elif [ "$$pages" -gt "$(MAX_PAGES)" ]; then \
			echo "FAIL $$v: $$pages pages (max $(MAX_PAGES))"; fail=1; \
		else \
			echo "ok   $$v: $$pages page(s)"; \
		fi; \
	done; \
	exit $$fail

# Rough ATS proxy: dump the text an parser would see, in reading order.
ats: resume
	@command -v pdftotext >/dev/null || { echo "needs poppler: brew install poppler"; exit 1; }
	@pdftotext $(OUTFILE) -

watch:
	@command -v fswatch >/dev/null || { echo "needs fswatch: brew install fswatch"; exit 1; }
	@$(MAKE) --no-print-directory resume || true
	@fswatch -o content variants templates render.py | \
		while read -r _; do $(MAKE) --no-print-directory resume || true; done

clean:
	@rm -rf build
	@echo "cleaned build/ (out/ kept)"

help:
	@echo "make [VARIANT=$(VARIANT)]  build one variant -> $(OUTFILE)"
	@echo "make all                   build every variant: $(VARIANTS)"
	@echo "make check                 fail if any variant exceeds $(MAX_PAGES) pages"
	@echo "make ats                   dump extracted text in reading order"
	@echo "make watch                 rebuild on save"
	@echo "make clean"

.DEFAULT_GOAL := resume
