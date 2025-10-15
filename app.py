import streamlit as st
from collections import defaultdict
import uuid

st.set_page_config(page_title="Multi-Payer Expense Splitter", layout="wide")

# Initialize session state
if "members" not in st.session_state:
    st.session_state.members = []
if "expenses" not in st.session_state:
    st.session_state.expenses = []

st.title("💰 Multi-Payer Expense Splitter")
st.markdown("Split costs fairly when different people pay for different items. Perfect for shared meals, trips, or roommate life!")

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

# Main: Log itemized expense
st.subheader("🧾 Log a New Itemized Expense")
with st.form("expense_form"):
    description = st.text_input("Expense Description")
    num_items = st.number_input("Number of items", min_value=1, max_value=10, value=1, step=1)

    item_data = []
    for i in range(int(num_items)):
        st.markdown(f"**Item {i+1}**")
        item_desc = st.text_input(f"Item Description {i+1}", key=f"desc_{i}")
        item_cost = st.number_input(f"Item Cost {i+1}", min_value=0.0, format="%.2f", key=f"cost_{i}")
        item_payer = st.selectbox(f"Who paid for Item {i+1}?", st.session_state.members, key=f"payer_{i}")
        item_users = st.multiselect(f"Who shared Item {i+1}?", st.session_state.members, key=f"users_{i}")

        item_data.append({
            "desc": item_desc,
            "cost": item_cost,
            "payer": item_payer,
            "participants": item_users
        })

    submitted = st.form_submit_button("Add Expense")

    if submitted:
        if all(item["cost"] > 0 and item["participants"] for item in item_data):
            expense = {
                "id": str(uuid.uuid4()),
                "description": description,
                "items": item_data
            }
            st.session_state.expenses.append(expense)
            st.success("Itemized expense added successfully.")
        else:
            st.error("Please fill all fields correctly.")

# Display expenses
st.subheader("📋 Expense History")
if st.session_state.expenses:
    for exp in st.session_state.expenses:
        st.markdown(f"**{exp['description']}**")
        for item in exp["items"]:
            st.markdown(
                f"- {item['payer']} paid ₹{item['cost']:.2f} for *{item['desc']}*, shared by {', '.join(item['participants'])}"
            )
else:
    st.info("No expenses logged yet.")

# Calculate balances
def calculate_balances(members, expenses):
    balances = defaultdict(float)
    for exp in expenses:
        for item in exp["items"]:
            split_cost = item["cost"] / len(item["participants"])
            for person in item["participants"]:
                balances[person] -= split_cost
            balances[item["payer"]] += item["cost"]
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
        settlements.append(f"{debtor} pays {creditor} ₹{payment:.2f}")
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
    st.write(f"- {person}: ₹{balances[person]:.2f}")

# Show settlement suggestions
st.subheader("🤝 Settlement Suggestions")
settlements = suggest_settlements(balances)
if settlements:
    for s in settlements:
        st.write(f"- {s}")
else:
    st.write("All balances are settled!")

