"""
IM&Finity – AI concierge agent (Flask blueprint)
=================================================

Drop this file into the `reservation_tracker/` folder (next to app.py and
database.py), then register it in app.py:

    from agent import agent_bp
    app.register_blueprint(agent_bp)

It adds a small, PUBLIC API the website's chat widget talks to. The agent's
"brain" (Claude) runs here on the server, so the API key is never exposed to
visitors, and it reads the SAME reservations.db the scheduling app uses.

What it can do (read-only — it never writes to the database):
  • suggest currently popular treatments  (counts from real bookings)
  • list current promotions / discounts    (from promotions.json, owner-edited)
  • suggest the next free time slots        (same hours logic as the app)
  • answer general questions and hand off to the booking form / phone

PRIVACY: the data the agent can reach is aggregate only — treatment counts and
open time slots. It can NEVER read client names, phones, or notes. Those columns
are never selected by the functions below.

Setup on PythonAnywhere (Web tab → WSGI file), add next to the other secrets:
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
    # optional overrides:
    # os.environ["IMFINITY_AGENT_MODEL"] = "claude-haiku-4-5"   # cheaper/faster
Then `pip install --user -U anthropic flask-cors` in a Bash console and Reload.

NOTE (free PythonAnywhere accounts): outbound internet is whitelisted and
api.anthropic.com is usually NOT on it — calling Claude typically needs the
paid tier (~$5/mo). The /availability, /popular and /promotions endpoints work
on any tier; only /chat needs outbound access to Claude.
"""

import os
import re
import json
import time
from datetime import date, datetime, timedelta

from flask import Blueprint, request, jsonify

import database

# ── Config ──────────────────────────────────────────────────────────────────

# Which websites are allowed to call this API (CORS).
ALLOWED_ORIGINS = [
    "https://www.imfinity.rs",
    "https://imfinity.rs",
    "http://localhost:5050",   # local testing
    "http://127.0.0.1:5500",   # VS Code Live Server, etc.
]

# Model: defaults to the most capable Opus. Set IMFINITY_AGENT_MODEL to
# "claude-haiku-4-5" or "claude-sonnet-4-6" to lower cost/latency.
MODEL = os.environ.get("IMFINITY_AGENT_MODEL", "claude-opus-4-8")

# Simple in-memory abuse guard (fine for a single PythonAnywhere worker).
RATE_LIMIT_MAX = 25            # requests ...
RATE_LIMIT_WINDOW = 600        # ... per this many seconds, per IP
MAX_MSG_CHARS = 1500           # reject absurdly long messages
MAX_HISTORY = 12               # only keep the last N turns

agent_bp = Blueprint("agent", __name__)

# CORS — kept dependency-light: handled manually in after_request below so the
# app still runs even if flask-cors isn't installed.
_rate_log = {}


# ── Data access (read-only, aggregate only — never returns personal data) ─────

def _hours_for(d):
    """Working hours for a given date — mirrors app.py (weekday 16-21, weekend 11-21)."""
    try:
        import app  # lazy import to avoid a circular import at load time
        weekday_hours, weekend_hours = app.WEEKDAY_HOURS, app.WEEKEND_HOURS
    except Exception:
        weekday_hours, weekend_hours = list(range(16, 22)), list(range(11, 22))
    return weekend_hours if d.weekday() >= 5 else weekday_hours


WEEKDAY_NAMES_SR = ["Ponedeljak", "Utorak", "Sreda", "Četvrtak", "Petak", "Subota", "Nedelja"]
WEEKDAY_NAMES_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _free_times_for(d, names, today, now_hour):
    """Free whole-hour slots for one date as a list of 'HH:00' strings."""
    booked = {r["time"] for r in database.get_by_date(d.isoformat())}
    free = []
    for h in _hours_for(d):
        if d == today and h <= now_hour:
            continue  # skip times that have already passed today
        t = f"{h:02d}:00"
        if t not in booked:
            free.append(t)
    return free


