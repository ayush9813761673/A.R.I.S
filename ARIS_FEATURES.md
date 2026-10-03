# A.R.I.S. features and tools

ARIS runs on Windows and uses Ollama for local AI by default. The current local model is `qwen3.5:2b`. Chat, images, task data, settings, and memory stay on this computer unless you deliberately open a browser or enable a plugin that accesses another service. ARIS does not download models automatically. A paid OpenAI-compatible API is disabled unless explicitly opted into through environment settings.

## Implemented features

- **Local AI chat and model selection:** `/models` lists installed Ollama models, their capabilities, file sizes, and a rough RAM estimate. `/model NAME` switches to an installed model without downloading it. Vision analysis requires a model that reports vision capability.
- **Desktop window:** launch `Start_ARIS_Desktop.bat` or run `python A.R.I.S.py --gui`. It includes chat, local model selection, task and folder controls, voice, and image/screen actions.
- **Health and capabilities:** `/health` checks Ollama, the selected model, plugin loading, and Windows prerequisites; the desktop runs a non-blocking startup check. `/capabilities` and the desktop Capabilities page list available tools and data-sharing behavior.
- **Windows tray and hotkey:** closing the desktop window minimizes it to the tray. Double-click the tray icon or press `Ctrl+Alt+Space` to reopen it. Choose Exit from the tray menu to stop ARIS.
- **Voice:** use `/voice` and `/text` in terminal mode, or the Voice button in the desktop window. It uses Windows speech components and a microphone when available.
- **Memory and conversation:** saves local memory in `aris_memory.json` and recent conversation in `aris_chat.json`.
- **Scoped file tools:** list, read, and search supported text files in PVA and folders you add. ARIS can rename or move one file inside approved folders after showing the exact source/destination and asking for `YES`; it never overwrites an existing destination. For multi-file organization, ARIS shows a read-only plan for up to 20 files and asks you to approve the plan before any change; then it asks separately before each move. `/folder add` opens a picker; `/folder add PATH` adds a named path; `/folders` lists approved folders; `/folder remove NUMBER` revokes access. The desktop Folders button also opens a picker.
- **Local previews:** `/preview PATH` opens a local image, PDF, or DOCX in its Windows default viewer after `YES`. The desktop Preview file button opens a picker. Files must be inside PVA or an added folder; ARIS does not upload them.
- **Local document reading:** `/document FILE.docx` extracts Word text with Python's standard library. `/document FILE.pdf` uses the free `pypdf` dependency from `requirements.txt` and Windows' installed OCR language pack on scanned/sparse pages. Extraction is read-only, capped at 20 MB, the first 40 PDF pages, and 20,000 returned characters; it does not use web services and refuses encrypted PDFs. OCR needs a supported Windows language installed.
- **DOCX draft edits:** when you explicitly ask for exact replacements, ARIS can change a phrase that occurs exactly once within one Word text run. It previews each before/after, asks `YES`, and saves a separate `_aris_draft.docx` copy without changing the source. Existing draft names get a numbered suffix. Text split across formatting runs or repeated phrases must be clarified/edited in Word.
- **File and command approval:** ARIS asks before it writes a file or executes a PowerShell command. The terminal tool requires the exact word `RUN` after showing the command.
- **Calculator, time, browser search, and app launcher:** `/calc EXPR`, `/time`, `/web QUERY` (opens Google in the browser), and `/openapp notepad|calculator|explorer|browser`.
- **Research and source comparison:** `/lookup QUERY` returns up to eight DuckDuckGo links/snippets with heuristic source labels. `/research QUERY` retrieves up to eight results, reads up to three distinct public sources in parallel, ranks likely official/academic sources using transparent domain/title heuristics, and asks the local Ollama model to compare supported claims, agreement/disagreement, missing dates, and access limits. ARIS appends stable `[S1]` citations with URLs and retrieval time. Search queries go to DuckDuckGo; source pages are fetched without login cookies. Page text is untrusted evidence, never instructions. If local Ollama is unavailable, ARIS still lists the sources and does not send source text to a remote model.
- **Public webpage/PDF reading:** `/readweb URL` extracts static HTML/plain text or bounded text from public PDFs (maximum 4 MB, first 12 pages, 3,200 characters). It reports when pages appear to require sign-in, JavaScript, or are blocked by anti-bot controls; ARIS does not bypass those limits. Remote scanned PDFs are not OCRed. Local `/document FILE.pdf` continues to use Windows OCR for scanned pages.
- **Local research notebook:** `/research save` stores the latest query, summary, citation links, and dates in `aris_research.json` only after `YES`. `/research list` and `/research view ID` read saved entries; `/research note ID | TEXT` adds a user-provided note after `YES`. The notebook is local to PVA and capped at 50 entries, 12 notes per entry.
- **Lookup results in the desktop:** source URLs are clickable, right-click offers open/copy, and “Copy last lookup” copies the most recent source-rich ARIS answer. The toolbar shows whether web lookups are enabled and can turn them off.
- **Weather:** `/weather CITY` returns current conditions and a 3-day forecast via [Open-Meteo geocoding](https://open-meteo.com/en/docs/geocoding-api) and [forecast](https://open-meteo.com/en/docs) endpoints. The location you enter is sent to its services.
- **Computer use:** ARIS can list open windows, inspect accessible control names in the active or named app, focus a window, fill a named non-password field, activate a named control, and send a supported key/shortcut. Each read or action asks you to type `ACT`. For Chrome, Edge, Firefox, Brave, Vivaldi, or Opera, it can read/search accessible page text, list browser windows for selection, and preview one uniquely named link's destination before opening it. Opening asks for a second `ACT` and shows the sanitized destination; hidden query parameters are disclosed, and URLs containing credentials are blocked. Browser reads omit form values/passwords; the local model receives the accessible page text. Form fills require a separate approval, and ARIS does not submit forms. The desktop Stop task button prevents ARIS from starting another step and lets it finish any required verification first. `CTRL+Z` can attempt undo only when you explicitly ask; whether it works depends on the app, and ARIS checks afterward. It uses Windows UI Automation and stays local; it does not read field values or password contents. It works best with apps that expose accessible controls. Destructive or externally submitting actions are blocked by control name, and unique visible controls are required.
- **Visual computer-use assist:** `/computer TASK` sends an initial full-desktop screenshot to the selected local vision model; `/computer-window TITLE | TASK` captures one uniquely matched app window. Windows OCR reads local text labels and normalized positions. After each approved state-changing action, ARIS checks accessible controls, then asks `YES` before refreshing that action's app window and sending the temporary image and OCR labels only to local Ollama. If accessibility labels do not expose a target, each fresh named-window screenshot can support one visual left click after ARIS shows the target and normalized position and asks for `ACT`. A declined or failed refresh invalidates old coordinates. Visual clicks refuse targets described with sensitive action names. Screenshots are temporary and not saved. `/screen` remains available for screen description only.
- **Persistent tasks:** `/task add TITLE | YYYY-MM-DD HH:MM | daily|weekly|monthly`, `/task list`, `/task done ID`, or `/tasks`. Repeat is optional; due times are local. `/reminderinterval SECONDS` sets the check interval from 5 to 3600 seconds. Reminders run only while ARIS is open.
- **Opt-in image understanding:** `/see [IMAGE]` opens a picker when no path is given. The desktop has an Analyze image button. ARIS asks you to type `YES` before sending the image to the selected local Ollama model. The image itself is not saved in chat history.
- **Opt-in screen understanding:** `/screen` or the desktop Analyze screen button asks you to type `YES`, then captures all monitors and sends the screenshot only to local Ollama. The temporary screenshot is deleted afterward.
- **Calendar exports:** `/calendar PATH.ics` lists upcoming events from an iCalendar export inside PVA or an added folder. UTC and recognized `TZID` event times are converted to the computer's local time; recurring `RRULE` entries are not expanded by this reader.
- **Email exports:** `/email search FOLDER | WORDS` searches local `.eml` exports under an approved folder. It does not connect to an email account.
- **Optional plugins:** trusted Python plugins live in `aris_plugins`. `/plugins` lists them; `/plugin enable NAME` asks for the exact word `ENABLE`; `/plugin disable NAME` disables one. Plugins can run arbitrary Python code with ARIS's permissions, so enable only code you trust.
- **Outlook connector:** the included, optional `aris_plugins/outlook.py` reads upcoming events and searches the inbox of a configured **classic Outlook for Windows** profile. Enable with `/plugin enable outlook`. Each calendar or inbox access asks for `YES`. It only returns event details or matching sender/subject/date; it never sends mail or changes calendar/email items. The newer Outlook app may not provide the COM interface this connector uses.

## Command reference

```text
/help
/health
/capabilities
/models
/model qwen3.5:2b
/folders
/folder add
/folder remove 1
/calc (24 + 8) * 3
/task add Finish homework | 2026-09-30 18:00 | weekly
/task list
/task done 1
/reminderinterval 15
/see
/screen
/preview AYUSH.jpeg
/computer Find the open Notepad window and fill the editor with a draft greeting
/computer-window Notepad | Click the visible editor area
/lookup current school calendar dates for Kathmandu
/research compare the latest official school calendar dates for Kathmandu
/research save
/research list
/research view 1
/research note 1 | Verify the school notice before relying on the date.
/readweb https://example.com/
/weather Kathmandu
/document notes.docx
/document syllabus.pdf
/calendar calendar.ics
/email search exported-mail | school
/plugins
/plugin enable outlook
/plugin disable outlook
/plugin disable computer_use
/time
/web local AI assistant ideas
/openapp calculator
/ls
/search phrase
/read filename.txt
/remember my preference
/recall preference
/voice
/text
/exit
```

The desktop window also exposes the model selector, folder picker, task list, reminder interval, local file preview, image/screen analysis, and voice mode through buttons. For computer use, ask ARIS in chat to inspect or operate an app, then type `ACT` in the approval dialog for each screen read or action.

## Service and hardware notes

- ARIS and local Ollama do not charge per message. Model disk size and actual RAM use depend on the model, context length, and other running apps; `/models` gives an estimate, not a guarantee.
- ARIS can use local `.ics` and `.eml` exports without signing into an online service.
- Personal web and weather lookups use external services when requested. Search results and page text are untrusted; weather locations are sent to Open-Meteo.
- Computer-use support depends on each Windows app's accessibility provider. Some canvas-heavy apps, remote desktops, games, or custom interfaces may expose few controls; screenshot/OCR-guided interaction and broader app-specific integrations are possible later upgrades.
- Scanned-PDF OCR uses Windows' local OCR language pack and Windows PDF renderer. If OCR is unavailable, ARIS still returns selectable PDF text and reports the issue.
- Outlook access requires classic Outlook already installed and configured on this PC. Other online providers can be added as plugins, but may require their own accounts, permission grants, and API limits.
