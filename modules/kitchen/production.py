import streamlit as st
from database.connection import get_database_connection
from decimal import Decimal
from datetime import datetime, timedelta
import time

def get_recipe_details(semi_id):
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get recipe and check ingredients availability
    cursor.execute("""
        SELECT 
            sf.name as recipe_name,
            sf.semi_id,
            ri.ingredient_id,
            ri.name as ingredient_name,
            ri.quantity as available_quantity,
            sfr.quantity_needed,
            sfr.output_quantity
        FROM semi_finished sf
        JOIN semi_finished_recipe sfr ON sf.semi_id = sfr.semi_id
        JOIN raw_ingredients ri ON sfr.ingredient_id = ri.ingredient_id
        WHERE sf.semi_id = %s
    """, (semi_id,))
    
    recipe_details = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return recipe_details if recipe_details else None

def check_ingredients_availability(recipe_details, production_quantity):
    """Check if enough ingredients are available for production"""
    for ingredient in recipe_details:
        batches = production_quantity / ingredient['output_quantity']
        needed_quantity = Decimal(str(batches)) * Decimal(str(ingredient['quantity_needed']))
        if needed_quantity > ingredient['available_quantity']:
            return False, f"Not enough {ingredient['ingredient_name']}. Need {needed_quantity}g but only {ingredient['available_quantity']}g available."
    return True, None

def record_production(recipe_details, production_quantity, expiry_date):
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Calculate batches needed
        batches = production_quantity / recipe_details[0]['output_quantity']
        
        # Deduct raw ingredients
        for ingredient in recipe_details:
            needed_quantity = Decimal(str(batches)) * Decimal(str(ingredient['quantity_needed']))
            cursor.execute("""
                UPDATE raw_ingredients 
                SET quantity = quantity - %s 
                WHERE ingredient_id = %s
            """, (needed_quantity, ingredient['ingredient_id']))
        
        # Add to semi-finished inventory
        cursor.execute("""
            UPDATE semi_finished 
            SET quantity = quantity + %s,
                expiry_date = %s
            WHERE semi_id = %s
        """, (production_quantity, expiry_date, recipe_details[0]['semi_id']))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error in production: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def production_management():
    st.subheader("Production Management")
    
    # Get all recipes
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT semi_id, name FROM semi_finished ORDER BY name")
    recipes = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not recipes:
        st.warning("No recipes available. Please create recipes first.")
        return
    
    with st.form("production_form"):
        # Recipe selection
        recipe_id = st.selectbox(
            "Select Recipe",
            options=[r['semi_id'] for r in recipes],
            format_func=lambda x: next(r['name'] for r in recipes if r['semi_id'] == x)
        )
        
        # Get recipe details
        recipe_details = get_recipe_details(recipe_id)
        if recipe_details:
            st.write("**Recipe Details:**")
            for ing in recipe_details:
                st.write(f"- {ing['ingredient_name']}: {ing['quantity_needed']}g per {ing['output_quantity']} units")
        
        # Production quantity
        quantity = st.number_input("Production Quantity (units)", min_value=1, value=1)
        
        # Expiry date
        default_expiry = datetime.now() + timedelta(days=3)  # Default 3 days expiry
        expiry_date = st.date_input("Expiry Date", value=default_expiry)
        
        submitted = st.form_submit_button("Record Production")
        
        if submitted:
            if recipe_details:
                # Check ingredients availability
                available, error_msg = check_ingredients_availability(recipe_details, quantity)
                
                if available:
                    if record_production(recipe_details, quantity, expiry_date):
                        st.success(f"Successfully produced {quantity} units!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error(error_msg) 