def get_free_slots(days_ahead=7, lang="sr", on_date=None):
    """Availability, grouped by day. Availability only — never returns client data.

    - on_date='YYYY-MM-DD' → availability for that one day.
    - otherwise → availability for each of the next `days_ahead` days.
    Each day is {date, weekday, free_times: [...]}. Days with no free time are
    omitted from the range view (but a specifically requested date is always
    returned, even if empty, so the agent can say it's full).
    """
    names = WEEKDAY_NAMES_EN if lang == "en" else WEEKDAY_NAMES_SR
    today = date.today()
    now_hour = datetime.now().hour

    if on_date:
        try:
            d = date.fromisoformat(on_date.strip())
        except (ValueError, AttributeError):
            return {"error": "bad_date"}
        if d < today:
            return {"date": d.isoformat(), "weekday": names[d.weekday()],
                    "free_times": [], "note": "past_date"}
        return {"date": d.isoformat(), "weekday": names[d.weekday()],
                "free_times": _free_times_for(d, names, today, now_hour)}

    days_ahead = max(1, min(int(days_ahead or 7), 30))
    out = []
    for offset in range(0, days_ahead + 1):
        d = today + timedelta(days=offset)
        free = _free_times_for(d, names, today, now_hour)
        if free:
            out.append({"date": d.isoformat(), "weekday": names[d.weekday()], "free_times": free})
    return out


def get_popular_treatments(days_back=90, top=3):
    """Most-booked treatments over a recent window. Counts only — no client data."""
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    with database.get_conn() as conn:
        rows = conn.execute(
            "SELECT service_type, COUNT(*) AS c FROM reservations "
            "WHERE date >= ? GROUP BY service_type ORDER BY c DESC LIMIT ?",
            (cutoff, top),
        ).fetchall()
    return [{"treatment": r["service_type"], "bookings": r["c"]} for r in rows]


