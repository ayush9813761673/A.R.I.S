# ARIS capability roadmap

## Goal

Make ARIS a useful, local-first assistant that can research a question, work across the user's Windows apps, and show what it verified. Keep paid services optional; use local Ollama and free public services where they fit.

## Available now

- **Computer use:** Windows UI Automation can list windows, inspect accessible control labels, focus an app, fill named non-password fields, activate a named control, and send a small set of keys. Each read or action asks for `ACT`.
- **Visual task start:** `/computer TASK` or `/computer-window TITLE | TASK` sends an initial screenshot to the local vision model after `YES`; approved actions can be followed by separately approved screenshot refreshes.
- **Web research:** `/lookup QUERY` returns search result links/snippets; the model can call `fetch_webpage` to read a public page. Use citations with the returned source URLs.
- **Weather:** `/weather CITY` returns current conditions and a short forecast without an API key.
- **Browser help:** supported browser page text/link reading, text search, and approved unique-link opening; form submission remains a separate user action.
- **Local assistant tools:** scoped file search/read, approved file rename/move, DOCX/PDF text extraction, tasks, reminders, calculator, memory, local calendar/email exports, voice, and allowlisted app launch.

## Build order

### 1. Make current use dependable

- **Built:** a startup/`/health` check reports Ollama/model/plugin state and local feature prerequisites, with recovery hints. It does not open the microphone or capture the screen at launch.
- **Built:** `/capabilities` and the desktop Capabilities page show available tools and privacy behavior.
- **Built:** lookup URLs are clickable; the desktop can copy the last source-rich answer; results identify DuckDuckGo/Open-Meteo.
- **Built:** the desktop shows whether online lookup is active and offers a direct off switch; `/plugin disable web_lookup` also disables it.

### 2. Complete the computer-use loop

- **Built:** ARIS is prompted to show a short plan, desktop calls are kept sequential, and after each click/field entry/key ARIS asks separately to inspect the target window. Field filling compares the entered value in memory without returning/saving it. Other app effects are only reported as verified when the next control inspection supports that claim.
- **Built:** `/computer-window TITLE | TASK` captures only one uniquely matched app window, restores the previously active window even when capture fails, and sends the temporary image only to local Ollama.
- **Built:** when accessible controls do not expose a requested target, the model can propose one visual left-click using normalized coordinates. ARIS shows the target and position, requires `ACT`, consumes that screenshot context after one attempt, and checks the app separately afterward. Sensitive target descriptions are blocked.
- **Built:** the desktop Stop task button prevents ARIS from starting another step and lets a required post-action check finish. An explicitly requested `CTRL+Z` undo shortcut is available where the app supports it and is followed by a separate check.
- **Built:** `/computer` and `/computer-window` tasks can refresh the affected app window after every approved state-changing action. Each refresh needs a separate `YES`, runs Windows OCR locally, and gives the local vision model the new image plus recognized text labels and normalized coordinates. A declined or failed refresh invalidates old coordinates; a fresh named-window view allows another separately approved visual click.
- **Built:** bounded text entry for named ordinary fields, a password-field block, and an approval preview.
- **Built:** Stop prevents the next action while required verification finishes. An explicitly requested `CTRL+Z` undo is followed by a separate check; ARIS reports when it cannot verify or reverse an action.

### 3. Add app-specific skills

- **Built (browser skill):** on Chrome, Edge, Firefox, Brave, Vivaldi, or Opera, ARIS can read the focused tab's accessible text and link labels, search that text, preview a visible link's sanitized destination, and open one unique link after a second `ACT`. It discloses hidden query parameters and blocks URLs containing credentials. A dedicated browser-window list helps select among several windows. Page reads omit URL query/fragment/credentials and form values/passwords. Existing approved field filling can draft ordinary forms; ARIS does not submit them.
- Improve browser support for pages whose content is not exposed through accessibility.
- **Built (File Explorer skill):** file rename and move tools work only inside PVA/added folders, show the exact destination and file size, require `YES`, and refuse to overwrite. A move planner shows a read-only plan for up to 20 files and gets approval before changes; ARIS then requests approval for each move separately. Existing list/read/search tools provide discovery.
- **Built:** `/preview` and the desktop Preview file button open scoped local images, PDFs, and DOCX files in their Windows default viewer after approval.
- **Built (document skill):** `/document` extracts DOCX locally with the standard library and PDF text with the free `pypdf` package. It uses Windows PDF rendering and local OCR for sparse/scanned pages. It refuses encrypted PDFs and limits input to 20 MB, PDF extraction to 40 pages, and returned text to 20,000 characters.
- **Built:** exact DOCX text-run replacements can be previewed and saved to a separate draft copy after `YES`; the original is left unchanged. Cross-run and ambiguous repeated-text edits still require manual review.
- **Office and calendar:** start with read-only actions; add account APIs only when the user chooses an integration.

### 4. Improve research and lookups

- **Built:** `/research QUERY` fetches up to three distinct public sources in parallel, heuristically ranks government/academic/documentation pages, supplies page text and dates when exposed, and asks local Ollama to compare evidence with `[S#]` citations. ARIS flags missing dates, conflicting claims, and pages it could not read.
- **Built:** `/readweb` handles public HTML/plain text and bounded text extraction from PDFs (4 MB, 12 pages, 3,200 characters). It identifies likely JavaScript, sign-in, paywall, and anti-bot barriers without trying to bypass them; remote scanned PDFs are reported as needing OCR rather than processed remotely.
- **Built:** `/research save|list|view|note` keeps an opt-in notebook in `aris_research.json`; saving a report or adding a note asks for `YES`. It keeps the latest 50 entries and 12 notes per entry.
- **Built:** DuckDuckGo remains the no-key search provider. Queries are disclosed as leaving the PC; no second provider or paid API was added.

### 5. Build reliable reusable workflows

- Add named recipes such as “research this topic,” “summarize this folder,” and “prepare a draft email.”
- Keep each recipe visible as a plan; ask before file edits or external actions and verify completed steps.
- Add per-skill permissions, an activity log, and a one-click pause/disable for computer use.

## Limits to address

- The current local model is small, so long plans and tool selection may be inconsistent. Compare already-installed models with `/models`; only add a larger model if the user chooses the disk/RAM cost.
- UI Automation depends on each app exposing accessible controls. Canvas apps, games, remote desktops, and some websites may need the future OCR/visual path.
- Public search and forecast services require internet and receive the query or location. Local file, memory, and computer-control data remain on the PC unless a feature explicitly sends it elsewhere.

## Priority after this update

Research improvements are in place. Next, improve browser support for inaccessible pages, then build reusable, reviewable workflows.
