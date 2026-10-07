# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
Parsing and `search_listings` are plain Python over a fixed 40-listing file, so
a query that matches once matches every time. The miss I'm allowing for is the
model. Each completed run makes two model calls (`suggest_outfit` and
`create_fit_card`) on a free tier capped at 15 requests a minute, and there's
no `ModelUnavailable` handler until unit 4, so one failed call crashes that try.
An empty model reply also makes `create_fit_card` return "Can't write a fit
card without an outfit.", which doesn't count as a fit card. 5 of 5 would be
betting that a service I don't control never hiccups.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
Nothing on this path is random. The cheapest listing in `data/listings.json` is
$12 (the braided leather belt), so "under $5" makes `search_listings` return
`[]` every time, and my branch is one empty-list check that returns before any
model call. The "what to change" message is built from `session["parsed"]`, so
it comes out the same every run. If this fails once it will fail every time —
that's a broken branch, not bad luck, so anything below 5 of 5 would be
accepting a known bug.

---

## 3. The item search found is the item the next two tools receive

Given the query `'vintage graphic tee under $30'`, `session["selected_item"]["id"]`
equals `session["search_results"][0]["id"]`, and the trace lines for
`suggest_outfit` and `create_fit_card` both show that same item's title and
price as their input — 5 of 5 tries.

<!-- Unit 4 note: when adding trace.step() calls, pass the item dict itself as
     `inputs` so the trace prints "Title ($price, platform)". A wrapper dict
     like {"new_item": ..., "wardrobe": ...} only prints its keys. -->

**Why this target:**
The handoff is dictionary reads from the session, with no model and no
randomness involved, so a mismatch would be a bug in my loop (reading a stale
variable or the wrong index) and would show up every run, not once. I check the
ids and the trace instead of the caption text because state failure doesn't
look like state failure: a fit card about the wrong item reads like a bad
caption, and I'd blame the prompt.

---

## 4. The fit card keeps the facts and the length, even when the words change

Given the query `'vintage graphic tee under $30'` run 5 times with caching off,
each fit card is under 280 characters, contains the selected item's price
written as `$` and the whole-dollar amount (`$24`; `$24.00` also counts), and
contains the item's platform name in any capitalization (`depop`, `Depop`) — in
at least 4 of 5 tries.

**Why this target:**
The words are supposed to change at `TEMPERATURE = 0.9`. What shouldn't change
is the facts and a length someone would actually post. Price and platform are
in the prompt, but at 0.9 the model sometimes drops a detail or runs long with
emoji and hashtags, and nothing in my code checks its output, so 5 of 5 would
mean trusting the model to follow every instruction every time. Below 4 would
mean the prompt isn't doing its job. I left the title out on purpose: the model
paraphrases titles ("2003 tour tee"), so an exact-title check would fail good
captions, while price and platform are exact strings I can search for.

---

## 5. The search respects the size and price the user typed

Given the query `'graphic tee size L under $30'`, `session["parsed"]` holds size
`"L"` and max_price `30.0`, `session["search_results"]` has at least one
listing, and every listing in it costs $30 or less and has a size that matches
L under my Tool Inventory rule (`L`, `L/XL`, or `One Size` — never `XL`,
`XL (oversized)`, or `XL (fits oversized)`) — 5 of 5 tries.

**Why this target:**
Parsing and search are deterministic, so five tries give the same answer and a
single miss means the filter is wrong, not unlucky. A size or price the user
typed is a hard limit: showing someone a $38 item after they said under $30 is a
broken product, not variance. The data has three XL listings under $30 (the $22
flannel, the $21 college crewneck, the $20 navy sweatshirt), which is exactly
the `"l" in "xl"` trap the starter warns about. "At least one listing" is there
so an empty result can't pass by default.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
