import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def get_database_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        return connection
    except Error as e:
        st.error(f"""Database connection failed:
        - Host: {os.getenv('DB_HOST')}
        - User: {os.getenv('DB_USER')}
        - Database: {os.getenv('DB_NAME')}
        Error: {str(e)}
        """)
        return None
