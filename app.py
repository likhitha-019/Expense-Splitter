import streamlit as st
from collections import defaultdict
import uuid

st.set_page_config(page_title="Expense Splitter Service", layout="wide")

# Session state initialization
if "members" not in st.session_state:
    st.session_state.members = []
if "expenses" not in st.session_state:
    st.session_state.expenses = []

st.title("💸 Expense Splitter Service")
st.markdown("Track shared expenses and settle up easily with your group.")

# Sidebar: Add group members
st.sidebar.header("👥 Group Members")
new_member = st.sidebar.text_input("Add member name")
if st.sidebar.button("Add Member") and new_member:
    if new_member not in st.session_state.members:
        st.session_state.members.append(new_member)
    else:
        st.sidebar.warning("Member already exists.")

if st.session_state.members:
    st.sidebar.write("### Current Members")
    st.sidebar.write(", ".join(st.session_state.members))

# Main: Log expenses
st.subheader("🧾 Log a New Expense")
with st.form("expense_form"):
    payer = st.selectbox("Who paid?", st.session_state.members)
    amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    description = st.text_input("Description")
    participants = st.multiselect("Who shares this expense?", st.session_state.members)
    submitted = st.form_submit_button("Add Expense")

    if submitted:
        if payer and amount > 0 and participants:
            expense = {
                "id": str(uuid.uuid4()),
                "payer": payer,
                "amount": amount,
                "description": description,
                "participants": participants,
            }
            st.session_state.expenses.append(expense)
            st.success("Expense added successfully.")
        else:
            st.error("Please fill all fields correctly.")

# Display expenses
st.subheader("📋 Expense History")
if st.session_state.expenses:
    for exp in st.session_state.expenses:
        st.markdown(
            f"- **{exp['payer']}** paid **${exp['amount']:.2f}** for *{exp['description']}*, split among {', '.join(exp['participants'])}"
        )
else:
    st.info("No expenses logged yet.")

# Calculate balances
def calculate_balances(members, expenses):
    balances = defaultdict(float)
    for exp in expenses:
        split_amount = exp["amount"] / len(exp["participants"])
        for person in exp["participants"]:
            balances[person] -= split_amount
        balances[exp["payer"]] += exp["amount"]
    return balances

# Settlement suggestion
def suggest_settlements(balances):
    creditors = []
    debtors = []
    for person, balance in balances.items():
        if balance > 0:
            creditors.append([person, balance])
        elif balance < 0:
            debtors.append([person, -balance])

    settlements = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor, d_amt = debtors[i]
        creditor, c_amt = creditors[j]
        payment = min(d_amt, c_amt)
        settlements.append(f"{debtor} pays {creditor} ${payment:.2f}")
        debtors[i][1] -= payment
        creditors[j][1] -= payment
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1
    return settlements

# Show balances
st.subheader("📊 Per-Person Balances")
balances = calculate_balances(st.session_state.members, st.session_state.expenses)
for person in st.session_state.members:
    st.write(f"- {person}: ${balances[person]:.2f}")

# Show settlement suggestions
st.subheader("🤝 Settlement Suggestions")
settlements = suggest_settlements(balances)
if settlements:
    for s in settlements:
        st.write(f"- {s}")
else:
    st.write("All balances are settled!")

