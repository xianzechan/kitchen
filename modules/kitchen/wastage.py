import streamlit as st
from database.connection import get_database_connection
from decimal import Decimal
import time

def record_wastage(item_type, item_id, quantity, reason, user_id):
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # First record the wastage
        cursor.execute("""
            INSERT INTO wastage (item_type, item_id, quantity, reason, recorded_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (item_type, item_id, quantity, reason, user_id))
        
        # Then update the stock
        if item_type == 'raw':
            cursor.execute("""
                UPDATE raw_ingredients 
                SET quantity = quantity - %s 
                WHERE ingredient_id = %s
            """, (quantity, item_id))
        else:  # semi-finished
            cursor.execute("""
                UPDATE semi_finished 
                SET quantity = quantity - %s 
                WHERE semi_id = %s
            """, (quantity, item_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error recording wastage: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_wastage_history():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            w.wastage_id,
            w.date,
            CASE 
                WHEN w.item_type = 'raw' THEN ri.name
                ELSE sf.name
            END as item_name,
            w.item_type,
            w.quantity,
            w.reason,
            u.username as recorded_by
        FROM wastage w
        LEFT JOIN raw_ingredients ri ON w.item_type = 'raw' AND w.item_id = ri.ingredient_id
        LEFT JOIN semi_finished sf ON w.item_type = 'semi' AND w.item_id = sf.semi_id
        JOIN users u ON w.recorded_by = u.user_id
        ORDER BY w.date DESC
        LIMIT 50
    """)
    
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history

def wastage_management():
    st.subheader("Wastage Management")
    
    tab1, tab2 = st.tabs(["Record Wastage", "View History"])
    
    # Record Wastage Tab
    with tab1:
        # Initialize form key in session state if not exists
        if 'wastage_form_key' not in st.session_state:
            st.session_state.wastage_form_key = 0
            
        # Select item type outside the form
        item_type = st.radio("Item Type", ["Raw Ingredient", "Semi-finished Product"], 
                            on_change=lambda: setattr(st.session_state, 'wastage_form_key', 
                                                    st.session_state.wastage_form_key + 1))
        
        with st.form(f"wastage_form_{st.session_state.wastage_form_key}"):
            # Get items based on type
            conn = get_database_connection()
            cursor = conn.cursor(dictionary=True)
            
            if item_type == "Raw Ingredient":
                cursor.execute("""
                    SELECT ingredient_id as id, name, quantity 
                    FROM raw_ingredients 
                    WHERE quantity > 0 
                    ORDER BY name
                """)
                type_code = 'raw'
            else:
                cursor.execute("""
                    SELECT semi_id as id, name, quantity 
                    FROM semi_finished 
                    WHERE quantity > 0 
                    ORDER BY name
                """)
                type_code = 'semi'
            
            items = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not items:
                st.warning(f"No {item_type}s available with stock.")
                st.form_submit_button("Record Wastage", disabled=True)
                return
            
            # Item selection
            item_id = st.selectbox(
                "Select Item",
                options=[item['id'] for item in items],
                format_func=lambda x: next(f"{item['name']} (Available: {item['quantity']} {'g' if type_code == 'raw' else 'units'})" 
                                         for item in items if item['id'] == x)
            )
            
            # Get current quantity for selected item
            current_qty = next(item['quantity'] for item in items if item['id'] == item_id)
            
            # Quantity input
            quantity = st.number_input(
                f"Wastage Quantity ({'g' if type_code == 'raw' else 'units'})", 
                min_value=0.0,
                max_value=float(current_qty),
                step=0.1 if type_code == 'raw' else 1.0
            )
            
            # Reason input with categories
            reason_category = st.selectbox(
                "Reason Category",
                ["Expired", "Damaged", "Quality Issue", "Production Error", "Other"]
            )
            
            reason_detail = st.text_area("Additional Details", height=100)
            
            submitted = st.form_submit_button("Record Wastage")
            
            if submitted and quantity > 0 and reason_detail:
                full_reason = f"{reason_category}: {reason_detail}"
                if record_wastage(type_code, item_id, quantity, full_reason, st.session_state.user['user_id']):
                    st.success("Wastage recorded successfully!")
                    time.sleep(1)
                    st.rerun()
    
    # View History Tab
    with tab2:
        history = get_wastage_history()
        if history:
            for entry in history:
                with st.expander(f"🗑️ {entry['item_name']} - {entry['date'].strftime('%Y-%m-%d %H:%M')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Quantity:** {entry['quantity']}g")
                        st.write(f"**Type:** {entry['item_type'].title()}")
                    with col2:
                        st.write(f"**Recorded by:** {entry['recorded_by']}")
                        st.write(f"**Reason:** {entry['reason']}")
        else:
            st.info("No wastage records found.") 