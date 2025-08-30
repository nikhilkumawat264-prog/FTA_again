import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth, exceptions
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
from PIL import Image
import io
import os

# Set the page to wide layout at the very beginning of the script
st.set_page_config(layout="wide")

# This script is a complete Personal Finance Tracker application with
# Firebase Authentication for multi-user support, Firestore for data storage,
# and various visualization and analysis features.

# --- Firebase Setup (MANDATORY) ---
try:
    # Use st.secrets to access the Firebase configuration for deployment
    firebase_config = st.secrets["firebase"]
    
    # Correctly parse the private key from secrets to handle multiline strings
    # This creates a dictionary to pass to the credentials function.
    creds_dict = {
        "type": firebase_config["type"],
        "project_id": firebase_config["project_id"],
        "private_key_id": firebase_config["private_key_id"],
        "private_key": firebase_config["private_key"],
        "client_email": firebase_config["client_email"],
        "client_id": firebase_config["client_id"],
        "auth_uri": firebase_config["auth_uri"],
        "token_uri": firebase_config["token_uri"],
        "auth_provider_x509_cert_url": firebase_config["auth_provider_x509_cert_url"],
        "client_x509_cert_url": firebase_config["client_x509_cert_url"],
    }
    
    cred = credentials.Certificate(creds_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"Error initializing Firebase. Please ensure your firebase_config is correct and is saved as a secrets.toml file in the .streamlit directory. Details: {e}")
    st.stop()
# End of Firebase Setup

def get_current_user_id():
    """Returns the current user's ID from session state."""
    return st.session_state.get('user_id')

