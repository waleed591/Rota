"""Trading Journal section for Rota Tracker.

Drop this file next to your main app file. It adds one new page with its own
Postgres table (trading_journal), scoped to the logged-in user via user_id,
and uses the same cards, hero and styling helpers as the rest of the app.
No new dependencies (native Streamlit charts only).
"""
import calendar
import html
import io
import math
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

MOODS = ["Calm", "Confident", "Anxious", "Impulsive", "Revenge", "Bored", "Tired"]
FIELDS = ["trade_date", "symbol", "side", "entry_price", "exit_price", "qty", "stop_price", "fees",
          "multiplier", "setup", "mood", "rating", "tags", "notes"]
NUM = ["entry_price", "exit_price", "qty", "stop_price", "fees", "multiplier"]

# Imported by the main app: table definition and the columns included in backups.
SCHEMA = [
    """CREATE TABLE IF NOT EXISTS trading_journal (
          id SERIAL PRIMARY KEY, user_id INTEGER, trade_date DATE, symbol TEXT, side TEXT,
          entry_price DOUBLE PRECISION, exit_price DOUBLE PRECISION, qty DOUBLE PRECISION,
          stop_price DOUBLE PRECISION, fees DOUBLE PRECISION, multiplier DOUBLE PRECISION,
          setup TEXT, mood TEXT, rating INTEGER, tags TEXT, notes TEXT)""",
    "CREATE INDEX IF NOT EXISTS trading_journal_user_idx ON trading_journal (user_id)",
    """CREATE TABLE IF NOT EXISTS trading_journal_shots (
          id SERIAL PRIMARY KEY, user_id INTEGER, trade_id INTEGER, filename TEXT, mime TEXT,
          data BYTEA, created_at TIMESTAMP DEFAULT NOW())""",
    "CREATE INDEX IF NOT EXISTS trading_journal_shots_idx ON trading_journal_shots (user_id, trade_id)",
]
BACKUP_COLS = FIELDS


# ---------- calculations ----------
def calc_net(side, entry, exit_, qty, mult, fees):
    sign = 1 if side == "Long" else -1
    return (exit_ - entry) * sign * qty * mult - fees


def load_trades(a):
    df = a.query_df("SELECT * FROM trading_journal WHERE user_id = %s", (a.uid(),)).drop(columns=["user_id"], errors="ignore")
    if df.empty:
        return df
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    for c in NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(3).astype(int)
    for c in ["setup", "mood", "tags", "notes"]:
        df[c] = df[c].fillna("").astype(str)
    return df


def enrich(df):
    d = df.copy().sort_values(["trade_date", "id"]).reset_index(drop=True)
    sign = np.where(d["side"] == "Long", 1, -1)
    d["gross"] = (d["exit_price"] - d["entry_price"]) * sign * d["qty"] * d["multiplier"]
    d["net"] = d["gross"] - d["fees"]
    risk = (d["entry_price"] - d["stop_price"]).abs() * d["qty"] * d["multiplier"]
    d["r"] = np.where((d["stop_price"] > 0) & (risk > 0), d["net"] / risk.where(risk > 0, np.nan), np.nan)
    d["weekday"] = d["trade_date"].dt.day_name()
    return d


def streaks(net):
    best_w = best_l = cur_w = cur_l = 0
    for v in net:
        cur_w = cur_w + 1 if v > 0 else 0
        cur_l = cur_l + 1 if v < 0 else 0
        best_w, best_l = max(best_w, cur_w), max(best_l, cur_l)
    return best_w, best_l


def metrics(d, capital):
    wins, losses = d[d["net"] > 0], d[d["net"] < 0]
    gw, gl = float(wins["net"].sum()), float(-losses["net"].sum())
    eq = capital + d["net"].cumsum()
    peak = np.maximum(eq.cummax(), capital)
    dd = eq - peak
    wr = len(wins) / len(d)
    avg_w = float(wins["net"].mean()) if len(wins) else 0.0
    avg_l = float(losses["net"].mean()) if len(losses) else 0.0
    bw, bl = streaks(d["net"])
    return {
        "net": float(d["net"].sum()), "n": len(d), "win_rate": wr * 100, "avg_w": avg_w, "avg_l": avg_l,
        "pf": gw / gl if gl else (np.inf if gw else 0.0), "expectancy": wr * avg_w + (1 - wr) * avg_l,
        "avg_r": d["r"].mean(), "max_dd": float(dd.min()),
        "max_dd_pct": float((dd / peak.where(peak > 0, np.nan)).min() * 100),
        "best": float(d["net"].max()), "worst": float(d["net"].min()), "bw": bw, "bl": bl,
        "eq": eq.reset_index(drop=True), "dd": dd.reset_index(drop=True),
    }


