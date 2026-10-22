import base64
import calendar
import hashlib
import hmac
import html
import io
import os
import secrets as pysecrets
import struct
import time as time_mod
import zipfile
from datetime import date, datetime, time, timedelta

import pandas as pd
import psycopg2
import streamlit as st

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(page_title="Rota Earnings Tracker", page_icon="💷", layout="wide")

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp, .stApp :is(h1,h2,h3,h4,p,label,input,textarea,button,li,td,th) {
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
}
.stApp {
    background:
        radial-gradient(1100px 560px at 8% -10%, rgba(99,102,241,.16), transparent 60%),
        radial-gradient(900px 500px at 100% 0%, rgba(20,184,166,.13), transparent 55%);
}
.block-container { padding-top: 2.2rem; max-width: 1250px; }
#MainMenu, footer, [data-testid="stToolbar"], .stAppDeployButton,
[data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }

.hero { padding: 26px 30px; border-radius: 20px; margin-bottom: 22px; color: #fff;
    background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 55%, #0ea5e9 100%);
    box-shadow: 0 12px 32px rgba(79,70,229,.35); }
.hero-title { font-size: 1.9rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.2; }
.hero-sub { opacity: .88; margin-top: 4px; font-size: .98rem; }

.card { position: relative; overflow: hidden; height: 100%; padding: 16px 18px 14px 22px; margin-bottom: 12px;
    border-radius: 16px; border: 1px solid rgba(128,128,128,.22); background: rgba(128,128,128,.07);
    box-shadow: 0 4px 18px rgba(0,0,0,.06); transition: transform .15s ease, box-shadow .15s ease; }
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.10); }
.card::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 6px; background: var(--accent); }
.card.indigo { --accent: linear-gradient(180deg,#6366f1,#8b5cf6); }
.card.green  { --accent: linear-gradient(180deg,#10b981,#34d399); }
.card.red    { --accent: linear-gradient(180deg,#ef4444,#f97316); }
.card.amber  { --accent: linear-gradient(180deg,#f59e0b,#fbbf24); }
.card.teal   { --accent: linear-gradient(180deg,#14b8a6,#0ea5e9); }
.card.slate  { --accent: linear-gradient(180deg,#64748b,#94a3b8); }
.card-label { font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; opacity: .7; font-weight: 600; }
.card-value { font-size: 1.65rem; font-weight: 800; line-height: 1.25; margin-top: 4px; }
.card-sub   { font-size: .78rem; opacity: .65; margin-top: 2px; }

.bar { height: 12px; border-radius: 99px; background: rgba(128,128,128,.22); overflow: hidden; margin: 8px 0 4px; }
.bar > div { height: 100%; border-radius: 99px; background: linear-gradient(90deg,#6366f1,#14b8a6); }
.bar.done > div { background: linear-gradient(90deg,#10b981,#34d399); }

.balance { padding: 22px 28px; border-radius: 20px; color: #fff; margin: 6px 0 18px 0; display: flex;
    justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; box-shadow: 0 12px 30px rgba(0,0,0,.18); }
.balance.owed { background: linear-gradient(120deg,#059669,#10b981 60%,#2dd4bf); }
.balance.owe  { background: linear-gradient(120deg,#dc2626,#f97316); }
.balance .b-label { font-size: .8rem; text-transform: uppercase; letter-spacing: .1em; opacity: .9; font-weight: 600; }
.balance .b-value { font-size: 2.3rem; font-weight: 800; letter-spacing: -.02em; }

.cal-wrap { overflow-x: auto; }
.cal { display: grid; grid-template-columns: repeat(7, minmax(0,1fr)); gap: 6px; min-width: 720px; }
.cal-h { text-align: center; font-weight: 700; font-size: .78rem; opacity: .7; padding: 4px 0; }
.cal-d { min-height: 98px; padding: 6px 7px; border-radius: 12px; font-size: .72rem;
    border: 1px solid rgba(128,128,128,.2); background: rgba(128,128,128,.06); }
.cal-d.empty { background: transparent; border-color: transparent; }
.cal-d.today { border: 2px solid #6366f1; }
.cal-n { font-weight: 700; font-size: .8rem; opacity: .8; }
.chip { display: block; margin-top: 3px; padding: 2px 6px; border-radius: 7px; color: #fff; font-weight: 600;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; background: #64748b; }
.chip.GOGO { background: #6366f1; } .chip.CHINESE { background: #ef4444; } .chip.DANIELLE { background: #14b8a6; }
.cal-t { margin-top: 4px; font-weight: 700; opacity: .75; }

[data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,.2); }
.brand { font-size: 1.3rem; font-weight: 800; padding: 6px 0 14px 0; letter-spacing: -.01em; }
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] { border-radius: 12px !important; }
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"],
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background: linear-gradient(120deg,#4f46e5,#7c3aed) !important; border: none !important; color: #fff !important;
    font-weight: 600; border-radius: 12px !important; padding: .55rem 1.3rem; box-shadow: 0 6px 18px rgba(79,70,229,.35); }
button[data-testid^="stBaseButton-secondary"] { border-radius: 12px !important; font-weight: 600; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: 8px 18px; font-weight: 600; }
[data-testid="stExpander"] { border-radius: 14px; border: 1px solid rgba(128,128,128,.25); background: rgba(128,128,128,.05); }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid rgba(128,128,128,.2); }
h2, h3 { letter-spacing: -.01em; font-weight: 700 !important; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)


# ==========================================================
# GENERIC HELPERS
# ==========================================================
def today_uk():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/London")).date()
    except Exception:
        return date.today()


TODAY = today_uk()
EMPLOYERS = ["GOGO", "CHINESE", "DANIELLE"]


def gbp(x):
    x = float(x or 0)
    return f"-£{abs(x):,.2f}" if x < 0 else f"£{x:,.2f}"


def hero(title, subtitle=""):
    st.markdown(f'<div class="hero"><div class="hero-title">{title}</div>'
                f'<div class="hero-sub">{subtitle}</div></div>', unsafe_allow_html=True)


def card(label, value, sub="", tone="indigo"):
    st.markdown(f'<div class="card {tone}"><div class="card-label">{label}</div>'
                f'<div class="card-value">{value}</div><div class="card-sub">{sub}</div></div>',
                unsafe_allow_html=True)


def progress_card(label, value, target, tone="indigo"):
    pct = min(100.0, value / target * 100) if target > 0 else 0.0
    done = "done" if target > 0 and value >= target else ""
    sub = f"{pct:.0f}% of {gbp(target)}" if target > 0 else "No target set"
    st.markdown(
        f'<div class="card {tone}"><div class="card-label">{label}</div>'
        f'<div class="card-value">{gbp(value)}</div>'
        f'<div class="bar {done}"><div style="width:{pct:.0f}%"></div></div>'
        f'<div class="card-sub">{sub}</div></div>', unsafe_allow_html=True)


def show_table(df, column_config=None):
    try:
        st.dataframe(df, width="stretch", hide_index=True, column_config=column_config)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True, column_config=column_config)


def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


def parse_hhmm(s):
    try:
        return datetime.strptime(str(s)[:5].strip(), "%H:%M").time()
    except Exception:
        return time(9, 0)


def to_excel_bytes(sheets):
    """Dict of {sheet_name: DataFrame} -> xlsx bytes (None if openpyxl is missing)."""
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            for name, df in sheets.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
        return buf.getvalue()
    except Exception:
        return None


def show_flash():
    if "flash" in st.session_state:
        level, msg = st.session_state.pop("flash")
        getattr(st, level)(msg)


# ---------- security helpers ----------
def make_password_hash(pw, iters=200_000):
    salt = pysecrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), iters).hex()
    return f"pbkdf2_sha256${iters}${salt}${digest}"


def verify_password(pw):
    stored_hash = get_secret("APP_PASSWORD_HASH")
    if stored_hash:
        try:
            _, iters, salt, digest = str(stored_hash).split("$")
            calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), int(iters)).hex()
            return hmac.compare_digest(calc, digest)
        except Exception:
            return False
    plain = get_secret("APP_PASSWORD")
    return bool(plain) and hmac.compare_digest(pw.encode(), str(plain).encode())


def totp_now(secret, t=None, step=30, digits=6):
    s = secret.replace(" ", "").upper()
    s += "=" * ((8 - len(s) % 8) % 8)
    key = base64.b32decode(s)
    counter = int((time_mod.time() if t is None else t) // step)
    h = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    code = (struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def verify_totp(secret, code):
    code = (code or "").strip().replace(" ", "")
    now = time_mod.time()
    return any(hmac.compare_digest(totp_now(secret, now + d * 30), code) for d in (-1, 0, 1))


# ==========================================================
# DATABASE
# ==========================================================
DATABASE_URL = get_secret("DATABASE_URL")
if not DATABASE_URL:
    st.error("⚠️ Database URL not configured.")
    st.stop()


@st.cache_resource(show_spinner=False)
def _connect(url):
    conn = psycopg2.connect(url, connect_timeout=10)
    conn.autocommit = True
    return conn


def get_conn():
    conn = _connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception:
        _connect.clear()
        conn = _connect(DATABASE_URL)
    return conn


def run(sql, params=None):
    with get_conn().cursor() as cur:
        cur.execute(sql, params)


def query_df(sql, params=None):
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)


SCHEMA = [
    """CREATE TABLE IF NOT EXISTS shifts (
          id SERIAL PRIMARY KEY, shift_date DATE, employer TEXT, start_time TEXT, end_time TEXT,
          hourly_rate REAL, hours_worked REAL, hourly_earning REAL, mileage_earning REAL, tips REAL,
          fuel_cost REAL, expense_cost REAL, gross_earning REAL)""",
    "ALTER TABLE shifts ADD COLUMN IF NOT EXISTS paid BOOLEAN DEFAULT TRUE",   # old shifts count as paid
    "ALTER TABLE shifts ADD COLUMN IF NOT EXISTS miles REAL DEFAULT 0",
    """CREATE TABLE IF NOT EXISTS gogo_transactions (
          id SERIAL PRIMARY KEY, trans_date DATE, trans_type TEXT, amount REAL, notes TEXT)""",
    "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)",
    """CREATE TABLE IF NOT EXISTS shift_templates (
          id SERIAL PRIMARY KEY, name TEXT, employer TEXT, start_time TEXT, end_time TEXT, hourly_rate REAL)""",
    "CREATE TABLE IF NOT EXISTS login_attempts (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), ok BOOLEAN)",
]


@st.cache_resource(show_spinner=False)
def init_schema(url):
    for stmt in SCHEMA:
        run(stmt)
    return True


try:
    init_schema(DATABASE_URL)
    DB_ERROR = None
except Exception as e:
    DB_ERROR = str(e)

# ==========================================================
# AUTHENTICATION  (hashed password, optional 2FA, DB lockout)
# ==========================================================
MAX_FAILS = 5

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        st.markdown("<div style='height:7vh'></div>", unsafe_allow_html=True)
        hero("🔒 Rota Tracker", "Sign in to view your shifts and earnings.")
        valid_user = get_secret("APP_USERNAME")
        totp_secret = get_secret("APP_TOTP_SECRET")

        if DB_ERROR:
            st.error("⚠️ Database connection failed.")
        elif not valid_user or not (get_secret("APP_PASSWORD") or get_secret("APP_PASSWORD_HASH")):
            st.error("Login is not configured. Add `APP_USERNAME` and `APP_PASSWORD` "
                     "(or `APP_PASSWORD_HASH`) to your Streamlit secrets.")
        else:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                code = st.text_input("2FA code", placeholder="6-digit code") if totp_secret else ""
                submitted = st.form_submit_button("Sign in", type="primary")

            if submitted:
                fails = int(query_df("SELECT COUNT(*) AS n FROM login_attempts WHERE ok = FALSE "
                                     "AND ts > NOW() - INTERVAL '15 minutes'")["n"].iloc[0])
                if fails >= MAX_FAILS:
                    st.error("🚫 Too many failed attempts. Please try again in 15 minutes.")
                else:
                    ok_user = hmac.compare_digest(username.encode(), str(valid_user).encode())
                    ok_pass = verify_password(password)
                    ok_2fa = verify_totp(str(totp_secret), code) if totp_secret else True
                    if ok_user and ok_pass and ok_2fa:
                        run("DELETE FROM login_attempts")
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        run("INSERT INTO login_attempts (ok) VALUES (FALSE)")
                        time_mod.sleep(1)
                        left = MAX_FAILS - fails - 1
                        st.error(f"❌ Invalid credentials. {max(left, 0)} attempt(s) left before lockout.")
    st.stop()

if DB_ERROR:
    st.error(f"⚠️ Database connection failed: {DB_ERROR}")
    st.stop()

# ==========================================================
# SETTINGS
# ==========================================================
SETTING_DEFAULTS = {
    "rate_GOGO": "9.50", "rate_CHINESE": "11.00", "rate_DANIELLE": "14.00",
    "gogo_rent": "400.00", "gogo_start": "384.75",
    "auto_rent": "0", "rent_day": "1", "auto_rent_since": "",
    "goal_weekly": "0", "goal_monthly": "0",
    # UK tax (editable estimates - check gov.uk for the current tax year)
    "tax_pa": "12570", "tax_basic_upper": "50270", "tax_add_threshold": "125140",
    "tax_basic_rate": "20", "tax_higher_rate": "40", "tax_add_rate": "45",
    "ni_lower": "12570", "ni_upper": "50270", "ni_main": "6", "ni_top": "2",
    "mile_rate_1": "0.45", "mile_rate_2": "0.25", "mile_threshold": "10000",
}


def load_settings():
    try:
        rows = query_df("SELECT key, value FROM app_settings")
        stored = dict(zip(rows["key"], rows["value"]))
    except Exception:
        stored = {}
    out = {}
    for k, v in {**SETTING_DEFAULTS, **stored}.items():
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            out[k] = v
    return out


def save_setting(key, value):
    run("""INSERT INTO app_settings (key, value) VALUES (%s, %s)
           ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""", (key, str(value)))


# ==========================================================
# DATA LAYER
# ==========================================================
SHIFT_NUM_COLS = ["hourly_rate", "hours_worked", "hourly_earning", "mileage_earning", "tips",
                  "fuel_cost", "expense_cost", "gross_earning", "miles"]


def load_shifts():
    try:
        df = query_df("SELECT * FROM shifts")
    except Exception as e:
        st.error(f"Error loading shifts: {e}")
        return pd.DataFrame()
    if df.empty:
        return df
    df["shift_date"] = pd.to_datetime(df["shift_date"])
    for col in SHIFT_NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["paid"] = df["paid"].fillna(True).astype(bool)
    df["week_start"] = df["shift_date"] - pd.to_timedelta(df["shift_date"].dt.weekday, unit="D")
    return df.sort_values(["shift_date", "id"], ascending=[False, False]).reset_index(drop=True)


def load_trans():
    try:
        df = query_df("SELECT * FROM gogo_transactions")
    except Exception as e:
        st.error(f"Error loading transactions: {e}")
        return pd.DataFrame()
    if df.empty:
        return df
    df["trans_date"] = pd.to_datetime(df["trans_date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df.sort_values(["trans_date", "id"]).reset_index(drop=True)


def load_templates():
    return query_df("SELECT * FROM shift_templates ORDER BY name")


def calculate_hours(start_t, end_t):
    s = datetime.combine(date.today(), start_t)
    e = datetime.combine(date.today(), end_t)
    if e < s:
        e += timedelta(days=1)
    return max(0.0, (e - s).total_seconds() / 3600)


def compute_shift(employer, hours, rate, paid_chinese, mileage, tips):
    hourly = hours * rate
    warning = None
    if employer == "CHINESE":
        mileage = paid_chinese - hourly
        if mileage < 0:
            warning = "Total paid is less than the hourly earnings, so mileage was set to £0."
            mileage = 0.0
        gross = paid_chinese + tips
    else:
        gross = hourly + mileage + tips
    return hourly, mileage, gross, warning


def insert_shift(d, employer, start_s, end_s, rate, hours, hourly, mileage, tips, fuel, exp, gross, miles, paid):
    run("""INSERT INTO shifts (shift_date, employer, start_time, end_time, hourly_rate, hours_worked,
                hourly_earning, mileage_earning, tips, fuel_cost, expense_cost, gross_earning, miles, paid)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (d, employer, start_s, end_s, rate, round(hours, 2), round(hourly, 2), round(mileage, 2),
         round(tips, 2), round(fuel, 2), round(exp, 2), round(gross, 2), round(miles, 1), bool(paid)))


def build_ledger(start_bal):
    rows = []
    shifts = load_shifts()
    if not shifts.empty:
        for r in shifts[shifts["employer"] == "GOGO"].itertuples():
            rows.append((r.shift_date, f"Shift ({r.start_time} – {r.end_time}, {r.hours_worked:.2f} hrs)",
                         "Wages", float(r.hourly_earning), 0, None))
    trans = load_trans()
    if not trans.empty:
        for r in trans.itertuples():
            is_rent = r.trans_type == "RENT"
            desc = "Rent deducted" if is_rent else "Payment received"
            if isinstance(r.notes, str) and r.notes.strip():
                desc += f" ({r.notes.strip()})"
            rows.append((r.trans_date, desc, "Rent" if is_rent else "Payment",
                         -float(r.amount), 1 if is_rent else 2, int(r.id)))
    led = pd.DataFrame(rows, columns=["Date", "Details", "Category", "Amount", "Order", "ID"])
    if led.empty:
        led["Balance"] = []
        return led
    led["Date"] = pd.to_datetime(led["Date"])
    led = led.sort_values(["Date", "Order"], kind="mergesort").reset_index(drop=True)
    led["Balance"] = start_bal + led["Amount"].cumsum()
    led["Month"] = led["Date"].dt.to_period("M")
    return led


def apply_auto_rent(s):
    """Streamlit has no background scheduler, so due rent is added (once) when the app is opened."""
    if not s.get("auto_rent") or not s.get("gogo_rent"):
        return
    try:
        since = datetime.strptime(str(s.get("auto_rent_since")), "%Y-%m-%d").date().replace(day=1)
    except Exception:
        return
    day = int(min(max(s.get("rent_day", 1), 1), 28))
    done = set(query_df("SELECT notes FROM gogo_transactions WHERE notes LIKE %s",
                        ("auto-rent %",))["notes"].tolist())
    y, m = since.year, since.month
    while (y, m) <= (TODAY.year, TODAY.month):
        due, tag = date(y, m, day), f"auto-rent {y}-{m:02d}"
        if due <= TODAY and tag not in done:
            run("INSERT INTO gogo_transactions (trans_date, trans_type, amount, notes) VALUES (%s,'RENT',%s,%s)",
                (due, float(s["gogo_rent"]), tag))
        m += 1
        if m > 12:
            y, m = y + 1, 1


def make_statement_pdf(period, opening, closing, wages, rent, paid, s_d, e_d):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception:
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    els = [Paragraph("GOGO Account Statement", styles["Title"]),
           Paragraph(f"Period: {s_d:%d %b %Y} to {e_d:%d %b %Y} &nbsp;|&nbsp; Generated {TODAY:%d %b %Y}",
                     styles["Normal"]), Spacer(1, 14)]
    summary = Table([["Opening balance", gbp(opening)], ["Wages earned", gbp(wages)],
                     ["Rent deducted", gbp(rent)], ["Payments received", gbp(paid)],
                     ["Closing balance", gbp(closing)]], colWidths=[200, 120])
    summary.setStyle(TableStyle([("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
                                 ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                                 ("LINEABOVE", (0, 4), (-1, 4), 1, colors.black),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    els += [summary, Spacer(1, 18)]
    rows = [["Date", "Details", "Category", "Amount (£)", "Balance (£)"]]
    for r in period.itertuples():
        rows.append([f"{r.Date:%d %b %Y}", str(r.Details)[:46], r.Category, f"{r.Amount:.2f}", f"{r.Balance:.2f}"])
    tbl = Table(rows, repeatRows=1, colWidths=[70, 220, 60, 75, 80])
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
                             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                             ("FONTSIZE", (0, 0), (-1, -1), 8),
                             ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                             ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1"))]))
    els.append(tbl)
    doc.build(els)
    return buf.getvalue()


def make_employer_pdf(emp, sel, s_d, e_d, flt):
    """Per-employer statement: every shift with PAID / UNPAID status (hourly pay only)."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception:
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    paid_amt = float(sel.loc[sel["paid"], "hourly_earning"].sum())
    unpaid_amt = float(sel.loc[~sel["paid"], "hourly_earning"].sum())
    total_amt = paid_amt + unpaid_amt
    hours = float(sel["hours_worked"].sum())
    red = colors.HexColor("#b91c1c")

    els = [Paragraph(f"{html.escape(emp)} - Shift Statement", styles["Title"]),
           Paragraph(f"Period: {s_d:%d %b %Y} to {e_d:%d %b %Y} &nbsp;|&nbsp; Showing: {html.escape(flt)} "
                     f"&nbsp;|&nbsp; Generated {TODAY:%d %b %Y}", styles["Normal"]),
           Spacer(1, 6),
           Paragraph("Amounts are hourly pay only (mileage and tips are paid on the day).", styles["Italic"]),
           Spacer(1, 12)]
    summary = Table([["Shifts", str(len(sel))], ["Total hours", f"{hours:.2f}"],
                     ["Total hourly pay", gbp(total_amt)], ["Paid", gbp(paid_amt)],
                     ["UNPAID (amount owed)", gbp(unpaid_amt)]], colWidths=[200, 120])
    summary.setStyle(TableStyle([("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
                                 ("TEXTCOLOR", (0, 4), (-1, 4), red),
                                 ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                                 ("LINEABOVE", (0, 4), (-1, 4), 1, colors.black),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    els += [summary, Spacer(1, 18)]

    rows = [["Date", "Time", "Hours", "Rate (£)", "Hourly pay (£)", "Status"]]
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("FONTSIZE", (0, 0), (-1, -1), 9),
             ("ALIGN", (2, 0), (4, -1), "RIGHT"),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1"))]
    for i, r in enumerate(sel.itertuples(), start=1):
        rows.append([f"{r.shift_date:%a %d %b %Y}", f"{r.start_time}-{r.end_time}", f"{r.hours_worked:.2f}",
                     f"{r.hourly_rate:.2f}", f"{r.hourly_earning:.2f}", "PAID" if r.paid else "UNPAID"])
        if not r.paid:
            style += [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fee2e2")),
                      ("TEXTCOLOR", (5, i), (5, i), red), ("FONTNAME", (5, i), (5, i), "Helvetica-Bold")]
    n = len(rows)
    rows.append(["TOTAL", "", f"{hours:.2f}", "", f"{total_amt:.2f}", ""])
    style += [("FONTNAME", (0, n), (-1, n), "Helvetica-Bold"), ("LINEABOVE", (0, n), (-1, n), 1, colors.black)]
    tbl = Table(rows, repeatRows=1, colWidths=[95, 90, 50, 60, 85, 60])
    tbl.setStyle(TableStyle(style))
    els.append(tbl)
    doc.build(els)
    return buf.getvalue()


# ---------- tax maths ----------
def uk_tax_year(d):
    return d.year if (d.month, d.day) >= (4, 6) else d.year - 1


def est_income_tax(profit, s):
    pa, bu, at = s["tax_pa"], s["tax_basic_upper"], s["tax_add_threshold"]
    return (max(0, min(profit, bu) - pa) * s["tax_basic_rate"] / 100
            + max(0, min(profit, at) - bu) * s["tax_higher_rate"] / 100
            + max(0, profit - at) * s["tax_add_rate"] / 100)


def est_class4_ni(profit, s):
    return (max(0, min(profit, s["ni_upper"]) - s["ni_lower"]) * s["ni_main"] / 100
            + max(0, profit - s["ni_upper"]) * s["ni_top"] / 100)


# ==========================================================
# SIDEBAR / NAV
# ==========================================================
PAGES = ["➕ Enter Rota", "📊 History & Earnings", "🏠 GOGO Ledger", "💼 Unpaid & Owed",
         "🎯 Goals & Insights", "📅 Calendar", "🧾 Tax & Mileage", "🛠️ Settings & Backup"]

with st.sidebar:
    st.markdown('<div class="brand">💷 Rota Tracker</div>', unsafe_allow_html=True)
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")
    st.divider()
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()

settings = load_settings()
try:
    apply_auto_rent(settings)
except Exception as e:
    st.sidebar.warning(f"Auto-rent skipped: {e}")

ss = st.session_state

# ==========================================================
# PAGE: ENTER ROTA
# ==========================================================
if page == PAGES[0]:
    hero("➕ Log a Shift", "Record your hours, tips and expenses in seconds.")
    show_flash()

    ss.setdefault("rate_input", settings["rate_GOGO"])
    ss.setdefault("start_time_in", time(9, 0))
    ss.setdefault("end_time_in", time(17, 0))

    def on_employer_change():
        ss.rate_input = load_settings()[f"rate_{ss.employer_sel}"]

    def apply_template():
        row = query_df("SELECT * FROM shift_templates WHERE id = %s", (int(ss.tpl_sel),))
        if row.empty:
            return
        r = row.iloc[0]
        ss.employer_sel = r["employer"]
        ss.rate_input = float(r["hourly_rate"])
        ss.start_time_in = parse_hhmm(r["start_time"])
        ss.end_time_in = parse_hhmm(r["end_time"])
        ss.flash = ("success", f"Template “{r['name']}” applied.")

    def save_template():
        name = (ss.get("tpl_name") or "").strip()
        if not name:
            ss.flash = ("error", "Give the template a name first.")
            return
        run("INSERT INTO shift_templates (name, employer, start_time, end_time, hourly_rate) VALUES (%s,%s,%s,%s,%s)",
            (name, ss.employer_sel, ss.start_time_in.strftime("%H:%M"), ss.end_time_in.strftime("%H:%M"),
             float(ss.rate_input)))
        ss.tpl_name = ""
        ss.flash = ("success", f"Template “{name}” saved.")

    with st.expander("⚙️ Edit Default Hourly Rates"):
        with st.form("rates_form"):
            rc = st.columns(3)
            new_rates = {emp: rc[i].number_input(f"{emp} default (£)", min_value=0.0,
                                                 value=float(settings[f"rate_{emp}"]), step=0.10, format="%.2f")
                         for i, emp in enumerate(EMPLOYERS)}
            if st.form_submit_button("Save default rates", type="primary"):
                for emp, val in new_rates.items():
                    save_setting(f"rate_{emp}", val)
                ss.rate_input = new_rates[ss.get("employer_sel", "GOGO")]
                st.success("Default rates saved.")

    templates = load_templates()
    with st.expander("⚡ Templates & copy last week"):
        t1, t2 = st.columns(2, gap="large")
        with t1:
            st.markdown("**Shift templates**")
            if templates.empty:
                st.caption("No templates yet. Fill the form below, name it here and save.")
            else:
                tmap = {int(r.id): f"{r.name} — {r.employer} {r.start_time}-{r.end_time} @ £{r.hourly_rate:.2f}"
                        for r in templates.itertuples()}
                st.selectbox("Template", list(tmap), format_func=tmap.get, key="tpl_sel")
                b1, b2 = st.columns(2)
                b1.button("Apply", on_click=apply_template)
                if b2.button("Delete"):
                    run("DELETE FROM shift_templates WHERE id = %s", (int(ss.tpl_sel),))
                    st.rerun()
            st.text_input("Save current form as template", placeholder="e.g. GOGO 9–5", key="tpl_name")
            st.button("Save template", on_click=save_template)
        with t2:
            st.markdown("**Copy a week**")
            mon = TODAY - timedelta(days=TODAY.weekday())
            src = st.date_input("Copy shifts from the week containing", value=mon - timedelta(days=7), key="copy_src")
            dst = st.date_input("…into the week containing", value=mon, key="copy_dst")
            st.caption("Copies hours and hourly pay only. Edit afterwards to add tips, mileage and costs.")
            if st.button("Copy week"):
                src_mon = src - timedelta(days=src.weekday())
                offset = (dst - timedelta(days=dst.weekday())) - src_mon
                allsh = load_shifts()
                if allsh.empty:
                    st.warning("No shifts to copy.")
                else:
                    existing = {(r.shift_date.date(), r.employer, r.start_time, r.end_time) for r in allsh.itertuples()}
                    block = allsh[(allsh["shift_date"].dt.date >= src_mon) &
                                  (allsh["shift_date"].dt.date <= src_mon + timedelta(days=6))]
                    n = 0
                    for r in block.itertuples():
                        nd = r.shift_date.date() + offset
                        if (nd, r.employer, r.start_time, r.end_time) in existing:
                            continue
                        insert_shift(nd, r.employer, r.start_time, r.end_time, r.hourly_rate, r.hours_worked,
                                     r.hourly_earning, 0, 0, 0, 0, r.hourly_earning, 0, False)
                        n += 1
                    ss.flash = ("success" if n else "info", f"Copied {n} shift(s)." if n else "Nothing new to copy.")
                    st.rerun()

    st.markdown("---")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.subheader("🗓️ When & where")
        employer = st.selectbox("Employer / Location", EMPLOYERS, key="employer_sel", on_change=on_employer_change)
        shift_date = st.date_input("Shift Date", value=TODAY)
        t1, t2 = st.columns(2)
        start_time = t1.time_input("Start Time", key="start_time_in")
        end_time = t2.time_input("End Time", key="end_time_in")
    with col2:
        st.subheader("💷 Pay details")
        hourly_rate = st.number_input("Hourly Rate (£)", min_value=0.0, step=0.10, format="%.2f", key="rate_input")
        paid_chinese, mileage_in = 0.0, 0.0
        if employer == "CHINESE":
            st.info("💡 **Chinese shift mode:** enter the total paid. Mileage is calculated automatically.")
            paid_chinese = st.number_input("Total Amount Paid by Employer (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            tips = st.number_input("Tips Earned (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        else:
            a1, a2 = st.columns(2)
            mileage_in = a1.number_input("Mileage Earned (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            tips = a2.number_input("Tips Earned (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        d1, d2, d3 = st.columns(3)
        fuel_cost = d1.number_input("Fuel Cost (£) −", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        expense_cost = d2.number_input("Other Expenses (£) −", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        miles = d3.number_input("Miles driven", min_value=0.0, value=0.0, step=1.0, format="%.1f")
        is_paid = st.checkbox("✅ Shift already paid", value=False, key="paid_in",
                              help="Leave unticked if you are still waiting to be paid for this shift.")

    hours = calculate_hours(start_time, end_time)
    hourly_e, mileage_e, gross_e, warn = compute_shift(employer, hours, hourly_rate, paid_chinese, mileage_in, tips)
    net_e = gross_e - fuel_cost - expense_cost

    st.markdown("---")
    st.subheader("🔎 Live preview")
    p = st.columns(4)
    with p[0]: card("Hours", f"{hours:.2f}", "this shift", "indigo")
    with p[1]: card("Hourly pay", gbp(hourly_e), f"@ £{hourly_rate:.2f}/hr", "teal")
    with p[2]: card("Gross", gbp(gross_e), f"mileage {gbp(mileage_e)} · tips {gbp(tips)}", "green")
    with p[3]: card("Net (after costs)", gbp(net_e), f"costs {gbp(fuel_cost + expense_cost)}", "amber")
    if warn:
        st.warning(f"⚠️ {warn}")

    if st.button("💾 Save Shift", type="primary"):
        if hours <= 0:
            st.error("Start and end time are the same – the shift has 0 hours.")
        else:
            insert_shift(shift_date, employer, start_time.strftime("%H:%M"), end_time.strftime("%H:%M"),
                         hourly_rate, hours, hourly_e, mileage_e, tips, fuel_cost, expense_cost, gross_e, miles, is_paid)
            st.success(f"Shift saved! **{hours:.2f} hours**, **{gbp(gross_e)}** gross.")
            st.balloons()

    recent = load_shifts()
    if not recent.empty:
        st.markdown("---")
        st.subheader("🕒 Recent shifts")
        show_table(recent.head(5)[["shift_date", "employer", "start_time", "end_time", "hours_worked", "gross_earning", "paid"]], {
            "shift_date": st.column_config.DateColumn("Date", format="DD MMM YYYY"), "employer": "Location",
            "start_time": "Start", "end_time": "End",
            "hours_worked": st.column_config.NumberColumn("Hours", format="%.2f"),
            "gross_earning": st.column_config.NumberColumn("Gross (£)", format="%.2f"),
            "paid": st.column_config.CheckboxColumn("Paid")})

# ==========================================================
# PAGE: HISTORY
# ==========================================================
elif page == PAGES[1]:
    hero("📊 Earnings History", "Filter, analyse, edit and export everything you've worked.")
    show_flash()
    df = load_shifts()

    if df.empty:
        st.info("No shifts recorded yet. Head to **Enter Rota** to add your first one.")
        st.stop()

    show_net = st.toggle("📉 Show net earnings (subtract fuel & expenses)", value=False)
    f1, f2 = st.columns(2)
    with f1:
        sel_emp = st.selectbox("Filter by Employer", ["All Employers"] + sorted(df["employer"].dropna().unique().tolist()))
    with f2:
        min_d, max_d = df["shift_date"].min().date(), df["shift_date"].max().date()
        date_range = st.date_input("Date Range", value=(min_d, max_d), min_value=min_d, max_value=max_d)

    fdf = df.copy()
    if sel_emp != "All Employers":
        fdf = fdf[fdf["employer"] == sel_emp]
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        fdf = fdf[(fdf["shift_date"].dt.date >= date_range[0]) & (fdf["shift_date"].dt.date <= date_range[1])]
    else:
        st.info("Pick an end date to apply the date filter.")
    if fdf.empty:
        st.warning("No shifts match these filters.")
        st.stop()

    fdf = fdf.copy()
    fdf["deductions"] = fdf["fuel_cost"] + fdf["expense_cost"]
    fdf["final"] = fdf["gross_earning"] - fdf["deductions"] if show_net else fdf["gross_earning"]
    hours_total, gross_total, deduct_total = fdf["hours_worked"].sum(), fdf["gross_earning"].sum(), fdf["deductions"].sum()
    headline = gross_total - deduct_total if show_net else gross_total

    st.markdown("---")
    st.subheader("Summary")
    k = st.columns(4)
    with k[0]: card("Shifts", f"{len(fdf)}", "in selection", "slate")
    with k[1]: card("Hours", f"{hours_total:.2f}", "total worked", "indigo")
    with k[2]: card("Hourly pay", gbp(fdf["hourly_earning"].sum()), "base wages", "teal")
    with k[3]: card("Avg £/hour", gbp(headline / hours_total if hours_total else 0), "net" if show_net else "gross", "amber")
    k = st.columns(4)
    with k[0]: card("Mileage", gbp(fdf["mileage_earning"].sum()), "", "teal")
    with k[1]: card("Tips", gbp(fdf["tips"].sum()), "", "green")
    with k[2]: card("Fuel & expenses", gbp(-deduct_total), "", "red")
    with k[3]: card("NET EARNINGS" if show_net else "TOTAL EARNINGS", gbp(headline),
                    f"gross {gbp(gross_total)}" if show_net else "before costs", "green" if headline >= 0 else "red")

    unp = fdf[~fdf["paid"]]
    k = st.columns(3)
    with k[0]: card("Unpaid (hourly pay)", gbp(unp["hourly_earning"].sum()), "mileage & tips are paid on the day",
                    "amber" if len(unp) else "green")
    with k[1]: card("Unpaid shifts", f"{len(unp)}", f"{unp['hours_worked'].sum():.2f} hrs outstanding",
                    "red" if len(unp) else "slate")
    with k[2]: card("Paid (hourly pay)", gbp(fdf.loc[fdf["paid"], "hourly_earning"].sum()), "already received", "green")

    st.markdown("---")
    tab_log, tab_week, tab_emp = st.tabs(["📋 Shift log", "📈 Weekly trend", "🏢 By employer"])
    with tab_log:
        ss.setdefault("log_ver", 0)
        sel_all = st.checkbox("Select all shifts shown", key="log_sel_all")
        log = fdf[["id", "shift_date", "employer", "start_time", "end_time", "hours_worked", "hourly_earning",
                   "mileage_earning", "tips", "fuel_cost", "expense_cost", "miles", "paid", "final"]].copy()
        log["status"] = log["paid"].map({True: "✅ Paid", False: "⏳ Unpaid"})
        log = log.drop(columns=["paid"])
        log.insert(0, "Select", bool(sel_all))
        mny = lambda t: st.column_config.NumberColumn(t, format="%.2f")
        edited = st.data_editor(
            log, hide_index=True, key=f"log_editor_{ss.log_ver}_{int(sel_all)}",
            disabled=[c for c in log.columns if c != "Select"],
            column_config={
                "Select": st.column_config.CheckboxColumn("Select"), "id": None,
                "shift_date": st.column_config.DateColumn("Date", format="DD MMM YYYY"), "employer": "Location",
                "start_time": "Start", "end_time": "End",
                "hours_worked": st.column_config.NumberColumn("Hours", format="%.2f"),
                "hourly_earning": mny("Hourly (£)"), "mileage_earning": mny("Mileage (£)"), "tips": mny("Tips (£)"),
                "fuel_cost": mny("Fuel (−£)"), "expense_cost": mny("Expense (−£)"),
                "miles": st.column_config.NumberColumn("Miles", format="%.1f"),
                "status": "Status", "final": mny("Net (£)" if show_net else "Gross (£)")})
        picked = edited.loc[edited["Select"], "id"].astype(int).tolist()
        st.caption(f"{len(picked)} shift(s) selected — tick the **Select** boxes, then choose an action:")
        b1, b2, _sp = st.columns([1, 1, 2])
        if b1.button("✅ Mark selected as paid", type="primary"):
            if picked:
                run("UPDATE shifts SET paid = TRUE WHERE id = ANY(%s)", (picked,))
                ss.log_ver += 1
                ss.flash = ("success", f"Marked {len(picked)} shift(s) as paid.")
                st.rerun()
            else:
                st.warning("Tick at least one shift first.")
        if b2.button("⏳ Mark selected as unpaid"):
            if picked:
                run("UPDATE shifts SET paid = FALSE WHERE id = ANY(%s)", (picked,))
                ss.log_ver += 1
                ss.flash = ("success", f"Marked {len(picked)} shift(s) as unpaid.")
                st.rerun()
            else:
                st.warning("Tick at least one shift first.")
    with tab_week:
        st.caption("Earnings per week (weeks start on Monday)")
        st.bar_chart(fdf.groupby("week_start")["final"].sum().sort_index(), color="#6366f1")
    with tab_emp:
        st.caption("Earnings per employer")
        st.bar_chart(fdf.groupby("employer")["final"].sum().sort_values(ascending=False), color="#14b8a6")

    labels = {int(r.id): f"{r.shift_date:%d %b %Y} · {r.employer} · {r.start_time}–{r.end_time} · {gbp(r.gross_earning)}"
              for r in fdf.itertuples()}

    with st.expander("✏️ Edit a shift"):
        esel = st.selectbox("Select shift to edit", list(labels), format_func=labels.get, key="edit_sel")
        r = fdf[fdf["id"] == esel].iloc[0]
        kk = f"e{esel}_{int(bool(r['paid']))}_"
        with st.form("edit_shift_form"):
            c1, c2 = st.columns(2)
            e_emp = c1.selectbox("Employer", EMPLOYERS, index=EMPLOYERS.index(r["employer"]) if r["employer"] in EMPLOYERS else 0, key=kk + "emp")
            e_date = c2.date_input("Date", value=r["shift_date"].date(), key=kk + "date")
            e_st = c1.time_input("Start", value=parse_hhmm(r["start_time"]), key=kk + "st")
            e_en = c2.time_input("End", value=parse_hhmm(r["end_time"]), key=kk + "en")
            e_rate = c1.number_input("Hourly rate (£)", min_value=0.0, value=float(r["hourly_rate"]), step=0.10, format="%.2f", key=kk + "rate")
            e_mil_e = c2.number_input("Mileage earned (£) — not used for CHINESE", min_value=0.0, value=float(r["mileage_earning"]), step=1.0, format="%.2f", key=kk + "me")
            e_total = c1.number_input("Total paid (£) — CHINESE only", min_value=0.0, value=float(r["hourly_earning"] + r["mileage_earning"]), step=1.0, format="%.2f", key=kk + "tp")
            e_tips = c2.number_input("Tips (£)", min_value=0.0, value=float(r["tips"]), step=1.0, format="%.2f", key=kk + "tips")
            e_fuel = c1.number_input("Fuel (£)", min_value=0.0, value=float(r["fuel_cost"]), step=1.0, format="%.2f", key=kk + "fuel")
            e_exp = c2.number_input("Other expenses (£)", min_value=0.0, value=float(r["expense_cost"]), step=1.0, format="%.2f", key=kk + "exp")
            e_miles = c1.number_input("Miles", min_value=0.0, value=float(r["miles"]), step=1.0, format="%.1f", key=kk + "miles")
            e_paid = c2.checkbox("Paid", value=bool(r["paid"]), key=kk + "paid")
            if st.form_submit_button("Save changes", type="primary"):
                hrs = calculate_hours(e_st, e_en)
                if hrs <= 0:
                    st.error("Start and end time are the same.")
                else:
                    hE, mE, gE, _w = compute_shift(e_emp, hrs, e_rate, e_total, e_mil_e, e_tips)
                    run("""UPDATE shifts SET shift_date=%s, employer=%s, start_time=%s, end_time=%s, hourly_rate=%s,
                           hours_worked=%s, hourly_earning=%s, mileage_earning=%s, tips=%s, fuel_cost=%s,
                           expense_cost=%s, gross_earning=%s, miles=%s, paid=%s WHERE id=%s""",
                        (e_date, e_emp, e_st.strftime("%H:%M"), e_en.strftime("%H:%M"), e_rate, round(hrs, 2),
                         round(hE, 2), round(mE, 2), round(e_tips, 2), round(e_fuel, 2), round(e_exp, 2),
                         round(gE, 2), round(e_miles, 1), bool(e_paid), int(esel)))
                    ss.flash = ("success", "Shift updated.")
                    st.rerun()

    with st.expander("⬇️ Export"):
        export_df = fdf.drop(columns=["week_start", "deductions", "final"]).copy()
        export_df["shift_date"] = export_df["shift_date"].dt.date
        xl = to_excel_bytes({"Shifts": export_df})
        e1, e2 = st.columns(2)
        if xl:
            e1.download_button("📗 Download Excel", xl, f"shifts_{TODAY:%Y%m%d}.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            e1.caption("Excel export needs `openpyxl` in requirements.txt.")
        e2.download_button("📄 Download CSV", export_df.to_csv(index=False).encode(), f"shifts_{TODAY:%Y%m%d}.csv", "text/csv")

    def delete_shift():
        run("DELETE FROM shifts WHERE id = %s", (int(ss.del_sel),))
        ss.confirm_del_shift = False  # allowed here: callbacks run before widgets are drawn
        ss.flash = ("success", "Shift deleted.")

    with st.expander("⚠️ Delete a shift"):
        st.selectbox("Select shift to delete", list(labels), format_func=labels.get, key="del_sel")
        sure = st.checkbox("Yes, delete this shift permanently", key="confirm_del_shift")
        st.button("Delete selected shift", disabled=not sure, on_click=delete_shift)

# ==========================================================
# PAGE: GOGO LEDGER
# ==========================================================
elif page == PAGES[2]:
    hero("🏠 GOGO Rent & Payments", "Wages earned, rent deducted and payments received — with a running balance.")
    show_flash()
    start_balance, monthly_rent = float(settings["gogo_start"]), float(settings["gogo_rent"])
    TYPES = ["Payment Received from Owner", "Rent Deducted by Owner"]

    with st.expander("⚙️ GOGO Settings & automatic rent"):
        with st.form("gogo_settings"):
            s1, s2 = st.columns(2)
            new_rent = s1.number_input("Monthly Rent Amount (£)", min_value=0.0, value=monthly_rent, step=10.0, format="%.2f")
            new_start = s2.number_input("Starting Balance (£)", min_value=-10000.0, value=start_balance, step=10.0, format="%.2f")
            a1, a2, a3 = st.columns(3)
            new_auto = a1.checkbox("Add rent automatically each month", value=bool(settings["auto_rent"]))
            new_day = a2.number_input("Rent day of month", min_value=1, max_value=28, value=int(settings["rent_day"]))
            try:
                since_default = datetime.strptime(str(settings["auto_rent_since"]), "%Y-%m-%d").date()
            except Exception:
                since_default = TODAY.replace(day=1)
            new_since = a3.date_input("Start from month", value=since_default)
            st.caption("Rent is added the next time the app is opened on/after the rent day (no background job needed).")
            if st.form_submit_button("Save settings", type="primary"):
                save_setting("gogo_rent", new_rent); save_setting("gogo_start", new_start)
                save_setting("auto_rent", int(new_auto)); save_setting("rent_day", int(new_day))
                save_setting("auto_rent_since", new_since.replace(day=1).isoformat())
                st.rerun()

    ss.setdefault("trans_amt", 0.0)
    ss.setdefault("trans_notes", "")

    def on_type_change():
        ss.trans_amt = load_settings()["gogo_rent"] if ss.trans_type == TYPES[1] else 0.0

    def add_transaction():
        amt = float(ss.trans_amt)
        if amt <= 0:
            ss.flash = ("error", "Enter an amount greater than £0.")
            return
        run("INSERT INTO gogo_transactions (trans_date, trans_type, amount, notes) VALUES (%s,%s,%s,%s)",
            (ss.trans_date, "RENT" if ss.trans_type == TYPES[1] else "PAYMENT", round(amt, 2), ss.trans_notes.strip()))
        ss.trans_amt, ss.trans_notes = 0.0, ""
        ss.flash = ("success", "Transaction added successfully!")

    ledger = build_ledger(start_balance)

    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("➕ Add transaction")
        st.selectbox("Transaction Type", TYPES, key="trans_type", on_change=on_type_change)
        st.date_input("Date", value=TODAY, key="trans_date")
        st.number_input("Amount (£)", min_value=0.0, step=1.0, format="%.2f", key="trans_amt")
        st.text_input("Notes (optional)", placeholder="e.g. Cash, bank transfer", key="trans_notes")
        st.button("Add Transaction", type="primary", on_click=add_transaction)
    with right:
        st.subheader("🗓️ Period")
        preset = st.radio("Show", ["This month", "Last 30 days", "All time", "Custom"], horizontal=True, label_visibility="collapsed")
        if preset == "This month":
            start_d, end_d = TODAY.replace(day=1), TODAY
        elif preset == "Last 30 days":
            start_d, end_d = TODAY - timedelta(days=30), TODAY
        elif preset == "All time":
            if ledger.empty:
                start_d, end_d = TODAY.replace(day=1), TODAY
            else:
                start_d, end_d = ledger["Date"].min().date(), max(TODAY, ledger["Date"].max().date())
        else:
            rng = st.date_input("Date range", value=(TODAY.replace(day=1), TODAY))
            if not (isinstance(rng, (tuple, list)) and len(rng) == 2):
                st.info("Pick an end date.")
                st.stop()
            start_d, end_d = rng
        st.caption(f"Showing {start_d:%d %b %Y} → {end_d:%d %b %Y}")

    if ledger.empty:
        balance_now, opening, period = start_balance, start_balance, ledger
    else:
        dts = ledger["Date"].dt.date
        balance_now = start_balance + ledger.loc[dts <= TODAY, "Amount"].sum()
        opening = start_balance + ledger.loc[dts < start_d, "Amount"].sum()
        period = ledger[(dts >= start_d) & (dts <= end_d)]

    wages = period.loc[period["Category"] == "Wages", "Amount"].sum() if not period.empty else 0.0
    rent = -period.loc[period["Category"] == "Rent", "Amount"].sum() if not period.empty else 0.0
    paid = -period.loc[period["Category"] == "Payment", "Amount"].sum() if not period.empty else 0.0
    net_period = wages - rent - paid
    closing = opening + net_period

    st.markdown("---")
    cls, label, amt = ("owed", "Owner currently owes you", balance_now) if balance_now >= 0 else ("owe", "You currently owe owner", abs(balance_now))
    st.markdown(f'<div class="balance {cls}"><div><div class="b-label">{label}</div><div class="b-value">{gbp(amt)}</div></div>'
                f'<div class="b-label">as of {TODAY:%d %b %Y}</div></div>', unsafe_allow_html=True)

    st.subheader("Summary for selected period")
    m = st.columns(3)
    with m[0]: card("Base wages earned", gbp(wages), "", "green")
    with m[1]: card("Rent deducted", gbp(rent), "", "red")
    with m[2]: card("Payments received", gbp(paid), "", "amber")
    m = st.columns(3)
    with m[0]: card("Opening balance", gbp(opening), f"before {start_d:%d %b}", "slate")
    with m[1]: card("Net for period", gbp(net_period), "wages − rent − payments", "green" if net_period >= 0 else "red")
    with m[2]: card("Closing balance", gbp(closing), f"at {end_d:%d %b}", "indigo")
    st.markdown("---")

    if ledger.empty:
        st.info("No GOGO shifts or transactions recorded yet.")
    else:
        tab_m, tab_l, tab_x = st.tabs(["📅 Monthly breakdown (with rollover)", "📋 Detailed ledger", "📄 Statement & export"])
        with tab_m:
            L = ledger.copy()
            L["RentAmt"] = (-L["Amount"]).where(L["Category"] == "Rent", 0.0)
            L["PayAmt"] = (-L["Amount"]).where(L["Category"] == "Payment", 0.0)
            L["WageAmt"] = L["Amount"].where(L["Category"] == "Wages", 0.0)
            monthly = L.groupby("Month").agg(Wages=("WageAmt", "sum"), Rent=("RentAmt", "sum"),
                                              Payments=("PayAmt", "sum"), Net=("Amount", "sum")).reset_index()
            monthly["Closing"] = start_balance + monthly["Net"].cumsum()
            monthly["Rollover"] = monthly["Closing"] - monthly["Net"]
            monthly = monthly[(monthly["Month"] >= pd.Period(start_d, "M")) & (monthly["Month"] <= pd.Period(end_d, "M"))].copy()
            monthly["Month"] = monthly["Month"].dt.strftime("%b %Y")
            nn = lambda t: st.column_config.NumberColumn(t, format="%.2f")
            show_table(monthly[["Month", "Rollover", "Wages", "Rent", "Payments", "Net", "Closing"]], {
                "Rollover": nn("Rollover in (£)"), "Wages": nn("Wages (£)"), "Rent": nn("Rent (£)"),
                "Payments": nn("Payments (£)"), "Net": nn("Net (£)"), "Closing": nn("Balance end (£)")})
        with tab_l:
            if period.empty:
                st.info("No entries in the selected period.")
            else:
                disp = period.sort_values(["Date", "Order"], ascending=False, kind="mergesort")[["Date", "Details", "Category", "Amount", "Balance"]]
                show_table(disp, {"Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                                  "Amount": st.column_config.NumberColumn("Amount (£)", format="%.2f"),
                                  "Balance": st.column_config.NumberColumn("Running balance (£)", format="%.2f")})
        with tab_x:
            if period.empty:
                st.info("Nothing to export for this period.")
            else:
                x1, x2 = st.columns(2)
                if x1.button("📄 Prepare PDF statement"):
                    ss.pdf_bytes = make_statement_pdf(period, opening, closing, wages, rent, paid, start_d, end_d)
                    ss.pdf_missing = ss.pdf_bytes is None
                if ss.get("pdf_missing"):
                    st.caption("PDF export needs `reportlab` in requirements.txt.")
                elif ss.get("pdf_bytes"):
                    st.download_button("⬇️ Download PDF statement", ss.pdf_bytes, f"gogo_statement_{TODAY:%Y%m%d}.pdf", "application/pdf")
                xl = to_excel_bytes({"Ledger": period.drop(columns=["Order", "ID", "Month"], errors="ignore")})
                if xl:
                    x2.download_button("📗 Download ledger (Excel)", xl, f"gogo_ledger_{TODAY:%Y%m%d}.xlsx",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    trans_all = load_trans()
    with st.expander("✏️ Edit a transaction"):
        if trans_all.empty:
            st.info("No transactions yet.")
        else:
            tl = {int(r.id): f"{r.trans_date:%d %b %Y} · {r.trans_type} · {gbp(r.amount)}" for r in trans_all.sort_values("trans_date", ascending=False).itertuples()}
            tsel = st.selectbox("Select transaction", list(tl), format_func=tl.get, key="tx_edit_sel")
            tr = trans_all[trans_all["id"] == tsel].iloc[0]
            kk = f"t{tsel}_"
            with st.form("edit_tx_form"):
                c1, c2 = st.columns(2)
                t_type = c1.selectbox("Type", TYPES, index=1 if tr["trans_type"] == "RENT" else 0, key=kk + "type")
                t_date = c2.date_input("Date", value=tr["trans_date"].date(), key=kk + "date")
                t_amt = c1.number_input("Amount (£)", min_value=0.0, value=float(tr["amount"]), step=1.0, format="%.2f", key=kk + "amt")
                t_notes = c2.text_input("Notes", value=tr["notes"] if isinstance(tr["notes"], str) else "", key=kk + "notes")
                if st.form_submit_button("Save changes", type="primary"):
                    run("UPDATE gogo_transactions SET trans_date=%s, trans_type=%s, amount=%s, notes=%s WHERE id=%s",
                        (t_date, "RENT" if t_type == TYPES[1] else "PAYMENT", round(t_amt, 2), t_notes.strip(), int(tsel)))
                    ss.flash = ("success", "Transaction updated.")
                    st.rerun()

    def delete_tx():
        run("DELETE FROM gogo_transactions WHERE id = %s", (int(ss.tx_del_sel),))
        ss.confirm_del_tx = False
        ss.flash = ("success", "Transaction deleted.")

    with st.expander("⚠️ Delete a transaction"):
        if trans_all.empty:
            st.info("No transactions recorded yet.")
        else:
            dl = {int(r.id): f"{r.trans_date:%d %b %Y} · {r.trans_type} · {gbp(r.amount)}" for r in trans_all.sort_values("trans_date", ascending=False).itertuples()}
            st.selectbox("Select transaction to delete", list(dl), format_func=dl.get, key="tx_del_sel")
            sure = st.checkbox("Yes, delete this transaction permanently", key="confirm_del_tx")
            st.button("Delete transaction", disabled=not sure, on_click=delete_tx)

# ==========================================================
# PAGE: UNPAID & OWED
# ==========================================================
elif page == PAGES[3]:
    hero("💼 Unpaid & Owed", "See exactly what each employer still owes you.")
    show_flash()
    shifts = load_shifts()
    ledger = build_ledger(float(settings["gogo_start"]))
    gogo_bal = float(settings["gogo_start"]) + (ledger.loc[ledger["Date"].dt.date <= TODAY, "Amount"].sum() if not ledger.empty else 0.0)

    unpaid = shifts[~shifts["paid"]] if not shifts.empty else pd.DataFrame()
    cols = st.columns(len(EMPLOYERS))
    for i, emp in enumerate(EMPLOYERS):
        with cols[i]:
            sub = unpaid[unpaid["employer"] == emp] if not unpaid.empty else unpaid
            tot = float(sub["hourly_earning"].sum()) if not sub.empty else 0.0
            if emp == "GOGO":
                card("GOGO (ledger balance)", gbp(gogo_bal),
                     f"{len(sub)} shift(s) marked unpaid · {gbp(tot)}", "green" if gogo_bal >= 0 else "red")
            else:
                card(emp, gbp(tot), f"{len(sub)} unpaid shift(s)", "amber" if tot > 0 else "slate")

    st.markdown("---")
    st.subheader("Unpaid shifts")
    st.caption("Amounts owed are **hourly pay only** — mileage and tips are paid on the day.")
    if unpaid.empty:
        st.success("🎉 Nothing outstanding — every shift is marked as paid.")
    else:
        ed = unpaid[["id", "shift_date", "employer", "start_time", "end_time", "hours_worked", "hourly_earning"]].copy()
        ed.insert(0, "Paid?", False)
        edited = st.data_editor(ed, hide_index=True, key="unpaid_editor",
                                disabled=[c for c in ed.columns if c != "Paid?"],
                                column_config={"id": None,
                                               "shift_date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                                               "employer": "Location", "start_time": "Start", "end_time": "End",
                                               "hours_worked": st.column_config.NumberColumn("Hours", format="%.2f"),
                                               "hourly_earning": st.column_config.NumberColumn("Owed – hourly pay (£)", format="%.2f")})
        c1, c2 = st.columns(2)
        if c1.button("✅ Mark ticked as paid", type="primary"):
            ids = edited.loc[edited["Paid?"], "id"].astype(int).tolist()
            if ids:
                run("UPDATE shifts SET paid = TRUE WHERE id = ANY(%s)", (ids,))
                ss.flash = ("success", f"Marked {len(ids)} shift(s) as paid.")
                st.rerun()
            else:
                st.warning("Tick at least one shift first.")
        emp_pick = c2.selectbox("Or mark everything paid for", EMPLOYERS, key="mark_all_emp")
        if c2.button(f"Mark all {emp_pick} as paid"):
            run("UPDATE shifts SET paid = TRUE WHERE employer = %s AND paid = FALSE", (emp_pick,))
            ss.flash = ("success", f"All {emp_pick} shifts marked as paid.")
            st.rerun()

    st.markdown("---")
    st.subheader("📄 Employer statement (PDF)")
    st.caption("Every shift with its **Paid / Unpaid** status. Amounts are hourly pay only.")
    if shifts.empty:
        st.info("No shifts recorded yet.")
    else:
        s1, s2, s3 = st.columns(3)
        st_emp = s1.selectbox("Employer", EMPLOYERS, key="stmt_emp")
        emp_sh = shifts[shifts["employer"] == st_emp]
        if emp_sh.empty:
            st.info(f"No {st_emp} shifts recorded yet.")
        else:
            lo, hi = emp_sh["shift_date"].min().date(), max(TODAY, emp_sh["shift_date"].max().date())
            rng = s2.date_input("Period", value=(lo, hi), key=f"stmt_rng_{st_emp}")
            flt = s3.radio("Include", ["All shifts", "Unpaid only", "Paid only"], key="stmt_filter")
            if not (isinstance(rng, (tuple, list)) and len(rng) == 2):
                st.info("Pick an end date for the period.")
            else:
                dts = emp_sh["shift_date"].dt.date
                sel = emp_sh[(dts >= rng[0]) & (dts <= rng[1])]
                if flt == "Unpaid only":
                    sel = sel[~sel["paid"]]
                elif flt == "Paid only":
                    sel = sel[sel["paid"]]
                sel = sel.sort_values("shift_date")
                if sel.empty:
                    st.info("No shifts match these choices.")
                else:
                    paid_amt = float(sel.loc[sel["paid"], "hourly_earning"].sum())
                    unpaid_amt = float(sel.loc[~sel["paid"], "hourly_earning"].sum())
                    q = st.columns(3)
                    with q[0]: card("Total hourly pay", gbp(paid_amt + unpaid_amt), f"{len(sel)} shift(s)", "indigo")
                    with q[1]: card("Paid", gbp(paid_amt), "", "green")
                    with q[2]: card("Unpaid", gbp(unpaid_amt), "amount owed", "amber" if unpaid_amt > 0 else "slate")

                    prev = sel[["shift_date", "start_time", "end_time", "hours_worked", "hourly_rate", "hourly_earning", "paid"]].copy()
                    prev["status"] = prev["paid"].map({True: "✅ Paid", False: "⏳ Unpaid"})
                    show_table(prev.drop(columns=["paid"]), {
                        "shift_date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                        "start_time": "Start", "end_time": "End",
                        "hours_worked": st.column_config.NumberColumn("Hours", format="%.2f"),
                        "hourly_rate": st.column_config.NumberColumn("Rate (£)", format="%.2f"),
                        "hourly_earning": st.column_config.NumberColumn("Hourly pay (£)", format="%.2f"),
                        "status": "Status"})

                    sig = (st_emp, str(rng[0]), str(rng[1]), flt, len(sel), round(unpaid_amt, 2))
                    if st.button("📄 Prepare PDF statement", key="prep_emp_pdf"):
                        ss.emp_pdf = {"sig": sig, "bytes": make_employer_pdf(st_emp, sel, rng[0], rng[1], flt)}
                    pdf = ss.get("emp_pdf")
                    if pdf and pdf["sig"] == sig:
                        if pdf["bytes"] is None:
                            st.caption("PDF export needs `reportlab` in requirements.txt.")
                        else:
                            st.download_button("⬇️ Download PDF statement", pdf["bytes"],
                                               f"{st_emp.lower()}_statement_{TODAY:%Y%m%d}.pdf", "application/pdf")

# ==========================================================
# PAGE: GOALS & INSIGHTS
# ==========================================================
elif page == PAGES[4]:
    hero("🎯 Goals & Insights", "Targets, trends and where your time pays best.")
    shifts = load_shifts()

    with st.expander("🎯 Set earnings goals (net, after fuel & expenses)"):
        with st.form("goals_form"):
            g1, g2 = st.columns(2)
            gw = g1.number_input("Weekly goal (£)", min_value=0.0, value=float(settings["goal_weekly"]), step=10.0, format="%.2f")
            gm = g2.number_input("Monthly goal (£)", min_value=0.0, value=float(settings["goal_monthly"]), step=50.0, format="%.2f")
            if st.form_submit_button("Save goals", type="primary"):
                save_setting("goal_weekly", gw); save_setting("goal_monthly", gm)
                st.rerun()

    if shifts.empty:
        st.info("Add some shifts to see goals and insights.")
        st.stop()

    shifts = shifts.copy()
    shifts["net"] = shifts["gross_earning"] - shifts["fuel_cost"] - shifts["expense_cost"]
    d = shifts["shift_date"].dt.date
    wk_start = TODAY - timedelta(days=TODAY.weekday())
    week_net = shifts.loc[d >= wk_start, "net"].sum()
    month_net = shifts.loc[d >= TODAY.replace(day=1), "net"].sum()

    g1, g2 = st.columns(2)
    with g1: progress_card("This week (net)", week_net, float(settings["goal_weekly"]), "indigo")
    with g2: progress_card("This month (net)", month_net, float(settings["goal_monthly"]), "teal")

    st.markdown("---")
    st.subheader("📆 Month on month")
    shifts["ym"] = shifts["shift_date"].dt.to_period("M")
    mon = shifts.groupby("ym")["net"].sum().sort_index()
    cur_p = pd.Period(TODAY, "M")
    prev_p = cur_p - 1
    cur_v, prev_v = float(mon.get(cur_p, 0.0)), float(mon.get(prev_p, 0.0))
    if prev_v > 0:
        chg = (cur_v - prev_v) / prev_v * 100
        arrow = "▲" if chg >= 0 else "▼"
        delta_txt, tone = f"{arrow} {abs(chg):.0f}% vs last month", ("green" if chg >= 0 else "red")
    else:
        delta_txt, tone = "no data last month", "slate"
    m1, m2, m3 = st.columns(3)
    with m1: card(f"{cur_p.strftime('%B %Y')}", gbp(cur_v), "this month so far", "indigo")
    with m2: card(f"{prev_p.strftime('%B %Y')}", gbp(prev_v), "last month", "slate")
    with m3: card("Change", delta_txt, "", tone)
    last12 = mon.tail(12)
    last12.index = last12.index.strftime("%Y-%m")
    st.bar_chart(last12, color="#6366f1")

    st.markdown("---")
    st.subheader("⏱️ What pays best?")
    t1, t2 = st.tabs(["By weekday", "By employer"])
    with t1:
        wd = shifts.groupby(shifts["shift_date"].dt.weekday).agg(net=("net", "sum"), hrs=("hours_worked", "sum"))
        wd["£/hour"] = wd["net"] / wd["hrs"].replace(0, pd.NA)
        wd = wd.reindex(range(7))
        wd.index = list(calendar.day_abbr)
        st.caption("Average net £ per hour, by day of the week")
        st.bar_chart(wd["£/hour"].astype(float).fillna(0), color="#14b8a6")
    with t2:
        em = shifts.groupby("employer").agg(net=("net", "sum"), hrs=("hours_worked", "sum"), shifts=("id", "count")).reset_index()
        em["£/hour"] = em["net"] / em["hrs"].replace(0, pd.NA)
        em = em.sort_values("£/hour", ascending=False)
        show_table(em, {"employer": "Employer", "net": st.column_config.NumberColumn("Net total (£)", format="%.2f"),
                        "hrs": st.column_config.NumberColumn("Hours", format="%.2f"), "shifts": "Shifts",
                        "£/hour": st.column_config.NumberColumn("Net £/hour", format="%.2f")})

# ==========================================================
# PAGE: CALENDAR
# ==========================================================
elif page == PAGES[5]:
    hero("📅 Calendar", "Your shifts laid out month by month.")
    shifts = load_shifts()
    c1, c2 = st.columns(2)
    year = int(c1.number_input("Year", min_value=2020, max_value=2100, value=TODAY.year, step=1))
    month = c2.selectbox("Month", list(range(1, 13)), index=TODAY.month - 1, format_func=lambda m: calendar.month_name[m])

    by_day = {}
    month_total, month_hours = 0.0, 0.0
    if not shifts.empty:
        sub = shifts[(shifts["shift_date"].dt.year == year) & (shifts["shift_date"].dt.month == month)]
        for r in sub.itertuples():
            by_day.setdefault(r.shift_date.date(), []).append(r)
        month_total, month_hours = float(sub["gross_earning"].sum()), float(sub["hours_worked"].sum())

    cells = [f'<div class="cal-h">{h}</div>' for h in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
    for week in calendar.monthcalendar(year, month):
        for dn in week:
            if dn == 0:
                cells.append('<div class="cal-d empty"></div>')
                continue
            dd = date(year, month, dn)
            items = by_day.get(dd, [])
            inner = f'<div class="cal-n">{dn}</div>'
            for it in items:
                emp = html.escape(str(it.employer))
                inner += f'<span class="chip {emp}">{emp} {html.escape(str(it.start_time))}-{html.escape(str(it.end_time))}</span>'
            if items:
                inner += f'<div class="cal-t">{gbp(sum(i.gross_earning for i in items))}</div>'
            cells.append(f'<div class="cal-d{" today" if dd == TODAY else ""}">{inner}</div>')
    st.markdown('<div class="cal-wrap"><div class="cal">' + "".join(cells) + "</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    with k1: card("Shifts this month", f"{sum(len(v) for v in by_day.values())}", f"{calendar.month_name[month]} {year}", "slate")
    with k2: card("Hours", f"{month_hours:.2f}", "", "indigo")
    with k3: card("Gross earnings", gbp(month_total), "", "green")

# ==========================================================
# PAGE: TAX & MILEAGE
# ==========================================================
elif page == PAGES[6]:
    hero("🧾 Tax & Mileage", "UK tax-year summary (6 April – 5 April) with rough tax and mileage figures.")
    st.warning("These are **estimates only** for a self-employed sole trader. They ignore other income, "
               "allowances, student loans etc. Always check current rates on gov.uk or with an accountant.")
    shifts = load_shifts()

    with st.expander("⚙️ Tax & mileage rates (editable)"):
        with st.form("tax_form"):
            keys = [("tax_pa", "Personal allowance (£)"), ("tax_basic_upper", "Basic-rate limit (£)"),
                    ("tax_add_threshold", "Additional-rate threshold (£)"), ("tax_basic_rate", "Basic rate (%)"),
                    ("tax_higher_rate", "Higher rate (%)"), ("tax_add_rate", "Additional rate (%)"),
                    ("ni_lower", "Class 4 NI lower limit (£)"), ("ni_upper", "Class 4 NI upper limit (£)"),
                    ("ni_main", "Class 4 NI main rate (%)"), ("ni_top", "Class 4 NI rate above upper (%)"),
                    ("mile_rate_1", "Mileage rate up to threshold (£/mile)"), ("mile_rate_2", "Mileage rate above (£/mile)"),
                    ("mile_threshold", "Mileage threshold (miles)")]
            cols = st.columns(3)
            newv = {k: cols[i % 3].number_input(lbl, min_value=0.0, value=float(settings[k]), step=0.01 if "rate" in k and "tax" not in k else 1.0, format="%.2f", key="tx_" + k)
                    for i, (k, lbl) in enumerate(keys)}
            if st.form_submit_button("Save rates", type="primary"):
                for k, v in newv.items():
                    save_setting(k, v)
                st.rerun()

    if shifts.empty:
        st.info("No shifts yet.")
        st.stop()

    years = sorted({uk_tax_year(x.date()) for x in shifts["shift_date"]}, reverse=True)
    cur_ty = uk_tax_year(TODAY)
    if cur_ty not in years:
        years.insert(0, cur_ty)
    f1, f2 = st.columns(2)
    ty = f1.selectbox("Tax year", years, index=years.index(cur_ty), format_func=lambda y: f"{y}/{str(y + 1)[2:]}")
    incl = f2.multiselect("Employers included (untick any that are PAYE)", EMPLOYERS, default=EMPLOYERS)
    method = st.radio("Vehicle costs method", ["Actual fuel & expenses", "HMRC mileage allowance + other expenses"], horizontal=True)

    s_d, e_d = date(ty, 4, 6), date(ty + 1, 4, 5)
    dts = shifts["shift_date"].dt.date
    ysh = shifts[(dts >= s_d) & (dts <= e_d) & (shifts["employer"].isin(incl))]
    if ysh.empty:
        st.info("No shifts in this tax year for the selected employers.")
        st.stop()

    gross = float(ysh["gross_earning"].sum())
    fuel, other = float(ysh["fuel_cost"].sum()), float(ysh["expense_cost"].sum())
    total_miles = float(ysh["miles"].sum())
    thr = settings["mile_threshold"]
    allowance = min(total_miles, thr) * settings["mile_rate_1"] + max(0.0, total_miles - thr) * settings["mile_rate_2"]
    expenses = (fuel + other) if method.startswith("Actual") else (allowance + other)
    profit = max(0.0, gross - expenses)
    tax, ni = est_income_tax(profit, settings), est_class4_ni(profit, settings)
    total_due = tax + ni

    st.markdown("---")
    st.subheader(f"Tax year {ty}/{str(ty + 1)[2:]}")
    a = st.columns(4)
    with a[0]: card("Gross income", gbp(gross), f"{len(ysh)} shifts", "indigo")
    with a[1]: card("Allowable expenses", gbp(expenses), method.split(" +")[0], "red")
    with a[2]: card("Taxable profit", gbp(profit), "", "teal")
    with a[3]: card("Est. tax + NI", gbp(total_due), f"≈ {total_due / profit * 100:.0f}% of profit" if profit else "", "amber")
    b = st.columns(3)
    with b[0]: card("Income tax (est.)", gbp(tax), "", "slate")
    with b[1]: card("Class 4 NI (est.)", gbp(ni), "", "slate")
    with b[2]: card("Take-home (est.)", gbp(profit - total_due), "profit − tax − NI", "green")

    st.markdown("---")
    st.subheader("🚗 Mileage")
    mm = st.columns(4)
    with mm[0]: card("Miles driven", f"{total_miles:,.1f}", "logged on shifts", "indigo")
    with mm[1]: card("HMRC allowance", gbp(allowance), f"{settings['mile_rate_1'] * 100:.0f}p/{settings['mile_rate_2'] * 100:.0f}p per mile", "teal")
    with mm[2]: card("Actual fuel spent", gbp(fuel), "", "red")
    better = allowance - fuel
    with mm[3]: card("Allowance vs fuel", gbp(better), "allowance claim is better" if better > 0 else "actual fuel is better", "green" if better > 0 else "amber")
    if total_miles > 0:
        mm2 = st.columns(2)
        with mm2[0]: card("Mileage earned from employers", gbp(ysh["mileage_earning"].sum()), f"{gbp(ysh['mileage_earning'].sum() / total_miles)} per mile", "teal")
        with mm2[1]: card("Profit per mile", gbp((gross - fuel - other) / total_miles), "gross − fuel − expenses", "indigo")
    else:
        st.caption("Log **Miles driven** when entering shifts to unlock per-mile figures.")

# ==========================================================
# PAGE: SETTINGS & BACKUP
# ==========================================================
elif page == PAGES[7]:
    hero("🛠️ Settings & Backup", "Security, backups and CSV import.")
    show_flash()
    t_sec, t_bak, t_imp = st.tabs(["🔐 Security", "💾 Backup & restore", "📥 Import CSV"])

    with t_sec:
        s1, s2 = st.columns(2)
        with s1: card("Password", "Hashed" if get_secret("APP_PASSWORD_HASH") else "Plain text", "APP_PASSWORD_HASH" if get_secret("APP_PASSWORD_HASH") else "switch to a hash below", "green" if get_secret("APP_PASSWORD_HASH") else "amber")
        with s2: card("Two-factor login", "On" if get_secret("APP_TOTP_SECRET") else "Off", "APP_TOTP_SECRET", "green" if get_secret("APP_TOTP_SECRET") else "amber")
        st.caption(f"Lockout: {MAX_FAILS} failed logins locks sign-in for 15 minutes.")

        st.markdown("#### Generate a password hash")
        newpw = st.text_input("New password", type="password", key="newpw")
        if st.button("Generate hash") and newpw:
            ss.pw_hash = make_password_hash(newpw)
        if ss.get("pw_hash"):
            st.code(f'APP_PASSWORD_HASH = "{ss.pw_hash}"', language="toml")
            st.caption("Paste into your Streamlit secrets and delete `APP_PASSWORD`.")

        st.markdown("#### Two-factor authentication (authenticator app)")
        if st.button("Generate a new 2FA secret"):
            ss.totp_new = base64.b32encode(os.urandom(20)).decode()
        if ss.get("totp_new"):
            uri = f"otpauth://totp/RotaTracker:{get_secret('APP_USERNAME', 'user')}?secret={ss.totp_new}&issuer=RotaTracker"
            st.code(f'APP_TOTP_SECRET = "{ss.totp_new}"', language="toml")
            try:
                import qrcode
                img = qrcode.make(uri)
                buf = io.BytesIO(); img.save(buf, format="PNG")
                st.image(buf.getvalue(), width=200)
            except Exception:
                st.caption("Add this key manually in Google Authenticator / Authy (type: time-based).")
            test = st.text_input("Enter the 6-digit code from your app to test", key="totp_test")
            if test:
                st.success("✅ Code is correct") if verify_totp(ss.totp_new, test) else st.error("Code doesn't match yet")
            st.caption("Once the test passes, paste the line above into your Streamlit secrets.")

    with t_bak:
        TABLE_COLS = {
            "shifts": ["id", "shift_date", "employer", "start_time", "end_time", "hourly_rate", "hours_worked",
                       "hourly_earning", "mileage_earning", "tips", "fuel_cost", "expense_cost", "gross_earning", "paid", "miles"],
            "gogo_transactions": ["id", "trans_date", "trans_type", "amount", "notes"],
            "shift_templates": ["id", "name", "employer", "start_time", "end_time", "hourly_rate"],
            "app_settings": ["key", "value"],
        }
        st.markdown("#### Download a full backup")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for tname in TABLE_COLS:
                zf.writestr(f"{tname}.csv", query_df(f"SELECT * FROM {tname}").to_csv(index=False))
        st.download_button("⬇️ Download backup (.zip)", buf.getvalue(), f"rota_backup_{TODAY:%Y%m%d}.zip", "application/zip", type="primary")

        st.markdown("#### Restore from a backup")
        st.warning("Restoring **replaces all current data** with the contents of the backup. Download a fresh backup first.")
        up = st.file_uploader("Backup .zip", type="zip", key="restore_zip")
        ok = st.checkbox("I understand this will overwrite my current data", key="restore_ok")
        if st.button("Restore now", disabled=not (up and ok)):
            conn = get_conn()
            conn.autocommit = False
            try:
                zf = zipfile.ZipFile(io.BytesIO(up.getvalue()))
                with conn.cursor() as cur:
                    for tname, allowed in TABLE_COLS.items():
                        fn = f"{tname}.csv"
                        if fn not in zf.namelist():
                            continue
                        df = pd.read_csv(zf.open(fn))
                        use = [c for c in allowed if c in df.columns]
                        cur.execute(f"TRUNCATE {tname}")
                        rows = [tuple(None if pd.isna(v) else (v.item() if hasattr(v, "item") else v) for v in row)
                                for row in df[use].itertuples(index=False)]
                        if rows:
                            cur.executemany(f"INSERT INTO {tname} ({','.join(use)}) VALUES ({','.join(['%s'] * len(use))})", rows)
                        if "id" in allowed:
                            cur.execute(f"SELECT setval(pg_get_serial_sequence('{tname}','id'), "
                                        f"COALESCE((SELECT MAX(id) FROM {tname}),1), (SELECT MAX(id) FROM {tname}) IS NOT NULL)")
                conn.commit()
                ss.flash = ("success", "Backup restored successfully.")
            except Exception as e:
                conn.rollback()
                ss.flash = ("error", f"Restore failed, nothing was changed: {e}")
            finally:
                conn.autocommit = True
            st.rerun()

    with t_imp:
        st.markdown("#### Import shifts from CSV (adds to existing data)")
        st.caption("Required columns: `shift_date`, `employer`, `start_time`, `end_time`. "
                   "Optional: `hourly_rate`, `mileage_earning`, `tips`, `fuel_cost`, `expense_cost`, `total_paid` (CHINESE), `miles`, `paid`. "
                   "Dates like 31/10/2026 are read day-first.")
        sample = pd.DataFrame([{"shift_date": "31/10/2026", "employer": "DANIELLE", "start_time": "09:00", "end_time": "17:00",
                                "hourly_rate": 14.0, "mileage_earning": 0, "tips": 5, "fuel_cost": 0, "expense_cost": 0, "miles": 0, "paid": False}])
        st.download_button("Download sample CSV", sample.to_csv(index=False).encode(), "shifts_sample.csv", "text/csv")
        up = st.file_uploader("Shifts CSV", type="csv", key="import_csv")
        if up:
            try:
                imp = pd.read_csv(up)
                imp.columns = [c.strip().lower() for c in imp.columns]
                missing = [c for c in ["shift_date", "employer", "start_time", "end_time"] if c not in imp.columns]
                if missing:
                    st.error(f"Missing column(s): {', '.join(missing)}")
                else:
                    imp["_date"] = pd.to_datetime(imp["shift_date"], dayfirst=True, errors="coerce")
                    imp["employer"] = imp["employer"].astype(str).str.strip().str.upper()
                    bad = imp[imp["_date"].isna() | ~imp["employer"].isin(EMPLOYERS)]
                    good = imp.drop(bad.index)
                    st.write(f"**{len(good)}** valid row(s), **{len(bad)}** skipped (bad date or unknown employer).")
                    show_table(good.drop(columns=["_date"]).head(20))
                    if len(good) and st.button(f"Import {len(good)} shift(s)", type="primary"):
                        num = lambda r, c: float(r[c]) if c in imp.columns and pd.notna(r[c]) else 0.0
                        n = 0
                        for _, r in good.iterrows():
                            st_t, en_t = parse_hhmm(r["start_time"]), parse_hhmm(r["end_time"])
                            hrs = calculate_hours(st_t, en_t)
                            rate = num(r, "hourly_rate") or float(settings[f"rate_{r['employer']}"])
                            hE, mE, gE, _w = compute_shift(r["employer"], hrs, rate, num(r, "total_paid"), num(r, "mileage_earning"), num(r, "tips"))
                            pd_flag = bool(r["paid"]) if "paid" in imp.columns and pd.notna(r["paid"]) else True
                            insert_shift(r["_date"].date(), r["employer"], st_t.strftime("%H:%M"), en_t.strftime("%H:%M"),
                                         rate, hrs, hE, mE, num(r, "tips"), num(r, "fuel_cost"), num(r, "expense_cost"), gE, num(r, "miles"), pd_flag)
                            n += 1
                        ss.flash = ("success", f"Imported {n} shift(s).")
                        st.rerun()
            except Exception as e:
                st.error(f"Could not read the CSV: {e}")
