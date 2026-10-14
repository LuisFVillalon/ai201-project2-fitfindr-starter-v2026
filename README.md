# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

A user types what they're thrifting for in plain words, like `'vintage graphic tee under $30'` or `'denim jacket size M'`. FitFindr pulls the size and max price out of the query, searches a file of 40 secondhand listings, and picks the best match. It then suggests 1–3 outfits that pair that item with pieces from the user's wardrobe and writes a short fit-card caption with the item's price and platform, ready to post. If nothing matches, it stops before the outfit step and says what was searched and what to change: a higher max price, a different size, or broader keywords.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:**
Filters data/listings.json to items whose title, description, or style_tags share at least one keyword with description, whose size matches size, and whose price is at or below max_price. Keywords are matched as whole words, and common filler words ("a", "the", "for", "under", "size", ...) are ignored.
- **Inputs:**
description (str, keywords like "vintage graphic tee"), size (str or None, e.g. "M"; None skips the size filter), max_price (float or None, inclusive; None skips the price filter)
- **Size match rule:**
Lowercase both sizes and split them into pieces on "/" and spaces. A listing matches if every piece of the requested size appears as a whole piece in the listing's size. So "M" matches "S/M" and "M/L", "S" does not match "US 9", and "L" does not match "XL". Listings whose size starts with "One Size" match any requested size.
- **Returns:**
A list of up to config.SEARCH_RESULT_LIMIT (10) full listing dicts, best keyword match first (most shared keywords), ties broken by lower price. Each dict has id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand (str or None), platform.
- **When it has nothing:**
Returns [] (an empty list, never None, no exception).

### `suggest_outfit`

- **What it does:**
Asks the model to pair the found item with pieces from the user's wardrobe and returns outfit ideas.
- **Inputs:**
new_item (dict, one listing dict from search_listings), wardrobe (dict with an "items" key holding a list of wardrobe item dicts, per data/wardrobe_schema.json; the list may be empty, as in {"items": []})
- **Returns:**
A non-empty str with 1–3 outfit ideas. Each idea names the new item and the wardrobe pieces it goes with (using their name field), plus one sentence on why they work together.
- **When it has nothing:**
If wardrobe["items"] is empty, it still calls the model and returns a non-empty str of general styling advice for the new item (e.g. "pair with straight-leg jeans and white sneakers") without naming any owned pieces. It never returns "" or raises.

### `create_fit_card`

- **What it does:**
Asks the model to write a short social-media caption for the new item styled as the given outfit.
- **Inputs:**
outfit (str, the outfit suggestion returned by suggest_outfit), new_item (dict, the listing dict)
- **Returns:**
A str caption of 2–4 sentences, under 280 characters, that mentions the item's title, price, and platform once each.
- **When it has nothing:**
If outfit is None, empty, or only whitespace, it returns the string "Can't write a fit card without an outfit." instead of calling the model.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:**
If search_listings returns an empty list, put a message in session["error"] that repeats the description, size, and max_price that were searched and names what to change (raise max_price, try another size or no size, or use fewer or broader keywords), leave session["fit_card"] as None, and return the session without calling suggest_outfit. Otherwise, put the first result (the best keyword match) in session["selected_item"], call suggest_outfit with that item and the wardrobe and put the string it returns in session["outfit_suggestion"], then call create_fit_card with that outfit and the same item and put the caption in session["fit_card"].

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** <!-- regex, string splitting, or asking the model — say which -->
String splitting, in `agent.py::_parse_query`. The query is split into words. The word after "size" becomes the size (uppercased, so "size m" → "M"). A word starting with "$", or a number right after "under" or "below", becomes max_price ("under $30" → 30.0). Every other word goes into the description. Filler words like "a" and "for" stay in, because search_listings drops them itself. No model call is made, so the same query always parses the same way.

**What moves through the session:** <!-- which fields, in what order -->
`new_session` starts with `query` and `wardrobe`. Then, in order:
1. `parsed` — the description, size, and max_price from `_parse_query(session["query"])`.
2. `search_results` — the list search_listings returned for those three values.
3. If `search_results` is empty: `error` gets the no-results message and the run stops. `selected_item`, `outfit_suggestion`, and `fit_card` stay None.
4. Otherwise: `selected_item` — `search_results[0]`.
5. `outfit_suggestion` — suggest_outfit(`selected_item`, `wardrobe`), both read from the session.
6. `fit_card` — create_fit_card(`outfit_suggestion`, `selected_item`), both read from the session.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'
  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1
