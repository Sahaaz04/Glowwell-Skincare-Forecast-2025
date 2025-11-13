import pandas as pd
from prophet import Prophet
import numpy as np
from datetime import datetime, timedelta

# Load data
df = pd.read_csv(r"C:\Program Files\Analysis\glowwell_skincare_daily_2024_data.csv")
df['Date'] = pd.to_datetime(df['Date'])

# Get last prices
last_prices = df.sort_values('Date').groupby(['Product_Name', 'State'])['Selling_Price'].last().reset_index()

# Aggregate to monthly
monthly_data = df.groupby(['Product_Name', 'State', pd.Grouper(key='Date', freq='M')])['Units_Sold'].sum().reset_index()
monthly_data = monthly_data.rename(columns={'Date': 'ds', 'Units_Sold': 'y'})

# Calculate historical daily demand statistics for safety stock
daily_data = df.groupby(['Product_Name', 'State', 'Date'])['Units_Sold'].sum().reset_index()
daily_stats = daily_data.groupby(['Product_Name', 'State']).agg(
    daily_std=('Units_Sold', 'std'),
    daily_avg=('Units_Sold', 'mean')
).reset_index()

# Forecast
forecast_results = []
for product in df['Product_Name'].unique():
    for state in df['State'].unique():
        data = monthly_data[(monthly_data['Product_Name'] == product) & (monthly_data['State'] == state)]
        if len(data) < 12: 
            continue
        
        model = Prophet(yearly_seasonality=True)
        model.fit(data[['ds', 'y']])
        
        future = model.make_future_dataframe(periods=12, freq='M')
        future = future[future['ds'].dt.year == 2025]
        
        forecast = model.predict(future)[['ds', 'yhat']]
        forecast['Product_Name'] = product
        forecast['State'] = state
        forecast_results.append(forecast)

# Combine forecasts
if forecast_results:
    monthly_forecast = pd.concat(forecast_results, ignore_index=True)
    monthly_forecast = monthly_forecast.merge(last_prices, on=['Product_Name', 'State'])
    monthly_forecast['Forecasted_Monthly_Sales'] = monthly_forecast['yhat'] * monthly_forecast['Selling_Price']
    monthly_forecast = monthly_forecast.rename(columns={
        'ds': 'Month', 
        'yhat': 'Forecasted_Monthly_Units', 
        'Selling_Price': 'Last_Price'
    })
    
    # Convert monthly forecast to daily forecast
    daily_forecasts = []
    
    for _, row in monthly_forecast.iterrows():
        month = row['Month']
        product = row['Product_Name']
        state = row['State']
        monthly_units = row['Forecasted_Monthly_Units']
        
        # Get number of days in the month
        days_in_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        days_in_month = days_in_month.day
        
        # Calculate daily forecast (distribute monthly units across days)
        daily_units = monthly_units / days_in_month
        
        # Create daily records for the entire month
        for day in range(1, days_in_month + 1):
            date = datetime(month.year, month.month, day)
            daily_forecasts.append({
                'Date': date,
                'Month': month,
                'Product_Name': product,
                'State': state,
                'Daily_Forecast_Units': daily_units,
                'Last_Price': row['Last_Price']
            })
    
    daily_forecast_df = pd.DataFrame(daily_forecasts)
    
    # Merge with daily statistics for safety stock calculation
    daily_forecast_df = daily_forecast_df.merge(daily_stats, on=['Product_Name', 'State'], how='left')
    
    # Fill NaN values in daily_std with a small value (1% of daily average)
    daily_forecast_df['daily_std'] = daily_forecast_df['daily_std'].fillna(daily_forecast_df['daily_avg'] * 0.01)
    
    # Calculate inventory metrics
    # Safety Stock = Z * σ * √lead_time (using Z=1.65 for 95% service level)
    lead_time = 3  # 3 days lead time
    z_score = 1.65  # 95% service level
    
    daily_forecast_df['Safety_Stock'] = z_score * daily_forecast_df['daily_std'] * np.sqrt(lead_time)
    daily_forecast_df['Reorder_Point'] = (daily_forecast_df['Daily_Forecast_Units'] * lead_time) + daily_forecast_df['Safety_Stock']
    
    # Aggregate back to monthly level for final output
    monthly_inventory = daily_forecast_df.groupby(['Month', 'Product_Name', 'State']).agg({
        'Daily_Forecast_Units': 'sum',  # equal the original monthly forecast
        'Last_Price': 'first',
        'Safety_Stock': 'mean',  # Average safety stock for the month
        'Reorder_Point': 'mean'  # Average reorder point for the month
    }).reset_index()
    
    monthly_inventory = monthly_inventory.rename(columns={
        'Daily_Forecast_Units': 'Forecasted_Monthly_Units'
    })
    
    # Calculate monthly sales
    monthly_inventory['Forecasted_Monthly_Sales'] = monthly_inventory['Forecasted_Monthly_Units'] * monthly_inventory['Last_Price']
    
    # Round the values
    monthly_inventory['Forecasted_Monthly_Units'] = monthly_inventory['Forecasted_Monthly_Units'].round(1)
    monthly_inventory['Safety_Stock'] = monthly_inventory['Safety_Stock'].round(1)
    monthly_inventory['Reorder_Point'] = monthly_inventory['Reorder_Point'].round(1)
    monthly_inventory['Forecasted_Monthly_Sales'] = monthly_inventory['Forecasted_Monthly_Sales'].round(2)
    
    # Save results
    monthly_inventory.to_csv('glowwell_forecast_2025.csv', index=False)
    
    print("2025 Monthly Forecast with Inventory Metrics:")
    print("=" * 100)
    print(f"{'Month':<12} {'Product':<15} {'State':<6} {'Monthly Units':<15} {'Monthly Sales':<15} {'Reorder Point':<15}")
    print("-" * 100)
    
    for _, row in monthly_inventory.iterrows():
        print(f"{row['Month'].strftime('%Y-%m'):<12} {row['Product_Name']:<15} {row['State']:<6} {row['Forecasted_Monthly_Units']:<15.1f} ${row['Forecasted_Monthly_Sales']:<14.2f} {row['Reorder_Point']:<15.1f}")
    