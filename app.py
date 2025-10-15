import streamlit as st
import pandas as pd
import sqlite3

# ----------------- Database Setup -----------------
conn = sqlite3.connect("expenses.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    amount REAL,
    paidBy TEXT,
    participants TEXT
)
""")
conn.commit()

# ----------------- Streamlit Setup -----------------
st.set_page_config(page_title="Expense Splitter", page_icon="💸", layout="centered")
st.title("💸 Expense Splitter")

# ----------------- Functions -----------------
def add_expense_db(description, amount, paid_by, participants):
    participants_str = ",".join(participants)
    c.execute("INSERT INTO expenses (description, amount, paidBy, participants) VALUES (?, ?, ?, ?)",
              (description, amount, paid_by, participants_str))
    conn.commit()

def delete_expense_db(expense_id):
    c.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    conn.commit()

def load_expenses():
    c.execute("SELECT id, description, amount, paidBy, participants FROM expenses")
    data = c.fetchall()
    expenses = []
    for row in data:
        expenses.append({
            "id": row[0],
            "description": row[1],
            "amount": row[2],
            "paidBy": row[3],
            "participants": row[4].split(",")
        })
    return expenses

def calculate_balances(expenses):
    balances = {}
    for exp in expenses:
        split = round(exp["amount"] / len(exp["participants"]), 2)
        for p in exp["participants"]:
            balances[p] = balances.get(p, 0) - split
        balances[exp["paidBy"]] = balances.get(exp["paidBy"], 0) + exp["amount"]
    return balances

def calculate_settlements(balances):
    creditors = []
    debtors = []
    for person, bal in balances.items():
        if bal > 0:
            creditors.append({"name": person, "amount": bal})
        elif bal < 0:
            debtors.append({"name": person, "amount": -bal})

    settlements = []
    while creditors and debtors:
        creditors.sort(key=lambda x: x["amount"], reverse=True)
        debtors.sort(key=lambda x: x["amount"], reverse=True)
        creditor = creditors[0]
        debtor = debtors[0]
        amount = min(creditor["amount"], debtor["amount"])
        settlements.append(f"💰 {debtor['name']} pays ₹{amount:.2f} to {creditor['name']}")
        creditor["amount"] -= amount
        debtor["amount"] -= amount
        if creditor["amount"] == 0: creditors.pop(0)
        if debtor["amount"] == 0: debtors.pop(0)
    return settlements

# ----------------- UI -----------------
st.subheader("➕ Add New Expense")
expenses = load_expenses()
all_people = list({p for exp in expenses for p in exp['participants']} | {exp['paidBy'] for exp in expenses})

with st.form("expense_form"):
    desc = st.text_input("Description")
    amount = st.number_input("Amount", min_value=1.0, format="%.2f")
    paid_by = st.text_input("Paid By")

    # Show existing participants only if they exist
    participants = st.multiselect(
        "Participants",
        options=all_people if all_people else [],
        help="Select from existing participants (if any)"
    )

    # Allow adding a new participant manually
    new_participant = st.text_input("Add new participant (optional)")
    if new_participant:
        participants.append(new_participant)

    submitted = st.form_submit_button("Add Expense")

    if submitted:
        if desc and amount and paid_by and participants:
            if paid_by not in participants:
                participants.append(paid_by)
            add_expense_db(desc, amount, paid_by, participants)
            st.success("Expense added successfully ✅")
            st.experimental_rerun()
        else:
            st.error("Please fill all fields!")

# ----------------- Show Expenses -----------------
st.subheader("📋 Expenses")
if expenses:
    df = pd.DataFrame(expenses)
    df_display = df.copy()
    df_display["participants"] = df_display["participants"].apply(lambda x: ", ".join(x))
    df_display["amount"] = df_display["amount"].apply(lambda x: f"₹{x:.2f}")
    for idx, row in df_display.iterrows():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{row['description']}** | Amount: {row['amount']} | Paid By: {row['paidBy']} | Participants: {row['participants']}")
        with col2:
            if st.button(f"Delete {row['description']}", key=row['id']):
                delete_expense_db(row['id'])
                st.experimental_rerun()
else:
    st.info("No expenses yet.")

# ----------------- Summary -----------------
st.subheader("📊 Summary")
balances = calculate_balances(expenses)
if balances:
    for person, bal in balances.items():
        if bal > 0:
            st.markdown(f"✅ **{person} should receive ₹{bal:.2f}**")
        elif bal < 0:
            st.markdown(f"🔴 **{person} owes ₹{abs(bal):.2f}**")
        else:
            st.markdown(f"⚪ **{person} is settled up**")
    bal_df = pd.DataFrame(balances.items(), columns=["Person", "Balance"])
    st.bar_chart(bal_df.set_index("Person"))
else:
    st.info("No balances to calculate yet.")

# ----------------- Settlements -----------------
st.subheader("🤝 Settlements")
settlements = calculate_settlements(balances)
if settlements:
    for s in settlements:
        st.write(s)
else:
    st.success("🎉 Everyone is settled up!")

# ----------------- Download CSV -----------------
if expenses:
    df_export = pd.DataFrame(expenses)
    df_export["participants"] = df_export["participants"].apply(lambda x: ", ".join(x))
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button("Download Expenses CSV", csv, "expenses.csv", "text/csv")
