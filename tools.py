"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings


# ── Shared helpers ────────────────────────────────────────────────────────────

# Filler words that would otherwise match nearly every listing description.
_STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "in", "of", "to", "or", "on",
    "my", "me", "i", "im", "want", "need", "looking", "something", "some",
    "under", "below", "less", "than", "size", "max", "price",
}


def _words(text: str) -> set[str]:
    """Lowercase whole words, so 'tee' never matches inside another word."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _size_pieces(size: str) -> list[str]:
    return [p for p in re.split(r"[/\s]+", size.lower().strip()) if p]


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    The size rule from the Tool Inventory: every piece of the requested size has
    to appear as a whole piece of the listing's size. "M" matches "S/M", but "L"
    does not match "XL (oversized)" and "S" does not match "US 9". Listings sized
    "One Size ..." match any request.
    """
    if listing_size.lower().startswith("one size"):
        return True
    have = set(_size_pieces(listing_size))
    return all(piece in have for piece in _size_pieces(wanted))


def _price(price: float) -> str:
    """$24 for whole dollars, $24.50 otherwise."""
    price = float(price)
    return f"${price:.0f}" if price.is_integer() else f"${price:.2f}"


def _describe_item(item: dict) -> str:
    """A listing's details as prompt lines. Brand only when there is one."""
    lines = [
        f"Title: {item['title']}",
        f"Category: {item['category']}",
        f"Colors: {', '.join(item['colors'])}",
        f"Style: {', '.join(item['style_tags'])}",
        f"Size: {item['size']}",
        f"Condition: {item['condition']}",
        f"Price: {_price(item['price'])}",
        f"Platform: {item['platform']}",
    ]
    if item.get("brand"):
        lines.append(f"Brand: {item['brand']}")
    return "\n".join(lines)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    # TODO: replace this with your implementation
    query = _words(description or "") - _STOPWORDS

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue

        text = " ".join(
            [listing["title"], listing["description"], " ".join(listing["style_tags"])]
        )
        score = len(query & _words(text))
        if score == 0:
            continue
        scored.append((score, listing))

    # Most shared keywords first; ties go to the cheaper listing.
    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    # TODO: replace this with your implementation
    items = (wardrobe or {}).get("items") or []

    if not items:
        system = (
            "You are a thrift stylist. The user hasn't saved any wardrobe "
            "pieces, so give general styling advice. Never say or imply that "
            "the user already owns something."
        )
        prompt = (
            f"Here is a thrifted item:\n{_describe_item(new_item)}\n\n"
            "Suggest 1 to 3 ways to style it. For each, name the kinds of "
            "pieces it pairs with (for example: straight-leg jeans, white "
            "sneakers) and give one sentence on why they work together. "
            "Plain text, no intro."
        )
        return generate(prompt, system=system)

    pieces = []
    for piece in items:
        details = [
            piece["category"],
            f"colors: {', '.join(piece['colors'])}",
            f"style: {', '.join(piece['style_tags'])}",
        ]
        if piece.get("notes"):
            details.append(f"notes: {piece['notes']}")
        pieces.append(f"- {piece['name']} ({'; '.join(details)})")

    system = (
        "You are a thrift stylist. Build outfits only from the new item plus "
        "pieces in the user's wardrobe list, and refer to wardrobe pieces by "
        "their names exactly as written."
    )
    prompt = (
        f"Here is a thrifted item the user is considering:\n"
        f"{_describe_item(new_item)}\n\n"
        f"Here is their wardrobe:\n" + "\n".join(pieces) + "\n\n"
        "Suggest 1 to 3 outfits. For each, name the new item and the wardrobe "
        "pieces it goes with, then give one sentence on why they work "
        "together. Plain text, no intro."
    )
    return generate(prompt, system=system)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    # TODO: replace this with your implementation
    if not outfit or not outfit.strip():
        return "Can't write a fit card without an outfit."

    system = (
        "You write captions people actually post about their thrift finds. "
        "Casual and specific, never a product description."
    )
    prompt = (
        f"The find:\n{_describe_item(new_item)}\n\n"
        f"How it's being styled:\n{outfit.strip()}\n\n"
        "Write a caption for a post about this find. Rules:\n"
        "- 2 to 4 sentences, under 280 characters total.\n"
        f"- Mention the item's title, its price written as {_price(new_item['price'])}, "
        f"and the platform ({new_item['platform']}) once each.\n"
        "- Be specific about the vibe of the outfit.\n"
        "Return only the caption."
    )
    return generate(prompt, system=system)
