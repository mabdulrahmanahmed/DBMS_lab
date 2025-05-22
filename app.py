import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Streamlit App Configuration - MUST BE FIRST
st.set_page_config(page_title="Retail Store Analysis System", layout="wide")

# Database connection
@st.cache_resource
def init_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="MySQL03032004",
        database="retail_store_db"
    )

conn = init_connection()

# Helper functions
def execute_query(query, params=None):
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    result = cursor.fetchall()
    cursor.close()
    return result

def execute_update(query, params=None):
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    conn.commit()
    cursor.close()

def get_table_data(table_name):
    query = f"SELECT * FROM {table_name}"
    return pd.read_sql(query, conn)

def get_table_columns(table_name):
    cursor = conn.cursor()
    cursor.execute(f"DESCRIBE {table_name}")
    columns = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return columns
st.title("🏪 Retail Store Analysis System")

# Sidebar navigation
st.sidebar.title("Navigation")
menu = st.sidebar.selectbox(
    "Select Operation",
    ["Dashboard", "Add Data", "Edit Data", "Delete Data", "View Tables", "View Records", 
     "Export CSV", "Import CSV", "Data Analysis"]
)

tables = ["Product", "Inventory", "Customer", "Employee", "Store", "Sales", 
          "OutOfStockLog", "Returns", "DeadStock", "SalesTrend"]

