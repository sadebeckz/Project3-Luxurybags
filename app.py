#Flask document 
from flask import Flask, jsonify, render_template, request
import sqlite3
import pandas as pd
import json
import plotly
import plotly.express as px
import altair as alt

app = Flask(__name__)

# Database connection function
def connect_db():
    conn = sqlite3.connect('Luxury_handbag_auctions.db')
    conn.row_factory = sqlite3.Row
    return conn

# Helper function to create a DataFrame from SQL query
def query_db(query, params=()):
    conn = connect_db()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# Home route that renders our main HTML template
@app.route('/')
def home():
    # Get list of brands for the dropdown filter
    brands = query_db("SELECT DISTINCT Brand FROM Christies_HongKong_March25_Sale ORDER BY Brand")['Brand'].tolist()
    brands.insert(0, "All Brands")  # Add "All Brands" option
    
    # Get list of colors for the dropdown filter
    colors = query_db("SELECT DISTINCT Color FROM Christies_HongKong_March25_Sale ORDER BY Color")['Color'].tolist()
    colors.insert(0, "All Colors")  # Add "All Colors" option
    
    # Get price stats for the dashboard header
    price_stats = query_db("""
        SELECT 
            COUNT(*) as total_items,
            AVG(Sale_Price) as avg_price, 
            MAX(Sale_Price) as max_price,
            MIN(Sale_Price) as min_price
        FROM Christies_HongKong_March25_Sale
    """).iloc[0]
    
    # Create default visualizations (when no filters are applied)
    brand_chart = create_brand_comparison()
    color_chart = create_color_comparison()
    year_chart = create_year_trend()
    leather_chart = create_leather_comparison()
    
    # Render the template with initial data
    return render_template('index.html', 
                          brands=brands,
                          colors=colors,
                          brand_chart=brand_chart,
                          color_chart=color_chart,
                          year_chart=year_chart,
                          leather_chart=leather_chart,
                          stats=price_stats)

# API endpoint to filter data based on user selection
@app.route('/api/filter_data')
def filter_data():
    # Get filter parameters from the request
    brand = request.args.get('brand', 'All Brands')
    color = request.args.get('color', 'All Colors')
    
    # Build the base query
    base_query = "SELECT * FROM Christies_HongKong_March25_Sale"
    conditions = []
    params = []
    
    # Add filter conditions if selected
    if brand != "All Brands":
        conditions.append("Brand = ?")
        params.append(brand)
    
    if color != "All Colors":
        conditions.append("Color = ?")
        params.append(color)
    
    # Combine conditions if any
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
    
    # Execute the query
    filtered_df = query_db(base_query, params)
    
    # Generate new visualizations based on filtered data
    brand_chart = create_brand_comparison(filtered_df)
    color_chart = create_color_comparison(filtered_df)
    year_chart = create_year_trend(filtered_df)
    leather_chart = create_leather_comparison(filtered_df)
    
    # Get price stats for the filtered data
    if len(filtered_df) > 0:
        avg_price = filtered_df['Sale_Price'].mean()
        max_price = filtered_df['Sale_Price'].max()
        min_price = filtered_df['Sale_Price'].min()
    else:
        avg_price = 0
        max_price = 0
        min_price = 0
    
    # Return the JSON data with all charts
    return jsonify({
        'brand_chart': brand_chart,
        'color_chart': color_chart,
        'year_chart': year_chart,
        'leather_chart': leather_chart,
        'stats': {
            'total_items': len(filtered_df),
            'avg_price': float(avg_price),
            'max_price': float(max_price),
            'min_price': float(min_price)
        }
    })

# Helper function to create brand comparison visualization
def create_brand_comparison(df=None):
    if df is None:
        # If no DataFrame provided, query the database
        df = query_db("""
            SELECT Brand, AVG(Sale_Price) as Avg_Price
            FROM Christies_HongKong_March25_Sale
            GROUP BY Brand
            ORDER BY Avg_Price DESC
        """)
    else:
        # Otherwise use the provided DataFrame
        df = df.groupby('Brand')['Sale_Price'].mean().reset_index().rename(
            columns={'Sale_Price': 'Avg_Price'}).sort_values('Avg_Price', ascending=False)
    
    # Create a bar chart using Altair (the non-standard library)
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Brand:N', sort='-y'),
        y=alt.Y('Avg_Price:Q', title='Average Price (USD)'),
        color=alt.Color('Brand:N', legend=None),
        tooltip=['Brand', alt.Tooltip('Avg_Price:Q', format='$,.2f')]
    ).properties(
        title='Average Price by Brand',
        width='container',
        height=300
    ).interactive()
    
    return chart.to_json()

