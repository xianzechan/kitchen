import streamlit as st
from database.connection import get_database_connection
from datetime import datetime
from decimal import Decimal
import time

def add_ingredient(name, quantity, cost_per_unit, expiry_date=None):
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Check if ingredient already exists
        cursor.execute("SELECT name FROM raw_ingredients WHERE name = %s", (name,))
        if cursor.fetchone():
            st.error("Ingredient already exists!")
            return False
            
        cursor.execute("""
            INSERT INTO raw_ingredients (name, quantity, cost_per_unit, expiry_date)
            VALUES (%s, %s, %s, %s)
        """, (name, quantity, cost_per_unit, expiry_date))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def update_stock(ingredient_id, quantity, operation='add'):
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Check current quantity first
        cursor.execute("SELECT quantity FROM raw_ingredients WHERE ingredient_id = %s", (ingredient_id,))
        current_qty = cursor.fetchone()[0]
        
        # Convert quantity to Decimal for consistent calculation
        quantity = Decimal(str(quantity))
        
        if operation == 'subtract' and current_qty < quantity:
            st.error("Cannot remove more than available stock!")
            return False
            
        final_qty = current_qty + quantity if operation == 'add' else current_qty - quantity
        
        cursor.execute("""
            UPDATE raw_ingredients 
            SET quantity = %s 
            WHERE ingredient_id = %s
        """, (final_qty, ingredient_id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def delete_ingredient(ingredient_id):
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Check if ingredient is used in any recipes before deleting
        cursor.execute("SELECT * FROM semi_finished_recipe WHERE ingredient_id = %s", (ingredient_id,))
        if cursor.fetchone():
            st.error("Cannot delete: This ingredient is used in recipes!")
            return False
            
        cursor.execute("DELETE FROM raw_ingredients WHERE ingredient_id = %s", (ingredient_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def warehouse_dashboard():
    st.title("Warehouse Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["Current Stock", "Add New Ingredient", "Update Stock"])
    
    # Tab 1: Current Stock
    with tab1:
        st.subheader("Current Inventory")
        
        # Search box
        search = st.text_input("Search ingredients", "")
        
        # Get total count for pagination
        conn = get_database_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Search query
        search_query = f"%{search}%" if search else "%"
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM raw_ingredients 
            WHERE name LIKE %s
        """, (search_query,))
        total_items = cursor.fetchone()['count']
        
        # Pagination setup
        items_per_page = 10
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        # Initialize page from session state or default to 1
        if 'page' not in st.session_state:
            st.session_state.page = 1
        
        # Calculate offset based on current page
        offset = (st.session_state.page - 1) * items_per_page
        
        # Table header
        header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([2,1,1,1,1])
        with header_col1:
            st.markdown("**Name**")
        with header_col2:
            st.markdown("**Quantity**")
        with header_col3:
            st.markdown("**Cost/g**")
        with header_col4:
            st.markdown("**Expiry**")
        with header_col5:
            st.markdown("**Action**")
        
        st.divider()
        
        # Fetch paginated and filtered results
        cursor.execute("""
            SELECT * FROM raw_ingredients 
            WHERE name LIKE %s
            ORDER BY name 
            LIMIT %s OFFSET %s
        """, (search_query, items_per_page, offset))
        ingredients = cursor.fetchall()
        
        # Display table contents
        if ingredients:
            for ing in ingredients:
                col1, col2, col3, col4, col5 = st.columns([2,1,1,1,1])
                with col1:
                    st.write(ing['name'])
                with col2:
                    st.write(f"{ing['quantity']} g")
                with col3:
                    st.write(f"${ing['cost_per_unit']:.4f}/g")
                with col4:
                    if ing['expiry_date']:
                        st.write(ing['expiry_date'].strftime('%Y-%m-%d'))
                    else:
                        st.write("No expiry")
                with col5:
                    if st.button("Delete", key=f"del_{ing['ingredient_id']}"):
                        if delete_ingredient(ing['ingredient_id']):
                            st.success("Ingredient deleted successfully!")
                            time.sleep(1)
                            st.rerun()
                st.divider()
        else:
            if search:
                st.info("No ingredients found matching your search.")
            else:
                st.info("No ingredients in stock")
        
        # Pagination controls at the bottom
        if total_items > 0:
            _, col2, col3 = st.columns([4,2,2])  # Adjusted column ratios for right alignment
            with col2:
                st.write(f"Showing {len(ingredients)} of {total_items} items")
            with col3:
                selected_page = st.selectbox(
                    "Page",
                    options=range(1, total_pages + 1),
                    key="page_select",
                    index=st.session_state.page - 1
                )
                if selected_page != st.session_state.page:
                    st.session_state.page = selected_page
                    st.rerun()
        
        cursor.close()
        conn.close()
    
    # Tab 2: Add New Ingredient
    with tab2:
        st.subheader("Add New Ingredient")
        
        with st.form("add_ingredient_form", clear_on_submit=True):
            name = st.text_input("Ingredient Name")
            col1, col2 = st.columns(2)
            
            with col1:
                quantity = st.number_input("Initial Quantity (g)", min_value=0.0)
                cost = st.number_input("Cost per gram ($)", 
                                     min_value=0.0, 
                                     step=0.0001,
                                     format="%.4f")
            
            with col2:
                has_expiry = st.checkbox("Has Expiry Date?")
                expiry_date = None
                if has_expiry:
                    expiry_date = st.date_input("Expiry Date")
            
            submitted = st.form_submit_button("Add Ingredient")
            
        if submitted:
            if name and quantity >= 0 and cost >= 0:
                if add_ingredient(name, quantity, cost, expiry_date):
                    st.success(f"Successfully added {name} to inventory!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("Please fill in all required fields")
    
    # Tab 3: Update Stock
    with tab3:
        st.subheader("Update Stock Levels")
        
        conn = get_database_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ingredient_id, name, quantity FROM raw_ingredients ORDER BY name")
        ingredients = cursor.fetchall()
        
        if ingredients:
            with st.form("update_stock_form", clear_on_submit=True):
                ingredient_id = st.selectbox(
                    "Select Ingredient",
                    options=[ing['ingredient_id'] for ing in ingredients],
                    format_func=lambda x: next(f"{ing['name']} (Current: {ing['quantity']}g)" 
                                              for ing in ingredients if ing['ingredient_id'] == x)
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    quantity = st.number_input("Quantity (g)", 
                                             min_value=0.0,
                                             step=0.01,
                                             format="%.2f")
                with col2:
                    operation = st.radio("Operation", ["Add", "Remove"])
                
                submitted = st.form_submit_button("Update Stock")

            # Success message outside the form to persist after form clear
            if submitted:
                op = 'add' if operation == "Add" else 'subtract'
                ing_name = next(ing['name'] for ing in ingredients if ing['ingredient_id'] == ingredient_id)
                if update_stock(ingredient_id, quantity, op):
                    st.success(f"Successfully {'added' if op == 'add' else 'removed'} {quantity}g to {ing_name}!")
                    time.sleep(1)  # Give user time to see the message
                    st.rerun()
        else:
            st.info("No ingredients available. Please add ingredients first.")
        
        cursor.close()
        conn.close() 