# --- Authentication Functions ---
def login_page():
    
    st.title("Welcome to Budget Buddy!")
    st.write("Please log in or sign up to continue.")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.subheader("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            try:
                user = auth.get_user_by_email(email)
                # Password validation is handled by Firebase SDK, but for a simplified example
                # we will assume the password is correct after finding the user.
                # A proper Streamlit implementation would use a more robust login flow.
                st.session_state['user_id'] = user.uid
                st.session_state['logged_in'] = True
                st.rerun()
            except exceptions.FirebaseError as e:
                st.error(f"Login failed: {e}")
            except ValueError:
                st.error("Invalid email or password.")
            except Exception:
                st.error("Invalid email or password.")

    with tab2:
        st.subheader("Sign Up")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Create Account"):
            try:
                user = auth.create_user(email=signup_email, password=signup_password)
                st.success("Account created successfully! Please log in.")
            except exceptions.FirebaseError as e:
                st.error(f"Sign up failed: {e}")
            except ValueError as e:
                st.error(f"Sign up failed: {e}")


# --- Firestore Functions ---
def add_transaction(user_id, transaction_date, description, amount, category):
    """Inserts a new transaction into the user's Firestore collection."""
    doc_ref = db.collection('users').document(user_id).collection('transactions').document()
    doc_ref.set({
        'date': str(transaction_date),
        'description': description,
        'amount': amount,
        'category': category
    })

def get_transactions_df(user_id):
    """Fetches all transactions for a user from Firestore and returns them as a DataFrame."""
    docs = db.collection('users').document(user_id).collection('transactions').stream()
    data = [doc.to_dict() for doc in docs]
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

def add_lending_loan(user_id, lending_date, person, amount, loan_type):
    """Inserts a new lending or loan record for a user into Firestore."""
    doc_ref = db.collection('users').document(user_id).collection('lending_loan').document()
    doc_ref.set({
        'date': str(lending_date),
        'person': person,
        'amount': amount,
        'type': loan_type
    })

def get_lending_loan_df(user_id):
    """Fetches all lending/loan records for a user and returns them as a DataFrame."""
    docs = db.collection('users').document(user_id).collection('lending_loan').stream()
    data = [doc.to_dict() for doc in docs]
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

# --- Keyword-based Categorization ---
def suggest_category(description):
    """Suggests a category based on keywords in the description."""
    keywords = {
        "Food": ["restaurant", "cafe", "groceries", "supermarket", "food", "eat"],
        "Transport": ["gas", "fuel", "bus", "train", "uber", "cab"],
        "Shopping": ["store", "online", "amazon", "mall", "clothes"],
        "Bills": ["rent", "utility", "phone bill", "electricity"],
        "Entertainment": ["movie", "cinema", "concert", "game"],
        "Trip": ["flight", "hotel", "travel", "vacation"],
        "Education/Fees": ["fees", "tuition", "school", "college", "university"],
        "Services": ["service", "repair", "instrument", "maintenance", "repare", "charge"]
    }
    desc = description.lower()
    for category, terms in keywords.items():
        if any(term in desc for term in terms):
            return category
    return "Other"

# --- Main App Dashboard ---
def main_app(user_id):
    """Main dashboard for the finance tracker."""
    # Custom CSS for the sky blue and pink gradient background
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(to right, #87CEEB, #FFC0CB);
        }}
        .stTabs [data-baseweb="tab-list"] button {{
            font-size: 16px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    transactions_df = get_transactions_df(user_id)
    lending_df = get_lending_loan_df(user_id)

    # --- Top Row: Title and Summary ---
    title_col, summary_col = st.columns([1, 1])
    with title_col:
        st.title("💰 Personal Finance Tracker")
    with summary_col:
        st.subheader("📊 Overall Summary")
        
        total_expenses = transactions_df['amount'].sum() if not transactions_df.empty else 0
        total_lent = lending_df[lending_df['type'] == 'Lent']['amount'].sum() if not lending_df.empty else 0
        total_loan = lending_df[lending_df['type'] == 'Loan']['amount'].sum() if not lending_df.empty else 0
        
        st.markdown(f"**Overall Expenses:** ₹{total_expenses:,.2f}")
        st.markdown(f"**Overall Money Lent:** ₹{total_lent:,.2f}")
        st.markdown(f"**Overall Money Taken as Loan:** ₹{total_loan:,.2f}")
        
    st.markdown("---")
    
    # --- Second Row: Add Transaction and Expense Trends (All in one row) ---
    st.subheader("➕ Add New Transaction & 📈 Expense Trends")
    trans_col, daily_col, weekly_col, monthly_col = st.columns(4)
    
    with trans_col:
        with st.form("transaction_form", clear_on_submit=True):
            transaction_date = st.date_input("Date", value=date.today())
            transaction_type = st.selectbox("Type", ["Expense", "Income"])
            amount_input = st.number_input("Amount", min_value=0.01, format="%.2f")
            description = st.text_input("Description")
            

            # Updated list of categories
            categories = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Trip", "Education/Fees", "Services", "Other"]
            
            suggested_cat = suggest_category(description)
            category = st.selectbox("Category", options=categories, index=categories.index(suggested_cat))

            submitted = st.form_submit_button("Add Transaction")

            if submitted:
                if description and amount_input:
                    amount = amount_input if transaction_type == "Income" else -amount_input
                    add_transaction(user_id, str(transaction_date), description, amount, category)
                    st.success(f"{transaction_type} added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in the description and amount.")
    
    if not transactions_df.empty:
        transactions_df['date'] = pd.to_datetime(transactions_df['date'])
        transactions_df['week'] = transactions_df['date'].dt.to_period('W').astype(str)
        transactions_df['month'] = transactions_df['date'].dt.to_period('M').astype(str)
        
        with daily_col:
            daily_expenses = transactions_df.groupby(transactions_df['date'].dt.date)['amount'].sum().reset_index()
            fig_daily = px.bar(daily_expenses, x='date', y='amount', title='Daily Expenses')
            st.plotly_chart(fig_daily, use_container_width=True, config={'staticPlot': True})

        with weekly_col:
            weekly_expenses = transactions_df.groupby('week')['amount'].sum().reset_index()
            fig_weekly = px.bar(weekly_expenses, x='week', y='amount', title='Weekly Expenses')
            st.plotly_chart(fig_weekly, use_container_width=True, config={'staticPlot': True})
        
        with monthly_col:
            monthly_expenses = transactions_df.groupby('month')['amount'].sum().reset_index()
            fig_monthly = px.bar(monthly_expenses, x='month', y='amount', title='Monthly Expenses')
            st.plotly_chart(fig_monthly, use_container_width=True, config={'staticPlot': True})

        category_expenses = transactions_df.groupby('category')['amount'].sum().reset_index()
        fig_category_pie = px.pie(category_expenses, 
            names='category', 
            values='amount', 
            title='Expenses by Category',
            hole=0.4  # This makes it donut shaped
)
        st.plotly_chart(fig_category_pie, use_container_width=True, config={'staticPlot': True})    
    else:
        # Fallback for empty transactions data
        with daily_col:
            st.info("No transactions to show trends.")
            
    st.markdown("---")

    # --- Third Row: Money Lending & Loans ---
    lending_form_col, lending_chart_col = st.columns([1, 1])
    with lending_form_col:
        st.subheader("🤝 Money Lending & Loans")
        with st.form("lending_loan_form", clear_on_submit=True):
            lending_date = st.date_input("Date of transaction", value=date.today())
            person = st.text_input("Person's Name")
            loan_amount = st.number_input("Amount", min_value=0.01, format="%.2f")
            loan_type = st.radio("Type", ("Lent", "Loan"))
            loan_submitted = st.form_submit_button("Add Record")

            if loan_submitted:
                if person and loan_amount:
                    add_lending_loan(user_id, str(lending_date), person, loan_amount, loan_type)
                    st.success("Record added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in the person's name and amount.")

    with lending_chart_col:
        lending_df = get_lending_loan_df(user_id)
        if not lending_df.empty:
            st.subheader("Bar Chart of Money Lent vs. Loans Taken")
            lending_df['date'] = pd.to_datetime(lending_df['date'])
            lending_df['month'] = lending_df['date'].dt.to_period('M').astype(str)
            monthly_lending_loan = lending_df.groupby(['month', 'type'])['amount'].sum().reset_index()
            fig_lending = px.bar(monthly_lending_loan, x='month', y='amount', color='type', title='Monthly Money Lent vs. Loans', barmode='group')
            st.plotly_chart(fig_lending, use_container_width=True, config={'staticPlot': True})
        else:
            st.info("No lending or loan records to display.")
    
    st.markdown("---")
    
    # --- Fourth Row: Good vs. Bad Expenses ---
    goodbad_text_col, goodbad_chart_col = st.columns([1, 1])
    with goodbad_text_col:
        st.subheader("🤔 Good vs. Bad Expenses")
        bad_categories = ["Entertainment", "Food", "Trip"]
        
        # Ensure transactions_df is not empty before filtering
        if not transactions_df.empty:
            bad_expenses_df = transactions_df[transactions_df['category'].isin(bad_categories)]
            good_expenses_df = transactions_df[~transactions_df['category'].isin(bad_categories)]
            total_bad_expenses = bad_expenses_df['amount'].sum()
        else:
            bad_expenses_df = pd.DataFrame()
            good_expenses_df = pd.DataFrame()
            total_bad_expenses = 0
            
        st.markdown(f"**Total amount you could have saved:** ₹{total_bad_expenses:,.2f}")
        
        st.subheader("💡 Suggestions")
        st.info(f"You could save approximately **₹{total_bad_expenses:,.2f}** next month by controlling your spending on entertainment, food, and trips.")
        
    with goodbad_chart_col:
        st.subheader("Donut Pie Chart of Good vs Bad Expenses")
        if not transactions_df.empty:
            good_expenses_amount = good_expenses_df['amount'].sum()
            bad_expenses_amount = bad_expenses_df['amount'].sum()
            goodbad_summary = pd.DataFrame({
                'Expense Type': ['Good Expenses', 'Bad Expenses'],
                'Amount': [good_expenses_amount, bad_expenses_amount]
            })
            fig_goodbad_pie = px.pie(
                goodbad_summary,
                names='Expense Type',
                values='Amount',
                title='Good vs Bad Expenses',
                hole=0.5
            )
            st.plotly_chart(fig_goodbad_pie, use_container_width=True, config={'staticPlot': True})
        else:
            st.info("No expense data to analyze.")


    st.markdown("---")

    # --- Display All Transactions and Lending/Loan Records at the bottom ---
    st.subheader("All Records")
    tab1, tab2 = st.tabs(["🧾 Transactions", "🤝 Lending/Loans"])
    with tab1:
        if not transactions_df.empty:
            st.dataframe(transactions_df, use_container_width=True)
        else:
            st.info("No transactions recorded yet.")

    with tab2:
        if not lending_df.empty:
            st.dataframe(lending_df, use_container_width=True)
        else:
            st.info("No lending or loan records yet.")


def app():
    """Main application loop that manages user sessions."""
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None

    if st.session_state['logged_in']:
        main_app(st.session_state['user_id'])
    else:
        login_page()

if __name__ == "__main__":
    app()
