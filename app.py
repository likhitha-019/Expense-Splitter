import streamlit as st
import pandas as pd
import sqlite3

# ----------------- Database Setup -----------------
conn = sqlite3.connect("expenses.db", check_same_thread=False)
c = conn.cursor()

# Groups
c.execute("""
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)
""")

# Expenses
c.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    description TEXT,
    amount REAL,
    paidBy TEXT
)
""")

# Expense Shares
c.execute("""
CREATE TABLE IF NOT EXISTS expense_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id INTEGER,
    participant TEXT,
    share REAL
)
""")
conn.commit()

# ----------------- Functions -----------------
def add_group(name):
    c.execute("INSERT INTO groups (name) VALUES (?)", (name,))
    conn.commit()

def load_groups():
    c.execute("SELECT * FROM groups")
    return c.fetchall()

def add_expense(group_id, desc, amount, paid_by, shares):
    c.execute("INSERT INTO expenses (group_id, description, amount, paidBy) VALUES (?, ?, ?, ?)",
              (group_id, desc, amount, paid_by))
    expense_id = c.lastrowid
    for p, s in shares.items():
        c.execute("INSERT INTO expense_shares (expense_id, participant, share) VALUES (?, ?, ?)",
                  (expense_id, p, s))
    conn.commit()

def load_expenses(group_id):
    c.execute("SELECT id, description, amount, paidBy FROM expenses WHERE group_id=?", (group_id,))
    rows = c.fetchall()
    expenses = []
    for r in rows:
        c.execute("SELECT participant, share FROM expense_shares WHERE expense_id=?", (r[0],))
        shares = dict(c.fetchall())
        expenses.append({
            "id": r[0],
            "description": r[1],
            "amount": r[2],
            "paidBy": r[3],
            "shares": shares
        })
    return expenses

def calculate_balances(expenses):
    balances = {}
    for exp in expenses:
        for p, share in exp["shares"].items():
            balances[p] = balances.get(p, 0) - share
        balances[exp["paidBy"]] = balances.get(exp["paidBy"], 0) + exp["amount"]
    return balances

def min_cash_flow(balances):
    settlements = []
    bal = balances.copy()
    while True:
        max_credit = max(bal, key=lambda k: bal[k])
        max_debit = min(bal, key=lambda k: bal[k])
        if round(bal[max_credit], 2) == 0 and round(bal[max_debit], 2) == 0:
            break
        amount = min(-bal[max_debit], bal[max_credit])
        bal[max_credit] -= amount
        bal[max_debit] += amount
        settlements.append(f"💰 {max_debit} pays ₹{amount:.2f} to {max_credit}")
    return settlements

# ----------------- Streamlit UI -----------------
st.set_page_config(page_title="Expense Splitter", page_icon="💸", layout="wide")
st.title("💸 Expense Splitter (Groups + Custom Participants)")

tab1, tab2, tab3, tab4 = st.tabs(["👥 Groups", "➕ Expenses", "📊 Summary", "🤝 Settlements"])

# ---- Groups Tab ----
with tab1:
    st.subheader("Manage Groups")
    groups = load_groups()
    group_names = {g[1]: g[0] for g in groups}
    selected_group = st.selectbox("Select Group", ["-- Create New --"] + list(group_names.keys()))

    if selected_group == "-- Create New --":
        new_group = st.text_input("New Group Name")
        if st.button("Create Group"):
            if new_group:
                add_group(new_group)
                st.success("✅ Group created. Refresh to see it.")

# ---- Expenses Tab ----
with tab2:
    st.subheader("Add Expense")
    groups = load_groups()
    if groups:
        group_names = {g[1]: g[0] for g in groups}
        selected_group = st.selectbox("Select Group", list(group_names.keys()))
        group_id = group_names[selected_group]

        with st.form("expense_form"):
            desc = st.text_input("Description")
            amount = st.number_input("Amount", min_value=1.0, format="%.2f")
            paid_by = st.text_input("Paid By (enter name)")

            participants_input = st.text_input("Participants (comma separated)")
            participants = [p.strip() for p in participants_input.split(",") if p.strip()]

            split_type = st.radio("Split Type", ["Equal", "Percentage", "Custom Amount"])

            shares = {}
            if split_type == "Equal" and participants:
                share_each = round(amount / len(participants), 2)
                for p in participants:
                    shares[p] = share_each
            elif split_type == "Percentage" and participants:
                total_pct = 0
                for p in participants:
                    pct = st.number_input(f"{p} (%)", min_value=0.0, max_value=100.0, key=p)
                    shares[p] = round(amount * pct / 100, 2)
                    total_pct += pct
                if total_pct != 100:
                    st.warning("⚠️ Percentages must add to 100")
            elif split_type == "Custom Amount" and participants:
                total_amt = 0
                for p in participants:
                    share = st.number_input(f"{p}'s Share", min_value=0.0, key=p)
                    shares[p] = share
                    total_amt += share
                if round(total_amt, 2) != round(amount, 2):
                    st.warning("⚠️ Shares must add to total amount")

            submitted = st.form_submit_button("Add Expense")
            if submitted and shares:
                add_expense(group_id, desc, amount, paid_by, shares)
                st.success("✅ Expense added.")
    else:
        st.info("Create a group first.")

# ---- Summary Tab ----
with tab3:
    st.subheader("Balances")
    groups = load_groups()
    if groups:
        group_names = {g[1]: g[0] for g in groups}
        selected_group = st.selectbox("Select Group for Summary", list(group_names.keys()))
        group_id = group_names[selected_group]
        expenses = load_expenses(group_id)

        if expenses:
            balances = calculate_balances(expenses)
            for p, b in balances.items():
                if b > 0:
                    st.success(f"✅ {p} should receive ₹{b:.2f}")
                elif b < 0:
                    st.error(f"🔴 {p} owes ₹{abs(b):.2f}")
                else:
                    st.info(f"⚪ {p} is settled up")

            df = pd.DataFrame(balances.items(), columns=["Person", "Balance"])
            st.bar_chart(df.set_index("Person"))
        else:
            st.info("No expenses yet.")
    else:
        st.info("Create a group first.")

# ---- Settlements Tab ----
with tab4:
    st.subheader("Optimal Settlements")
    groups = load_groups()
    if groups:
        group_names = {g[1]: g[0] for g in groups}
        selected_group = st.selectbox("Select Group for Settlements", list(group_names.keys()))
        group_id = group_names[selected_group]
        expenses = load_expenses(group_id)

        if expenses:
            balances = calculate_balances(expenses)
            settlements = min_cash_flow(balances)
            if settlements:
                for s in settlements:
                    st.write(s)
            else:
                st.success("🎉 Everyone is settled up!")
        else:
            st.info("No expenses yet.")
    else:
        st.info("Create a group first.")
