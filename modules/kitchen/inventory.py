import streamlit as st
from database.connection import get_database_connection
from datetime import datetime

def get_semi_finished_inventory():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            sf.semi_id,
            sf.name,
            sf.quantity,
            sf.expiry_date,
            GROUP_CONCAT(
                CONCAT(ri.name, ' (', sfr.quantity_needed, 'g)')
                SEPARATOR ', '
            ) as recipe
        FROM semi_finished sf
        LEFT JOIN semi_finished_recipe sfr ON sf.semi_id = sfr.semi_id
        LEFT JOIN raw_ingredients ri ON sfr.ingredient_id = ri.ingredient_id
        GROUP BY sf.semi_id, sf.name, sf.quantity, sf.expiry_date
        ORDER BY 
            CASE 
                WHEN sf.expiry_date IS NULL THEN 1 
                ELSE 0 
            END,
            sf.expiry_date
    """)
    
    inventory = cursor.fetchall()
    cursor.close()
    conn.close()
    return inventory

def semi_finished_inventory():
    st.subheader("Semi-finished Inventory")
    
    # Search box
    search = st.text_input("Search semi-finished products", "")
    
    inventory = get_semi_finished_inventory()
    
    if inventory:
        # Filter based on search
        if search:
            inventory = [item for item in inventory if search.lower() in item['name'].lower()]
        
        # Table header
        col1, col2, col3, col4, col5 = st.columns([2,1,1.5,2,1])
        with col1:
            st.markdown("**Product Name**")
        with col2:
            st.markdown("**Quantity**")
        with col3:
            st.markdown("**Expiry Date**")
        with col4:
            st.markdown("**Recipe**")
        with col5:
            st.markdown("**Status**")
        
        st.divider()
        
        # Table content
        for item in inventory:
            col1, col2, col3, col4, col5 = st.columns([2,1,1.5,2,1])
            
            with col1:
                st.write(item['name'])
            with col2:
                st.write(f"{item['quantity']} units")
            with col3:
                if item['expiry_date']:
                    days_to_expiry = (item['expiry_date'] - datetime.now().date()).days
                    expiry_text = item['expiry_date'].strftime('%Y-%m-%d')
                    st.write(expiry_text)
            with col4:
                if item['recipe']:
                    with st.expander("View Recipe"):
                        st.write(item['recipe'])
                else:
                    st.write("No recipe found")
            with col5:
                if item['expiry_date']:
                    if days_to_expiry < 0:
                        st.error("Expired")
                    elif days_to_expiry <= 1:
                        st.warning("Expiring soon")
                    else:
                        st.success("Good")
                else:
                    st.info("No expiry")
            
            st.divider()
    else:
        st.info("No semi-finished products in inventory") 