New item: Y2K Baby Tee — Butterfly Print
Wardrobe pieces: Baggy straight-leg jeans, dark wash; Chunky white sneakers; Black crossbody bag
The fitted, graphic nature of the baby tee contrasts with the relaxed silhouette of the dark baggy jeans to nail that authentic Y2K streetwear aesthetic, finished cleanly with chunky white sneakers and a black crossbody bag.

Outfit 2
New item: Y2K Baby Tee — Butterfly Print
Wardrobe pieces: Wide-leg khaki trousers; Brown leather belt; Chunky white sneakers
The white and pink tones of the baby tee pop against the neutral wide-leg khaki trousers, creating a playful blend of Y2K style and minimalist earth tones brought together by a brown leather belt and chunky white sneakers.

Outfit 3
New item: Y2K Baby Tee — Butterfly Print
Wardrobe pieces: Vintage black denim jacket; Baggy straight-leg jeans, dark wash; Black combat boots; Black crossbody bag
Layering the slightly cropped vintage black denim jacket over the butterfly print tee adds a touch of grunge to the Y2K aesthetic, while the baggy straight-leg jeans, black combat boots, and black crossbody bag tie the dark elements together seamlessly.

  Fit card: Found this Y2K Baby Tee — Butterfly Print on depop for $18 and I’m obsessed. Styled it with dark baggy jeans and chunky sneakers for that ultimate early 2000s mall rat vibe. So good for everyday.

0 model calls this session, 2 served from cache
```

**The three tools, tested one at a time**

```
$ python
>>> from tools import search_listings
>>> search_listings('graphic tee', size='L', max_price=30)
[{'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}]
>>> search_listings('graphic tee', max_price=5)
[]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_example_wardrobe()))"
Outfit 1
New item: Graphic Tee — 2003 Tour Bootleg Style
Wardrobe pieces: Baggy straight-leg jeans, dark wash; Black combat boots; Black crossbody bag
Why they work together: This combination leans entirely into the vintage grunge aesthetic, pairing the distressed band tee with heavy denim and rugged boots for an effortless, classic streetwear look.

Outfit 2
New item: Graphic Tee — 2003 Tour Bootleg Style
Wardrobe pieces: Vintage black denim jacket; Wide-leg khaki trousers; Chunky white sneakers
Why they work together: Tucking the graphic tee into the wide-leg khaki trousers creates a balanced silhouette, while the vintage black denim jacket and chunky white sneakers add a modern, casual contrast.

Outfit 3
New item: Graphic Tee — 2003 Tour Bootleg Style
Wardrobe pieces: Black cropped zip hoodie; Baggy straight-leg jeans, dark wash; Chunky white sneakers; Black crossbody bag
Why they work together: Layering the black cropped zip hoodie unzipped over the longer graphic tee creates a dimensional streetwear vibe that pairs seamlessly with baggy denim and chunky sneakers.

$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_empty_wardrobe()))"
Option 1
Pair the tee with distressed light-wash mom jeans, chunky black combat boots, and a silver chain necklace. This combination leans into the vintage grunge aesthetic by contrasting the dark graphic with worn denim and edgy hardware.

Option 2
Layer the t-shirt over a tight long-sleeve mesh top, and pair it with a pleated plaid mini skirt, knee-high socks, and platform loafers. The playful school-girl elements balance the heavy, rebellious energy of the bootleg tour style.

Option 3
Tuck the graphic tee into wide-leg cargo trousers, add a nylon shoulder bag, and finish the look with retro platform sneakers. The baggy silhouettes create an effortless, high-fashion streetwear feel that looks intentional and modern.
```

```
$ $env:AI201_CACHE='0'    # cache off, so each run is a real model call
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; card = create_fit_card('baggy dark-wash jeans and chunky white sneakers', load_listings()[5]); print(card); print(len(card), 'chars')"
Scored this Graphic Tee — 2003 Tour Bootleg Style on depop for just $24. Paired it with baggy dark-wash jeans and chunky white sneakers for the ultimate grunge look. So stoked on how this fit came together.
206 chars

(same command, run 2)
Scored this Graphic Tee — 2003 Tour Bootleg Style on depop for only $24. Paired it with baggy dark-wash jeans and chunky white sneakers for the ultimate grunge fit. Obsessed with how heavy and faded this tee is.
211 chars

(same command, run 3)
Scored this Graphic Tee — 2003 Tour Bootleg Style on depop for only $24. Paired it with baggy dark-wash jeans and chunky white sneakers for the ultimate grunge street look. Total win.
183 chars