def get_promotions(lang="sr"):
    """Active promotions from promotions.json (owner-edited). Never invented by the model."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "promotions.json")
    try:
        with open(path, encoding="utf-8") as f:
            promos = json.load(f)
    except (FileNotFoundError, ValueError):
        return []
    today = date.today().isoformat()
    active = []
    for p in promos:
        if not p.get("active", True):
            continue
        if p.get("valid_until") and p["valid_until"] < today:
            continue
        active.append({
            "title": p.get("title", {}).get(lang) or p.get("title", {}).get("sr", ""),
            "description": p.get("description", {}).get(lang) or p.get("description", {}).get("sr", ""),
            "discount": p.get("discount", ""),
            "valid_until": p.get("valid_until", ""),
        })
    return active


def create_reservation(client_name, phone, service_type, date_str, time_str, lang="sr"):
    """Create a PENDING reservation after the visitor confirmed the details.

    Validates everything and refuses anything unsafe (past/invalid date, outside
    working hours, or a slot that's already taken) so the public chat can't create
    junk or double-bookings. Returns {"ok": True, ...} or {"ok": False, "error": ...}.
    """
    name = (client_name or "").strip()
    phone = (phone or "").strip()
    service = (service_type or "").strip()
    if not (name and phone and service and date_str and time_str):
        return {"ok": False, "error": "missing_fields"}

    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        return {"ok": False, "error": "bad_date"}
    today = date.today()
    if d < today:
        return {"ok": False, "error": "past_date"}

    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if not m:
        return {"ok": False, "error": "bad_time"}
    hh, mm = int(m.group(1)), int(m.group(2))
    if mm != 0 or hh not in _hours_for(d):
        return {"ok": False, "error": "outside_hours"}
    if d == today and hh <= datetime.now().hour:
        return {"ok": False, "error": "past_time"}

    time_norm = f"{hh:02d}:00"
    booked = {r["time"] for r in database.get_by_date(d.isoformat())}
    if time_norm in booked:
        return {"ok": False, "error": "slot_taken"}

    if len(re.sub(r"\D", "", phone)) < 6:
        return {"ok": False, "error": "bad_phone"}

    # Neutral source note (stays accurate whether pending or confirmed). The
    # pending/confirmed state is shown by the `status` column / badge, not here.
    note = ("🤖 Rezervacija preko sajta"
            if lang != "en" else "🤖 Booked online via website")
    try:
        database.add(name, phone, d.isoformat(), time_norm, service, note, status="pending")
    except TypeError:
        # Old database.py without a status param — mark pending in the note instead.
        database.add(name, phone, d.isoformat(), time_norm, service, note + " — NEPOTVRĐENO")
    names = WEEKDAY_NAMES_EN if lang == "en" else WEEKDAY_NAMES_SR
    return {"ok": True, "date": d.isoformat(), "time": time_norm, "weekday": names[d.weekday()]}


def get_treatments(category=None, lang="sr"):
    """The salon's treatment catalog (exactly what IM&Finity offers). No prices."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "treatments.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, ValueError):
        return []
    out = []
    for t in data:
        if category and category.lower() not in t.get("category", "").lower():
            continue
        desc = (t.get("opis") if lang != "en" else t.get("description_en")) or t.get("opis", "")
        entry = {"name": t.get("name", ""), "category": t.get("category", ""), "description": desc}
        if t.get("dostupne_zone_i_paketi"):
            entry["zones_and_packages"] = t["dostupne_zone_i_paketi"]
        out.append(entry)
    return out


# ── Claude tool definitions + dispatch ────────────────────────────────────────

TOOLS = [
    {
        "name": "get_free_slots",
        "description": "Get available appointment times, grouped by day. Two ways to use it: "
                       "pass `date` (YYYY-MM-DD) to check ONE specific day, or pass `days_ahead` to scan the "
                       "next N days. Use this for any availability question. If the visitor names a date "
                       "(e.g. '25.06'), convert it to YYYY-MM-DD using today's date and pass it as `date`. "
                       "For ranges like 'this week' or 'next 7 days', pass days_ahead. Only offer times this "
                       "tool returns in `free_times`; never invent availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "One specific day to check, as YYYY-MM-DD."},
                "days_ahead": {"type": "integer", "description": "Days ahead to scan when no specific date is given (default 7, max 30)."},
            },
        },
    },
    {
        "name": "get_popular_treatments",
        "description": "Get the most-booked treatments recently, as a popularity signal. "
                       "Use when the visitor asks what's popular, trending, or recommended.",
        "input_schema": {
            "type": "object",
            "properties": {
                "top": {"type": "integer", "description": "How many treatments to return (default 3)."},
            },
        },
    },
    {
        "name": "get_promotions",
        "description": "Get the salon's currently active promotions and discounts. "
                       "ALWAYS use this before mentioning any promotion, discount, or price — "
                       "never invent one.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_treatments",
        "description": "Get IM&Finity's treatment catalog — the exact treatments the salon offers, each "
                       "with a short description (no prices). Use this for ANY question about treatments: "
                       "what a treatment is, what it helps with, how it works, preparation/aftercare, what "
                       "the salon offers, or to recommend options for a goal. Optionally filter by category. "
                       "Only ever mention or recommend treatments returned by this tool.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Optional filter: 'Tretmani lica', 'Tretmani tela', 'Tretmani kose', or 'Laserska epilacija'."},
            },
        },
    },
    {
        "name": "create_reservation",
        "description": "Save a reservation REQUEST for the visitor. Call this ONLY after you have "
                       "collected the visitor's full name, phone number, the treatment they want, and a "
                       "specific free date and time (confirm availability with get_free_slots first), AND "
                       "the visitor has explicitly confirmed those details. The reservation is saved as "
                       "UNCONFIRMED for the salon to review and confirm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Visitor's full name"},
                "phone": {"type": "string", "description": "Visitor's phone number"},
                "service_type": {"type": "string", "description": "Desired treatment"},
                "date": {"type": "string", "description": "Date as YYYY-MM-DD"},
                "time": {"type": "string", "description": "Whole-hour time as HH:MM, e.g. 18:00"},
            },
            "required": ["client_name", "phone", "service_type", "date", "time"],
        },
    },
]


def _run_tool(name, tool_input, lang):
    if name == "get_free_slots":
        return get_free_slots(
            days_ahead=int(tool_input.get("days_ahead", 7) or 7),
            on_date=(tool_input.get("date") or None),
            lang=lang,
        )
    if name == "get_popular_treatments":
        return get_popular_treatments(top=int(tool_input.get("top", 3)))
    if name == "get_promotions":
        return get_promotions(lang=lang)
    if name == "get_treatments":
        return get_treatments(category=(tool_input.get("category") or None), lang=lang)
    if name == "create_reservation":
        return create_reservation(
            client_name=tool_input.get("client_name", ""),
            phone=tool_input.get("phone", ""),
            service_type=tool_input.get("service_type", ""),
            date_str=tool_input.get("date", ""),
            time_str=tool_input.get("time", ""),
            lang=lang,
        )
    return {"error": f"unknown tool: {name}"}


# ── System prompt ─────────────────────────────────────────────────────────────

