# TestMu SDET-1 Submission

AI-native regression suite for Login, Dashboard, and REST API, plus a real
LLM integration that explains test failures in plain English.

## How this was actually built

Three AI tools, each doing a different part of the job - full breakdown in
`ai-usage-log.md`, short version here: ChatGPT-5 for the early design pass
(reading the ticket, proposing structure, picking Option A vs. B, writing
the build prompt), Claude Sonnet 5 for turning that into actual code and
for Task 2's test-case prompts, and a locally-run Llama 3.1 8B for the
live failure explainer wired into the tests themselves (see "Why a local
model" below).

## About the target application

The ticket describes TestMu's own web-based test management platform but
doesn't include a staging URL or credentials, so "Show us something
working" needed a real, live target to point Playwright and `requests` at
instead of talking to itself. I used two public, no-signup demo services
as stand-ins, chosen deliberately rather than picking the first thing that
came up:

- **Login + Dashboard:** [SauceDemo](https://www.saucedemo.com) - a
  purpose-built QA practice site with real (if simple) auth, a locked-out
  account, and a "problem_user" fixture that renders a visible bug on
  purpose. That last part matters: it's what let me write
  `test_problem_user_sees_broken_images`, a test whose entire job is to
  prove the rest of the dashboard assertions aren't so loose they'd pass
  against a broken page.
- **REST API:** [DummyJSON](https://dummyjson.com) - a free, no-signup
  fake REST API with a real `/auth/login` (returns an actual JWT) and
  simulated CRUD. I initially considered reqres.in, but a quick search
  before committing to it turned up that it now gates most endpoints
  behind a paid signup and its blog markets that signup flow specifically
  at AI coding agents - not a dependency I wanted this suite quietly
  picking up. DummyJSON has no such requirement.

Every test case that assumes a feature neither demo site has (forgot
password, a live brute-force counter, role-based permissions, a real
rate-limit threshold) is still written to spec in
`generated_test_cases/*.json` and, where relevant, checked into `tests/`
as `@pytest.mark.skip(reason=...)` with the reason spelled out - the way
I'd handle a ticket that covers a feature the staging environment hasn't
shipped yet, rather than quietly dropping it or faking a pass.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium     # required - the pip package alone doesn't
                                 # ship the browser binaries. If you skip
                                 # this you'll get an "executable doesn't
                                 # exist" error on the first UI test.
```

You'll also need [Ollama](https://ollama.com) running locally for the LLM
integration (Task 3) - see below.

## Running the suite

```bash
# Everything
pytest

# One module
pytest -m login
pytest -m dashboard
pytest -m api

# With an HTML report (recommended - this is where the AI failure
# analysis shows up per failed test)
pytest --html=reports/report.html --self-contained-html
```

Tests run against the live public demo sites, so results depend on those
sites being up. If a run fails and you're not sure whether that's TestMu's
tests or SauceDemo/DummyJSON being flaky, that's exactly the kind of
question the Task 3 integration is built to help answer faster.

## Running the LLM integration

The failure explainer (`llm_integration/failure_explainer.py`) makes a
real call to a locally-running LLM - it's wired into every test via the
`pytest_runtest_makereport` hook in `conftest.py`, not called separately.

1. Install [Ollama](https://ollama.com) and pull the model:
   ```bash
   ollama pull llama3.1:8b
   ```
2. Make sure Ollama is running (`ollama serve`, or it's already running as
   a background service depending on your install).
3. Run `pytest --html=reports/report.html --self-contained-html`.
4. Any failing test gets an "AI Failure Analysis" section in the HTML
   report, and every failure is also appended under `reports/`.

`tests/demo_failures/` exists specifically to exercise this: a few tests
in there are written to fail on purpose (a bad locator, a mismatched
schema assertion) so there's always at least one genuine, real failure to
generate a real explanation from, rather than the demo only working when
something happens to be broken upstream. `reports/report.html` and
`reports/archive/` contain actual output from real local runs, not
hand-written examples.

Without Ollama running, the suite still runs fine - failed tests just get
a placeholder note instead of a live explanation, rather than crashing the
run.

## Why a local model instead of the Anthropic API

Short version: no API key to manage or pay for, Llama 3.1 8B runs
comfortably on my laptop, and reading a stack trace / response body and
explaining what broke is a bounded-enough task that an 8B model handles
it fine - I wouldn't trust it to write the test suite itself, but that's
not what it's doing here. It also means the integration has zero network
dependency, which felt like the right tradeoff for something a reviewer
needs to be able to run themselves without setup friction. Full reasoning
in `ai-usage-log.md`.

## Why Option A (Failure Explainer) over Option B (Flaky Classifier)

The ticket's stated pain point is time spent "writing and fixing
regression tests" - that's triage time, spent right after a failure,
before you even know if it's your test or the app. A flaky-test
classifier is a genuinely good idea, but it needs a history of runs before
its real-bug/environment/flaky buckets mean anything; it pays off in week
three. A failure explainer pays off on the very first failed run, on
someone's laptop, with zero history required. Given the specific pain
point in the ticket, that's the one worth shipping first - the classifier
is in "what I'd build next" below.

## Project structure

```
generated_test_cases/    Task 2: LLM-generated test cases per module (JSON)
llm_integration/         Task 3: the real, locally-run LLM call
pages/                   Page Object Model classes (LoginPage, InventoryPage)
reports/                 HTML report + archive of past runs (real AI output lives here)
tests/login/              Login module tests
tests/dashboard/          Dashboard module tests
tests/api/                REST API module tests
tests/demo_failures/      Deliberately-failing tests, to prove the failure explainer works
ai-usage-log.md            Every AI tool used, what for, what it produced
conftest.py                 Fixtures + the failure-explainer pytest hook
prompts.md                   Task 2: raw prompts + iteration notes
pytest.ini                    Pytest config (markers, report settings)
README.md
requirements.txt
```

## Known limitations (being upfront about these rather than hiding them)

- **Public demo targets, not TestMu's real app.** Every design decision
  above follows from that constraint. Swapping in real staging URLs +
  credentials should be close to a drop-in replacement for `pages/` and
  the API base URL in `tests/api/test_api.py`, since both are already
  isolated from the test logic itself.
- **DummyJSON's writes don't persist.** `TestProductCRUD` verifies the
  response contract (correct fields, correct status code) but can't verify
  a write actually stuck, since the backend is simulated. Flagged per-case
  in `generated_test_cases/api_test_cases.json`.
- **No enforced rate limit on the demo API**, so `TestRateLimiting` checks
  "fails safely under burst load" rather than a real 429 threshold. See
  the class docstring in `tests/api/test_api.py` for the honest version of
  this tradeoff.
- **Five test cases across the three modules are written but marked
  `skip`** because the public demo targets don't implement the feature
  (forgot password, idle session timeout, lockout cooldown, role-based
  widget visibility, filter controls). They're real, spec'd test cases,
  not placeholders - see the `reason=` on each for exactly what's missing
  and `generated_test_cases/*.json` for the full case.
- **8B is a small model.** It's reliably good at "here's a traceback and
  some context, explain it" - it's not something I'd lean on for anything
  requiring broader judgment. That's a fine tradeoff for this specific
  job, not a claim that it's a general substitute for a larger model.

## What I'd build next with more time

1. **The flaky-test classifier (Option B).** Not a replacement for the
   failure explainer - a second pass over the accumulated reports under
   `reports/` that buckets recurring failures into real-bug / env / flaky,
   now that there'd be run history to bucket.
2. **Visual regression on the Dashboard module**, since "widget loading"
   and "data accuracy" as written only check the DOM, not what actually
   renders on screen - a Playwright screenshot-diff step would catch a
   whole class of CSS regressions these tests currently can't see.
3. **Point the suite at TestMu's real staging environment** and re-enable
   the five skipped test cases once forgot-password, idle-timeout,
   lockout-cooldown, and role-based permissions exist there.
4. **A throughput guardrail on the failure explainer itself** - right now
   every failure gets its own local model call, sequentially; at a much
   higher test count I'd batch failures from a single run into fewer
   calls instead of one per failure.
5. **Trace/video capture on UI failures** (`--tracing=retain-on-failure`),
   attached alongside the AI explanation in the HTML report, so a human
   reviewing a failure gets the visual context and the explanation in the
   same place.