$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('   ', load_listings()[5]))"
Can't write a fit card without an outfit.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I gave Claude the Milestone 5 task: open agent.py and fill in `run_agent()` following my branch rule from Milestone 2.
- *What came back:* It decided on its own to parse the query with regex. It added `import re` and started sending several edits to agent.py at once. The assignment never asks for regex, and it leaves the parsing method up to me.
- *What I changed:* I rejected those edits, asked why it was using regex, and told it to make one change at a time. When it asked how I wanted the query parsed, I picked string splitting. `_parse_query` now splits the query into words: the word after "size" is the size, and a "$" word or the number after "under"/"below" is the max price. I reviewed each change to agent.py on its own before accepting it.

**Moment 2**

- *What I asked for:* I asked Claude to implement the three tools in tools.py from my Tool Inventory spec.
- *What came back:* Its edits replaced the stub bodies but also deleted the starter's comments and docstrings around them.
- *What I changed:* I rejected those edits and told it to leave the comments. It redid them, adding the code under the existing docstrings and comments so the starter's notes stay next to my implementation. Then I tested each tool on its own; those are the three per-tool tests in Sample Run.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item the next two tools receive | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card keeps the facts and the length | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. The search respects the size and price the user typed | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Full log: `results/run_2026-10-13_1817_before.md`, produced by `run_eval.py::main`
(5 tries per scenario, caching off, temperature 0.9, 50 model calls). The
empty-wardrobe scenario also ran 5 times as a diagnostic (5/5 completed with
general advice) but isn't one of my five criteria.

**Real output from one try**, pasted as text, naming the file and function
that produced it:

**Criterion 1** — try 1, `agent.py::run_agent` (fit card from `tools.py::create_fit_card`):

```
- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 10

Fit card:
Manifesting spring with this Y2K Baby Tee — Butterfly Print. Snagged it on depop for just $18 and it’s giving major 2000s mall rat energy paired with baggy denim.
```

**Criterion 2** — try 1, `agent.py::run_agent` (message from `agent.py::_no_results_message`):

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit

stopped early: yes — No listings matched "designer ballgown" in size XXS under $5. Try a max price higher than $5, a different size or no size, or fewer or broader keywords.
```

**Criterion 3** — try 1, trace from `agent.py::run_agent` via `trace.py::step`:

```
[2] search_listings (via MCP)
      →    branch: found, selected [lst_002] Y2K Baby Tee — Butterfly Print ($18.0, depop)
      results: lst_002 S/M $18 | lst_033 L $19 | lst_006 L $24 | ...
[3] suggest_outfit
      in:  new_item=[lst_002] Y2K Baby Tee — Butterfly Print ($18.0, depop), wardrobe_items=10
[4] create_fit_card
      in:  new_item=[lst_002] Y2K Baby Tee — Butterfly Print ($18.0, depop), outfit='Outfit 1:\nNew item: Y2K Baby Tee— …
```

**Criterion 4** — try 1, `tools.py::create_fit_card` (199 characters, contains `$18` and `depop`):

```
Just scored this Y2K Baby Tee — Butterfly Print on depop for $18. Obsessed with how the pastel graphics look paired with baggy dark wash jeans and chunky sneakers for that ultimate 2000s street vibe.
```

Lengths across the 5 tries: 199, 168, 213, 164, 170. All under 280, and all contain `$18` and `depop`.

**Criterion 5** — try 1, `agent.py::_parse_query` + `tools.py::search_listings` (via MCP):

```
[1] parse_query
      in:  graphic tee size L under $30
      out: {'description': 'graphic tee', 'size': 'L', 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'graphic tee', 'size': 'L', 'max_price': 30.0}
      out: 3 items: Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style, Vintage Graphic Hoodie — Faded Black
      →    branch: found, selected [lst_033] Vintage Band Tee — Faded Grey ($19.0, depop)
      results: lst_033 L $19 | lst_006 L $24 | lst_015 L $26
