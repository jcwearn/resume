# Resume build. See README.md.

VARIANT   ?= default
MAX_PAGES ?= 2
NAME      := jackson-wearn-resume

# Cover letters. Both the content and the output live under private/, which is
# gitignored: this repo is public, and which companies you applied to is not.
# Nothing here is reachable from `check`, so CI -- which never checks out
# private/ -- is unaffected.
LETTERNAME       := jackson-wearn-cover-letter
LETTERDIR        ?= private/letters
LETTEROUT        ?= private/out
MAX_LETTER_PAGES ?= 1

PY        := uv run --quiet python
VARIANTS  := $(sort $(notdir $(basename $(wildcard variants/*.yaml))))

# XeTeX stamps a creation date into the PDF, so an unpinned build is never
# byte-identical twice. Pinning SOURCE_DATE_EPOCH to the last commit that
# touched a build input makes output reproducible: the PDF changes only when
# something it's derived from changes. That's what lets CI commit rebuilt PDFs
# without looping, and what keeps a local `make` from producing a spurious diff.
# Falls back to a fixed epoch outside a git checkout (git exits 0 with empty
# output there, so a shell `||` would not catch it).
# Letters are deliberately not inputs here: they're untracked, so git can't
# date them, and their PDFs are never committed for a rebuild to churn.
GIT_EPOCH := $(shell git log -1 --format=%ct -- content templates render.py 2>/dev/null)
SOURCE_DATE_EPOCH ?= $(or $(GIT_EPOCH),1700000000)
export SOURCE_DATE_EPOCH

# The default variant is the canonical resume, so it keeps the bare filename.
SUFFIX    := $(if $(filter default,$(VARIANT)),,-$(VARIANT))
OUTFILE   := out/$(NAME)$(SUFFIX).pdf
JSONFILE  := out/resume.json

.PHONY: resume all json check letter letters ats watch clean help

resume:
	@$(PY) render.py --variant $(VARIANT)
	@tectonic -X compile build/resume-$(VARIANT).tex \
		--outdir build --keep-intermediates --keep-logs
	@mkdir -p out
	@cp build/resume-$(VARIANT).pdf $(OUTFILE)
	@echo "built $(OUTFILE)"

all:
	@for v in $(VARIANTS); do $(MAKE) --no-print-directory resume VARIANT=$$v || exit 1; done

# The same filtered content as the PDF, for consumers that are not LaTeX.
# jacksonwearn.com renders its resume page from this, so the site shows real
# HTML instead of an embedded PDF viewer. Only the default variant is
# published: it is the canonical resume, and the others exist for tailoring
# applications, not for the website.
json:
	@$(PY) render.py --variant default --json $(JSONFILE)
	@echo "built $(JSONFILE)"

# Page count comes from the LastPage label the lastpage package writes into the
# .aux, so this needs no PDF tooling beyond what already built the document.
check: all json
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

# A cover letter that runs to two pages doesn't get read, so the page gate is
# the same idea as `check` -- same LastPage-from-.aux trick, tighter limit.
letter:
	@test -n "$(LETTER)" || { echo "usage: make letter LETTER=<slug>   ($(LETTERDIR)/<slug>.yaml)"; exit 1; }
	@$(PY) render.py --letter $(LETTERDIR)/$(LETTER).yaml
	@tectonic -X compile build/letter-$(LETTER).tex \
		--outdir build --keep-intermediates --keep-logs
	@mkdir -p $(LETTEROUT)
	@cp build/letter-$(LETTER).pdf $(LETTEROUT)/$(LETTERNAME)-$(LETTER).pdf
	@pages=$$(sed -n 's/.*newlabel{LastPage}{{}*{\([0-9][0-9]*\)}.*/\1/p' build/letter-$(LETTER).aux | tail -1); \
	if [ -z "$$pages" ]; then \
		echo "FAIL $(LETTER): could not determine page count"; exit 1; \
	elif [ "$$pages" -gt "$(MAX_LETTER_PAGES)" ]; then \
		echo "FAIL $(LETTER): $$pages pages (max $(MAX_LETTER_PAGES))"; exit 1; \
	fi; \
	echo "built $(LETTEROUT)/$(LETTERNAME)-$(LETTER).pdf ($$pages page(s))"

# A no-op rather than an error when there are no letters: a fresh clone has no
# private/. Guard and loop share one shell -- as separate recipe lines an early
# exit would only end the guard, leaving the loop to run on an unmatched glob.
letters:
	@found=0; \
	for f in $(LETTERDIR)/*.yaml; do \
		[ -e "$$f" ] || continue; \
		found=1; \
		$(MAKE) --no-print-directory letter LETTER=$$(basename $$f .yaml) || exit 1; \
	done; \
	[ "$$found" = 1 ] || echo "no letters in $(LETTERDIR)/"

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
	@echo "make json                  write $(JSONFILE) for the website"
	@echo "make check                 fail if any variant exceeds $(MAX_PAGES) pages"
	@echo "make letter LETTER=<slug>  build $(LETTERDIR)/<slug>.yaml -> $(LETTEROUT)/"
	@echo "make letters               build every letter in $(LETTERDIR)/"
	@echo "make ats                   dump extracted text in reading order"
	@echo "make watch                 rebuild on save"
	@echo "make clean"

.DEFAULT_GOAL := resume
