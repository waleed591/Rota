import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, time
import os

# ==========================================
# 1. AUTHENTICATION CHECK
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.set_page_config(page_title="Login", page_icon="🔒", layout="centered")
    st.title("🔒 Rota Tracker Login")
    st.markdown("Please enter your credentials to access the app.")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            # These are checked against your secure Streamlit Secrets
            valid_user = st.secrets.get("APP_USERNAME", "admin")
            valid_pass = st.secrets.get("APP_PASSWORD", "password")
            
            if username == valid_user and password == valid_pass:
                st.session_state.authenticated = True
                st.success("Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")
    
    st.stop() # Stops the app from loading the rest of the code until logged in

# ==========================================
# 2. MAIN APP (Only runs if authenticated)
# ==========================================
st.set_page_config(page_title="Rota Earnings Tracker", page_icon="💷", layout="wide")
st.title("💷 Rota & Earnings Tracker")

# Add Logout button to the top of the sidebar
if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.rerun()

# Hide Streamlit menu for app-like feel
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- DATABASE SETUP ---
DATABASE_URL = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL"))

if not DATABASE_URL:
    st.error("⚠️ Database URL not configured.")
    st.stop()

try:
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
except Exception as e:
    st.error(f"⚠️ Database connection failed: {e}")
    st.stop()

c.execute('''CREATE TABLE IF NOT EXISTS shifts
             (id SERIAL PRIMARY KEY,
              shift_date DATE,
              employer TEXT,
              start_time TEXT,
              end_time TEXT,
              hourly_rate REAL,
              hours_worked REAL,
              hourly_earning REAL,
              mileage_earning REAL,
              tips REAL,
              fuel_cost REAL,
              expense_cost REAL,
              gross_earning REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS gogo_transactions
             (id SERIAL PRIMARY KEY,
              trans_date DATE,
              trans_type TEXT,
              amount REAL,
              notes TEXT)''')

conn.commit()

# --- HELPER FUNCTIONS ---
def calculate_hours(start_t, end_t):
    start_dt = datetime.combine(datetime.today(), start_t)
    end_dt = datetime.combine(datetime.today(), end_t)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    total_mins = (end_dt - start_dt).total_seconds() / 60
    return max(0, total_mins / 60)

def get_week_start(date_obj):
    return date_obj - timedelta(days=date_obj.weekday())

def load_data():
    try:
        df = pd.read_sql_query("SELECT * FROM shifts", conn)
        if not df.empty:
            df['shift_date'] = pd.to_datetime(df['shift_date'])
            df['week_start'] = df['shift_date'].apply(get_week_start)
            df['fuel_cost'] = df['fuel_cost'].fillna(0.0)
            df['expense_cost'] = df['expense_cost'].fillna(0.0)
            df['mileage_earning'] = df['mileage_earning'].fillna(0.0)
            df['tips'] = df['tips'].fillna(0.0)
            df = df.sort_values(by='shift_date', ascending=False)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def load_gogo_transactions():
    try:
        df = pd.read_sql_query("SELECT * FROM gogo_transactions", conn)
        if not df.empty:
            df['trans_date'] = pd.to_datetime(df['trans_date'])
            df = df.sort_values(by='trans_date', ascending=True)
        return df
    except Exception as e:
        st.error(f"Error loading transactions: {e}")
        return pd.DataFrame()

page = st.sidebar.radio("Navigation", ["➕ Enter Rota", "📊 View History & Earnings", "🏠 GOGO Ledger"])

if 'default_rates' not in st.session_state:
    st.session_state.default_rates = {"GOGO": 9.50, "CHINESE": 11.00, "DANIELLE": 14.00}

if 'hourly_rate' not in st.session_state:
    st.session_state.hourly_rate = st.session_state.default_rates["GOGO"]

if 'gogo_monthly_rent' not in st.session_state:
    st.session_state.gogo_monthly_rent = 400.0

if 'gogo_starting_balance' not in st.session_state:
    st.session_state.gogo_starting_balance = 384.75