def breakdown(d, col):
    g = d.groupby(col, dropna=False)
    out = pd.DataFrame({
        "Trades": g.size(),
        "Win rate %": g["net"].apply(lambda s: (s > 0).mean() * 100).round(1),
        "Net P&L": g["net"].sum().round(2),
        "Avg P&L": g["net"].mean().round(2),
        "Avg R": g["r"].mean().round(2),
    }).reset_index().rename(columns={col: "Group"})
    return out.sort_values("Net P&L", ascending=False)


# ---------- screenshots ----------
MAX_SHOTS = 8          # per trade
MAX_UPLOAD_MB = 10     # per image, before compression
IMG_TYPES = ["png", "jpg", "jpeg", "webp"]


def md_safe(s):
    return str(s or "").replace("$", "\\$")


def compress_image(data):
    """Shrink a screenshot to at most 1800px and store it as JPEG. Returns (bytes, mime) or (None, reason)."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im.load()
        im.thumbnail((1800, 1800))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, "JPEG", quality=85, optimize=True)
        return out.getvalue(), "image/jpeg"
    except Exception as e:
        return None, str(e)


def shot_counts(a):
    df = a.query_df("SELECT trade_id, COUNT(*) AS n FROM trading_journal_shots WHERE user_id = %s GROUP BY trade_id", (a.uid(),))
    return {int(t): int(n) for t, n in zip(df["trade_id"], df["n"])}


def load_shots(a, trade_id):
    df = a.query_df("SELECT id, filename, data FROM trading_journal_shots WHERE user_id = %s AND trade_id = %s ORDER BY id",
                    (a.uid(), int(trade_id)))
    return [{"id": int(r.id), "filename": r.filename or "", "data": bytes(r.data)} for r in df.itertuples()]


def save_shots(a, trade_id, files):
    """Compress and store uploaded images for a trade. Returns (number_saved, list_of_problems)."""
    import psycopg2
    have = shot_counts(a).get(int(trade_id), 0)
    saved, problems = 0, []
    for f in files or []:
        if have + saved >= MAX_SHOTS:
            problems.append(f"Limit of {MAX_SHOTS} screenshots per trade reached.")
            break
        raw = f.getvalue()
        if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
            problems.append(f"{f.name} is over {MAX_UPLOAD_MB} MB.")
            continue
        data, mime = compress_image(raw)
        if data is None:
            problems.append(f"{f.name} isn't a readable image.")
            continue
        a.run("INSERT INTO trading_journal_shots (user_id, trade_id, filename, mime, data) VALUES (%s,%s,%s,%s,%s)",
              (a.uid(), int(trade_id), f.name[:120], mime, psycopg2.Binary(data)))
        saved += 1
    return saved, problems


def _upload_cb(a, trade_id, key):
    ss = st.session_state
    saved, problems = save_shots(a, trade_id, ss.get(key))
    ss.tj_up_ver += 1
    if problems:
        ss.flash = ("warning", f"Saved {saved}. " + " ".join(problems))
    elif saved:
        ss.flash = ("success", f"Added {saved} screenshot(s).")
    else:
        ss.flash = ("info", "Choose at least one image first.")


def _delete_shot_cb(a, shot_id):
    a.run("DELETE FROM trading_journal_shots WHERE id = %s AND user_id = %s", (int(shot_id), a.uid()))
    st.session_state.flash = ("success", "Screenshot removed.")


def show_img(data, caption=None):
    try:
        st.image(data, caption=caption, width="stretch")
    except Exception:                      # older Streamlit versions
        st.image(data, caption=caption, use_container_width=True)


def render_trade(a, r, prefix):
    """One trade as a card: result, details, notes, screenshots, and a box to add more screenshots."""
    ss = st.session_state
    tid = int(r["id"])
    pnl = float(r["net"])
    tone = "green" if pnl >= 0 else "red"
    r_txt = f" · {r['r']:.2f}R" if pd.notna(r["r"]) else ""
    with st.container(border=True):
        h1, h2 = st.columns([3, 1])
        h1.markdown(f"**{r['trade_date']:%a %d %b %Y} · {md_safe(r['symbol'])}** · {r['side']}")
        h2.markdown(f":{tone}[**{a.gbp(pnl)}**]{r_txt}")
        stop_txt = f" · stop {r['stop_price']:g}" if r["stop_price"] > 0 else ""
        st.caption(f"Entry {r['entry_price']:g} → exit {r['exit_price']:g} · qty {r['qty']:g}{stop_txt} · fees {a.gbp(r['fees'])}")
        meta = [str(x) for x in (r["setup"], r["mood"], f"execution {int(r['rating'])}/5", r["tags"]) if x]
        st.caption(md_safe(" · ".join(meta)))
        if r["notes"]:
            st.markdown(md_safe(r["notes"]))
        shots = load_shots(a, tid)
        if shots:
            cols = st.columns(min(3, len(shots)))
            for i, s in enumerate(shots):
                with cols[i % 3]:
                    show_img(s["data"], s["filename"])
                    st.button("🗑️ Remove", key=f"{prefix}_rm_{s['id']}", on_click=_delete_shot_cb, args=(a, s["id"]))
        if len(shots) < MAX_SHOTS:
            with st.expander("➕ Add screenshots"):
                key = f"{prefix}_up_{tid}_{ss.tj_up_ver}"
                st.file_uploader("Images", type=IMG_TYPES, accept_multiple_files=True, key=key, label_visibility="collapsed")
                st.button("Upload", key=f"{prefix}_ub_{tid}", on_click=_upload_cb, args=(a, tid, key))


def render_calendar(a, df, counts):
    """Month calendar: each day shows its trades, the day's P&L and how many screenshots it has."""
    c1, c2 = st.columns(2)
    year = int(c1.number_input("Year", min_value=2020, max_value=2100, value=a.today.year, step=1, key="tj_cal_year"))
    month = c2.selectbox("Month", list(range(1, 13)), index=a.today.month - 1,
                         format_func=lambda m: calendar.month_name[m], key="tj_cal_month")
    sub = df[(df["trade_date"].dt.year == year) & (df["trade_date"].dt.month == month)]
    by_day = {d: g for d, g in sub.groupby(sub["trade_date"].dt.date)}
    sign = lambda v: ("+" if v > 0 else "") + a.gbp(v)

    cells = [f'<div class="cal-h">{h}</div>' for h in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
    for week in calendar.monthcalendar(year, month):
        for dn in week:
            if dn == 0:
                cells.append('<div class="cal-d empty"></div>')
                continue
            dd = date(year, month, dn)
            g = by_day.get(dd)
            style, inner = "", f'<div class="cal-n">{dn}</div>'
            if g is not None:
                net = float(g["net"].sum())
                style = f' style="background:{"rgba(16,185,129,.20)" if net >= 0 else "rgba(239,68,68,.20)"}"'
                for _, t in g.head(3).iterrows():
                    v = float(t["net"])
                    inner += (f'<span class="chip" style="background:{"#10b981" if v >= 0 else "#ef4444"}">'
                              f'{html.escape(str(t["symbol"]))} {sign(v)}</span>')
                if len(g) > 3:
                    inner += f'<div class="cal-t">+{len(g) - 3} more</div>'
                n_shots = sum(counts.get(int(i), 0) for i in g["id"])
                inner += f'<div class="cal-t">{sign(net)}' + (f" · 📷 {n_shots}" if n_shots else "") + "</div>"
            cells.append(f'<div class="cal-d{" today" if dd == a.today else ""}"{style}>{inner}</div>')
    st.markdown('<div class="cal-wrap"><div class="cal">' + "".join(cells) + "</div></div>", unsafe_allow_html=True)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    if sub.empty:
        st.info("No trades in this month.")
        return
    day_net = sub.groupby(sub["trade_date"].dt.date)["net"].sum()
    k = st.columns(4)
    with k[0]: a.card("Month P&L", a.gbp(sub["net"].sum()), f"{len(sub)} trade(s)", "green" if sub["net"].sum() >= 0 else "red")
    with k[1]: a.card("Green / red days", f"{int((day_net > 0).sum())} / {int((day_net < 0).sum())}", f"{len(day_net)} trading day(s)", "indigo")
    with k[2]: a.card("Best day", a.gbp(day_net.max()), f"{day_net.idxmax():%a %d %b}", "green")
    with k[3]: a.card("Worst day", a.gbp(day_net.min()), f"{day_net.idxmin():%a %d %b}", "red")

    days = sorted(by_day)
    st.subheader("Open a day")
    pick = st.selectbox("Day", days, index=len(days) - 1, key=f"tj_cal_day_{year}_{month}", label_visibility="collapsed",
                        format_func=lambda d: f"{d:%a %d %b} · {sign(float(by_day[d]['net'].sum()))} · {len(by_day[d])} trade(s)")
    for _, r in by_day[pick].iterrows():
        render_trade(a, r, "cal")


def render_history(a, df, counts):
    """Searchable trade history with screenshots, newest first, paged."""
    h1, h2, h3, h4 = st.columns([2, 1, 1, 1])
    q = h1.text_input("Search symbol, setup, tags or notes", key="tj_h_q")
    only = h2.checkbox("Only with screenshots", key="tj_h_only")
    order = h3.selectbox("Sort", ["Newest first", "Oldest first", "Best P&L", "Worst P&L"], key="tj_h_sort")
    per = h4.selectbox("Per page", [5, 10, 20], index=1, key="tj_h_per")
    v = df.copy()
    v["shots"] = v["id"].map(counts).fillna(0).astype(int)
    if q.strip():
        mask = False
        for c in ("symbol", "setup", "tags", "notes"):
            mask = mask | v[c].str.contains(q.strip(), case=False, regex=False)
        v = v[mask]
    if only:
        v = v[v["shots"] > 0]
    if v.empty:
        st.info("No trades match your search.")
        return
    by = {"Newest first": ("trade_date", False), "Oldest first": ("trade_date", True),
          "Best P&L": ("net", False), "Worst P&L": ("net", True)}[order]
    v = v.sort_values([by[0], "id"], ascending=[by[1], by[1]])
    pages = max(1, math.ceil(len(v) / per))
    page = 1
    if pages > 1:
        page = int(st.number_input("Page", min_value=1, max_value=pages, value=1, step=1, key=f"tj_h_page_{pages}_{per}"))
    st.caption(f"{len(v)} trade(s) · page {page} of {pages}")
    for _, r in v.iloc[(page - 1) * per: page * per].iterrows():
        render_trade(a, r, "hist")


# ---------- the page ----------
def render(a):
    """`a` is a namespace of helpers from the main app (uid, run, query_df, hero, card, show_table,
    gbp, show_flash, today, settings, save_setting, to_excel_bytes)."""
    ss = st.session_state
    a.hero("📈 Trading Journal", "Log every trade, track your edge and spot the habits that cost you money.")
    a.show_flash()

    capital = float(a.settings.get("tj_capital", 10000.0))
    with st.expander("⚙️ Journal settings"):
        new_cap = st.number_input("Starting capital (£)", min_value=0.0, value=capital, step=500.0, format="%.2f", key="tj_cap_in")
        if st.button("Save starting capital"):
            a.save_setting("tj_capital", new_cap)
            ss.flash = ("success", "Starting capital saved.")
            st.rerun()

    raw = load_trades(a)
    ss.setdefault("tj_ver", 0)
    ss.setdefault("tj_up_ver", 0)
    # clean up screenshots whose trade no longer exists (for example after restoring a backup)
    a.run("DELETE FROM trading_journal_shots WHERE user_id = %s AND trade_id NOT IN "
          "(SELECT id FROM trading_journal WHERE user_id = %s)", (a.uid(), a.uid()))
    counts = shot_counts(a)

    # ----- filters (apply to Dashboard and Analytics) -----
    df = pd.DataFrame()
    if not raw.empty:
        full = enrich(raw)
        with st.expander("🔎 Filters (Dashboard, Calendar, History & Analytics)"):
            lo, hi = full["trade_date"].min().date(), max(a.today, full["trade_date"].max().date())
            rng = st.date_input("Date range", value=(lo, hi), min_value=lo, max_value=hi, key="tj_rng")
            f1, f2, f3, f4 = st.columns(4)
            syms = f1.multiselect("Symbols", sorted(full["symbol"].unique()), key="tj_f_sym")
            setups = f2.multiselect("Setups", sorted(s for s in full["setup"].unique() if s), key="tj_f_setup")
            moods = f3.multiselect("Mood", sorted(full["mood"].unique()), key="tj_f_mood")
            side_f = f4.radio("Side", ["Both", "Long", "Short"], horizontal=True, key="tj_f_side")
        df = full
        if isinstance(rng, (tuple, list)) and len(rng) == 2:
            df = df[(df["trade_date"].dt.date >= rng[0]) & (df["trade_date"].dt.date <= rng[1])]
        if syms:
            df = df[df["symbol"].isin(syms)]
        if setups:
            df = df[df["setup"].isin(setups)]
        if moods:
            df = df[df["mood"].isin(moods)]
        if side_f != "Both":
            df = df[df["side"] == side_f]
        df = df.reset_index(drop=True)

    t_dash, t_cal, t_log, t_hist, t_trades, t_an, t_io = st.tabs(
        ["📊 Dashboard", "📅 Calendar", "➕ Log trade", "🖼️ History", "🧾 Edit trades", "🔬 Analytics", "📥 Import & export"])

    # ================= dashboard =================
    with t_dash:
        if raw.empty:
            st.info("No trades yet. Log your first one in the **Log trade** tab.")
        elif df.empty:
            st.warning("No trades match these filters.")
        else:
            m = metrics(df, capital)
            ret = m["net"] / capital * 100 if capital else 0.0
            c = st.columns(5)
            with c[0]: a.card("Net P&L", a.gbp(m["net"]), f"{ret:.1f}% of capital" if capital else "", "green" if m["net"] >= 0 else "red")
            with c[1]: a.card("Win rate", f"{m['win_rate']:.0f}%", f"{m['n']} trades", "indigo")
            with c[2]: a.card("Profit factor", "∞" if np.isinf(m["pf"]) else f"{m['pf']:.2f}", "gross wins ÷ gross losses", "teal")
            with c[3]: a.card("Expectancy", a.gbp(m["expectancy"]), "average per trade", "green" if m["expectancy"] >= 0 else "red")
            with c[4]: a.card("Max drawdown", a.gbp(m["max_dd"]), f"{m['max_dd_pct']:.1f}% from peak", "red")
            c = st.columns(5)
            with c[0]: a.card("Avg win", a.gbp(m["avg_w"]), "", "green")
            with c[1]: a.card("Avg loss", a.gbp(m["avg_l"]), "", "red")
            with c[2]: a.card("Avg R", "–" if np.isnan(m["avg_r"]) else f"{m['avg_r']:.2f}R", "needs a stop price", "indigo")
            with c[3]: a.card("Best / worst", f"{a.gbp(m['best'])} / {a.gbp(m['worst'])}", "single trades", "amber")
            with c[4]: a.card("Longest streaks", f"{m['bw']}W / {m['bl']}L", "wins / losses in a row", "slate")

            st.markdown("---")
            st.subheader("Equity curve")
            st.caption("Account value after each trade (starting capital + cumulative P&L)")
            st.line_chart(pd.DataFrame({"Equity": m["eq"].values}, index=range(1, len(df) + 1)), color="#6366f1")
            d1, d2 = st.columns(2)
            with d1:
                st.subheader("Drawdown")
                st.area_chart(pd.DataFrame({"Drawdown": m["dd"].values}, index=range(1, len(df) + 1)), color="#ef4444")
            with d2:
                st.subheader("Daily P&L")
                day = df.groupby(df["trade_date"].dt.date)["net"].sum()
                st.bar_chart(pd.DataFrame({"Profit": day.clip(lower=0), "Loss": day.clip(upper=0)}),
                             color=["#10b981", "#ef4444"])

    # ================= calendar =================
    with t_cal:
        if raw.empty:
            st.info("No trades yet. Log your first one in the **Log trade** tab.")
        elif df.empty:
            st.warning("No trades match these filters.")
        else:
            render_calendar(a, df, counts)

    # ================= history with screenshots =================
    with t_hist:
        if raw.empty:
            st.info("No trades yet. Log your first one in the **Log trade** tab.")
        elif df.empty:
            st.warning("No trades match these filters.")
        else:
            render_history(a, df, counts)

    # ================= log a trade =================
    with t_log:
        defaults = {"tj_side": "Long", "tj_qty": 100.0, "tj_mult": 1.0, "tj_fees": 0.0, "tj_entry": 0.0,
                    "tj_exit": 0.0, "tj_stop": 0.0, "tj_symbol": "", "tj_setup": "", "tj_tags": "",
                    "tj_notes": "", "tj_mood": MOODS[0], "tj_rating": 3}
        for k, v in defaults.items():
            ss.setdefault(k, v)

        def save_trade():
            sym = (ss.tj_symbol or "").strip().upper()
            if not sym or ss.tj_entry <= 0 or ss.tj_exit <= 0 or ss.tj_qty <= 0:
                ss.flash = ("error", "Symbol, entry price, exit price and quantity are required.")
                return
            pnl = calc_net(ss.tj_side, ss.tj_entry, ss.tj_exit, ss.tj_qty, ss.tj_mult, ss.tj_fees)
            new = a.query_df(f"INSERT INTO trading_journal (user_id, {', '.join(FIELDS)}) VALUES (%s, {', '.join(['%s'] * len(FIELDS))}) RETURNING id",
                  (a.uid(), ss.tj_date, sym, ss.tj_side, float(ss.tj_entry), float(ss.tj_exit), float(ss.tj_qty),
                   float(ss.tj_stop), float(ss.tj_fees), float(ss.tj_mult), (ss.tj_setup or "").strip(),
                   ss.tj_mood, int(ss.tj_rating), (ss.tj_tags or "").strip(), (ss.tj_notes or "").strip()))
            saved, problems = save_shots(a, int(new["id"].iloc[0]), ss.get(f"tj_shots_{ss.tj_up_ver}"))
            ss.tj_up_ver += 1
            for k in ("tj_symbol", "tj_setup", "tj_tags", "tj_notes"):
                ss[k] = ""
            for k in ("tj_entry", "tj_exit", "tj_stop", "tj_fees"):
                ss[k] = 0.0
            shots_txt = f" with {saved} screenshot(s)" if saved else ""
            ss.flash = ("warning" if problems else "success",
                        f"Trade saved{shots_txt}: {sym} {ss.tj_side.lower()}, P&L {a.gbp(pnl)}." + (" " + " ".join(problems) if problems else ""))

        l1, l2 = st.columns(2, gap="large")
        with l1:
            st.subheader("🗓️ The trade")
            st.date_input("Date", value=a.today, key="tj_date")
            st.text_input("Symbol", placeholder="e.g. AAPL, EURUSD, ES", key="tj_symbol")
            x1, x2 = st.columns(2)
            x1.selectbox("Side", ["Long", "Short"], key="tj_side")
            x2.number_input("Quantity", min_value=0.0, step=1.0, format="%.2f", key="tj_qty")
            p1, p2, p3 = st.columns(3)
            p1.number_input("Entry price", min_value=0.0, format="%.4f", key="tj_entry")
            p2.number_input("Exit price", min_value=0.0, format="%.4f", key="tj_exit")
            p3.number_input("Stop loss (0 = none)", min_value=0.0, format="%.4f", key="tj_stop",
                            help="Used to work out your R-multiple (profit as a multiple of what you risked).")
            q1, q2 = st.columns(2)
            q1.number_input("Fees (£)", min_value=0.0, step=0.5, format="%.2f", key="tj_fees")
            q2.number_input("Contract multiplier", min_value=0.0, step=1.0, key="tj_mult",
                            help="1 for shares and spot FX, 50 for ES futures, 100 for options.")
        with l2:
            st.subheader("🧠 Context")
            st.text_input("Setup", placeholder="Breakout, pullback, gap fill…", key="tj_setup")
            y1, y2 = st.columns(2)
            y1.selectbox("Mood", MOODS, key="tj_mood")
            y2.slider("Execution quality", 1, 5, key="tj_rating", help="How well did you follow your plan, win or lose?")
            st.text_input("Tags (comma separated)", placeholder="earnings, news, london-open", key="tj_tags")
            st.text_area("Notes: what happened, what would you change?", height=120, key="tj_notes")
            st.file_uploader(f"Screenshots (optional, up to {MAX_SHOTS})", type=IMG_TYPES, accept_multiple_files=True,
                             key=f"tj_shots_{ss.tj_up_ver}", help="Chart before entry, the exit, your platform's trade summary…")

        pnl = calc_net(ss.tj_side, ss.tj_entry, ss.tj_exit, ss.tj_qty, ss.tj_mult, ss.tj_fees)
        risk = abs(ss.tj_entry - ss.tj_stop) * ss.tj_qty * ss.tj_mult if ss.tj_stop > 0 else 0.0
        st.markdown("---")
        st.subheader("🔎 Live preview")
        pv = st.columns(4)
        with pv[0]: a.card("Net P&L", a.gbp(pnl), "after fees", "green" if pnl >= 0 else "red")
        with pv[1]: a.card("R multiple", f"{pnl / risk:.2f}R" if risk > 0 else "–", "needs a stop price", "indigo")
        with pv[2]: a.card("Risk at stop", a.gbp(risk) if risk > 0 else "–", "", "amber")
        with pv[3]: a.card("Fees", a.gbp(ss.tj_fees), "", "slate")
        st.button("💾 Save trade", type="primary", on_click=save_trade)

    # ================= trades table (edit / delete) =================
    with t_trades:
        if raw.empty:
            st.info("Nothing logged yet.")
        else:
            view = enrich(raw).sort_values(["trade_date", "id"], ascending=[False, False]).copy()
            view["trade_date"] = view["trade_date"].dt.date
            view.insert(0, "Delete", False)
            view["shots"] = view["id"].map(counts).fillna(0).astype(int)
            view = view[["Delete", "id"] + FIELDS + ["net", "shots"]]
            extra = sorted(set(view["mood"]) - set(MOODS) - {""})
            st.caption("Edit any cell, tick **Delete** to remove rows, then press **Save changes**. "
                       "This table always shows all of your trades, regardless of the filters.")
            edited = st.data_editor(
                view, hide_index=True, key=f"tj_editor_{ss.tj_ver}", disabled=["id", "net", "shots"],
                column_config={
                    "Delete": st.column_config.CheckboxColumn("Delete"), "id": None,
                    "trade_date": st.column_config.DateColumn("Date", format="DD MMM YYYY", required=True),
                    "symbol": st.column_config.TextColumn("Symbol", required=True),
                    "side": st.column_config.SelectboxColumn("Side", options=["Long", "Short"], required=True),
                    "entry_price": st.column_config.NumberColumn("Entry", format="%.4f", min_value=0.0),
                    "exit_price": st.column_config.NumberColumn("Exit", format="%.4f", min_value=0.0),
                    "qty": st.column_config.NumberColumn("Qty", min_value=0.0),
                    "stop_price": st.column_config.NumberColumn("Stop", format="%.4f", min_value=0.0),
                    "fees": st.column_config.NumberColumn("Fees (£)", format="%.2f", min_value=0.0),
                    "multiplier": st.column_config.NumberColumn("Mult.", min_value=0.0),
                    "mood": st.column_config.SelectboxColumn("Mood", options=MOODS + extra),
                    "rating": st.column_config.NumberColumn("Quality", min_value=1, max_value=5, step=1),
                    "net": st.column_config.NumberColumn("Net P&L (£)", format="%.2f"),
                    "shots": st.column_config.NumberColumn("📷", format="%d")})
            if st.button("💾 Save changes", type="primary", key="tj_save_edits"):
                orig = view.set_index("id")
                n_upd = n_del = n_bad = 0
                for _, r in edited.iterrows():
                    rid = int(r["id"])
                    if r["Delete"]:
                        a.run("DELETE FROM trading_journal_shots WHERE trade_id = %s AND user_id = %s", (rid, a.uid()))
                        a.run("DELETE FROM trading_journal WHERE id = %s AND user_id = %s", (rid, a.uid()))
                        n_del += 1
                        continue
                    sym = str(r["symbol"] or "").strip().upper()
                    nums_ok = all(pd.notna(r[c]) for c in NUM) and r["entry_price"] > 0 and r["exit_price"] > 0 and r["qty"] > 0
                    if pd.isna(r["trade_date"]) or not sym or r["side"] not in ("Long", "Short") or not nums_ok:
                        n_bad += 1
                        continue
                    new = [pd.to_datetime(r["trade_date"]).date(), sym, r["side"]] + [float(r[c]) for c in NUM] + [
                        str(r["setup"] or "").strip(), str(r["mood"] or ""), int(r["rating"]) if pd.notna(r["rating"]) else 3,
                        str(r["tags"] or "").strip(), str(r["notes"] or "").strip()]
                    # NUM columns sit in a different order than FIELDS, so rebuild in FIELDS order
                    vals = dict(zip(["trade_date", "symbol", "side"] + NUM + ["setup", "mood", "rating", "tags", "notes"], new))
                    o = orig.loc[rid]
                    changed = any((str(vals[f]) != str(o[f])) if f in ("trade_date", "symbol", "side", "setup", "mood", "tags", "notes")
                                  else round(float(vals[f]), 6) != round(float(o[f]), 6) for f in FIELDS)
                    if changed:
                        a.run(f"UPDATE trading_journal SET {', '.join(f'{f} = %s' for f in FIELDS)} WHERE id = %s AND user_id = %s",
                              [vals[f] for f in FIELDS] + [rid, a.uid()])
                        n_upd += 1
                ss.tj_ver += 1
                msg = f"Saved: {n_upd} updated, {n_del} deleted."
                ss.flash = ("warning", msg + f" {n_bad} row(s) skipped (check date, symbol, side, prices and quantity).") if n_bad else ("success", msg)
                st.rerun()

    # ================= analytics =================
    with t_an:
        if df.empty:
            st.info("Log some trades (and check your filters) to see analytics.")
        else:
            by = st.selectbox("Break down by", ["setup", "mood", "symbol", "weekday", "side", "rating", "tags"], key="tj_by")
            src = df.copy()
            if by == "tags":
                src["tags"] = src["tags"].str.split(",")
                src = src.explode("tags")
                src["tags"] = src["tags"].str.strip().replace("", "(none)")
            elif by in ("setup", "mood"):
                src[by] = src[by].replace("", "(none)")
            tbl = breakdown(src, by)
            a.show_table(tbl, {"Net P&L": st.column_config.NumberColumn("Net P&L (£)", format="%.2f"),
                               "Avg P&L": st.column_config.NumberColumn("Avg P&L (£)", format="%.2f"),
                               "Win rate %": st.column_config.NumberColumn("Win rate %", format="%.1f"),
                               "Avg R": st.column_config.NumberColumn("Avg R", format="%.2f")})
            st.caption("Net P&L per group. Look for the moods and setups that cost you money.")
            st.bar_chart(tbl.set_index("Group")["Net P&L"].astype(float), color="#6366f1")

            r = df["r"].dropna()
            if len(r) >= 2:
                st.subheader("R-multiple distribution")
                counts, edges = np.histogram(r, bins=min(12, max(4, len(r) // 3)))
                labels = [f"{edges[i]:.1f} to {edges[i + 1]:.1f}" for i in range(len(counts))]
                st.bar_chart(pd.Series(counts, index=labels, name="Trades"), color="#14b8a6")
            else:
                st.caption("Add stop prices to trades to unlock R-multiple analysis.")

            st.subheader("P&L by month")
            mon = df.groupby(df["trade_date"].dt.to_period("M"))["net"].sum()
            mon.index = mon.index.strftime("%Y-%m")
            st.bar_chart(pd.DataFrame({"Profit": mon.clip(lower=0), "Loss": mon.clip(upper=0)}), color=["#10b981", "#ef4444"])

    # ================= import / export =================
    with t_io:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("#### Export")
            if raw.empty:
                st.caption("Nothing to export yet.")
            else:
                out = enrich(raw).drop(columns=["weekday"])
                out["trade_date"] = out["trade_date"].dt.date
                st.download_button("📄 Download CSV", out.to_csv(index=False).encode(), f"trading_journal_{a.today:%Y%m%d}.csv", "text/csv")
                xl = a.to_excel_bytes({"Trades": out})
                if xl:
                    st.download_button("📗 Download Excel", xl, f"trading_journal_{a.today:%Y%m%d}.xlsx",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with c2:
            st.markdown("#### Import from CSV (adds to existing trades)")
            st.caption("Required: `trade_date`, `symbol`, `side` (Long/Short or Buy/Sell), `entry_price`, `exit_price`, `qty`. "
                       "Optional: `stop_price`, `fees`, `multiplier`, `setup`, `mood`, `rating`, `tags`, `notes`. Dates are read day-first.")
            sample = pd.DataFrame([{"trade_date": "31/10/2026", "symbol": "AAPL", "side": "Long", "entry_price": 180.5,
                                    "exit_price": 184.2, "qty": 50, "stop_price": 178.0, "fees": 1.0, "setup": "Breakout",
                                    "mood": "Calm", "rating": 4, "tags": "earnings", "notes": ""}])
            st.download_button("Download sample CSV", sample.to_csv(index=False).encode(), "trades_sample.csv", "text/csv")
            up = st.file_uploader("Trades CSV", type="csv", key="tj_import")
            if up:
                try:
                    imp = pd.read_csv(up)
                    imp.columns = [c.strip().lower() for c in imp.columns]
                    need = ["trade_date", "symbol", "side", "entry_price", "exit_price", "qty"]
                    missing = [c for c in need if c not in imp.columns]
                    if missing:
                        st.error(f"Missing column(s): {', '.join(missing)}")
                    else:
                        imp["_date"] = pd.to_datetime(imp["trade_date"], dayfirst=True, errors="coerce")
                        imp["side"] = imp["side"].astype(str).str.strip().str.lower().map(
                            {"long": "Long", "buy": "Long", "short": "Short", "sell": "Short"})
                        for c in ["entry_price", "exit_price", "qty"]:
                            imp[c] = pd.to_numeric(imp[c], errors="coerce")
                        ok = imp["_date"].notna() & imp["side"].notna() & imp["symbol"].notna() & \
                            (imp["entry_price"] > 0) & (imp["exit_price"] > 0) & (imp["qty"] > 0)
                        good = imp[ok]
                        st.write(f"**{len(good)}** valid row(s), **{int((~ok).sum())}** skipped.")
                        a.show_table(good.drop(columns=["_date"]).head(20))
                        if len(good) and st.button(f"Import {len(good)} trade(s)", type="primary", key="tj_do_import"):
                            def num(r, c, d=0.0):
                                return float(r[c]) if c in imp.columns and pd.notna(r[c]) else d
                            def txt(r, c, d=""):
                                return str(r[c]).strip() if c in imp.columns and pd.notna(r[c]) else d
                            for _, r in good.iterrows():
                                a.run(f"INSERT INTO trading_journal (user_id, {', '.join(FIELDS)}) VALUES (%s, {', '.join(['%s'] * len(FIELDS))})",
                                      (a.uid(), r["_date"].date(), str(r["symbol"]).strip().upper(), r["side"],
                                       float(r["entry_price"]), float(r["exit_price"]), float(r["qty"]),
                                       num(r, "stop_price"), num(r, "fees"), num(r, "multiplier", 1.0) or 1.0,
                                       txt(r, "setup"), txt(r, "mood", MOODS[0]) or MOODS[0],
                                       int(num(r, "rating", 3)) or 3, txt(r, "tags"), txt(r, "notes")))
                            ss.flash = ("success", f"Imported {len(good)} trade(s).")
                            st.rerun()
                except Exception as e:
                    st.error(f"Could not read the CSV: {e}")

        if not raw.empty:
            def wipe():
                if ss.get("tj_wipe_ok"):
                    a.run("DELETE FROM trading_journal_shots WHERE user_id = %s", (a.uid(),))
                    a.run("DELETE FROM trading_journal WHERE user_id = %s", (a.uid(),))
                    ss.tj_wipe_ok = False
                    ss.flash = ("success", "All journal trades deleted.")
                else:
                    ss.flash = ("error", "Tick the confirmation box first.")
            with st.expander("⚠️ Delete all my journal trades"):
                st.checkbox("Yes, delete every trade in my journal permanently", key="tj_wipe_ok")
                st.button("Delete all trades", on_click=wipe)
