# Prompts

Tool used: Claude (Sonnet 5), chat interface - for Task 2 specifically.
(Task 1's scaffold and Task 3's integration code went through a different
workflow - ChatGPT-5 for design, then Claude for the actual files. See
`ai-usage-log.md`. This file is scoped to Task 2's test-case prompts only.)

I didn't iterate the same way on every module, and I'm not going to
pretend I did. Login is where I spent the most time - it's the one where
getting the error-message wording wrong actually matters. Dashboard and
API mostly worked well enough on the first or near-first try that going
back and writing a whole second, formally-structured prompt would've been
manufacturing effort I didn't actually put in. Where that's the case below,
I said so and just fixed the small stuff by hand in the generated JSON
instead of looping back to the model.

---

## Login

### Attempt 1 (too vague)

```
generate test cases for a login page. cover valid login, invalid creds,
forgot password, session expiry, and brute force lockout
```

**What came back:** a reasonable-looking list, but shallow - "test invalid
login" as a single case instead of separating wrong-password vs.
wrong-username vs. blank-field (which are different code paths and different
bugs), no priority/severity, no explicit statement of what the *error
message itself* should and shouldn't say (e.g. it should never reveal
whether the username exists), and nothing about what happens to
already-open sessions elsewhere after a lockout or logout.

### Attempt 2 (what I actually used)

```
You are a senior SDET writing regression test cases for a web app's Login
module. Generate test cases for these five areas: valid login, invalid
credentials, forgot password, session expiry, brute-force lockout.

Rules:
- Split "invalid credentials" into separate cases for wrong password, wrong
  username, and blank fields - these are different code paths.
- For every negative case, state explicitly what the error message should
  NOT reveal (e.g. don't confirm whether a username/email exists).
- Include at least one case about what happens to an *already open* session
  after logout or after a lockout is triggered elsewhere.
- Output as JSON: a list of objects with id, title, type (positive/negative),
  priority (P0-P2), steps (array), expected_result, and a "note" field for
  anything that assumes infrastructure I might not have (e.g. a live email
  inbox, a configurable session timeout).
- Don't pad the list. I'd rather have 8 sharp cases than 15 that overlap.
```

**What changed and why:** splitting "invalid credentials" surfaced LOGIN-02
vs. LOGIN-03 vs. LOGIN-04 as genuinely distinct cases with distinct
automation. Asking for the "note" field up front is what flagged, before I
wrote a single line of code, that forgot-password and idle-session-timeout
would need infrastructure (a real inbox, a controllable clock) that a public
demo target doesn't have - so I could design around that instead of
discovering it mid-implementation. This is the one module where I actually
wrote out a full second prompt, because the gap between attempt 1 and what
I needed was big enough that a quick follow-up message wouldn't have
covered it.

---

## Dashboard

### The one prompt I actually used

```
write test cases for a dashboard - widgets, filters, sorting, different
user roles. same idea as the login ones - split widget load vs data
accuracy since those are different failure modes, and for permission
stuff make sure it says whether a hidden widget is removed from the dom
or just css-hidden, don't leave it vague. also throw in one case that's
designed to actually fail against a broken dashboard, not just pass on a
good one. same json format as before
```

**Why there's no attempt 1/attempt 2 here:** I already knew from Login
what usually goes wrong with a first pass (vague merged cases, "hidden"
left ambiguous), so I front-loaded those asks into a single message
instead of deliberately writing a bad prompt first to demonstrate the gap.
It came back close enough to usable that I didn't bother iterating further
- didn't feel like a good use of time when the output was already doing
what I needed, even if it was a little rough in one spot.

**The one thing I fixed by hand instead of going back to the model:**
DASH-07's expected result still said "hidden" without committing to
DOM-removed vs. CSS-hidden, despite me asking for exactly that. Writing a
whole new prompt over one ambiguous word felt like overkill, so I just
edited that line directly in the generated JSON. DASH-08 - the case whose
whole job is to fail against a visibly broken dashboard - is the one I
ended up actually automating against `problem_user`'s known broken-image
bug on SauceDemo. It's the only widget test in the suite currently
exercising a real, visible defect rather than a healthy page, which
matters because a suite that only ever runs against a healthy app can't
tell you if its own checks are strong enough.

---

## REST API

### First pass

```
same as before but for a rest api - auth token validation, crud, error
handling (4xx/5xx), rate limiting, schema validation. same json format,
and for crud say in each case whether you can tell success just from the
response or if it actually needs a follow up read, cause some fake apis
fake the response without saving anything
```

**What came back:** mostly solid - error handling was already split by
cause (malformed body / missing field / not-found) without me having to
ask a second time, and the per-case response-vs-read note I asked for up
front is why API-07 and API-08 explicitly flag that a fake backend's
"success" can only be checked at the response-contract level. Two real
gaps, though: it quietly assumed cookie-session auth, and it wrote rate
limiting as if a 429 threshold is guaranteed, which it isn't against a lot
of demo/fake APIs.

### Follow-up (same thread, not a rewrite)

```
two things - don't assume cookie auth, could be bearer tokens instead,
keep the auth cases generic. and for rate limiting don't assume a real
429 exists, add a fallback case for "fails safely under burst load" and
flag in the note that the threshold might not be enforced
```

**What changed and why:** didn't see the point in rewriting the whole
prompt when only two things were actually wrong. The transport-agnostic
auth cases are why API-03 and API-04 read as "a protected endpoint" rather
than hardcoding a cookie flow - which mattered once DummyJSON (my actual
target once I got to Task 3) turned out to use Bearer tokens, not cookies.
The rate-limiting fallback note is the direct reason
`TestRateLimiting.test_burst_of_requests_completes_without_crashing`
exists in its current, deliberately weaker form instead of asserting a 429
the target doesn't actually guarantee.