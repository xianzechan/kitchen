import streamlit as st
from database.connection import get_database_connection
from datetime import datetime
import time

def get_available_products():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            fp.product_id,
            fp.name,
            fp.selling_price,
            MIN(FLOOR(sf.quantity / fpr.quantity_needed)) as max_possible_units
        FROM final_products fp
        JOIN final_product_recipe fpr ON fp.product_id = fpr.product_id
        JOIN semi_finished sf ON fpr.semi_id = sf.semi_id
        GROUP BY fp.product_id, fp.name, fp.selling_price
        HAVING max_possible_units > 0
        ORDER BY fp.name
    """)
    
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return products

def check_stock_availability(product_id, quantity=1):
    """Check if enough semi-finished products are available for the sale"""
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            sf.name,
            sf.quantity as available,
            fpr.quantity_needed,
            (fpr.quantity_needed * %s) as total_needed
        FROM final_product_recipe fpr
        JOIN semi_finished sf ON fpr.semi_id = sf.semi_id
        WHERE fpr.product_id = %s
    """, (quantity, product_id))
    
    components = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not components:
        return False, "Product recipe not found!"
    
    for comp in components:
        if comp['available'] < comp['total_needed']:
            return False, f"Not enough {comp['name']}! Need {comp['total_needed']} but only {comp['available']} available."
    
    return True, None

def record_sale(product_id, quantity, notes=None):
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Check stock availability
        available, error_msg = check_stock_availability(product_id, quantity)
        if not available:
            st.error(error_msg)
            return False
        
        # Get product price
        cursor.execute("SELECT selling_price FROM final_products WHERE product_id = %s", (product_id,))
        sale_price = cursor.fetchone()[0]
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Record the sale
        cursor.execute("""
            INSERT INTO sales (product_id, quantity, sale_price, sale_date, notes, recorded_by)
            VALUES (%s, %s, %s, NOW(), %s, %s)
        """, (product_id, quantity, sale_price, notes, st.session_state.user['user_id']))
        
        # Deduct semi-finished products
        cursor.execute("""
            UPDATE semi_finished sf
            JOIN final_product_recipe fpr ON sf.semi_id = fpr.semi_id
            SET sf.quantity = sf.quantity - (fpr.quantity_needed * %s)
            WHERE fpr.product_id = %s
        """, (quantity, product_id))
        
        cursor.execute("COMMIT")
        return True
        
    except Exception as e:
        cursor.execute("ROLLBACK")
        st.error(f"Error recording sale: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_daily_sales():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            s.sale_id,
            fp.name as product_name,
            s.quantity,
            CAST(s.sale_price AS FLOAT) as sale_price,
            s.sale_date,
            s.notes,
            u.username as recorded_by
        FROM sales s
        JOIN final_products fp ON s.product_id = fp.product_id
        JOIN users u ON s.recorded_by = u.user_id
        WHERE DATE(s.sale_date) = CURDATE()
        ORDER BY s.sale_date DESC
    """)
    
    sales = cursor.fetchall()
    cursor.close()
    conn.close()
    return sales

def sales_management():
    st.title("Sales Management")
    
    tab1, tab2 = st.tabs(["Record Sales", "Today's Sales"])
    
    # Record Sales Tab
    with tab1:
        st.subheader("Record New Sale")
        
        products = get_available_products()
        
        if not products:
            st.warning("No products available for sale!")
            return
        
        with st.form("sales_form", clear_on_submit=True):
            # Product selection
            product_id = st.selectbox(
                "Select Product",
                options=[p['product_id'] for p in products],
                format_func=lambda x: next(
                    f"{p['name']} (Can make: {p['max_possible_units']} units) - ${p['selling_price']:.2f}/unit"
                    for p in products if p['product_id'] == x
                )
            )
            
            # Get selected product details
            selected_product = next(p for p in products if p['product_id'] == product_id)
            
            quantity = st.number_input(
                "Quantity", 
                min_value=1,
                max_value=int(selected_product['max_possible_units']),
                value=1
            )
            
            notes = st.text_area("Notes (Optional)", placeholder="Enter any additional notes...")
            
            # Calculate and show total
            total_price = quantity * selected_product['selling_price']
            st.write(f"**Total Sale Price:** ${total_price:.2f}")
            
            submitted = st.form_submit_button("Record Sale")
            
            if submitted:
                if record_sale(product_id, quantity, notes):
                    st.success(f"Successfully recorded sale of {quantity} {selected_product['name']}!")
                    time.sleep(1)
                    st.rerun()
    
    # Today's Sales Tab
    with tab2:
        st.subheader("Today's Sales")
        
        sales = get_daily_sales()
        
        if sales:
            # Summary metrics
            total_revenue = sum(sale['quantity'] * sale['sale_price'] for sale in sales)
            total_items = sum(sale['quantity'] for sale in sales)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Revenue", f"${total_revenue:.2f}")
            with col2:
                st.metric("Total Items Sold", total_items)
            
            # Detailed sales list
            st.divider()
            for sale in sales:
                with st.expander(
                    f"🧾 {sale['product_name']} - {sale['sale_date'].strftime('%H:%M')} "
                    f"(${sale['quantity'] * sale['sale_price']:.2f})"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Quantity:**", sale['quantity'])
                        st.write("**Price per Unit:**", f"${sale['sale_price']:.2f}")
                    with col2:
                        st.write("**Recorded by:**", sale['recorded_by'])
                        if sale['notes']:
                            st.write("**Notes:**", sale['notes'])
        else:
            st.info("No sales recorded today yet.") 