# ==========================================
# PAGE 1: ENTER ROTA
# ==========================================
if page == "➕ Enter Rota":
    st.header("Log a Shift")
    
    with st.expander("⚙️ Edit Default Hourly Rates"):
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.session_state.default_rates["GOGO"] = st.number_input("GOGO Default Rate (£)", value=st.session_state.default_rates["GOGO"], step=0.10, format="%.2f")
        with col_r2:
            st.session_state.default_rates["CHINESE"] = st.number_input("CHINESE Default Rate (£)", value=st.session_state.default_rates["CHINESE"], step=0.10, format="%.2f")
        with col_r3:
            st.session_state.default_rates["DANIELLE"] = st.number_input("DANIELLE Default Rate (£)", value=st.session_state.default_rates["DANIELLE"], step=0.10, format="%.2f")

    st.markdown("---")

    col1, col2 = st.columns(2)
    
    with col1:
        employer = st.selectbox("Employer / Location", ["GOGO", "CHINESE", "DANIELLE"])
        if st.session_state.get('last_employer') != employer:
            st.session_state.hourly_rate = st.session_state.default_rates[employer]
            st.session_state.last_employer = employer

        shift_date = st.date_input("Shift Date", value=datetime.today())
        start_time = st.time_input("Start Time", value=time(9, 0))
        end_time = st.time_input("End Time", value=time(17, 0))
        
    with col2:
        st.session_state.hourly_rate = st.number_input(
            "Hourly Rate (£)", min_value=0.0, value=st.session_state.hourly_rate, step=0.10, format="%.2f"
        )
        hourly_rate = st.session_state.hourly_rate
        
        st.divider()
        
        if employer == "CHINESE":
            st.info("💡 **Chinese Shift Mode:** Enter the total amount paid. Mileage will be calculated automatically.")
            total_paid_chinese = st.number_input("Total Amount Paid by Employer (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            mileage_earning = 0.0
            
            st.markdown("**Additions & Deductions**")
            tips = st.number_input("Tips Earned (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            col_ded1, col_ded2 = st.columns(2)
            with col_ded1: fuel_cost = st.number_input("Fuel Cost (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            with col_ded2: expense_cost = st.number_input("Other Expenses (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        else:
            total_paid_chinese = 0.0
            st.markdown("**Additions**")
            col_add1, col_add2 = st.columns(2)
            with col_add1: mileage_earning = st.number_input("Mileage Earned (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            with col_add2: tips = st.number_input("Tips Earned (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
                
            st.markdown("**Deductions**")
            col_ded1, col_ded2 = st.columns(2)
            with col_ded1: fuel_cost = st.number_input("Fuel Cost (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            with col_ded2: expense_cost = st.number_input("Other Expenses (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")

    if st.button("Calculate & Save Shift", type="primary"):
        hours = calculate_hours(start_time, end_time)
        hourly_earning = hours * hourly_rate
        
        if employer == "CHINESE":
            calculated_mileage = total_paid_chinese - hourly_earning
            if calculated_mileage < 0:
                st.warning(f"⚠️ Total paid is less than hourly earnings. Mileage set to £0.")
                mileage_earning = 0.0
            else:
                mileage_earning = calculated_mileage
            gross_earning = total_paid_chinese + tips
        else:
            gross_earning = hourly_earning + mileage_earning + tips
        
        c.execute('''INSERT INTO shifts 
                     (shift_date, employer, start_time, end_time, hourly_rate, hours_worked, hourly_earning, 
                      mileage_earning, tips, fuel_cost, expense_cost, gross_earning)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                  (shift_date, employer, start_time.strftime('%H:%M'), end_time.strftime('%H:%M'), 
                   hourly_rate, round(hours, 2), round(hourly_earning, 2),
                   round(mileage_earning, 2), round(tips, 2), round(fuel_cost, 2), round(expense_cost, 2), round(gross_earning, 2)))
        conn.commit()
        
        st.success(f"Shift saved! You worked **{hours:.2f} hours**.")
        st.info(f"Gross Earning for this shift: **£{gross_earning:.2f}**")
        st.balloons()

# ==========================================
# PAGE 2: VIEW HISTORY
# ==========================================
elif page == "📊 View History & Earnings":
    st.header("Earnings History")
    df = load_data()
    
    if df.empty:
        st.warning("No shifts recorded yet.")
    else:
        subtract_deductions = st.checkbox("📉 Show Net Earnings (Subtract Fuel & Expenses from Total)", value=False)
        st.markdown("---")
        
        st.subheader("Filter Data")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            employers = ["All Employers"] + sorted(df['employer'].dropna().unique().tolist())
            selected_employer = st.selectbox("Filter by Employer", employers)
        with col_f2:
            min_date = df['shift_date'].min().date()
            max_date = df['shift_date'].max().date()
            date_range = st.date_input("Select Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        filtered_df = df.copy()
        if selected_employer != "All Employers":
            filtered_df = filtered_df[filtered_df['employer'] == selected_employer]
        if len(date_range) == 2:
            start_d, end_d = date_range
            filtered_df = filtered_df[(filtered_df['shift_date'].dt.date >= start_d) & (filtered_df['shift_date'].dt.date <= end_d)]
            
        st.markdown("---")
        
        total_hours = filtered_df['hours_worked'].sum()
        total_hourly_earning = filtered_df['hourly_earning'].sum()
        total_mileage_earning = filtered_df['mileage_earning'].sum()
        total_tips = filtered_df['tips'].sum()
        total_fuel = filtered_df['fuel_cost'].sum()
        total_expense = filtered_df['expense_cost'].sum()
        gross_total = total_hourly_earning + total_mileage_earning + total_tips
        net_total = gross_total - total_fuel - total_expense
        total_shifts = len(filtered_df)
        
        st.subheader("Summary for Selection")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Shifts", total_shifts)
        c2.metric("Total Hours", f"{total_hours:.2f}")
        c3.metric("Total Hourly Earnings", f"£{total_hourly_earning:.2f}")
        
        c4, c5, c6 = st.columns(3)
        c4.metric("Total Mileage", f"£{total_mileage_earning:.2f}")
        c5.metric("Total Tips", f"£{total_tips:.2f}")
        c6.metric("Fuel & Expenses", f"-£{total_fuel + total_expense:.2f}")
        
        c7, c8 = st.columns(2)
        c7.metric("Gross Total", f"£{gross_total:.2f}")
        if subtract_deductions:
            c8.metric("NET EARNINGS", f"£{net_total:.2f}", delta=f"-£{total_fuel + total_expense:.2f}")
        else:
            c8.metric("TOTAL EARNINGS", f"£{gross_total:.2f}")
        
        st.markdown("---")
        st.subheader("Detailed Shift Log")
        
        display_df = filtered_df.copy()
        display_df['shift_date'] = display_df['shift_date'].dt.strftime('%d %b %Y')
        display_df['hourly_earning_disp'] = display_df['hourly_earning'].apply(lambda x: f"£{x:.2f}")
        display_df['mileage_earning_disp'] = display_df['mileage_earning'].apply(lambda x: f"£{x:.2f}" if x > 0 else "-")
        display_df['tips_disp'] = display_df['tips'].apply(lambda x: f"£{x:.2f}" if x > 0 else "-")
        display_df['fuel_cost_disp'] = display_df['fuel_cost'].apply(lambda x: f"-£{x:.2f}" if x > 0 else "-")
        display_df['expense_cost_disp'] = display_df['expense_cost'].apply(lambda x: f"-£{x:.2f}" if x > 0 else "-")
        
        if subtract_deductions:
            display_df['final_earning_calc'] = display_df['gross_earning'] - display_df['fuel_cost'] - display_df['expense_cost']
        else:
            display_df['final_earning_calc'] = display_df['gross_earning']
            
        display_df['final_earning_disp'] = display_df['final_earning_calc'].apply(lambda x: f"£{x:.2f}")
        display_df['hours_disp'] = display_df['hours_worked'].apply(lambda x: f"{x:.2f} hrs")
        
        final_display_cols = ['shift_date', 'employer', 'start_time', 'end_time', 'hours_disp', 
                              'hourly_earning_disp', 'mileage_earning_disp', 'tips_disp', 
                              'fuel_cost_disp', 'expense_cost_disp', 'final_earning_disp']
        final_col_name = "Net £" if subtract_deductions else "Gross £"
        rename_cols = {'shift_date': 'Date', 'employer': 'Location', 'start_time': 'Start', 'end_time': 'End',
                       'hours_disp': 'Hours', 'hourly_earning_disp': 'Hourly £', 'mileage_earning_disp': 'Mileage £',
                       'tips_disp': 'Tips £', 'fuel_cost_disp': 'Fuel (-£)', 'expense_cost_disp': 'Expense (-£)',
                       'final_earning_disp': final_col_name}
        
        st.dataframe(display_df[final_display_cols].rename(columns=rename_cols), use_container_width=True, hide_index=True)
        
        with st.expander("⚠️ Delete a Shift"):
            shift_options = filtered_df['id'].astype(str) + " - " + filtered_df['shift_date'].dt.strftime('%d %b %Y') + " (" + filtered_df['employer'] + ")"
            shift_to_delete = st.selectbox("Select shift to delete", shift_options)
            if st.button("Delete Selected Shift", type="secondary"):
                del_id = int(shift_to_delete.split(' - ')[0])
                c.execute("DELETE FROM shifts WHERE id = %s", (del_id,))
                conn.commit()
                st.success("Shift deleted successfully!")
                st.rerun()

# ==========================================
# PAGE 3: GOGO LEDGER
# ==========================================
elif page == "🏠 GOGO Ledger":
    st.header("🏠 GOGO Rent & Payments Ledger")
    
    with st.expander("⚙️ GOGO Settings"):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.session_state.gogo_monthly_rent = st.number_input(
                "Monthly Rent Amount (£)", min_value=0.0, 
                value=st.session_state.gogo_monthly_rent, step=10.0, format="%.2f"
            )
        with col_s2:
            st.session_state.gogo_starting_balance = st.number_input(
                "Starting Balance (£)", min_value=-10000.0, 
                value=st.session_state.gogo_starting_balance, step=10.0, format="%.2f"
            )
    
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("Add Transaction")
        trans_type = st.selectbox("Transaction Type", ["Payment Received from Owner", "Rent Deducted by Owner"])
        trans_date = st.date_input("Date", value=datetime.today().date())
        trans_amount = st.number_input("Amount (£)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        trans_notes = st.text_input("Notes (Optional)", placeholder="e.g., Cash, Bank Transfer")
        
        if st.button("Add Transaction", type="primary"):
            db_type = "PAYMENT" if "Payment" in trans_type else "RENT"
            c.execute('''INSERT INTO gogo_transactions (trans_date, trans_type, amount, notes)
                         VALUES (%s, %s, %s, %s)''', (trans_date, db_type, trans_amount, trans_notes))
            conn.commit()
            st.success("Transaction added successfully!")
            st.rerun()
            
    with col_right:
        st.subheader("Filter by Date")
        today = datetime.today()
        first_day = today.replace(day=1).date()
        last_day = today.date()
        date_range = st.date_input("Select Date Range", value=(first_day, last_day))
        
    st.markdown("---")
    
    all_shifts = load_data()
    gogo_shifts = all_shifts[all_shifts['employer'] == 'GOGO'].copy() if not all_shifts.empty else pd.DataFrame()
    gogo_trans = load_gogo_transactions()
    
    if len(date_range) == 2:
        start_d, end_d = date_range
        if not gogo_shifts.empty:
            gogo_shifts = gogo_shifts[(gogo_shifts['shift_date'].dt.date >= start_d) & (gogo_shifts['shift_date'].dt.date <= end_d)]
        if not gogo_trans.empty:
            gogo_trans = gogo_trans[(gogo_trans['trans_date'].dt.date >= start_d) & (gogo_trans['trans_date'].dt.date <= end_d)]
    
    ledger_data = []
    
    if not gogo_shifts.empty:
        for _, row in gogo_shifts.iterrows():
            ledger_data.append({
                'Date': row['shift_date'], 
                'Description': f"Shift ({row['start_time']} - {row['end_time']})",
                'Type': 'Wages Earned', 
                'Amount': row['hourly_earning'],
                'Month': row['shift_date'].to_period('M')
            })
    if not gogo_trans.empty:
        for _, row in gogo_trans.iterrows():
            desc = "Rent Deducted" if row['trans_type'] == 'RENT' else "Payment Received"
            if row['notes']: desc += f" ({row['notes']})"
            ledger_data.append({
                'Date': row['trans_date'], 
                'Description': desc, 
                'Type': row['trans_type'],
                'Amount': -row['amount'],
                'Month': row['trans_date'].to_period('M')
            })
    
    total_wages = gogo_shifts['hourly_earning'].sum() if not gogo_shifts.empty else 0.0
    total_payments = gogo_trans[gogo_trans['trans_type'] == 'PAYMENT']['amount'].sum() if not gogo_trans.empty else 0.0
    total_rent_deducted = gogo_trans[gogo_trans['trans_type'] == 'RENT']['amount'].sum() if not gogo_trans.empty else 0.0
    
    net_for_period = total_wages - total_rent_deducted - total_payments
    
    st.subheader("Summary for Selected Period")
    m1, m2, m3 = st.columns(3)
    m1.metric("Base Wages Earned", f"£{total_wages:.2f}")
    m2.metric("Rent Deducted", f"£{total_rent_deducted:.2f}")
    m3.metric("Payments Received", f"£{total_payments:.2f}")
    
    m4, m5 = st.columns(2)
    m4.metric("Net for Period", f"£{net_for_period:.2f}")
    
    if ledger_data:
        ledger_df = pd.DataFrame(ledger_data)
        ledger_df = ledger_df.sort_values(by='Date', ascending=True)
        ledger_df['Running Balance'] = st.session_state.gogo_starting_balance + ledger_df['Amount'].cumsum()
        current_balance = ledger_df['Running Balance'].iloc[-1]
    else:
        current_balance = st.session_state.gogo_starting_balance
    
    if current_balance >= 0:
        m5.metric("OWNER CURRENTLY OWES YOU", f"£{current_balance:.2f}")
    else:
        m5.metric("YOU CURRENTLY OWE OWNER", f"£{abs(current_balance):.2f}")
    
    st.markdown("---")
    
    st.subheader("📅 Monthly Breakdown (with Rollover)")
    
    if ledger_data:
        wages_by_month = ledger_df[ledger_df['Amount'] > 0].groupby('Month')['Amount'].sum()
        deductions_by_month = ledger_df[ledger_df['Amount'] < 0].groupby('Month')['Amount'].sum().abs()
        
        all_months = sorted(ledger_df['Month'].unique())
        monthly_rows = []
        cumulative = st.session_state.gogo_starting_balance
        
        for month in all_months:
            wages = wages_by_month.get(month, 0.0)
            deductions = deductions_by_month.get(month, 0.0)
            net = wages - deductions
            rollover_in = cumulative
            cumulative = cumulative + net
            monthly_rows.append({
                'Month': str(month),
                'Rollover from Previous Month': rollover_in,
                'Wages Earned': wages,
                'Rent + Payments (Deducted)': deductions,
                'Net This Month': net,
                'Balance at End of Month': cumulative
            })
        
        monthly_df = pd.DataFrame(monthly_rows)
        
        display_monthly = monthly_df.copy()
        for col in ['Rollover from Previous Month', 'Wages Earned', 'Rent + Payments (Deducted)', 
                    'Net This Month', 'Balance at End of Month']:
            display_monthly[col] = display_monthly[col].apply(lambda x: f"£{x:.2f}")
        
        st.dataframe(display_monthly, use_container_width=True, hide_index=True)
    else:
        st.info("No GOGO shifts or transactions found for the selected date range.")
    
    st.markdown("---")
    
    st.subheader("📋 Detailed Ledger")
    
    if ledger_data:
        display_ledger = ledger_df.copy()
        display_ledger['Date'] = display_ledger['Date'].dt.strftime('%d %b %Y')
        display_ledger['Amount'] = display_ledger['Amount'].apply(lambda x: f"£{x:.2f}")
        display_ledger['Running Balance'] = display_ledger['Running Balance'].apply(lambda x: f"£{x:.2f}")
        
        final_cols = ['Date', 'Description', 'Type', 'Amount', 'Running Balance']
        rename_cols = {'Description': 'Details', 'Type': 'Category', 
                       'Amount': 'Amount (£)', 'Running Balance': 'Running Balance (£)'}
        
        st.dataframe(display_ledger[final_cols].rename(columns=rename_cols), 
                     use_container_width=True, hide_index=True)
        
        with st.expander("⚠️ Delete a Transaction"):
            if not gogo_trans.empty:
                trans_options = gogo_trans.sort_values('trans_date', ascending=False).apply(
                    lambda x: f"{x['id']} - {x['trans_date'].strftime('%d %b %Y')} ({x['trans_type']} - £{x['amount']:.2f})", axis=1
                ).tolist()
                trans_to_delete = st.selectbox("Select transaction to delete", trans_options)
                if st.button("Delete Transaction"):
                    del_id = int(trans_to_delete.split(' - ')[0])
                    c.execute("DELETE FROM gogo_transactions WHERE id = %s", (del_id,))
                    conn.commit()
                    st.success("Deleted!")
                    st.rerun()
            else:
                st.info("No transactions recorded yet.")
    else:
        st.info("No GOGO shifts or transactions found for the selected date range.")
