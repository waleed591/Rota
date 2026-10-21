import hmac
import os
import time as time_mod
from datetime import date, datetime, time, timedelta

import pandas as pd
import psycopg2
import streamlit as st

# ==========================================================
# PAGE CONFIG (must be the first Streamlit call, only once)
# ==========================================================
st.set_page_config(page_title="Rota Earnings Tracker", page_icon="💷", layout="wide")

# ==========================================================
# THEME / CSS  (translucent colours -> works in light & dark)
# ==========================================================
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

/* Hide Streamlit chrome WITHOUT hiding the sidebar toggle */
#MainMenu, footer, [data-testid="stToolbar"], .stAppDeployButton,
[data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }

/* Hero banner */
.hero {
    padding: 26px 30px; border-radius: 20px; margin-bottom: 22px; color: #fff;
    background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 55%, #0ea5e9 100%);
    box-shadow: 0 12px 32px rgba(79,70,229,.35);
}
.hero-title { font-size: 1.9rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.2; }
.hero-sub { opacity: .88; margin-top: 4px; font-size: .98rem; }

/* Stat cards */
.card {
    position: relative; overflow: hidden; height: 100%;
    padding: 16px 18px 14px 22px; margin-bottom: 12px; border-radius: 16px;
    border: 1px solid rgba(128,128,128,.22);
    background: rgba(128,128,128,.07);
    box-shadow: 0 4px 18px rgba(0,0,0,.06);
    transition: transform .15s ease, box-shadow .15s ease;
}
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

/* Balance banner */
.balance {
    padding: 22px 28px; border-radius: 20px; color: #fff; margin: 6px 0 18px 0;
    display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;
    box-shadow: 0 12px 30px rgba(0,0,0,.18);
}
.balance.owed { background: linear-gradient(120deg,#059669,#10b981 60%,#2dd4bf); }
.balance.owe  { background: linear-gradient(120deg,#dc2626,#f97316); }
.balance .b-label { font-size: .8rem; text-transform: uppercase; letter-spacing: .1em; opacity: .9; font-weight: 600; }
.balance .b-value { font-size: 2.3rem; font-weight: 800; letter-spacing: -.02em; }

/* Sidebar */
[data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,.2); }
.brand { font-size: 1.3rem; font-weight: 800; padding: 6px 0 14px 0; letter-spacing: -.01em; }

/* Inputs, buttons, tabs, expanders */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] { border-radius: 12px !important; }
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"],
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background: linear-gradient(120deg,#4f46e5,#7c3aed) !important; border: none !important;
    color: #fff !important; font-weight: 600; border-radius: 12px !important; padding: .55rem 1.3rem;
    box-shadow: 0 6px 18px rgba(79,70,229,.35);
}
button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    filter: brightness(1.08); transform: translateY(-1px);
}
button[data-testid^="stBaseButton-secondary"] { border-radius: 12px !important; font-weight: 600; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: 8px 18px; font-weight: 600; }
[data-testid="stExpander"] {
    border-radius: 14px; border: 1px solid rgba(128,128,128,.25); background: rgba(128,128,128,.05);
}
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid rgba(128,128,128,.2); }
h2, h3 { letter-spacing: -.01em; font-weight: 700 !important; }
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)


# ==========================================================
# SMALL UI HELPERS
# ==========================================================
def gbp(x):
    x = float(x or 0)
    return f"-£{abs(x):,.2f}" if x < 0 else f"£{x:,.2f}"