# Helper function to create color comparison visualization
def create_color_comparison(df=None):
    if df is None:
        # If no DataFrame provided, query the database
        df = query_db("""
            SELECT Color, AVG(Sale_Price) as Avg_Price
            FROM Christies_HongKong_March25_Sale
            GROUP BY Color
            ORDER BY Avg_Price DESC
        """)
    else:
        # Otherwise use the provided DataFrame
        df = df.groupby('Color')['Sale_Price'].mean().reset_index().rename(
            columns={'Sale_Price': 'Avg_Price'}).sort_values('Avg_Price', ascending=False)
    
    # Create visualization with Plotly
    fig = px.bar(df, x='Color', y='Avg_Price', 
                title='Average Price by Color',
                labels={'Avg_Price': 'Average Price (USD)', 'Color': 'Color'},
                color='Color')
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# Helper function to create year trend visualization
def create_year_trend(df=None):
    if df is None:
        # If no DataFrame provided, query the database
        df = query_db("""
            SELECT Year, AVG(Sale_Price) as Avg_Price
            FROM Christies_HongKong_March25_Sale
            GROUP BY Year
            ORDER BY Year
        """)
    else:
        # Otherwise use the provided DataFrame
        if 'Year' in df.columns:
            df = df.groupby('Year')['Sale_Price'].mean().reset_index().rename(
                columns={'Sale_Price': 'Avg_Price'}).sort_values('Year')
        else:
            # If no Year column, use a dummy DataFrame
            df = pd.DataFrame({'Year': ['No Year Data'], 'Avg_Price': [0]})
    
    # Create visualization with Plotly
    fig = px.line(df, x='Year', y='Avg_Price', 
                 title='Price Trends Over Years',
                 labels={'Avg_Price': 'Average Price (USD)', 'Year': 'Year'},
                 markers=True)
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# Helper function to create leather comparison visualization
def create_leather_comparison(df=None):
    if df is None:
        # If no DataFrame provided, query the database
        df = query_db("""
            SELECT Leather, AVG(Sale_Price) as Avg_Price
            FROM Christies_HongKong_March25_Sale
            GROUP BY Leather
            ORDER BY Avg_Price DESC
            LIMIT 10
        """)
    else:
        # Otherwise use the provided DataFrame
        df = df.groupby('Leather')['Sale_Price'].mean().reset_index().rename(
            columns={'Sale_Price': 'Avg_Price'}).sort_values('Avg_Price', ascending=False).head(10)
    
    # Create visualization with Plotly
    fig = px.bar(df, x='Leather', y='Avg_Price', 
                title='Top 10 Leathers by Average Price',
                labels={'Avg_Price': 'Average Price (USD)', 'Leather': 'Leather Type'},
                color='Leather')
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# API endpoint to get top performing bags
@app.route('/api/top_bags')
def get_top_bags():
    df = query_db("""
        SELECT Brand, Description, Leather, Color, Sale_Price 
        FROM Christies_HongKong_March25_Sale
        ORDER BY Sale_Price DESC
        LIMIT 10
    """)
    
    return jsonify(df.to_dict(orient='records'))

# API endpoint to get database statistics
@app.route('/api/stats')
def get_stats():
    stats_df = query_db("""
        SELECT 
            COUNT(*) as total_items,
            COUNT(DISTINCT Brand) as brand_count,
            COUNT(DISTINCT Color) as color_count,
            COUNT(DISTINCT Leather) as leather_count,
            AVG(Sale_Price) as avg_price,
            MAX(Sale_Price) as max_price,
            MIN(Sale_Price) as min_price
        FROM Christies_HongKong_March25_Sale
    """)
    
    stats = stats_df.iloc[0].to_dict()Christies_HongKong_March25_Sale 
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