if menu == "Dashboard":
    st.header("📊 System Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_products = execute_query("SELECT COUNT(*) FROM Product")[0][0]
        st.metric("Total Products", total_products)
    
    with col2:
        total_sales = execute_query("SELECT COUNT(*) FROM Sales")[0][0]
        st.metric("Total Sales", total_sales)
    
    with col3:
        out_of_stock = execute_query("SELECT COUNT(*) FROM Product WHERE current_stock = 0")[0][0]
        st.metric("Out of Stock Items", out_of_stock)
    
    with col4:
        total_customers = execute_query("SELECT COUNT(*) FROM Customer")[0][0]
        st.metric("Total Customers", total_customers)

elif menu == "Add Data":
    st.header("➕ Add New Data")
    
    selected_table = st.selectbox("Select Table", tables)
    columns = get_table_columns(selected_table)
    
    st.subheader(f"Add to {selected_table}")
    
    form_data = {}
    with st.form(f"add_{selected_table}"):
        for col in columns[1:]:  # Skip primary key
            if 'date' in col.lower():
                form_data[col] = st.date_input(col.replace('_', ' ').title())
            elif 'id' in col.lower() and col != columns[0]:
                form_data[col] = st.number_input(col.replace('_', ' ').title(), min_value=1)
            elif any(word in col.lower() for word in ['price', 'amount', 'points', 'quantity']):
                form_data[col] = st.number_input(col.replace('_', ' ').title(), min_value=0.0, step=0.01)
            else:
                form_data[col] = st.text_input(col.replace('_', ' ').title())
        
        if st.form_submit_button("Add Record"):
            placeholders = ', '.join(['%s'] * len(form_data))
            query = f"INSERT INTO {selected_table} ({', '.join(form_data.keys())}) VALUES ({placeholders})"
            try:
                execute_update(query, list(form_data.values()))
                st.success("Record added successfully!")
            except Exception as e:
                st.error(f"Error: {e}")

elif menu == "Edit Data":
    st.header("✏️ Edit Data")
    
    selected_table = st.selectbox("Select Table", tables)
    df = get_table_data(selected_table)
    
    if not df.empty:
        record_id = st.selectbox("Select Record ID", df.iloc[:, 0].tolist())
        record = df[df.iloc[:, 0] == record_id].iloc[0]
        
        st.subheader(f"Edit {selected_table} Record")
        
        form_data = {}
        with st.form(f"edit_{selected_table}"):
            for col in df.columns[1:]:  # Skip primary key
                current_value = record[col]
                if pd.isna(current_value):
                    current_value = ""
                
                if 'date' in col.lower():
                    form_data[col] = st.date_input(col.replace('_', ' ').title(), value=current_value)
                elif isinstance(current_value, (int, float)):
                    form_data[col] = st.number_input(col.replace('_', ' ').title(), value=float(current_value))
                else:
                    form_data[col] = st.text_input(col.replace('_', ' ').title(), value=str(current_value))
            
            if st.form_submit_button("Update Record"):
                set_clause = ', '.join([f"{col} = %s" for col in form_data.keys()])
                query = f"UPDATE {selected_table} SET {set_clause} WHERE {df.columns[0]} = %s"
                try:
                    execute_update(query, list(form_data.values()) + [record_id])
                    st.success("Record updated successfully!")
                except Exception as e:
                    st.error(f"Error: {e}")

elif menu == "Delete Data":
    st.header("🗑️ Delete Data")
    
    selected_table = st.selectbox("Select Table", tables)
    df = get_table_data(selected_table)
    
    if not df.empty:
        record_id = st.selectbox("Select Record ID to Delete", df.iloc[:, 0].tolist())
        
        if st.button("Delete Record", type="primary"):
            query = f"DELETE FROM {selected_table} WHERE {df.columns[0]} = %s"
            try:
                execute_update(query, (record_id,))
                st.success("Record deleted successfully!")
            except Exception as e:
                st.error(f"Error: {e}")

elif menu == "View Tables":
    st.header("📋 View All Tables")
    
    selected_table = st.selectbox("Select Table", tables)
    df = get_table_data(selected_table)
    
    st.subheader(f"{selected_table} Table")
    st.dataframe(df, use_container_width=True)

elif menu == "View Records":
    st.header("🔍 View Table Records")
    
    selected_table = st.selectbox("Select Table", tables)
    df = get_table_data(selected_table)
    
    if not df.empty:
        record_id = st.selectbox("Select Record ID", df.iloc[:, 0].tolist())
        record = df[df.iloc[:, 0] == record_id]
        
        st.subheader(f"{selected_table} Record Details")
        st.table(record.T)

elif menu == "Export CSV":
    st.header("📤 Export CSV")
    
    selected_table = st.selectbox("Select Table to Export", tables)
    
    if st.button("Generate CSV"):
        df = get_table_data(selected_table)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name=f"{selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

elif menu == "Import CSV":
    st.header("📥 Import CSV")
    
    selected_table = st.selectbox("Select Table to Import", tables)
    uploaded_file = st.file_uploader("Choose CSV file", type="csv")
    
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Preview:")
        st.dataframe(df.head())
        
        if st.button("Import Data"):
            try:
                df.to_sql(selected_table, conn, if_exists='append', index=False)
                st.success(f"Data imported successfully to {selected_table}!")
            except Exception as e:
                st.error(f"Error: {e}")

elif menu == "Data Analysis":
    st.header("📈 Data Analysis & Visualization")
    
    analysis_options = [
        "Out of Stock Analysis",
        "Sales Trends by Time",
        "Dead Stock Analysis",
        "Return and Refund Trends",
        "Employee Sales Performance",
        "Store-Level Comparison"
    ]
    
    selected_analysis = st.selectbox("Select Analysis", analysis_options)
    
    if selected_analysis == "Out of Stock Analysis":
        st.subheader("📉 Out of Stock Items Analysis")
        
        query = """
        SELECT p.name, p.category, o.demand_date, o.missed_quantity
        FROM OutOfStockLog o
        JOIN Product p ON o.product_id = p.product_id
        ORDER BY o.demand_date DESC
        """
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            fig = px.bar(df.groupby('category')['missed_quantity'].sum().reset_index(),
                        x='category', y='missed_quantity',
                        title="Missed Sales by Category")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df)
    
    elif selected_analysis == "Sales Trends by Time":
        st.subheader("📊 Sales Trends Analysis")
        
        query = """
        SELECT DATE(sale_date) as date, COUNT(*) as sales_count, SUM(total_amount) as revenue
        FROM Sales
        GROUP BY DATE(sale_date)
        ORDER BY date DESC
        LIMIT 30
        """
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            fig = px.line(df, x='date', y='revenue', title="Daily Revenue Trend")
            st.plotly_chart(fig, use_container_width=True)
            
            fig2 = px.bar(df, x='date', y='sales_count', title="Daily Sales Count")
            st.plotly_chart(fig2, use_container_width=True)
    
    elif selected_analysis == "Dead Stock Analysis":
        st.subheader("📦 Dead Stock Analysis")
        
        query = """
        SELECT p.name, p.category, d.days_unsold, p.current_stock, 
               (p.current_stock * p.cost_price) as tied_capital
        FROM DeadStock d
        JOIN Product p ON d.product_id = p.product_id
        WHERE d.days_unsold > 30
        ORDER BY d.days_unsold DESC
        """
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            fig = px.scatter(df, x='days_unsold', y='tied_capital', 
                           color='category', size='current_stock',
                           title="Dead Stock: Days Unsold vs Capital Tied")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df)
    
    elif selected_analysis == "Return and Refund Trends":
        st.subheader("↩️ Returns Analysis")
        
        query = """
        SELECT p.name, p.category, r.reason, COUNT(*) as return_count
        FROM Returns r
        JOIN Product p ON r.product_id = p.product_id
        GROUP BY p.product_id, r.reason
        ORDER BY return_count DESC
        """
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            fig = px.pie(df, values='return_count', names='reason',
                        title="Returns by Reason")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df)
    
    elif selected_analysis == "Employee Sales Performance":
        st.subheader("👥 Employee Performance")
        
        query = """
        SELECT e.name, COUNT(s.sale_id) as sales_count, 
               SUM(s.total_amount) as total_revenue
        FROM Employee e
        LEFT JOIN Sales s ON e.employee_id = s.employee_id
        GROUP BY e.employee_id
        ORDER BY total_revenue DESC
        """
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            fig = px.bar(df, x='name', y='total_revenue',
                        title="Employee Sales Performance")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df)
    
    elif selected_analysis == "Store-Level Comparison":
        st.subheader("🏪 Store Performance Comparison")
        
        query = """
        SELECT st.location, COUNT(s.sale_id) as sales_count,
               SUM(s.total_amount) as revenue
        FROM Store st
        LEFT JOIN Employee e ON st.store_id = e.store_id
        LEFT JOIN Sales s ON e.employee_id = s.employee_id
        GROUP BY st.store_id
        ORDER BY revenue DESC
        """
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            fig = px.bar(df, x='location', y='revenue',
                        title="Revenue by Store Location")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df)

# Footer
st.sidebar.markdown("---")
st.sidebar.info("Retail Store Analysis System v1.0")