def hero(title, subtitle=""):
    st.markdown(
        f'<div class="hero"><div class="hero-title">{title}</div>'
        f'<div class="hero-sub">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


def card(label, value, sub="", tone="indigo"):
    st.markdown(
        f'<div class="card {tone}"><div class="card-label">{label}</div>'
        f'<div class="card-value">{value}</div><div class="card-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def show_table(df, column_config=None):
    """st.dataframe wrapper that works on old and new Streamlit versions."""
    try:
        st.dataframe(df, width="stretch", hide_index=True, column_config=column_config)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True, column_config=column_config)


def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


# ==========================================================
# 1. AUTHENTICATION
# ==========================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        st.markdown("<div style='height:7vh'></div>", unsafe_allow_html=True)
        hero("🔒 Rota Tracker", "Sign in to view your shifts and earnings.")

        valid_user = get_secret("APP_USERNAME")
        valid_pass = get_secret("APP_PASSWORD")

        if not valid_user or not valid_pass:
            st.error(
                "Login is not configured. Add `APP_USERNAME` and `APP_PASSWORD` "
                "to your Streamlit secrets."
            )
        else:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign in", type="primary")

            if submitted:
                ok_user = hmac.compare_digest(username.encode(), str(valid_user).encode())
                ok_pass = hmac.compare_digest(password.encode(), str(valid_pass).encode())
                if ok_user and ok_pass:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    time_mod.sleep(1)  # slows down brute-force guessing
                    st.error("❌ Invalid username or password.")
    st.stop()

# ==========================================================
# 2. DATABASE
# ==========================================================
DATABASE_URL = get_secret("DATABASE_URL")
if not DATABASE_URL:
    st.error("⚠️ Database URL not configured.")
    st.stop()


@st.cache_resource(show_spinner=False)
def _connect(url):
    conn = psycopg2.connect(url, connect_timeout=10)
    conn.autocommit = True  # no stuck/aborted transactions after an error
    return conn


def get_conn():
    """Return a live connection, reconnecting if it dropped."""
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


try:
    run("""CREATE TABLE IF NOT EXISTS shifts (
              id SERIAL PRIMARY KEY, shift_date DATE, employer TEXT,
              start_time TEXT, end_time TEXT, hourly_rate REAL, hours_worked REAL,
              hourly_earning REAL, mileage_earning REAL, tips REAL,
              fuel_cost REAL, expense_cost REAL, gross_earning REAL)""")
    run("""CREATE TABLE IF NOT EXISTS gogo_transactions (
              id SERIAL PRIMARY KEY, trans_date DATE, trans_type TEXT,
              amount REAL, notes TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)""")
except Exception as e:
    st.error(f"⚠️ Database connection failed: {e}")
    st.stop()

# ---------- persistent settings (previously lost on every refresh) ----------
SETTING_DEFAULTS = {
    "rate_GOGO": "9.50", "rate_CHINESE": "11.00", "rate_DANIELLE": "14.00",
    "gogo_rent": "400.00", "gogo_start": "384.75",
}


def load_settings():
    try:
        rows = query_df("SELECT key, value FROM app_settings")
        stored = dict(zip(rows["key"], rows["value"]))
    except Exception:
        stored = {}
    merged = {**SETTING_DEFAULTS, **stored}
    return {k: float(v) for k, v in merged.items()}


def save_setting(key, value):
    run("""INSERT INTO app_settings (key, value) VALUES (%s, %s)
           ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""", (key, str(value)))


# ---------- data loaders ----------
SHIFT_NUM_COLS = ["hourly_rate", "hours_worked", "hourly_earning", "mileage_earning",
                  "tips", "fuel_cost", "expense_cost", "gross_earning"]


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


def calculate_hours(start_t, end_t):
    start_dt = datetime.combine(date.today(), start_t)
    end_dt = datetime.combine(date.today(), end_t)
    if end_dt < start_dt:  # overnight shift
        end_dt += timedelta(days=1)
    return max(0.0, (end_dt - start_dt).total_seconds() / 3600)


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


# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.markdown('<div class="brand">💷 Rota Tracker</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        ["➕ Enter Rota", "📊 History & Earnings", "🏠 GOGO Ledger"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()

settings = load_settings()
EMPLOYERS = ["GOGO", "CHINESE", "DANIELLE"]


# ==========================================================
# PAGE 1: ENTER ROTA
# ==========================================================
if page == "➕ Enter Rota":
    hero("➕ Log a Shift", "Record your hours, tips and expenses in seconds.")

    if "rate_input" not in st.session_state:
        st.session_state.rate_input = settings["rate_GOGO"]

    def on_employer_change():
        emp = st.session_state.employer_sel
        st.session_state.rate_input = load_settings()[f"rate_{emp}"]

    with st.expander("⚙️ Edit Default Hourly Rates"):
        with st.form("rates_form"):
            rc = st.columns(3)
            new_rates = {
                emp: rc[i].number_input(f"{emp} default (£)", min_value=0.0,
                                        value=settings[f"rate_{emp}"], step=0.10, format="%.2f")
                for i, emp in enumerate(EMPLOYERS)
            }
            if st.form_submit_button("Save default rates", type="primary"):
                for emp, val in new_rates.items():
                    save_setting(f"rate_{emp}", val)
                current = st.session_state.get("employer_sel", "GOGO")
                st.session_state.rate_input = new_rates[current]
                st.success("Default rates saved.")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("🗓️ When & where")
        employer = st.selectbox("Employer / Location", EMPLOYERS, key="employer_sel",
                                on_change=on_employer_change)
        shift_date = st.date_input("Shift Date", value=date.today())
        t1, t2 = st.columns(2)
        start_time = t1.time_input("Start Time", value=time(9, 0))
        end_time = t2.time_input("End Time", value=time(17, 0))

    with col2:
        st.subheader("💷 Pay details")
        hourly_rate = st.number_input("Hourly Rate (£)", min_value=0.0, step=0.10,
                                      format="%.2f", key="rate_input")
        paid_chinese, mileage_in = 0.0, 0.0

        if employer == "CHINESE":
            st.info("💡 **Chinese shift mode:** enter the total paid. Mileage is calculated automatically.")
            paid_chinese = st.number_input("Total Amount Paid by Employer (£)", min_value=0.0,
                                           value=0.0, step=1.0, format="%.2f")
            tips = st.number_input("Tips Earned (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        else:
            a1, a2 = st.columns(2)
            mileage_in = a1.number_input("Mileage Earned (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            tips = a2.number_input("Tips Earned (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")

        d1, d2 = st.columns(2)
        fuel_cost = d1.number_input("Fuel Cost (£) −", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        expense_cost = d2.number_input("Other Expenses (£) −", min_value=0.0, value=0.0, step=1.0, format="%.2f")

    # ----- live preview -----
    hours = calculate_hours(start_time, end_time)
    hourly_e, mileage_e, gross_e, warn = compute_shift(
        employer, hours, hourly_rate, paid_chinese, mileage_in, tips)
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
            run("""INSERT INTO shifts
                   (shift_date, employer, start_time, end_time, hourly_rate, hours_worked,
                    hourly_earning, mileage_earning, tips, fuel_cost, expense_cost, gross_earning)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (shift_date, employer, start_time.strftime("%H:%M"), end_time.strftime("%H:%M"),
                 hourly_rate, round(hours, 2), round(hourly_e, 2), round(mileage_e, 2),
                 round(tips, 2), round(fuel_cost, 2), round(expense_cost, 2), round(gross_e, 2)))
            st.success(f"Shift saved! You worked **{hours:.2f} hours** and earned **{gbp(gross_e)}** gross.")
            st.balloons()

    recent = load_shifts()
    if not recent.empty:
        st.markdown("---")
        st.subheader("🕒 Recent shifts")
        r = recent.head(5)[["shift_date", "employer", "start_time", "end_time",
                            "hours_worked", "gross_earning"]]
        show_table(r, {
            "shift_date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
            "employer": "Location", "start_time": "Start", "end_time": "End",
            "hours_worked": st.column_config.NumberColumn("Hours", format="%.2f"),
            "gross_earning": st.column_config.NumberColumn("Gross (£)", format="%.2f"),
        })


# ==========================================================
# PAGE 2: HISTORY & EARNINGS
# ==========================================================
elif page == "📊 History & Earnings":
    hero("📊 Earnings History", "Filter, analyse and review everything you've worked.")
    df = load_shifts()

    if df.empty:
        st.info("No shifts recorded yet. Head to **Enter Rota** to add your first one.")
    else:
        show_net = st.toggle("📉 Show net earnings (subtract fuel & expenses)", value=False)

        f1, f2 = st.columns(2)
        with f1:
            employers = ["All Employers"] + sorted(df["employer"].dropna().unique().tolist())
            selected_employer = st.selectbox("Filter by Employer", employers)
        with f2:
            min_d, max_d = df["shift_date"].min().date(), df["shift_date"].max().date()
            date_range = st.date_input("Date Range", value=(min_d, max_d),
                                       min_value=min_d, max_value=max_d)

        fdf = df.copy()
        if selected_employer != "All Employers":
            fdf = fdf[fdf["employer"] == selected_employer]
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            s, e = date_range
            fdf = fdf[(fdf["shift_date"].dt.date >= s) & (fdf["shift_date"].dt.date <= e)]
        else:
            st.info("Pick an end date to apply the date filter.")

        if fdf.empty:
            st.warning("No shifts match these filters.")
            st.stop()

        fdf = fdf.copy()
        fdf["deductions"] = fdf["fuel_cost"] + fdf["expense_cost"]
        fdf["final"] = fdf["gross_earning"] - fdf["deductions"] if show_net else fdf["gross_earning"]

        hours_total = fdf["hours_worked"].sum()
        gross_total = fdf["gross_earning"].sum()
        deduct_total = fdf["deductions"].sum()
        net_total = gross_total - deduct_total
        headline = net_total if show_net else gross_total

        st.markdown("---")
        st.subheader("Summary")
        k = st.columns(4)
        with k[0]: card("Shifts", f"{len(fdf)}", "in selection", "slate")
        with k[1]: card("Hours", f"{hours_total:.2f}", "total worked", "indigo")
        with k[2]: card("Hourly pay", gbp(fdf["hourly_earning"].sum()), "base wages", "teal")
        with k[3]: card("Avg £/hour", gbp(headline / hours_total if hours_total else 0),
                        "net" if show_net else "gross", "amber")
        k = st.columns(4)
        with k[0]: card("Mileage", gbp(fdf["mileage_earning"].sum()), "", "teal")
        with k[1]: card("Tips", gbp(fdf["tips"].sum()), "", "green")
        with k[2]: card("Fuel & expenses", gbp(-deduct_total), "", "red")
        with k[3]: card("NET EARNINGS" if show_net else "TOTAL EARNINGS", gbp(headline),
                        f"gross {gbp(gross_total)}" if show_net else "before costs",
                        "green" if headline >= 0 else "red")

        st.markdown("---")
        tab_log, tab_week, tab_emp = st.tabs(["📋 Shift log", "📈 Weekly trend", "🏢 By employer"])

        with tab_log:
            log = fdf[["shift_date", "employer", "start_time", "end_time", "hours_worked",
                       "hourly_earning", "mileage_earning", "tips", "fuel_cost",
                       "expense_cost", "final"]]
            money = lambda t: st.column_config.NumberColumn(t, format="%.2f")
            show_table(log, {
                "shift_date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                "employer": "Location", "start_time": "Start", "end_time": "End",
                "hours_worked": st.column_config.NumberColumn("Hours", format="%.2f"),
                "hourly_earning": money("Hourly (£)"), "mileage_earning": money("Mileage (£)"),
                "tips": money("Tips (£)"), "fuel_cost": money("Fuel (−£)"),
                "expense_cost": money("Expense (−£)"),
                "final": money("Net (£)" if show_net else "Gross (£)"),
            })

        with tab_week:
            weekly = fdf.groupby("week_start")["final"].sum().sort_index()
            st.caption("Earnings per week (weeks start on Monday)")
            st.bar_chart(weekly, color="#6366f1")

        with tab_emp:
            by_emp = fdf.groupby("employer")["final"].sum().sort_values(ascending=False)
            st.caption("Earnings per employer")
            st.bar_chart(by_emp, color="#14b8a6")

        with st.expander("⚠️ Delete a shift"):
            labels = {
                int(r.id): f"{r.shift_date:%d %b %Y} · {r.employer} · {r.start_time}–{r.end_time} · {gbp(r.gross_earning)}"
                for r in fdf.itertuples()
            }
            sel = st.selectbox("Select shift to delete", list(labels.keys()), format_func=labels.get)
            sure = st.checkbox("Yes, delete this shift permanently", key="confirm_del_shift")
            if st.button("Delete selected shift", disabled=not sure):
                run("DELETE FROM shifts WHERE id = %s", (sel,))
                st.session_state.confirm_del_shift = False
                st.rerun()


# ==========================================================
# PAGE 3: GOGO LEDGER
# ==========================================================
elif page == "🏠 GOGO Ledger":
    hero("🏠 GOGO Rent & Payments", "Wages earned, rent deducted and payments received — with a running balance.")

    start_balance = settings["gogo_start"]
    monthly_rent = settings["gogo_rent"]

    if "flash" in st.session_state:
        level, msg = st.session_state.pop("flash")
        getattr(st, level)(msg)

    with st.expander("⚙️ GOGO Settings"):
        with st.form("gogo_settings"):
            s1, s2 = st.columns(2)
            new_rent = s1.number_input("Monthly Rent Amount (£)", min_value=0.0, value=monthly_rent,
                                       step=10.0, format="%.2f")
            new_start = s2.number_input("Starting Balance (£)", min_value=-10000.0, value=start_balance,
                                        step=10.0, format="%.2f")
            if st.form_submit_button("Save settings", type="primary"):
                save_setting("gogo_rent", new_rent)
                save_setting("gogo_start", new_start)
                st.rerun()

    # ---------- transaction form (uses callbacks so inputs can reset) ----------
    TYPES = ["Payment Received from Owner", "Rent Deducted by Owner"]
    if "trans_amt" not in st.session_state:
        st.session_state.trans_amt = 0.0
    if "trans_notes" not in st.session_state:
        st.session_state.trans_notes = ""

    def on_type_change():
        is_rent = st.session_state.trans_type == TYPES[1]
        st.session_state.trans_amt = load_settings()["gogo_rent"] if is_rent else 0.0

    def add_transaction():
        amt = float(st.session_state.trans_amt)
        if amt <= 0:
            st.session_state.flash = ("error", "Enter an amount greater than £0.")
            return
        db_type = "RENT" if st.session_state.trans_type == TYPES[1] else "PAYMENT"
        run("""INSERT INTO gogo_transactions (trans_date, trans_type, amount, notes)
               VALUES (%s, %s, %s, %s)""",
            (st.session_state.trans_date, db_type, round(amt, 2), st.session_state.trans_notes.strip()))
        st.session_state.trans_amt = 0.0
        st.session_state.trans_notes = ""
        st.session_state.flash = ("success", "Transaction added successfully!")

    # ---------- build the FULL ledger (so balances are always correct) ----------
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

    ledger = build_ledger(start_balance)
    today = date.today()

    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("➕ Add transaction")
        st.selectbox("Transaction Type", TYPES, key="trans_type", on_change=on_type_change)
        st.date_input("Date", value=today, key="trans_date")
        st.number_input("Amount (£)", min_value=0.0, step=1.0, format="%.2f", key="trans_amt")
        st.text_input("Notes (optional)", placeholder="e.g. Cash, bank transfer", key="trans_notes")
        st.button("Add Transaction", type="primary", on_click=add_transaction)

    with right:
        st.subheader("🗓️ Period")
        preset = st.radio("Show", ["This month", "Last 30 days", "All time", "Custom"],
                          horizontal=True, label_visibility="collapsed")
        if preset == "This month":
            start_d, end_d = today.replace(day=1), today
        elif preset == "Last 30 days":
            start_d, end_d = today - timedelta(days=30), today
        elif preset == "All time":
            if ledger.empty:
                start_d, end_d = today.replace(day=1), today
            else:
                start_d = ledger["Date"].min().date()
                end_d = max(today, ledger["Date"].max().date())
        else:
            rng = st.date_input("Date range", value=(today.replace(day=1), today))
            if not (isinstance(rng, (tuple, list)) and len(rng) == 2):
                st.info("Pick an end date.")
                st.stop()
            start_d, end_d = rng
        st.caption(f"Showing {start_d:%d %b %Y} → {end_d:%d %b %Y}")

    # ---------- balances ----------
    if ledger.empty:
        balance_now, opening, period = start_balance, start_balance, ledger
    else:
        dates = ledger["Date"].dt.date
        balance_now = start_balance + ledger.loc[dates <= today, "Amount"].sum()
        opening = start_balance + ledger.loc[dates < start_d, "Amount"].sum()
        period = ledger[(dates >= start_d) & (dates <= end_d)]

    wages = period.loc[period["Category"] == "Wages", "Amount"].sum() if not period.empty else 0.0
    rent = -period.loc[period["Category"] == "Rent", "Amount"].sum() if not period.empty else 0.0
    paid = -period.loc[period["Category"] == "Payment", "Amount"].sum() if not period.empty else 0.0
    net_period = wages - rent - paid
    closing = opening + net_period

    st.markdown("---")
    cls, label, amt = ("owed", "Owner currently owes you", balance_now) if balance_now >= 0 \
        else ("owe", "You currently owe owner", abs(balance_now))
    st.markdown(
        f'<div class="balance {cls}"><div><div class="b-label">{label}</div>'
        f'<div class="b-value">{gbp(amt)}</div></div>'
        f'<div class="b-label">as of {today:%d %b %Y}</div></div>',
        unsafe_allow_html=True,
    )

    st.subheader("Summary for selected period")
    m = st.columns(3)
    with m[0]: card("Base wages earned", gbp(wages), "", "green")
    with m[1]: card("Rent deducted", gbp(rent), "", "red")
    with m[2]: card("Payments received", gbp(paid), "", "amber")
    m = st.columns(3)
    with m[0]: card("Opening balance", gbp(opening), f"before {start_d:%d %b}", "slate")
    with m[1]: card("Net for period", gbp(net_period), "wages − rent − payments",
                    "green" if net_period >= 0 else "red")
    with m[2]: card("Closing balance", gbp(closing), f"at {end_d:%d %b}", "indigo")

    st.markdown("---")

    if ledger.empty:
        st.info("No GOGO shifts or transactions recorded yet.")
    else:
        tab_m, tab_l = st.tabs(["📅 Monthly breakdown (with rollover)", "📋 Detailed ledger"])

        with tab_m:
            monthly = ledger.groupby("Month").apply(
                lambda g: pd.Series({
                    "Wages": g.loc[g["Category"] == "Wages", "Amount"].sum(),
                    "Rent": -g.loc[g["Category"] == "Rent", "Amount"].sum(),
                    "Payments": -g.loc[g["Category"] == "Payment", "Amount"].sum(),
                    "Net": g["Amount"].sum(),
                })
            ).reset_index()
            monthly["Closing"] = start_balance + monthly["Net"].cumsum()
            monthly["Rollover"] = monthly["Closing"] - monthly["Net"]
            in_range = (monthly["Month"] >= pd.Period(start_d, "M")) & (monthly["Month"] <= pd.Period(end_d, "M"))
            monthly = monthly[in_range].copy()
            monthly["Month"] = monthly["Month"].dt.strftime("%b %Y")
            monthly = monthly[["Month", "Rollover", "Wages", "Rent", "Payments", "Net", "Closing"]]
            n = lambda t: st.column_config.NumberColumn(t, format="%.2f")
            show_table(monthly, {
                "Rollover": n("Rollover in (£)"), "Wages": n("Wages (£)"), "Rent": n("Rent (£)"),
                "Payments": n("Payments (£)"), "Net": n("Net (£)"), "Closing": n("Balance end (£)"),
            })

        with tab_l:
            if period.empty:
                st.info("No entries in the selected period.")
            else:
                disp = period.sort_values(["Date", "Order"], ascending=False, kind="mergesort")
                disp = disp[["Date", "Details", "Category", "Amount", "Balance"]]
                show_table(disp, {
                    "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                    "Amount": st.column_config.NumberColumn("Amount (£)", format="%.2f"),
                    "Balance": st.column_config.NumberColumn("Running balance (£)", format="%.2f"),
                })

        with st.expander("⚠️ Delete a transaction"):
            tx = period[period["ID"].notna()] if not period.empty else period
            if tx.empty:
                st.info("No transactions in this period.")
            else:
                labels = {
                    int(r.ID): f"{r.Date:%d %b %Y} · {r.Category} · {gbp(abs(r.Amount))}"
                    for r in tx.sort_values("Date", ascending=False).itertuples()
                }
                sel = st.selectbox("Select transaction to delete", list(labels.keys()),
                                   format_func=labels.get)
                sure = st.checkbox("Yes, delete this transaction permanently", key="confirm_del_tx")
                if st.button("Delete transaction", disabled=not sure):
                    run("DELETE FROM gogo_transactions WHERE id = %s", (sel,))
                    st.session_state.confirm_del_tx = False
                    st.rerun()
