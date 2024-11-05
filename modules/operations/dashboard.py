import streamlit as st
from database.connection import get_database_connection
from datetime import datetime, timedelta
import pandas as pd

def get_inventory_value():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Raw ingredients value
    cursor.execute("""
        SELECT 
            CAST(SUM(quantity * cost_per_unit) AS FLOAT) as raw_value,
            COUNT(*) as total_items,
            SUM(CASE WHEN quantity < 1000 THEN 1 ELSE 0 END) as low_stock_items
        FROM raw_ingredients
    """)
    raw_stats = cursor.fetchone()
    
    # Semi-finished value (using recipe cost)
    cursor.execute("""
        SELECT 
            sf.semi_id,
            CAST(sf.quantity AS FLOAT) as quantity,
            CAST(SUM(ri.cost_per_unit * sfr.quantity_needed) AS FLOAT) as unit_cost
        FROM semi_finished sf
        JOIN semi_finished_recipe sfr ON sf.semi_id = sfr.semi_id
        JOIN raw_ingredients ri ON sfr.ingredient_id = ri.ingredient_id
        GROUP BY sf.semi_id, sf.quantity
    """)
    semi_stats = cursor.fetchall()
    
    semi_value = float(sum(row['quantity'] * row['unit_cost'] for row in semi_stats) if semi_stats else 0)
    raw_value = float(raw_stats['raw_value'] if raw_stats['raw_value'] else 0)
    
    return {
        'raw_value': raw_value,
        'semi_value': semi_value,
        'total_value': raw_value + semi_value,
        'total_items': int(raw_stats['total_items']),
        'low_stock': int(raw_stats['low_stock_items'])
    }

def get_expiring_items():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get items expiring in next 7 days
    cursor.execute("""
        SELECT 
            'semi' as type,
            name,
            quantity,
            expiry_date,
            DATEDIFF(expiry_date, CURDATE()) as days_left
        FROM semi_finished
        WHERE expiry_date IS NOT NULL 
        AND expiry_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        AND quantity > 0
        ORDER BY expiry_date
    """)
    
    expiring = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return expiring

def get_wastage_stats():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get last 30 days wastage
    cursor.execute("""
        SELECT 
            DATE(date) as waste_date,
            item_type,
            SUM(CASE 
                WHEN item_type = 'raw' THEN 
                    quantity * (SELECT cost_per_unit FROM raw_ingredients WHERE ingredient_id = item_id)
                ELSE 
                    quantity * (
                        SELECT SUM(ri.cost_per_unit * sfr.quantity_needed)
                        FROM semi_finished_recipe sfr
                        JOIN raw_ingredients ri ON sfr.ingredient_id = ri.ingredient_id
                        WHERE sfr.semi_id = item_id
                    )
            END) as waste_value
        FROM wastage
        WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY DATE(date), item_type
        ORDER BY waste_date DESC
    """)
    
    wastage = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return wastage

def get_sales_metrics():
    conn = get_database_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Today's sales
    cursor.execute("""
        SELECT 
            CAST(COALESCE(SUM(quantity * sale_price), 0) AS FLOAT) as today_revenue,
            COALESCE(SUM(quantity), 0) as today_units
        FROM sales 
        WHERE DATE(sale_date) = CURDATE()
    """)
    today = cursor.fetchone()
    
    # This month's sales
    cursor.execute("""
        SELECT 
            CAST(COALESCE(SUM(quantity * sale_price), 0) AS FLOAT) as month_revenue,
            COALESCE(SUM(quantity), 0) as month_units
        FROM sales 
        WHERE MONTH(sale_date) = MONTH(CURDATE())
        AND YEAR(sale_date) = YEAR(CURDATE())
    """)
    month = cursor.fetchone()
    
    # Top selling products this month
    cursor.execute("""
        SELECT 
            fp.name,
            COALESCE(SUM(s.quantity), 0) as units_sold,
            CAST(COALESCE(SUM(s.quantity * s.sale_price), 0) AS FLOAT) as revenue
        FROM final_products fp
        LEFT JOIN sales s ON fp.product_id = s.product_id
        AND MONTH(s.sale_date) = MONTH(CURDATE())
        AND YEAR(s.sale_date) = YEAR(CURDATE())
        GROUP BY fp.product_id, fp.name
        HAVING units_sold > 0
        ORDER BY units_sold DESC
        LIMIT 5
    """)
    top_products = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return today, month, top_products

def operations_dashboard():
    st.title("Operations Dashboard")
    
    # Get all stats
    inventory_value = get_inventory_value()
    expiring_items = get_expiring_items()
    wastage_stats = get_wastage_stats()
    today_sales, month_sales, top_products = get_sales_metrics()
    
    # Sales & Inventory Overview
    st.subheader("📊 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Today's Revenue", 
            f"${today_sales['today_revenue']:.2f}",
            f"{today_sales['today_units']} units"
        )
    
    with col2:
        st.metric(
            "Monthly Revenue", 
            f"${month_sales['month_revenue']:.2f}",
            f"{month_sales['month_units']} units"
        )
    
    with col3:
        st.metric(
            "Inventory Value", 
            f"${inventory_value['total_value']:.2f}",
            f"Raw: ${inventory_value['raw_value']:.2f}"
        )
    
    with col4:
        st.metric(
            "Low Stock Items", 
            inventory_value['low_stock'],
            f"of {inventory_value['total_items']} total"
        )
    
    # Top Products and Alerts
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.subheader("🏆 Top Selling Products")
        if top_products:
            for product in top_products:
                with st.expander(f"📦 {product['name']}"):
                    st.write(f"Units Sold: {product['units_sold']}")
                    st.write(f"Revenue: ${product['revenue']:.2f}")
        else:
            st.info("No sales data available this month")
    
    with col2:
        st.subheader("⚠️ Alerts")
        expiring_count = len(expiring_items)
        if expiring_count > 0:
            st.warning(f"{expiring_count} items expiring soon")
            if st.button("View Details"):
                for item in expiring_items:
                    days_left = (item['expiry_date'] - datetime.now().date()).days
                    if days_left <= 0:
                        st.error(f"🚨 EXPIRED: {item['name']} - {item['quantity']} units")
                    elif days_left <= 2:
                        st.warning(f"⚠️ {item['name']} - Expires in {days_left} days")
                    else:
                        st.info(f"ℹ️ {item['name']} - Expires in {days_left} days")
        else:
            st.success("No items expiring soon")
    
    # Wastage Analysis
    st.subheader("📉 Wastage Analysis")
    if wastage_stats:
        df = pd.DataFrame(wastage_stats)
        
        # Show total wastage value
        total_waste = df['waste_value'].sum()
        st.metric("Total Wastage Value (30 days)", f"${total_waste:.2f}")
        
        # Plot wastage trend
        st.line_chart(
            df.pivot_table(
                index='waste_date',
                columns='item_type',
                values='waste_value',
                aggfunc='sum'
            ).fillna(0)
        )
    else:
        st.info("No wastage data available for the last 30 days") 