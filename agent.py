"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable
from mcp_client import call_tool


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── query parsing ─────────────────────────────────────────────────────────────

def _to_price(word: str) -> float | None:
    """'$30', '30', or '$29.99.' -> a float. Anything else -> None."""
    try:
        return float(word.lstrip("$").rstrip("."))
    except ValueError:
        return None


def _parse_query(query: str) -> dict:
    """
    Split the query into words and pull out the size and the price.

        the word after "size"                   -> size       ("size m" -> "M")
        a "$" word, or a number after "under"
        or "below"                              -> max_price  ("under $30" -> 30.0)
        every other word                        -> description

    search_listings drops filler words itself, so "looking for a" can stay in
    the description.
    """
    words = query.replace(",", " ").split()
    description = []
    size = None
    max_price = None

    for i, word in enumerate(words):
        previous = words[i - 1].lower() if i > 0 else ""

        if previous == "size":
            size = word.upper()
        elif word.startswith("$") or previous in ("under", "below"):
            price = _to_price(word)
            if price is not None:
                max_price = price
            else:
                description.append(word)
        elif word.lower() in ("size", "under", "below"):
            continue  # the keyword itself; its value is the next word
        else:
            description.append(word)

    return {
        "description": " ".join(description),
        "size": size,
        "max_price": max_price,
    }


def _no_results_message(parsed: dict) -> str:
    """
    The empty-search message: what was searched, and what to change. It only
    names a filter the user actually set — no "try another size" for someone
    who never gave one.
    """
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    searched = f'"{description}"' if description else "your search"
    if size:
        searched += f" in size {size}"
    if max_price is not None:
        searched += f" under ${max_price:g}"

    changes = []
    if max_price is not None:
        changes.append(f"a max price higher than ${max_price:g}")
    if size:
        changes.append("a different size or no size")
    if description:
        changes.append("fewer or broader keywords")
    else:
        changes.append('a few words saying what the item is, like "denim jacket"')

    if len(changes) == 1:
        tries = changes[0]
    else:
        tries = ", ".join(changes[:-1]) + ", or " + changes[-1]
    return f"No listings matched {searched}. Try {tries}."


def _model_unavailable_message(item: dict, exc: Exception) -> str:
    """
    The model-unavailable message: the search still worked, so name the item
    found, say the styling step couldn't reach the model, and pass on the
    reason (bad key, no network, ...) so the user knows what to fix.
    """
    found = f'Found "{item.get("title")}" for ${item.get("price"):g}, but ' if item else ""
    return (
        f"{found}the AI model couldn't be reached, so no outfit or fit card was made. "
        f"{exc} Then run the same search again."
    )


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # TODO: delete these two lines and build the loop.
    next_step = "parse"
    count = 0

    while next_step != "done":
        count += 1
        trace.check_iterations(count)

        if next_step == "parse":
            session["parsed"] = _parse_query(session["query"])
            next_step = "search_listings"
            trace.step("parse_query", inputs=session["query"], returned=str(session["parsed"]))

        elif next_step == "search_listings":
            # Unit 4: search_listings now runs through the MCP server.
            search_args = {
                "description": session["parsed"]["description"],
                "size": session["parsed"]["size"],
                "max_price": session["parsed"]["max_price"],
            }
            session["search_results"] = call_tool("search_listings", search_args)

            # THE BRANCH: nothing found means stop here, before suggest_outfit.
            if not session["search_results"]:
                session["error"] = _no_results_message(session["parsed"])
                next_step = "done"
                note = "branch: empty, stopping before suggest_outfit"
            else:
                session["selected_item"] = session["search_results"][0]
                next_step = "suggest_outfit"
                note = f"branch: found, selected {session['selected_item']['title']}"
            trace.step("search_listings (via MCP)", inputs=str(search_args),
                       returned=session["search_results"], note=note)

        elif next_step == "suggest_outfit":
            outfit_inputs = {
                "new_item": session["selected_item"]["title"],
                "wardrobe_items": len(session["wardrobe"].get("items", [])),
            }
            try:
                session["outfit_suggestion"] = suggest_outfit(
                    session["selected_item"], session["wardrobe"]
                )
                next_step = "create_fit_card"
                trace.step("suggest_outfit", inputs=str(outfit_inputs),
                           returned=session["outfit_suggestion"])
            except ModelUnavailable as exc:
                session["error"] = _model_unavailable_message(session["selected_item"], exc)
                next_step = "done"
                trace.step("suggest_outfit", inputs=str(outfit_inputs),
                           note=f"model unavailable, stopping: {exc}")

        elif next_step == "create_fit_card":
            card_inputs = {
                "outfit": session["outfit_suggestion"],
                "new_item": session["selected_item"]["title"],
            }
            try:
                session["fit_card"] = create_fit_card(
                    session["outfit_suggestion"], session["selected_item"]
                )
                trace.step("create_fit_card", inputs=str(card_inputs),
                           returned=session["fit_card"], note="done")
            except ModelUnavailable as exc:
                session["error"] = _model_unavailable_message(session["selected_item"], exc)
                trace.step("create_fit_card", inputs=str(card_inputs),
                           note=f"model unavailable, stopping: {exc}")
            next_step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
