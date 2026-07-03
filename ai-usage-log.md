# AI Usage Log

Three tools ended up in this, each for a different reason - not because I
was trying to check a "used multiple models" box, but because they're what
I actually reach for at each stage of a task like this:

- **ChatGPT-5** - early-stage thinking: reading the ticket, figuring out
  scope, deciding on structure. I have heavier daily usage on it and it's
  fast, so it's where I do the "think out loud across several follow-up
  questions" stage without worrying about quota.
- **Claude (Sonnet 5)** - anything that had to turn into actual files: the
  bulk of the code, and Task 2's test-case generation. In my experience it
  holds a multi-file spec together better and follows a detailed prompt
  more literally, which mattered once I had a structure I wanted built
  exactly, not roughly.
- **Llama 3.1 8B, local via Ollama** - the model actually wired into
  `llm_integration/failure_explainer.py`. Reasoning below.

**Note on fidelity:** I didn't save full transcripts for the design
conversations, so "what I asked for" below is an accurate summary, not a
quote. `prompts.md` is the one file with reconstructed-but-close prompt
text, since Task 2 specifically asks for that.

## Tool usage table

| # | Task | Tool | What I asked for | What it produced | What I changed / kept |
|---|------|------|-------------------|-------------------|------------------------|
| 1 | Reading the ticket / scoping | ChatGPT-5 | Gave it the assessment PDF directly and asked what a production-grade design for this would look like - modules, structure, what "working" means per task | A breakdown of the three tasks, a proposed folder structure, and which files were the core deliverables vs. supporting ones | Kept the folder structure close to as proposed - it matched how I'd split it myself, just faster to get to |
| 2 | Feature choice (Task 3) | ChatGPT-5 | Asked it to lay out what Option A (Failure Explainer) vs Option B (Flaky Classifier) would each actually involve, against the ticket's specific pain point | A comparison plus its own recommendation | Decided on Option A myself off that comparison - reasoning is in README's "Why Option A" section, in my own words |
| 3 | Coding-agent prompt | ChatGPT-5 | Once I had the structure and feature decided, asked it to write one detailed prompt - functional + non-functional requirements, the full file tree, and what each file was responsible for - that I could hand to a different model to generate the code | A long structured build prompt covering all of the above | Used it close to verbatim as the opening message to Claude - see #4 |
| 4 | Code generation (Task 1 scaffold, Task 3 skeleton) | Claude Sonnet 5 | Pasted in the ChatGPT-written build prompt as-is | `pages/`, `tests/login`, `tests/dashboard`, `tests/api`, `conftest.py`, the `llm_integration/failure_explainer.py` scaffold, `generated_test_cases/*.json` | Ran the suite myself and fixed what didn't actually work first try (see Debugging note below). Reviewed every file rather than committing blind |
| 5 | Prompt engineering (Task 2) | Claude Sonnet 5 | Draft-then-critique prompts for Login/Dashboard/API test case generation | Both attempt-1 and attempt-2 prompts, and the generated JSON | Documented in `prompts.md`; trimmed a few overlapping cases per module |
| 6 | Follow-up features | Claude Sonnet 5 | Two small additions once the base suite ran: (1) more granular, individually-named test cases per module instead of a few broad ones, and (2) a `tests/demo_failures/` package whose entire job is to fail on purpose, so the failure explainer has real failures to explain instead of only ever seeing a healthy run | Expanded per-module test cases, plus `tests/demo_failures/test_demo_failures.py` | Kept as-is - the deliberately-broken tests are the ones actually showing up with real AI explanations in `reports/report.html` |
| 7 | Failure explanation (Task 3, live) | Llama 3.1 8B, local via Ollama | Wired directly into `conftest.py`'s `pytest_runtest_makereport` hook - sends the real failure context (traceback, response body / visible page text) and gets back root cause, category, and a suggested fix | Everything in `reports/report.html` and `reports/archive/` is genuine local model output, not written up after the fact | This is the real integration, not a mock - I didn't touch its output, since editing an "AI explained this" section by hand would defeat the point |
| 8 | Documentation | Claude Sonnet 5 | First drafts of README, this file, and JSON formatting | Initial drafts | Rewrote in first person to match what actually happened this session instead of generic boilerplate |

## Why a local model (Llama 3.1 8B) instead of the Anthropic API for Task 3

Roughly in the order these actually occurred to me:

- **No API key to buy or manage.** This is a take-home, not a production
  system - I didn't want whether the reviewer can see live output to
  depend on me having credit on a key, or on them setting up their own.
- **It fits on my laptop without drama.** Llama 3.1 8B loads and runs
  comfortably on my hardware. I'm not fighting for VRAM or waiting minutes
  per call.
- **The task doesn't need a frontier model.** Reading a traceback, an HTTP
  response body, or a page's visible text, and explaining what broke and
  why, is a narrower job than open-ended coding or long-context reasoning.
  8B is enough for "explain this specific, bounded failure." I wouldn't
  trust it to have written the test suite itself - that's not what it's
  doing here.
- **A side benefit I didn't plan for:** it also means zero network
  dependency. The assessment is explicit that "the call must be real, not
  mocked" - a local call to Ollama is as real as it gets, and it means
  anyone running this repo gets live output the moment Ollama's running
  locally, no key setup required on their end either.

Setup is in the README (`ollama pull llama3.1:8b`, then the model is
called over `localhost:11434` from `failure_explainer.py`).

## Debugging note (not AI-assisted, logging it anyway)

First local run failed immediately - Playwright couldn't find a browser
executable. I'd installed the `playwright` pip package but never run
`playwright install chromium` to actually pull the browser binaries down.
One-line fix, not a design decision, but I'm logging it because part of
"how I actually work" is: I ran the generated code myself, hit a real
error, and fixed it, instead of assuming everything a model produces runs
correctly on the first try.