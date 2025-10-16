import streamlit as st
from collections import defaultdict, Counter
import uuid
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date

# ---- Initialize group_id first ----
if "group_id" not in st.session_state:
    st.session_state.group_id = uuid.uuid4().hex  # 32-char secure ID

# ---- Then check query params ----
query_params = st.query_params
if "group_id" in query_params:
    invited_group_id = query_params["group_id"]
    st.session_state.is_invited = (invited_group_id == st.session_state.group_id)
else:
    st.session_state.is_invited = False

# ---- Set page config ----
st.set_page_config(page_title="Multi-Payer Expense Splitter", layout="wide")

    

    # Check if it matches current group
    if invited_group_id == st.session_state.group_id:
        st.session_state.is_invited = True
    else:
        st.session_state.is_invited = False



# Initialize session state
if "members" not in st.session_state:
    st.session_state.members = []
if "expenses" not in st.session_state:
    st.session_state.expenses = []
if "groups" not in st.session_state:
    st.session_state.groups = {}

st.title("💰 Multi-Payer Expense Splitter")
st.markdown("Split costs fairly when different people pay for different items. Perfect for shared meals, trips, or roommate life!")

# Sidebar: Add group members
st.sidebar.header("👥 Group Members")
new_member = st.sidebar.text_input("Add member name")
new_group = st.sidebar.selectbox("Assign to group", ["Roommates", "Friends", "Family", "Other"])
if st.sidebar.button("Add Member") and new_member:
    if new_member not in st.session_state.members:
        st.session_state.members.append(new_member)
        st.session_state.groups[new_member] = new_group
    else:
        st.sidebar.warning("Member already exists.")
        
st.sidebar.subheader("🔗 Invite Friends")
base_url = "https://your-app.streamlit.app"  # replace with actual deployed URL
invite_link = f"{base_url}?group_id={st.session_state.group_id}"
st.sidebar.code(invite_link, language="text")


if st.session_state.members:
    st.sidebar.write("### Current Members")
    for m in st.session_state.members:
        st.sidebar.write(f"- {m} ({st.session_state.groups.get(m, 'Unassigned')})")

# Sidebar: Date filter
st.sidebar.subheader("📅 Filter by Date")
start_date = st.sidebar.date_input("Start Date", value=date(2025, 1, 1))
end_date = st.sidebar.date_input("End Date", value=date.today())


if "is_invited" in st.session_state and st.session_state.is_invited:
    st.success("✅ You have joined the group via invite link!")

    # Automatically add user (ask name once)
    friend_name = st.text_input("Enter your name to confirm joining")
    if st.button("Join Group"):
        if friend_name and friend_name not in st.session_state.members:
            st.session_state.members.append(friend_name)
            st.session_state.groups[friend_name] = "Invited"
            st.success(f"🎉 Welcome {friend_name}, you are now part of the group!")
        elif friend_name in st.session_state.members:
            st.info("You are already in the group.")


# Main: Log itemized expense
st.subheader("🧾 Log a New Itemized Expense")
with st.form("expense_form"):
    description = st.text_input("Expense Description")
    expense_date = st.date_input("Expense Date", value=date.today())
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
                "date": expense_date,
                "items": item_data
            }
            st.session_state.expenses.append(expense)
            st.success("Itemized expense added successfully.")
        else:
            st.error("Please fill all fields correctly.")

# Filter expenses by date
filtered_expenses = [
    exp for exp in st.session_state.expenses
    if start_date <= exp["date"] <= end_date
]

# Display expenses
st.subheader("📋 Expense History")
if filtered_expenses:
    for exp in filtered_expenses:
        st.markdown(f"**{exp['description']}** ({exp['date']})")
        for item in exp["items"]:
            st.markdown(
                f"- {item['payer']} paid ₹{item['cost']:.2f} for *{item['desc']}*, shared by {', '.join(item['participants'])}"
            )
else:
    st.info("No expenses logged in selected date range.")

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
balances = calculate_balances(st.session_state.members, filtered_expenses)
for person in st.session_state.members:
    st.write(f"- {person}: ₹{balances[person]:.2f}")

# Bar Chart: Debt vs Credit
st.subheader("📉 Balance Bar Chart")
balance_df = pd.DataFrame(list(balances.items()), columns=["Member", "Balance"])
colors = ['green' if x > 0 else 'red' for x in balance_df["Balance"]]

fig, ax = plt.subplots()
ax.bar(balance_df["Member"], balance_df["Balance"], color=colors)
ax.axhline(0, color='black', linewidth=0.8)
ax.set_ylabel("Balance (₹)")
ax.set_title("Who owes and who is owed")
st.pyplot(fig)

# Pie Chart: Contributions
def get_total_contributions(expenses):
    contributions = Counter()
    for exp in expenses:
        for item in exp["items"]:
            contributions[item["payer"]] += item["cost"]
    return contributions

contributions = get_total_contributions(filtered_expenses)
if contributions:
    st.subheader("🍰 Contribution Pie Chart")
    contrib_df = pd.DataFrame(list(contributions.items()), columns=["Member", "Total Paid"])
    fig2, ax2 = plt.subplots()
    ax2.pie(contrib_df["Total Paid"], labels=contrib_df["Member"], autopct='%1.1f%%', startangle=90)
    ax2.axis('equal')
    st.pyplot(fig2)

# Group-wise summary
st.subheader("👥 Group-Wise Balances")
group_balances = defaultdict(float)
for member, balance in balances.items():
    group = st.session_state.groups.get(member, "Unassigned")
    group_balances[group] += balance

for group, total in group_balances.items():
    st.write(f"- {group}: ₹{total:.2f}")

# Settlement suggestions
st.subheader("🤝 Settlement Suggestions")
settlements = suggest_settlements(balances)
if settlements:
    for s in settlements:
        st.write(f"- {s}")
else:
    st.write("All balances are settled!")

# Downloadable report
st.subheader("📥 Download Report")
report_text = f"Expense Report ({start_date} to {end_date})\n\n"
for person in st.session_state.members:
    report_text += f"{person}: ₹{balances[person]:.2f}\n"
report_text += "\nSettlement Suggestions:\n"
for s in settlements:
    report_text += f"{s}\n"

st.download_button(
    label="Download Summary as TXT",
    data=report_text,
    file_name="expense_report.txt",
    mime="text/plain"
)
