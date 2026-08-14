% ===========================================================================
% resume.cls -- single-column, ATS-safe class for this repo's documents.
%
% Serves both resume.tex.j2 and letter.tex.j2. A cover letter shares the
% resume's fonts, margins, and header macro so the two read as one set of
% documents; the only letter-specific piece is the letterbody environment.
%
% Style knobs live in the "Layout" block below. Everything under "Macros" is
% plumbing the template calls into; you shouldn't need to touch it.
%
% Font: the default is Latin Modern (XeTeX's built-in), which needs no
% download and renders identically everywhere. To use something else, add one
% of these right after \LoadClass:
%     \usepackage{charter}     % warmer serif
%     \usepackage{newtxtext}   % Times-like
% ===========================================================================
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{resume}[2026/08/04 Resume]

\LoadClass[10pt,letterpaper]{article}

\RequirePackage[margin=0.5in,bottom=0.45in]{geometry}
\RequirePackage{enumitem}
\RequirePackage{titlesec}
\RequirePackage{tabularx}
\RequirePackage{etoolbox}
\RequirePackage{lastpage}
\RequirePackage{needspace}
\RequirePackage[hidelinks]{hyperref}

\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\raggedright
\raggedbottom
% Discourage a section heading stranded at the foot of a page.
\widowpenalty=10000
\clubpenalty=10000

% ---------------------------------------------------------------------------
% Layout
% ---------------------------------------------------------------------------
% Spacing is deliberately loose. A resume is skimmed, not read, so whitespace
% between blocks does more for legibility than fitting another bullet in.
% Content is trimmed via bullet priority to pay for it -- see README.
\newcommand{\sectionrulewidth}{0.6pt}
\newcommand{\headerskip}{1.2em}     % header block -> summary
\newcommand{\summaryskip}{0.4em}    % summary -> first section
\newcommand{\entryskip}{1.4em}      % space between jobs
\newcommand{\entryheadskip}{0.3em}  % entry header -> its bullets
\newcommand{\bulletindent}{1.1em}
\newcommand{\bulletsep}{0.3em}      % space between bullets
\newcommand{\lettersep}{0.8em}      % space between letter paragraphs
\newcommand{\lettersignskip}{2.2em} % closing -> signature name

% A touch more leading than the 10pt default; the single biggest readability
% win in a dense document.
\linespread{1.06}\selectfont
% An entry header won't start unless this much room is left on the page, so a
% job title never strands itself at the foot of a page above its bullets.
\newcommand{\entrykeep}{4\baselineskip}

% Uppercased rather than \scshape: Latin Modern has no bold small-caps in TU.
\titleformat{\section}
  {\normalsize\bfseries}{}{0em}{\MakeUppercase}
  [\vspace{-0.55em}\rule{\textwidth}{\sectionrulewidth}]
\titlespacing*{\section}{0pt}{1.5em}{0.7em}

% ---------------------------------------------------------------------------
% Macros
% ---------------------------------------------------------------------------

% \resumeheader{name}{contact lines}
% Name left, contacts stacked right. Two minipages rather than a tabular so
% text extraction still yields name-then-contacts in reading order.
\newcommand{\resumeheader}[2]{%
  \begin{minipage}[t]{0.42\textwidth}%
    \vspace{0pt}\raggedright{\LARGE\bfseries #1}%
  \end{minipage}%
  \hfill
  \begin{minipage}[t]{0.56\textwidth}%
    \vspace{0pt}\raggedleft\small #2%
  \end{minipage}%
  \par\vspace{\headerskip}%
}

% \resumeentry{title}{organization}{subtitle}{dates and location}
% Line 1: bold title left, bold org right. Line 2: italic subtitle left,
% dates right. An empty subtitle collapses rather than leaving a blank line.
\newcommand{\resumeentry}[4]{%
  \vspace{\entryskip}%
  \Needspace*{\entrykeep}%
  \nobreak
  {\bfseries #1}\hfill{\bfseries #2}\par
  \nobreak
  \notblank{#3}{{\small\itshape #3}\hfill{\small #4}\par}%
             {\hfill{\small #4}\par}%
  \nobreak
  \vspace{\entryheadskip}%
}

% \projectentry{name}{meta}
\newcommand{\projectentry}[2]{%
  \vspace{\entryskip}%
  \Needspace*{\entrykeep}%
  \nobreak
  {\bfseries #1}\hfill{\small #2}\par
  \nobreak
  \vspace{\entryheadskip}%
}

\newlist{bullets}{itemize}{1}
\setlist[bullets]{
  leftmargin=\bulletindent,
  labelsep=0.45em,
  itemsep=\bulletsep,
  parsep=0pt,
  topsep=0pt,
  partopsep=0pt,
  label=\textbullet,
}

% Skills: a hanging-indent description list. Deliberately not a tabular --
% tabularx cannot be wrapped in a custom environment, and a list extracts more
% cleanly for text parsers anyway.
\newlist{skills}{description}{1}
\setlist[skills]{
  style=multiline,
  leftmargin=8.8em,
  labelwidth=8.5em,
  labelsep=0.3em,
  font=\bfseries\small,
  itemsep=0.35em,
  topsep=0.2em,
  parsep=0pt,
  partopsep=0pt,
}

% A single free-standing line (education, etc.)
\newcommand{\plainline}[2]{{\bfseries #1}\hfill{\small #2}\par}

% Letter prose. The class sets \parskip=0pt, which is right for a resume --
% its blocks are separated by explicit skips -- and wrong for running text,
% where consecutive paragraphs would otherwise run together with no indent to
% tell them apart. Scoped to the environment so the resume is unaffected.
\newenvironment{letterbody}{\par\setlength{\parskip}{\lettersep}}{\par}
