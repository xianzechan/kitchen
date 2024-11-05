import streamlit as st
from database.connection import get_database_connection
import pandas as pd

def get_recipe_costs():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            sf.semi_id,
            sf.name as recipe_name,
            CAST(SUM(ri.cost_per_unit * sfr.quantity_needed) AS FLOAT) as total_cost,
            sfr.output_quantity,
            CAST(SUM(ri.cost_per_unit * sfr.quantity_needed) / sfr.output_quantity AS FLOAT) as cost_per_unit
        FROM semi_finished sf
        JOIN semi_finished_recipe sfr ON sf.semi_id = sfr.semi_id
        JOIN raw_ingredients ri ON sfr.ingredient_id = ri.ingredient_id
        GROUP BY sf.semi_id, sf.name, sfr.output_quantity
        ORDER BY sf.name
    """)
    
    recipes = cursor.fetchall()
    cursor.close()
    conn.close()
    return recipes

def get_ingredient_usage():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            ri.name as ingredient_name,
            CAST(ri.cost_per_unit AS FLOAT) as cost_per_unit,
            COUNT(DISTINCT sfr.semi_id) as used_in_recipes,
            CAST(COALESCE(SUM(sfr.quantity_needed), 0) AS FLOAT) as total_needed
        FROM raw_ingredients ri
        LEFT JOIN semi_finished_recipe sfr ON ri.ingredient_id = sfr.ingredient_id
        GROUP BY ri.ingredient_id, ri.name, ri.cost_per_unit
        ORDER BY COALESCE(SUM(sfr.quantity_needed), 0) DESC
    """)
    
    usage = cursor.fetchall()
    cursor.close()
    conn.close()
    return usage

def cost_analysis():
    st.title("Cost Analysis")
    
    tab1, tab2 = st.tabs(["Recipe Costs", "Ingredient Usage"])
    
    # Recipe Costs Tab
    with tab1:
        st.subheader("Recipe Cost Breakdown")
        recipes = get_recipe_costs()
        
        if recipes:
            # Search box
            search = st.text_input("Search recipes", key="recipe_search")
            filtered_recipes = [r for r in recipes if search.lower() in r['recipe_name'].lower()] if search else recipes
            
            # Cost summary
            col1, col2 = st.columns(2)
            with col1:
                avg_cost = sum(r['cost_per_unit'] for r in recipes) / len(recipes)
                st.metric("Average Cost per Unit", f"${avg_cost:.4f}")
            with col2:
                highest_cost = max(recipes, key=lambda x: x['cost_per_unit'])
                st.metric("Highest Cost Recipe", 
                         f"${highest_cost['cost_per_unit']:.4f}", 
                         highest_cost['recipe_name'])
            
            # Recipe table
            st.divider()
            for recipe in filtered_recipes:
                with st.expander(f"🧾 {recipe['recipe_name']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write("**Total Cost per Batch:**")
                        st.write(f"${recipe['total_cost']:.4f}")
                    with col2:
                        st.write("**Output Quantity:**")
                        st.write(f"{recipe['output_quantity']} units")
                    with col3:
                        st.write("**Cost per Unit:**")
                        st.write(f"${recipe['cost_per_unit']:.4f}")
                    
                    # Get recipe details
                    conn = get_database_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT 
                            ri.name,
                            CAST(sfr.quantity_needed AS FLOAT) as quantity,
                            CAST(ri.cost_per_unit AS FLOAT) as unit_cost,
                            CAST(sfr.quantity_needed * ri.cost_per_unit AS FLOAT) as total_cost
                        FROM semi_finished_recipe sfr
                        JOIN raw_ingredients ri ON sfr.ingredient_id = ri.ingredient_id
                        WHERE sfr.semi_id = %s
                    """, (recipe['semi_id'],))
                    details = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    
                    # Show ingredient breakdown
                    st.write("**Ingredient Breakdown:**")
                    for item in details:
                        st.write(f"- {item['name']}: {item['quantity']}g × ${item['unit_cost']:.4f}/g = ${item['total_cost']:.4f}")
        else:
            st.info("No recipes found. Please create recipes first.")
    
    # Ingredient Usage Tab
    with tab2:
        st.subheader("Ingredient Usage Analysis")
        usage = get_ingredient_usage()
        
        if usage:
            # Create DataFrame for better analysis
            df = pd.DataFrame(usage)
            df['total_cost'] = df['total_needed'] * df['cost_per_unit']
            
            # Cost distribution using Streamlit's native chart
            st.write("**Cost Distribution by Ingredient**")
            
            # Calculate percentages for the chart
            total_cost = df['total_cost'].sum()
            df['percentage'] = df['total_cost'] / total_cost * 100
            
            # Create bar chart
            st.bar_chart(
                df.set_index('ingredient_name')['total_cost']
            )
            
            # Show percentage breakdown
            st.write("**Cost Breakdown:**")
            col1, col2 = st.columns(2)
            with col1:
                for idx, row in df.iterrows():
                    st.write(f"- {row['ingredient_name']}: {row['percentage']:.1f}%")
            
            # Usage table
            st.write("**Detailed Usage**")
            for item in usage:
                if item['total_needed']:  # Only show used ingredients
                    with st.expander(f"📊 {item['ingredient_name']}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write("**Cost per Unit:**")
                            st.write(f"${item['cost_per_unit']:.4f}/g")
                        with col2:
                            st.write("**Used in Recipes:**")
                            st.write(f"{item['used_in_recipes']} recipes")
                        with col3:
                            st.write("**Total Quantity Needed:**")
                            st.write(f"{item['total_needed']:.2f}g")
                            
                        # Add total cost for this ingredient
                        st.write("**Total Cost Contribution:**")
                        total_cost = item['total_needed'] * item['cost_per_unit']
                        st.write(f"${total_cost:.2f}")
        else:
            st.info("No ingredient usage data available.")