import streamlit as st
from database.connection import get_database_connection
import time

def get_all_ingredients():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT ingredient_id, name FROM raw_ingredients ORDER BY name")
    ingredients = cursor.fetchall()
    cursor.close()
    conn.close()
    return ingredients

def get_all_recipes():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            sf.semi_id,
            sf.name as recipe_name,
            GROUP_CONCAT(
                CONCAT(ri.name, ' (', sfr.quantity_needed, 'g)') 
                ORDER BY ri.name 
                SEPARATOR ', '
            ) as ingredients,
            MAX(sfr.output_quantity) as output_quantity
        FROM semi_finished sf
        JOIN semi_finished_recipe sfr ON sf.semi_id = sfr.semi_id
        JOIN raw_ingredients ri ON sfr.ingredient_id = ri.ingredient_id
        GROUP BY sf.semi_id, sf.name
        ORDER BY sf.name
    """)
    recipes = cursor.fetchall()
    cursor.close()
    conn.close()
    return recipes

def create_recipe(name, ingredients_data, output_quantity):
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # First, create the semi-finished product
        cursor.execute("""
            INSERT INTO semi_finished (name, quantity) 
            VALUES (%s, 0)
        """, (name,))
        semi_id = cursor.lastrowid
        
        # Then create recipe entries
        for ing_id, quantity in ingredients_data:
            cursor.execute("""
                INSERT INTO semi_finished_recipe 
                (semi_id, ingredient_id, quantity_needed, output_quantity)
                VALUES (%s, %s, %s, %s)
            """, (semi_id, ing_id, quantity, output_quantity))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error creating recipe: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def recipe_management():
    st.subheader("Recipe Management")
    
    tab1, tab2 = st.tabs(["View Recipes", "Create Recipe"])
    
    # View Recipes Tab
    with tab1:
        recipes = get_all_recipes()
        if recipes:
            for recipe in recipes:
                with st.expander(f"🧾 {recipe['recipe_name']}"):
                    st.write("**Ingredients:**")
                    st.write(recipe['ingredients'])
                    st.write(f"**Output Quantity:** {recipe['output_quantity']} units")
        else:
            st.info("No recipes available. Create your first recipe!")
    
    # Create Recipe Tab
    with tab2:
        with st.form("create_recipe_form"):
            recipe_name = st.text_input("Recipe Name")
            output_quantity = st.number_input("Output Quantity (units)", min_value=1, value=1)
            
            st.write("**Add Ingredients**")
            ingredients = get_all_ingredients()
            
            if not ingredients:
                st.warning("No ingredients available. Please add ingredients first.")
                st.form_submit_button("Create Recipe", disabled=True)
                return
            
            # Dynamic ingredient selection
            ingredient_list = []
            col1, col2, col3 = st.columns([3,2,1])
            with col1:
                st.write("**Ingredient**")
            with col2:
                st.write("**Quantity (g)**")
            with col3:
                st.write("**Action**")
            
            if 'ingredient_count' not in st.session_state:
                st.session_state.ingredient_count = 1
            
            for i in range(st.session_state.ingredient_count):
                col1, col2, col3 = st.columns([3,2,1])
                with col1:
                    ing = st.selectbox(
                        "Select Ingredient",
                        options=[ing['ingredient_id'] for ing in ingredients],
                        format_func=lambda x: next(ing['name'] for ing in ingredients if ing['ingredient_id'] == x),
                        key=f"ing_{i}"
                    )
                with col2:
                    qty = st.number_input("Quantity", min_value=0.1, step=0.1, key=f"qty_{i}")
                ingredient_list.append((ing, qty))
            
            if st.form_submit_button("Add Another Ingredient"):
                st.session_state.ingredient_count += 1
                st.rerun()
            
            submitted = st.form_submit_button("Create Recipe")
            
            if submitted and recipe_name and ingredient_list:
                if create_recipe(recipe_name, ingredient_list, output_quantity):
                    st.success(f"Recipe for {recipe_name} created successfully!")
                    time.sleep(1)
                    st.session_state.ingredient_count = 1
                    st.rerun() 