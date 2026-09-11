# B 题 LaTeX Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular, B-problem-specific Chinese mathematical-modeling paper template that compiles with XeLaTeX.

**Architecture:** `latex/main.tex` is the only entry point and loads reusable format definitions from `latex/config/`. Every level-one paper section owns a directory under `latex/chapters/`; the four problem directories further split analysis, model/strategy, algorithm, and results into focused files. Assets are isolated in `figures/`, `tables/`, `code/`, and bibliography data in `references/`.

**Tech Stack:** XeLaTeX, `ctexart`, `amsmath`, `booktabs`, `longtable`, a dependency-free custom pseudocode environment, `listings`, `hyperref`, `biblatex`/Biber, and a Python structure checker with a PowerShell entry point.

---

### Task 1: Create the compile contract and shared format

**Files:**
- Create: `latex/main.tex`
- Create: `latex/config/packages.tex`
- Create: `latex/config/layout.tex`
- Create: `latex/config/commands.tex`
- Create: `latex/tests/check_structure.ps1`

- [x] **Step 1: Write the failing structure check**

Create a PowerShell check that verifies `main.tex`, the three configuration files, every required chapter directory, and both formal-test tables. It must exit with code 1 and list missing paths when the project has not yet been created.

- [x] **Step 2: Run the check to verify it fails**

Run: `powershell -ExecutionPolicy Bypass -File latex/tests/check_structure.ps1`

Expected: `FAIL` with one or more missing template paths.

- [x] **Step 3: Implement the entry point and shared configuration**

Use `ctexart` on A4 paper. Define `\placeholder{}`, `\safeimage{}`, `\vect{}`, `\diff`, theorem environments, a contest metadata block, consistent headings, page geometry, captions, equation numbering, hyperlinks, algorithms, code listings, and an optional table-of-contents switch. `main.tex` must load every chapter through `\input` and print the bibliography.

- [x] **Step 4: Run the structure check**

Run: `powershell -ExecutionPolicy Bypass -File latex/tests/check_structure.ps1`

Expected: configuration checks pass; chapter checks may remain failing until Tasks 2–3.

- [x] **Step 5: Commit the shared framework**

Run: `git add latex/main.tex latex/config latex/tests && git commit -m "feat: add LaTeX template framework"`

### Task 2: Add common paper chapters

**Files:**
- Create: `latex/chapters/摘要/main.tex`
- Create: `latex/chapters/问题重述/main.tex`
- Create: `latex/chapters/问题分析/main.tex`
- Create: `latex/chapters/模型假设/main.tex`
- Create: `latex/chapters/符号说明/main.tex`
- Create: `latex/chapters/模型评价与推广/main.tex`
- Create: `latex/chapters/参考文献/main.tex`
- Create: `latex/chapters/附录/main.tex`
- Create: `latex/references/references.bib`
- Create: `latex/code/example.py`

- [x] **Step 1: Extend the structure check**

Require all common chapter files, the bibliography database, and example code. Require the abstract to contain keywords and the appendix to mention the three unmodified official-test logs.

- [x] **Step 2: Run the check to verify the new assertions fail**

Run: `powershell -ExecutionPolicy Bypass -File latex/tests/check_structure.ps1`

Expected: `FAIL` naming the common chapter files.

- [x] **Step 3: Write the common chapters**

Add B-problem-specific prompts for the abstract, restatement of all four questions, per-question analysis, assumptions, a core-symbol longtable, strengths/weaknesses/promotion, bibliography invocation, appendix code listing, and supporting-material checklist. Use `\placeholder{}` only for content that genuinely depends on the team's results.

- [x] **Step 4: Run the structure check**

Run: `powershell -ExecutionPolicy Bypass -File latex/tests/check_structure.ps1`

Expected: all common-chapter assertions pass.

- [x] **Step 5: Commit common chapters**

Run: `git add latex/chapters latex/references latex/code latex/tests && git commit -m "feat: add common modeling paper chapters"`

