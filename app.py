import streamlit as st
from utils.auth import login_user, create_admin_if_not_exists, hash_password
from database.connection import get_database_connection
from modules.warehouse import warehouse_dashboard
from modules.kitchen.recipe import recipe_management
from modules.kitchen.production import production_management
from modules.kitchen.wastage import wastage_management
from modules.kitchen.inventory import semi_finished_inventory
from modules.operations.dashboard import operations_dashboard
from modules.operations.costs import cost_analysis
from modules.operations.sales import sales_management
from modules.operations.products import product_management

def admin_dashboard():
    st.title("Admin Dashboard")
    
    # Tabs for different admin functions
    tab1, tab2 = st.tabs(["User Management", "System Settings"])
    
    with tab1:
        st.subheader("Create New User")
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["warehouse", "kitchen", "operations", "admin"])
            
            if st.button("Create User"):
                conn = get_database_connection()
                cursor = conn.cursor()
                
                # Check if username exists
                cursor.execute("SELECT username FROM users WHERE username = %s", (new_username,))
                if cursor.fetchone():
                    st.error("Username already exists!")
                else:
                    hashed_pw = hash_password(new_password)
                    cursor.execute(
                        "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                        (new_username, hashed_pw, role)
                    )
                    conn.commit()
                    st.success("User created successfully!")
                cursor.close()
                conn.close()
        
        with col2:
            st.subheader("Existing Users")
            conn = get_database_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT user_id, username, role FROM users")
            users = cursor.fetchall()
            
            # Display users in a table
            if users:
                for user in users:
                    col1, col2, col3 = st.columns([2,2,1])
                    with col1:
                        st.write(user['username'])
                    with col2:
                        st.write(user['role'])
                    with col3:
                        if user['username'] != 'admin':  # Prevent admin deletion
                            if st.button('Delete', key=f"del_{user['user_id']}"):
                                cursor.execute("DELETE FROM users WHERE user_id = %s", (user['user_id'],))
                                conn.commit()
                                st.rerun()
            
            cursor.close()
            conn.close()

def main():
    st.set_page_config(page_title="Cake Inventory System", layout="wide")
    
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None

    # Create admin account if it doesn't exist
    create_admin_if_not_exists()

    if not st.session_state.user:
        st.title("Login")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                user = login_user(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    else:
        st.sidebar.title(f"Welcome, {st.session_state.user['username']}")
        st.sidebar.button("Logout", on_click=lambda: setattr(st.session_state, 'user', None))
        
        # Main content based on role
        if st.session_state.user['role'] == 'admin':
            admin_dashboard()
        elif st.session_state.user['role'] == 'warehouse':
            warehouse_dashboard()
        elif st.session_state.user['role'] == 'kitchen':
            tab1, tab2, tab3, tab4 = st.tabs(["Recipe Management", "Production", "Inventory", "Wastage"])
            with tab1:
                recipe_management()
            with tab2:
                production_management()
            with tab3:
                semi_finished_inventory()
            with tab4:
                wastage_management()
        elif st.session_state.user['role'] == 'operations':
            tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Products", "Sales", "Cost Analysis"])
            with tab1:
                operations_dashboard()
            with tab2:
                product_management()
            with tab3:
                sales_management()
            with tab4:
                cost_analysis()

if __name__ == "__main__":
    main()
