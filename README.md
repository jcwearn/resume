# resume

Resume content lives in YAML. A small renderer feeds it through a Jinja2 LaTeX template and
Tectonic compiles the PDF. Adding a job means writing ~15 lines of YAML — you never touch LaTeX.

```
content/*.yaml  ->  render.py  ->  build/resume-<variant>.tex  ->  out/*.pdf
```

## Setup

```sh
brew install tectonic uv
```

Tectonic downloads the LaTeX packages it needs on first build and caches them; there is no TeX Live
install to manage. `uv` handles the Python venv automatically — no activation step.

## Build

```sh
make              # default variant -> out/jackson-wearn-resume.pdf
make VARIANT=backend
make all          # every variant in variants/
make json         # out/resume.json, the content the website renders from
make check        # build everything and fail if a variant exceeds MAX_PAGES (default 2)
make watch        # rebuild on save
make clean
```

## CI

- **`build.yaml`** — runs on every PR: builds all variants, fails if any exceeds `MAX_PAGES`,
  uploads the PDFs as a run artifact.
- **`publish.yaml`** — runs on push to `main`: rebuilds and commits `out/*.pdf` if they changed, so
  the committed PDFs always match the YAML.

Builds are reproducible. The Makefile pins `SOURCE_DATE_EPOCH` to the last commit touching
`content/`, `templates/`, or `render.py`, so the same inputs always produce byte-identical PDFs —
locally and in CI alike. Without that, XeTeX's embedded timestamp would make every rebuild differ,
`publish.yaml` would commit on every run, and its own commit would re-trigger it in a loop.

Practically: run `make` before committing if you want, but you don't have to. CI will rebuild and
commit the PDFs itself, and it won't create a diff unless the content actually changed.

## Adding a job

Drop a new file in `content/experience/`. Filenames don't matter and there are no numeric prefixes —
entries are sorted by `start` date descending at render time.

```yaml
company: Acme Corp
title: Staff Software Engineer
subtitle: Platform Team          # optional
location: Atlanta, GA
start: 2026-09                   # YYYY-MM
end: present                     # or YYYY-MM
max_bullets: 6                   # optional cap for this entry
bullets:
  - text: "Did the thing that mattered."
    tags: [backend, api]
    priority: 1
```

Write bullet text in plain prose. Unicode punctuation (`—`, `·`, `–`, `“ ”`) is converted to portable
LaTeX automatically, and every LaTeX special character is escaped for you. Use curly quotes rather
than `"` — TeX renders both halves of a straight pair as closing quotes.

### Bullet priority

| priority | meaning |
|---|---|
| 1 | Always keep. The bullets that carry the role. |
| 2 | Default. Included in the standard resume. |
| 3 | Extra detail. Dropped unless a variant asks for it. |

Write more bullets than fit. Priority is what lets one content set produce a tight resume and a
detailed one without rewriting anything.

### Tags

Free-form, but stay consistent so variants keep working. In use today:
`backend`, `frontend`, `fullstack`, `api`, `data`, `devops`, `k8s`, `testing`, `ai`, `leadership`,
`ops`, `migration`.

## Variants

A variant is three knobs:

```yaml
# variants/backend.yaml
label: Backend
max_priority: 2                     # drop anything above this
emphasize: [backend, api, devops]   # stable-sort these bullets first
exclude_tags: []                    # rarely needed
```

`emphasize` reorders rather than filters, so a bullet never silently vanishes because of a missing
tag. Priority still dominates the ordering — emphasis only breaks ties *within* a priority tier, so
a variant can't float a minor bullet above the work that carries the role. If you want frontend
bullets leading the fullstack variant, raise their priority rather than leaning on `emphasize`.

To add a variant, drop in a new file — `make all` picks it up automatically.

Optionally override the summary per variant by adding a matching key under `summary_variants` in
`content/profile.yaml`.

## Cover letters

Letters run through the same pipeline — YAML in, LaTeX out, no template editing:

```sh
make letter LETTER=acme        # private/letters/acme.yaml -> private/out/
make letters                   # every letter in private/letters/
```

```yaml
# private/letters/acme.yaml
company: Acme Corp
role: Staff Software Engineer
date: September 1, 2026     # optional, free text; omit to drop the line
salutation: Acme Team       # optional, defaults to "Hiring Team"
closing: Sincerely          # optional
paragraphs:
  - >-
    First paragraph.
  - >-
    Second paragraph.
```

`company` and `role` render as a `Re:` line, so the role can't go stale in the prose without
showing. Name, contacts, and links are **not** repeated here — they come from
`content/profile.yaml`, and the letter reuses the resume's `\resumeheader`, fonts, and margins, so
the two documents can't drift apart visually. `make letter` fails past `MAX_LETTER_PAGES` (default
1) the same way `make check` guards the resume.

**Letters live in gitignored `private/`, and that is deliberate.** This repo is public and
`publish.yaml` commits build output back to `main` — committing letters would publish which
companies you applied to. Only the machinery is tracked; the letters and their PDFs are not, so CI
never builds them and `make check` deliberately leaves them alone.

## Layout

```
content/
  profile.yaml           # name, contact links, summary
  experience/*.yaml      # one file per employer
  projects.yaml          # Infrastructure & Projects
  skills.yaml
  education.yaml
variants/*.yaml
templates/
  resume.cls             # document class: fonts, spacing, macros
  resume.tex.j2          # resume body
  letter.tex.j2          # cover letter body
render.py
out/                     # committed PDFs
build/                   # gitignored intermediates
private/                 # gitignored source material
  letters/*.yaml         # cover letter content
  out/                   # cover letter PDFs
```

`private/` holds the Jira export, performance reviews, and employment verification letter used to
write the bullets, plus the cover letters. It is gitignored because it contains salary and review
content — keep it that way.

## Styling

Fonts, margins, and spacing live at the top of `templates/resume.cls`. The default is Latin Modern,
which ships with every TeX distribution and needs no download; the class header documents how to
swap it.

Spacing is deliberately loose — `\headerskip`, `\entryskip`, `\bulletsep`, and `\linespread` are the
knobs. A resume gets skimmed before it gets read, so whitespace between blocks buys more than an
extra bullet does. Tightening them fits more content; loosening them costs content. That tradeoff is
what bullet priority is for: write everything, then let `max_bullets` and `max_priority` decide what
survives at a given density. If a spacing change pushes past two pages, `make check` fails rather
than letting it ship.

The template is deliberately ATS-safe: single column, real selectable text, no icon fonts, and no
layout built from multi-column boxes. Verify with `make ats`, which dumps the extracted text in
reading order.