### Task 3: Add the four problem modules

**Files:**
- Create: `latex/chapters/问题一/{main,问题分析,模型建立,算法设计,结果分析}.tex`
- Create: `latex/chapters/问题二/{main,问题分析,候选区域,优化模型,结果分析}.tex`
- Create: `latex/chapters/问题三/{main,问题分析,搜索策略,算法设计,结果分析}.tex`
- Create: `latex/chapters/问题四/{main,问题分析,检测策略,算法设计,结果分析}.tex`
- Create: `latex/tables/problem3_formal_tests.tex`
- Create: `latex/tables/problem4_formal_tests.tex`

- [x] **Step 1: Extend the structure and content check**

Require each module file, require problem 1 to mention the bearing error and polygon diameter, problem 2 to define a candidate region and objective, and problems 3–4 to include the required clearance ratio, average time, practice table, and formal-test table.

- [x] **Step 2: Run the check to verify it fails**

Run: `powershell -ExecutionPolicy Bypass -File latex/tests/check_structure.ps1`

Expected: `FAIL` naming problem module files.

- [x] **Step 3: Write problem 1 and problem 2 modules**

For problem 1, provide angular wedge constraints, intersection with the target disk, convex polygon diameter, coverage-circle criterion, pseudocode, and result tables. For problem 2, provide geometric constraints, a candidate-region set, crossing-angle and travel-cost terms, a normalized scoring model, selection pseudocode, and sensitivity/result tables.

- [x] **Step 4: Write problem 3 and problem 4 modules**

For problem 3, provide a state-machine strategy, 20-channel scan logic, time-cost equations, termination conditions, pseudocode, practice statistics, and the exact four-column formal-test table. For problem 4, extend the state with directional visibility, multi-direction revisits and coverage compensation, then provide the same statistics and formal-test reporting structure.

- [x] **Step 5: Run the structure check**

Run: `powershell -ExecutionPolicy Bypass -File latex/tests/check_structure.ps1`

Expected: `PASS: LaTeX template structure and required content are complete.`

- [x] **Step 6: Commit problem modules**

Run: `git add latex/chapters latex/tables latex/tests && git commit -m "feat: add B problem modeling modules"`

### Task 4: Document, compile, and visually verify

**Files:**
- Create: `latex/README.md`
- Create: `latex/.gitignore`
- Modify: `latex/main.tex`
- Modify: any `.tex` file implicated by compilation diagnostics

- [x] **Step 1: Write usage documentation**

Document `xelatex -> biber -> xelatex -> xelatex`, the `latexmk -xelatex` alternative, directory responsibilities, image replacement, placeholder cleanup, and the fallback for missing Biber. Ignore only generated LaTeX build products.

- [x] **Step 2: Compile the template**

Run from `latex/`: `xelatex -interaction=nonstopmode -halt-on-error main.tex; biber main; xelatex -interaction=nonstopmode -halt-on-error main.tex; xelatex -interaction=nonstopmode -halt-on-error main.tex`

Expected: all commands exit 0 and create `latex/main.pdf`.

- [x] **Step 3: Check logs and PDF metadata**

Run: `rg -n "LaTeX Error|Undefined control sequence|Citation.*undefined|Reference.*undefined" main.log` and `pdfinfo main.pdf`.

Expected: no error/undefined-reference matches; PDF has at least one page and A4 dimensions.

- [x] **Step 4: Render representative pages for inspection**

Run: `pdftoppm -f 1 -l 4 -png -r 120 main.pdf build-preview/page`

Expected: four PNG pages with readable Chinese text, no clipped tables, and no overlapping headings.

- [x] **Step 5: Run all checks and commit**

Run: `powershell -ExecutionPolicy Bypass -File tests/check_structure.ps1`

Expected: `PASS: LaTeX template structure and required content are complete.`

Run: `git add latex && git commit -m "docs: add template usage and verified build"`