def _system_prompt(lang):
    today = date.today()
    wd = WEEKDAY_NAMES_EN[today.weekday()]
    common = (
        f"Today's date is {today.isoformat()} ({wd}). Use it to resolve relative dates like "
        "'tomorrow' or 'this week', and to convert any date the visitor types (e.g. '25.06') into "
        "YYYY-MM-DD when calling tools.\n\n"
        "You are Jutrana, the warm virtual guide of IM&Finity, an aesthetic salon with two "
        "locations in Vranje and Surdulica, Serbia. You help website visitors discover treatments, "
        "learn about current promotions, and find available appointment times.\n\n"
        "Persona & voice:\n"
        "- You are female. When writing in Serbian, ALWAYS use feminine grammatical forms for yourself "
        "(e.g. 'ja sam Jutrana', 'rado bih vam pomogla', 'proverila sam', 'sačuvala sam vašu rezervaciju').\n"
        "- Be warm, cordial, genuinely caring and well-intentioned — like a kind, elegant host who is "
        "happy the visitor came by.\n"
        "- Speak politely and respectfully: in Serbian use the formal 'Vi' form (persiranje).\n"
        "- Now and then add a small, tasteful touch of light humor or warmth, but keep it gentle and "
        "classy — never crude, sarcastic, at the visitor's expense, or overdone. Most of the message "
        "should still be genuinely helpful.\n"
        "- You may occasionally add a single tasteful emoji (e.g. 😊) to warm up a message, but use them "
        "sparingly — not in every message, and never more than one at a time.\n"
        "- The chat already opens with a greeting where you introduce yourself by name, so do NOT "
        "re-introduce yourself or repeat 'Ja sam Jutrana' in your replies — simply continue helping, in "
        "character.\n\n"
        "Facts you can rely on:\n"
        "- Consultations are always free.\n"
        "- Phone: 063 304 700. Instagram: @imfinityaesthetics.\n"
        "- The salon offers 50+ treatments (laser hair removal, Tesla EMS body sculpting, "
        "IPL, mesotherapy, fillers, PRP, and more).\n\n"
        "Rules:\n"
        "- Use the tools to ground every answer about availability, popular treatments, and "
        "promotions. NEVER invent a promotion, discount, price, or free slot — if a tool returns "
        "nothing, say so honestly and offer a free consultation instead.\n"
        "- For ANY question about treatments — what a treatment is, what it helps with, how it works, how "
        "to prepare, aftercare, what the salon offers, or which treatment suits a goal — call "
        "get_treatments and answer based on that catalog plus accurate, modest general knowledge of the "
        "treatment. Recommend ONLY treatments in the catalog; never invent one the salon doesn't list. "
        "Do NOT quote prices — for prices and whether a treatment is right for someone, invite a free "
        "consultation or 063 304 700. Keep medical claims cautious; never promise specific medical results.\n"
        "- You CAN save a reservation request for the visitor. Booking has three steps, in strict order:\n"
        "  1) Collect all four details: full name, phone number, desired treatment, and a specific "
        "date+time. Use get_free_slots to offer only real open whole-hour times; never invent availability.\n"
        "  2) Show a short summary of those four details and ask the visitor to confirm.\n"
        "  3) The MOMENT the visitor confirms (e.g. says 'da', 'potvrđujem', 'može', 'ok', 'yes'), your "
        "VERY NEXT action MUST be to call the create_reservation tool exactly once, with the details from "
        "your summary. After a confirmation, do NOT call get_free_slots again and do NOT re-list times — "
        "the visitor already chose; calling anything other than create_reservation is an error.\n"
        "  After create_reservation returns ok, tell the visitor the request is saved and the salon will "
        "call their number to confirm (consultations are free). If it returns an error such as the slot "
        "being taken, apologize briefly and offer another free time. If the visitor would rather not book "
        "in chat, point them to the booking form on the page or 063 304 700.\n"
        "- Never share or imply any information about other clients. You only know aggregate "
        "popularity and which times are open.\n"
        "- Be warm, concise, and elegant — a few sentences, not an essay. Stay on the topic of "
        "the salon and its services; politely decline unrelated requests.\n"
    )
    if lang == "en":
        return common + "\nAlways reply in English."
    return common + "\nUvek odgovaraj na srpskom jeziku (latinica)."


# ── Anthropic call (defensive across SDK versions) ────────────────────────────

