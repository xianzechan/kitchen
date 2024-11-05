import streamlit as st
from database.connection import get_database_connection
import time

def get_all_semi_finished():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            sf.semi_id, 
            sf.name,
            sf.quantity as available_quantity
        FROM semi_finished sf
        ORDER BY sf.name
    """)
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def create_final_product(name, description, selling_price, recipe_items):
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Create final product
        cursor.execute("""
            INSERT INTO final_products (name, description, selling_price)
            VALUES (%s, %s, %s)
        """, (name, description, selling_price))
        
        product_id = cursor.lastrowid
        
        # Add recipe items
        for semi_id, quantity in recipe_items:
            if quantity > 0:  # Only add if quantity is specified
                cursor.execute("""
                    INSERT INTO final_product_recipe (product_id, semi_id, quantity_needed)
                    VALUES (%s, %s, %s)
                """, (product_id, semi_id, quantity))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error creating product: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_product_details(product_id):
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            fp.product_id,
            fp.name,
            fp.description,
            fp.selling_price,
            GROUP_CONCAT(
                CONCAT(sf.name, ' (', fpr.quantity_needed, ' units)')
                SEPARATOR ', '
            ) as recipe
        FROM final_products fp
        LEFT JOIN final_product_recipe fpr ON fp.product_id = fpr.product_id
        LEFT JOIN semi_finished sf ON fpr.semi_id = sf.semi_id
        WHERE fp.product_id = %s
        GROUP BY fp.product_id
    """, (product_id,))
    
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return product

def product_management():
    st.title("Final Product Management")
    
    tab1, tab2 = st.tabs(["Create Product", "View Products"])
    
    # Create Product Tab
    with tab1:
        st.subheader("Create New Product")
        
        with st.form("create_product"):
            name = st.text_input("Product Name")
            description = st.text_area("Description (optional)")
            selling_price = st.number_input("Selling Price ($)", min_value=0.0, step=0.01)
            
            st.write("**Add Semi-finished Components**")
            semi_finished = get_all_semi_finished()
            
            if not semi_finished:
                st.warning("No semi-finished products available. Create some first!")
                st.form_submit_button("Create Product", disabled=True)
                return
            
            # Dynamic component selection
            num_components = st.number_input("Number of components", min_value=1, max_value=10, value=1)
            
            recipe_items = []
            for i in range(num_components):
                st.write(f"**Component {i+1}**")
                col1, col2 = st.columns([3,1])
                
                with col1:
                    semi_id = st.selectbox(
                        "Select Component",
                        options=[item['semi_id'] for item in semi_finished],
                        format_func=lambda x: next(
                            f"{item['name']} (Available: {item['available_quantity']} units)"
                            for item in semi_finished if item['semi_id'] == x
                        ),
                        key=f"semi_{i}"
                    )
                
                with col2:
                    qty = st.number_input(
                        "Units needed",
                        min_value=0,
                        max_value=1000,
                        value=0,
                        key=f"qty_{i}"
                    )
                
                if semi_id and qty > 0:
                    recipe_items.append((semi_id, qty))
            
            submitted = st.form_submit_button("Create Product")
            
            if submitted:
                if not name:
                    st.error("Please enter a product name!")
                elif selling_price <= 0:
                    st.error("Please enter a valid selling price!")
                elif not recipe_items:
                    st.error("Please add at least one component with quantity!")
                else:
                    # Check for duplicate components
                    semi_ids = [item[0] for item in recipe_items]
                    if len(semi_ids) != len(set(semi_ids)):
                        st.error("Each component can only be used once!")
                    else:
                        if create_final_product(name, description, selling_price, recipe_items):
                            st.success(f"Successfully created {name}!")
                            time.sleep(1)
                            st.rerun()
    
    # View Products Tab
    with tab2:
        st.subheader("Existing Products")
        
        conn = get_database_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                fp.product_id,
                fp.name,
                fp.selling_price,
                GROUP_CONCAT(
                    CONCAT(sf.name, ' (', fpr.quantity_needed, ' units)')
                    SEPARATOR ', '
                ) as recipe
            FROM final_products fp
            LEFT JOIN final_product_recipe fpr ON fp.product_id = fpr.product_id
            LEFT JOIN semi_finished sf ON fpr.semi_id = sf.semi_id
            GROUP BY fp.product_id
            ORDER BY fp.name
        """)
        
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if products:
            for product in products:
                with st.expander(f"🎂 {product['name']} - ${product['selling_price']:.2f}"):
                    st.write("**Recipe:**")
                    st.write(product['recipe'] if product['recipe'] else "No components added")
        else:
            st.info("No products created yet.")