```

None of the three XL listings under $30 (lst_012 $20, plus the $22 flannel and $21 crewneck) showed up in any of the 5 tries.

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | MET (5/5) | All 5 tries reached `create_fit_card` and returned a real caption. None stopped early, crashed, or returned "Can't write a fit card without an outfit." 5 passes ≥ 4. |
| 2 | An impossible query stops before the second tool | 5 of 5 | MET (5/5) | In all 5 traces, step 2 returned `[] (empty)`, the branch note says "stopping before suggest_outfit", there's no step 3, and the message names three things to change. 5 = 5. |
| 3 | The item search found is the item the next two tools receive | 5 of 5 | MET (5/5) | In all 5 traces, the selected item is `search_results[0]` (`lst_002`), and the `suggest_outfit` and `create_fit_card` inputs both show `[lst_002] Y2K Baby Tee — Butterfly Print ($18.0, depop)`. 5 = 5. |
| 4 | The fit card keeps the facts and the length | 4 of 5 | MET (5/5) | I checked each card against the exact rule: lengths 199, 168, 213, 164, 170 (all < 280), all contain `$18`, all contain `depop`. 5 passes ≥ 4. |
| 5 | The search respects the size and price the user typed | 5 of 5 | MET (5/5) | All 5 parsed `size: 'L'`, `max_price: 30.0`. Every try returned the same 3 results (`lst_033 L $19`, `lst_006 L $24`, `lst_015 L $26`): at least one, all ≤ $30, all size L, no XL. 5 = 5. |

**Diagnoses**

**I missed nothing.** All five criteria met their target on the before run, so there's no miss to trace to a step. The honest question is whether my targets were too low.

- **Criteria 2, 3 and 5 were never going to vary.** None of them touches the model. Parsing, `search_listings` and the session handoff are plain Python over a fixed 40-listing file, so 5 of 5 is the right target: one failure would mean a bug, not bad luck. But each was tested with **one query**. Criterion 5 only proves size `L` works. It says nothing about `S` (the `"s" in "us 9"` trap) or `M`.
- **Criteria 1 and 4 cleared their 4-of-5 targets with room to spare.** In Unit 3 I set 4 of 5 to allow for a failed model call crashing a try. Two things removed that risk: the starter's rate limiter paced the run instead of failing, and Unit 4's `ModelUnavailable` handler turns a model failure into a message instead of a crash. The query `vintage graphic tee under $30` completed 15 of 15 times across the three scenarios that used it.
- **Pattern:** every criterion was scored on a single query, and the three model-based checks all used the same item. The test proves the agent works for the Y2K Baby Tee. It doesn't prove it works for the catalog.

**The criterion I'd tighten: #4, the fit card.** It ran 5 times on one item: the $18 Y2K Baby Tee on depop, a short whole-dollar price on a lowercase platform name. That's the easiest case for the rule I wrote. The longest card in the whole run (248 characters) came from a different item (`lst_033`, criterion 5's scenario), so the 280-character limit is closer than criterion 4's own scores (164–213) suggest. Tightened version: *for 5 different items, each fit card is under 280 characters and contains that item's own `$price` and platform — 5 of 5.*

**Things I noticed that aren't criteria** (no verdict, but worth recording):
- `suggest_outfit`'s format drifts between tries: `Outfit 1:`, `Outfit 1` with no colon, `- New Item:` bullets, `Style 1:` (empty wardrobe). Nothing downstream parses it yet, so it didn't fail anything.
- `create_fit_card` sometimes shortens the title ("Vintage Band Tee" instead of "Vintage Band Tee — Faded Grey"), which is exactly why criterion 4 left the title out.



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path** — `python app.py ask 'vintage graphic tee under $30' --trace`

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: found, selected Y2K Baby Tee — Butterfly Print
[3] suggest_outfit
      in:  {'new_item': 'Y2K Baby Tee — Butterfly Print', 'wardrobe_items': 10}
      out: Outfit 1 New item: Y2K Baby Tee — Butterfly Print Wardrobe pieces: Baggy straight-leg jeans, dark wash; Chunky…
[4] create_fit_card
      in:  {'outfit': 'Outfit 1\nNew item: Y2K Baby Tee — Butterfly Print\nWardrobe pieces: Baggy straight-leg jeans, dar…
      out: Found this Y2K Baby Tee — Butterfly Print on depop for $18 and I’m obsessed. Styled it with dark baggy jeans a…
      →    done
```

**Empty search** — `python app.py ask 'purple wedding dress size 2 under $1' --trace`

```
[1] parse_query
      in:  purple wedding dress size 2 under $1
      out: {'description': 'purple wedding dress', 'size': '2', 'max_price': 1.0}
[2] search_listings (via MCP)
      in:  {'description': 'purple wedding dress', 'size': '2', 'max_price': 1.0}
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit
```

