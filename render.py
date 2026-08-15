"""Render resume content (YAML) into a LaTeX document.

Content lives in content/, presentation lives in templates/. This script is the
seam between them: it loads the YAML, applies a variant's filtering rules, and
feeds the result through a Jinja2 template configured with LaTeX-safe
delimiters (\\VAR{...}, \\BLOCK{...}) so braces don't collide with LaTeX itself.

Every string reaching the template is LaTeX-escaped by default. Fields that
intentionally hold LaTeX or a URL opt out with the `raw` filter.

Cover letters go through the same machinery via --letter, sharing the escaping,
the template environment, and profile.yaml's header.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
VARIANTS = ROOT / "variants"
TEMPLATES = ROOT / "templates"

DEFAULT_PRIORITY = 2
DEFAULT_SALUTATION = "Hiring Team"
DEFAULT_CLOSING = "Sincerely"
MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


# --------------------------------------------------------------------------
# LaTeX escaping
# --------------------------------------------------------------------------


class Raw(str):
    """A string the finalizer leaves alone."""


_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Unicode we allow in the YAML, mapped to portable LaTeX so the output stays
# pure ASCII and compiles under any engine.
_UNICODE = {
    "·": r"\textperiodcentered{}",  # ·
    "–": "--",  # –
    "—": "---",  # —
    "→": r"$\rightarrow$",  # →
    "←": r"$\leftarrow$",  # ←
    "≤": r"$\leq$",  # ≤
    "≥": r"$\geq$",  # ≥
    "‘": "`",
    "’": "'",
    "“": "``",
    "”": "''",
    "…": r"\ldots{}",  # …
    " ": "~",
}

_SPECIAL_RE = re.compile("|".join(re.escape(c) for c in _SPECIAL))
_UNICODE_RE = re.compile("|".join(re.escape(c) for c in _UNICODE))


def latex_escape(text: str) -> str:
    text = _SPECIAL_RE.sub(lambda m: _SPECIAL[m.group()], text)
    return _UNICODE_RE.sub(lambda m: _UNICODE[m.group()], text)


def finalize(value):
    if isinstance(value, Raw):
        return str(value)
    if isinstance(value, str):
        return latex_escape(value)
    return value


# --------------------------------------------------------------------------
# Content loading
# --------------------------------------------------------------------------


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        raise SystemExit(f"{path} is empty")
    return data


def parse_month(value) -> tuple[int, int]:
    """'2024-06' -> (2024, 6). 'present' sorts after everything."""
    text = str(value).strip().lower()
    if text == "present":
        return (9999, 12)
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
    if not match:
        raise SystemExit(f"bad date {value!r}: expected YYYY-MM or 'present'")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise SystemExit(f"bad month in {value!r}")
    return (year, month)


def format_month(value) -> str:
    if str(value).strip().lower() == "present":
        return "Present"
    year, month = parse_month(value)
    return f"{MONTHS[month - 1]} {year}"


def format_range(start, end) -> str:
    return f"{format_month(start)} – {format_month(end)}"


def load_experience() -> list[dict]:
    entries = []
    for path in sorted((CONTENT / "experience").glob("*.yaml")):
        entry = load_yaml(path)
        for field in ("company", "title", "start", "end"):
            if field not in entry:
                raise SystemExit(f"{path}: missing required field '{field}'")
        entry["_sort"] = parse_month(entry["start"])
        entry["dates"] = format_range(entry["start"], entry["end"])
        entries.append(entry)
    entries.sort(key=lambda e: e["_sort"], reverse=True)
    return entries


# --------------------------------------------------------------------------
# Variant filtering
# --------------------------------------------------------------------------


def select_bullets(bullets: list[dict], variant: dict, cap: int | None) -> list[dict]:
    max_priority = variant.get("max_priority", DEFAULT_PRIORITY)
    exclude = set(variant.get("exclude_tags") or [])
    emphasize = list(variant.get("emphasize") or [])

    kept = []
    for bullet in bullets or []:
        if "text" not in bullet:
            raise SystemExit(f"bullet missing 'text': {bullet!r}")
        tags = set(bullet.get("tags") or [])
        if bullet.get("priority", DEFAULT_PRIORITY) > max_priority:
            continue
        if tags & exclude:
            continue
        kept.append(bullet)

    if emphasize:
        rank = {tag: i for i, tag in enumerate(emphasize)}

        def order(bullet: dict) -> tuple[int, int]:
            # Priority dominates so a variant can never float a minor bullet
            # above the work that carries the role; emphasis only breaks ties
            # within a tier. Sorting is stable, so bullets matching on both
            # keep their authored order.
            emphasis = min(
                (rank[t] for t in (bullet.get("tags") or []) if t in rank),
                default=len(emphasize),
            )
            return (bullet.get("priority", DEFAULT_PRIORITY), emphasis)

        kept.sort(key=order)

    return kept[:cap] if cap else kept


def apply_variant(experience: list[dict], projects: dict, variant: dict) -> None:
    for entry in experience:
        entry["bullets"] = select_bullets(
            entry.get("bullets"), variant, entry.get("max_bullets")
        )
    projects["bullets"] = select_bullets(
        projects.get("bullets"), variant, projects.get("max_bullets")
    )


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
        finalize=finalize,
    )
    env.filters["raw"] = Raw
    return env


def build_context(variant_name: str) -> dict:
    """Load the content and apply a variant's filtering.

    The single source of what a variant actually says, shared by every output
    format. Anything derived from it -- LaTeX, JSON -- gets the same bullets in
    the same order, so the PDF and the website cannot drift apart.
    """
    variant_path = VARIANTS / f"{variant_name}.yaml"
    if not variant_path.exists():
        available = ", ".join(sorted(p.stem for p in VARIANTS.glob("*.yaml")))
        raise SystemExit(f"unknown variant {variant_name!r}. Available: {available}")

    variant = load_yaml(variant_path)
    variant.setdefault("name", variant_name)

    profile = load_yaml(CONTENT / "profile.yaml")
    experience = load_experience()
    projects = load_yaml(CONTENT / "projects.yaml")
    skills = load_yaml(CONTENT / "skills.yaml")
    education = load_yaml(CONTENT / "education.yaml")

    # A variant may override the summary via profile.summary_variants.<name>.
    overrides = profile.get("summary_variants") or {}
    profile["summary"] = overrides.get(variant_name, profile["summary"])

    apply_variant(experience, projects, variant)

    return {
        "profile": profile,
        "experience": experience,
        "projects": projects,
        "skills": skills,
        "education": education,
        "variant": variant,
    }


def render(variant_name: str, out_dir: Path) -> Path:
    context = build_context(variant_name)

    out_dir.mkdir(parents=True, exist_ok=True)
    # The class file has to sit beside the .tex so the build dir is self-contained.
    shutil.copy2(TEMPLATES / "resume.cls", out_dir / "resume.cls")

    template = build_env().get_template("resume.tex.j2")
    tex = template.render(**context)

    target = out_dir / f"resume-{variant_name}.tex"
    target.write_text(tex, encoding="utf-8")
    return target


# --------------------------------------------------------------------------
# Cover letters
# --------------------------------------------------------------------------


def build_letter_context(letter_path: Path) -> dict:
    """Load one letter alongside the profile it shares a header with.

    The letter YAML carries only what is specific to an application -- company,
    role, prose. Name, location, email, and links come from profile.yaml, so a
    letter's header cannot drift from the resume's.
    """
    if not letter_path.exists():
        raise SystemExit(f"no such letter: {letter_path}")

    letter = load_yaml(letter_path)
    for field in ("company", "role", "paragraphs"):
        if field not in letter:
            raise SystemExit(f"{letter_path}: missing required field '{field}'")
    if not letter["paragraphs"]:
        raise SystemExit(f"{letter_path}: 'paragraphs' is empty")

    letter.setdefault("name", letter_path.stem)
    letter.setdefault("salutation", DEFAULT_SALUTATION)
    letter.setdefault("closing", DEFAULT_CLOSING)
    letter.setdefault("date", None)

    return {"profile": load_yaml(CONTENT / "profile.yaml"), "letter": letter}


def render_letter(letter_path: Path, out_dir: Path) -> Path:
    context = build_letter_context(letter_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    # Same reason as render(): the class has to sit beside the .tex.
    shutil.copy2(TEMPLATES / "resume.cls", out_dir / "resume.cls")

    template = build_env().get_template("letter.tex.j2")
    tex = template.render(**context)

    target = out_dir / f"letter-{letter_path.stem}.tex"
    target.write_text(tex, encoding="utf-8")
    return target


# --------------------------------------------------------------------------
# JSON output
# --------------------------------------------------------------------------


def render_json(variant_name: str, target: Path) -> Path:
    """Write the same filtered content as JSON, for consumers that are not LaTeX.

    jacksonwearn.com renders its resume page from this, so the site shows real
    selectable HTML rather than an embedded PDF viewer, without reimplementing
    the variant rules or reading the PDF back.

    Nothing here is LaTeX-escaped: escaping belongs to the LaTeX finalizer, and
    a JSON consumer wants the original text. Dates arrive already formatted as
    `dates` on each entry, and the raw start/end are kept so a consumer can
    sort or reformat without parsing "Jun 2024 – Jul 2026".
    """
    context = build_context(variant_name)

    # _sort is an internal tuple used only to order entries here.
    experience = [
        {k: v for k, v in entry.items() if k != "_sort"}
        for entry in context["experience"]
    ]

    # summary is already resolved for this variant, so shipping every other
    # variant's summary alongside it is noise a consumer could pick the wrong
    # one from.
    profile = {k: v for k, v in context["profile"].items() if k != "summary_variants"}

    payload = {
        "variant": context["variant"].get("name", variant_name),
        "profile": profile,
        "experience": experience,
        "projects": context["projects"],
        "skills": context["skills"],
        "education": context["education"],
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys=False keeps authored order; ensure_ascii=False keeps the em
    # dashes and middots readable rather than escaping them.
    text = json.dumps(
        payload, indent=2, ensure_ascii=False, sort_keys=False, default=str
    )
    target.write_text(text + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default="default")
    parser.add_argument("--out", type=Path, default=ROOT / "build")
    # Neither of these renders the resume template, so asking for both is a
    # request for two different documents in one run.
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--json",
        type=Path,
        metavar="PATH",
        help="write the filtered content as JSON to PATH instead of rendering LaTeX",
    )
    # A path rather than a slug: letters live outside the repo tree by design,
    # so the renderer shouldn't assume where. See README.
    mode.add_argument(
        "--letter",
        type=Path,
        metavar="PATH",
        help="render the cover letter at PATH instead of the resume",
    )
    args = parser.parse_args()

    if args.json:
        target = render_json(args.variant, args.json)
    elif args.letter:
        target = render_letter(args.letter, args.out)
    else:
        target = render(args.variant, args.out)

    # --json takes an arbitrary path, which may sit outside the repo.
    resolved = target.resolve()
    shown = resolved.relative_to(ROOT) if resolved.is_relative_to(ROOT) else resolved
    print(f"rendered {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