def _create_message(client, **kwargs):
    """Call messages.create, gracefully dropping params the SDK or model rejects.

    - Older SDKs raise TypeError on unknown kwargs (thinking / output_config).
    - Lighter models (e.g. Haiku) return a 400 like "adaptive thinking is not
      supported on this model" / "effort ... not supported".
    In both cases we retry once without the optional params so the agent works
    on any model.
    """
    import anthropic
    try:
        return client.messages.create(**kwargs)
    except TypeError:
        kwargs.pop("thinking", None)
        kwargs.pop("output_config", None)
        return client.messages.create(**kwargs)
    except anthropic.BadRequestError as e:
        msg = str(e).lower()
        if "thinking" in msg or "effort" in msg or "not supported" in msg:
            kwargs.pop("thinking", None)
            kwargs.pop("output_config", None)
            return client.messages.create(**kwargs)
        raise


def _ask_claude(history, lang):
    import anthropic  # imported here so the rest of the API works without the SDK installed
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    messages = [{"role": m["role"], "content": m["content"]} for m in history]

    for _ in range(5):  # cap the tool loop
        resp = _create_message(
            client,
            model=MODEL,
            max_tokens=1024,
            system=_system_prompt(lang),
            tools=TOOLS,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
        )

        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    result = _run_tool(block.name, block.input or {}, lang)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # final answer
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        return text or _fallback_text(lang)

    return _fallback_text(lang)


def _fallback_text(lang):
    if lang == "en":
        return ("I'm having trouble right now — please use the booking form on this page "
                "or call us on 063 304 700 and we'll be glad to help.")
    return ("Trenutno imam tehničkih poteškoća — molimo iskoristite formu za zakazivanje na "
            "ovoj stranici ili nas pozovite na 063 304 700. Rado ćemo pomoći.")


# ── HTTP endpoints ────────────────────────────────────────────────────────────

@agent_bp.after_request
def _cors(resp):
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


def _rate_limited(ip):
    now = time.time()
    hits = [t for t in _rate_log.get(ip, []) if now - t < RATE_LIMIT_WINDOW]
    if len(hits) >= RATE_LIMIT_MAX:
        _rate_log[ip] = hits
        return True
    hits.append(now)
    _rate_log[ip] = hits
    return False


@agent_bp.route("/api/agent/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)

    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    if _rate_limited(ip):
        return jsonify({"reply": _fallback_text("sr"), "error": "rate_limited"}), 429

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return jsonify({"reply": _fallback_text("sr"), "error": "no_api_key"}), 503

    data = request.get_json(silent=True) or {}
    lang = "en" if str(data.get("lang", "sr")).lower().startswith("en") else "sr"
    raw = data.get("messages", [])

    # sanitize history: keep last N, only user/assistant text, cap length
    history = []
    for m in raw[-MAX_HISTORY:]:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            history.append({"role": role, "content": content[:MAX_MSG_CHARS]})
    if not history or history[-1]["role"] != "user":
        return jsonify({"reply": _fallback_text(lang), "error": "bad_request"}), 400

    try:
        reply = _ask_claude(history, lang)
    except Exception as e:  # noqa: BLE001 — never 500 the public widget
        print("agent error:", repr(e))
        reply = _fallback_text(lang)
    return jsonify({"reply": reply})


# Lightweight JSON endpoints (no Claude — free to call, handy for testing and
# for building "dynamic page sections" later).

@agent_bp.route("/api/agent/availability", methods=["GET"])
def availability():
    lang = "en" if request.args.get("lang", "sr").lower().startswith("en") else "sr"
    return jsonify(get_free_slots(
        days_ahead=int(request.args.get("days", 7)),
        on_date=request.args.get("date") or None,
        lang=lang,
    ))


@agent_bp.route("/api/agent/popular", methods=["GET"])
def popular():
    return jsonify(get_popular_treatments(top=int(request.args.get("top", 3))))


@agent_bp.route("/api/agent/promotions", methods=["GET"])
def promotions():
    lang = "en" if request.args.get("lang", "sr").lower().startswith("en") else "sr"
    return jsonify(get_promotions(lang=lang))


@agent_bp.route("/api/agent/treatments", methods=["GET"])
def treatments():
    lang = "en" if request.args.get("lang", "sr").lower().startswith("en") else "sr"
    return jsonify(get_treatments(category=request.args.get("category") or None, lang=lang))