The empty-search trace stops at step 2, two steps shorter than the happy path, so the branch is working.

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->
I registered `search_listings` in `mcp_server.py` with `@mcp.tool()` and typed inputs (`description: str`, `size: str | None`, `max_price: float | None`) that match my Tool Inventory. Then in `run_agent()` (`agent.py`) I replaced the direct `search_listings(...)` call with `call_tool("search_listings", {...})` from `mcp_client.py`. `python mcp_client.py` listed the tool with all three inputs. Nothing behaved differently afterwards: `'vintage graphic tee under $30'` returned the same top item (Y2K Baby Tee — Butterfly Print, $18.0) through MCP as it did with the direct call, and the empty search still returned `[]`.


---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** One prompt: the user prompt in `tools.py::suggest_outfit`, in both branches (wardrobe and empty wardrobe). The old prompt said "name the new item and the wardrobe pieces… one sentence on why… Plain text, no intro" and left the layout to the model. The new one spells out an exact three-line format per outfit and forbids bullets, bold and intros:

```
Outfit 1: <new item title>
Pieces: <piece>; <piece>; <piece>
Why: <one sentence on why they work together>
```

Pieces are separated by semicolons because some wardrobe names contain commas ("Baggy straight-leg jeans, dark wash"). The system prompts, the empty-wardrobe check and every other line of code are unchanged.

**Which failure it was meant to fix:** No criterion missed, so this follows the side observation in my diagnosis: `suggest_outfit`'s layout drifted from try to try. Before I changed anything, I wrote the measure into `check_outfit_format.py`. A suggestion passes if every non-blank line starts with `Outfit N:`, `Pieces:` or `Why:`, the first line is `Outfit 1:`, and there are the same number (1–3) of each. On the before log it scored **0/25**. The 20 with-wardrobe suggestions mixed `Outfit 1` / `Outfit 1:` with `New item:` / `New Item:` / `- New Item:` bullets, and the 5 empty-wardrobe ones were headerless prose or `Style 1:`. The before score is 0 partly because the old prompt never asked for this format, so the real question was whether asking for it makes the output consistent.

### Run Log — After

`results/run_2026-10-13_1833_after.md`, produced by `run_eval.py::main` (same 6 scenarios, 5 tries each, caching off, temperature 0.9, 50 model calls).

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. The item search found is the item the next two tools receive | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. The fit card keeps the facts and the length | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. The search respects the size and price the user typed | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Side by side:**

| Measure | Before | After |
|---|---|---|
| Criteria met | 5 of 5 | 5 of 5 |
| Outfit suggestions in the fixed format (`check_outfit_format.py`) | **0/25** | **25/25** |
| Criterion 4 fit card lengths | 199, 168, 213, 164, 170 | 184, 188, 194, 167, 162 |
| Fit cards that describe the user as the **seller** ("listed it on depop") | **0/25** | **4/25** |

Real output, criterion 4 try 1, `tools.py::suggest_outfit` then `tools.py::create_fit_card`:

```
Outfit 1: Y2K Baby Tee — Butterfly Print
Pieces: Baggy straight-leg jeans, dark wash; Chunky white sneakers; Black crossbody bag
Why: The dark wash denim anchors the playful pastel graphic for an effortless, street-smart Y2K look.

Outfit 2: Y2K Baby Tee — Butterfly Print
Pieces: Wide-leg khaki trousers; Brown leather belt; Chunky white sneakers
Why: The khaki trousers and brown belt balance the fitted tee with relaxed, earthy tones.

Outfit 3: Y2K Baby Tee — Butterfly Print
Pieces: Vintage black denim jacket; Baggy straight-leg jeans, dark wash; Black combat boots
Why: The black denim jacket and combat boots add an edgy contrast to the soft butterfly graphics.

Fit card:
Obsessed with this Y2K Baby Tee — Butterfly Print for $18. Styled it with wide-leg khakis and a leather belt for the ultimate earthy, low-key fit. Listing this beauty on depop tonight!
```

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->

It fixed what it targeted. Format consistency went from 0/25 to 25/25, empty-wardrobe runs included, and all five criteria stayed MET, so nothing I was measuring got worse. But it likely caused a side effect that none of my criteria catch. In 4 of the 25 after cards, `create_fit_card` framed the user as **selling** the item ("Just listed it on depop", "before I list it on depop", "Got it listed on depop", and the "Listing this beauty on depop tonight!" card above). The before run had 0 of 25. My best explanation: the old outfit text almost always opened with `New item: <title>`, which told `create_fit_card` the item was a new purchase. The new format drops the words "New item", so the caption prompt has one less cue about who bought what. Those cards still pass criterion 4, because the price and platform are there, which shows that criterion checks the facts are *present*, not that they're *used correctly*. 4 of 25 is a small sample, so I'd treat it as a likely cause, not a proven one.



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
