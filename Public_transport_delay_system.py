import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from datetime import datetime
import random

# Setup page config
st.set_page_config(page_title="🚍 Public Transport Delay Analysis", layout="wide")

# Title
st.markdown("<h1 style='text-align: center;'>🚍 Public Transport Delay Analysis</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: grey;'>Studying GPS and trip data to find peak delay zones in a city's transit network.</h4>", unsafe_allow_html=True)
st.markdown("---")

# Fetch Data from MBTA API
@st.cache_data(ttl=60)
def fetch_vehicle_data():
    url = "https://api-v3.mbta.com/vehicles"
    response = requests.get(url)
    data = response.json()

    vehicle_info = []
    for item in data["data"]:
        try:
            vehicle_info.append({
                "Vehicle ID": item["id"],
                "Route": item["relationships"]["route"]["data"]["id"],
                "Latitude": item["attributes"]["latitude"],
                "Longitude": item["attributes"]["longitude"],
                "Current Status": item["attributes"]["current_status"],
                "Updated At": item["attributes"]["updated_at"]
            })
        except:
            pass

    df = pd.DataFrame(vehicle_info)

    # Simulate realistic delays (0–6 mins)
    df["Delay (min)"] = [random.randint(0, 6) for _ in range(len(df))]

    # Categorize delay with new thresholds
    def categorize_delay(mins):
        if mins <= 1:
            return "On Time"
        elif mins == 2:
            return "Low Delay"
        elif mins <= 4:
            return "Moderate Delay"
        else:
            return "High Delay"

    df["Delay Category"] = df["Delay (min)"].apply(categorize_delay)
    df["Hour"] = pd.to_datetime(df["Updated At"]).dt.hour
    return df

df = fetch_vehicle_data()

# Sidebar
st.sidebar.header("🔎 Search & Filter")
vehicle_ids = df["Vehicle ID"].unique().tolist()
route_ids = df["Route"].unique().tolist()
search_vehicle = st.sidebar.selectbox("Search by Vehicle ID", ["None"] + vehicle_ids)
search_route = st.sidebar.selectbox("Search by Route ID", ["None"] + route_ids)
delay_filter = st.sidebar.selectbox("Filter by Delay Category", ["All", "On Time", "Low Delay", "Moderate Delay", "High Delay"])

# Apply Filters
filtered_df = df.copy()
if search_vehicle != "None":
    filtered_df = filtered_df[filtered_df["Vehicle ID"] == search_vehicle]
if search_route != "None":
    filtered_df = filtered_df[filtered_df["Route"] == search_route]
if delay_filter != "All":
    filtered_df = filtered_df[filtered_df["Delay Category"] == delay_filter]

# Live Data Table
st.subheader("🚌 Live Vehicle Status (Filtered)")
st.dataframe(filtered_df, use_container_width=True)

# 📋 Summary Statistics (Moved up here)
st.markdown("### 📋 Summary Statistics", unsafe_allow_html=True)
st.markdown("<hr style='border:1px solid #eee;'>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
col1.metric("🚌 Total Vehicles", len(df))
col2.metric("🛣️ Unique Routes", df["Route"].nunique())
col3.metric("⏱️ Avg Delay", f"{df['Delay (min)'].mean():.2f} min")

col4, col5, col6 = st.columns(3)
col4.metric("✅ On Time", len(df[df["Delay Category"] == "On Time"]))
col5.metric("🔴 High Delay", len(df[df["Delay Category"] == "High Delay"]))
col6.metric("⛔ Most Delayed Vehicle", df.sort_values("Delay (min)", ascending=False).iloc[0]["Vehicle ID"])

most_ontime_vehicle = df[df["Delay (min)"] == df["Delay (min)"].min()].iloc[0]["Vehicle ID"]
col7, _ = st.columns([1, 2])
col7.metric("💚 Most On-Time Vehicle", most_ontime_vehicle)

# Map
st.subheader("🗺️ GPS Map of Vehicle Locations")
if not filtered_df.empty:
    map_center = [filtered_df["Latitude"].mean(), filtered_df["Longitude"].mean()]
    m = folium.Map(location=map_center, zoom_start=12)

    color_map = {
        "On Time": "green",
        "Low Delay": "lightgreen",
        "Moderate Delay": "orange",
        "High Delay": "red"
    }

    for _, row in filtered_df.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f"Bus {row['Vehicle ID']} - Route {row['Route']} - Delay: {row['Delay (min)']} min",
            icon=folium.Icon(color=color_map.get(row["Delay Category"], "gray"), icon="bus", prefix="fa")
        ).add_to(m)

    # Delay legend
    legend_html = """
<div style='position: fixed; bottom: 50px; left: 50px; z-index:9999;
background-color: white; padding: 10px; border: 2px solid #333;
border-radius: 8px; font-size:14px; color: black; font-weight: bold;
box-shadow: 2px 2px 5px rgba(0,0,0,0.3);'>

<div style="margin-bottom: 5px;">🚍 <u>Legend</u></div>
<div><i class="fa fa-map-marker fa-2x" style="color:green;"></i>
<span style="color: black;">On Time</span></div>
<div><i class="fa fa-map-marker fa-2x" style="color:lightgreen;"></i>
<span style="color: black;">Low Delay</span></div>
<div><i class="fa fa-map-marker fa-2x" style="color:orange;"></i>
<span style="color: black;">Moderate Delay</span></div>
<div><i class="fa fa-map-marker fa-2x" style="color:red;"></i>
<span style="color: black;">High Delay</span></div>
</div>
"""
    m.get_root().html.add_child(folium.Element(legend_html))
    st_folium(m, width=900, height=500)
else:
    st.warning("No data to show on the map for current filters.")

# 📊 Filtered Comparative Graph
st.subheader("📊 Vehicle Delays in Same Route")
if not filtered_df.empty:
    route_to_show = filtered_df["Route"].iloc[0]
    vehicles_same_route = df[df["Route"] == route_to_show]

    if len(vehicles_same_route) > 1:
        sorted_df = vehicles_same_route.sort_values("Delay (min)", ascending=False)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(sorted_df["Vehicle ID"], sorted_df["Delay (min)"], color='salmon')
        ax.set_xlabel("Delay (min)")
        ax.set_ylabel("Vehicle ID")
        ax.set_title(f"Delays for Vehicles on Route {route_to_show}")
        st.pyplot(fig)
    else:
        st.info("Only one vehicle found for this route.")
else:
    st.info("Search or select a route to view comparison chart.")

# 📊 All Routes - Average Delay
st.subheader("📊 Average Delay by Route (All Vehicles)")
route_avg = df.groupby("Route")["Delay (min)"].mean().sort_values(ascending=False)
route_avg_df = route_avg.reset_index().rename(columns={"Delay (min)": "Average Delay"})
st.bar_chart(route_avg_df.set_index("Route"))

# 🧠 Smart AI Module: Best Vehicle & Hour Prediction
st.subheader("🧠 AI Prediction: Best Time & Vehicle")

ai_route = st.selectbox("Select a Route ID for prediction", sorted(df["Route"].unique()))

if ai_route:
    route_df = df[df["Route"].astype(str).str.lower().str.strip() == str(ai_route).lower().strip()]
    
    if not route_df.empty:
        best_hour = route_df.groupby("Hour")["Delay (min)"].mean().idxmin()
        best_vehicle_row = route_df.sort_values("Delay (min)").iloc[0]
        best_vehicle = best_vehicle_row["Vehicle ID"]
        best_delay = best_vehicle_row["Delay (min)"]

        st.success(f"🕒 Best Hour to Travel: **{best_hour}:00 hrs** (least average delay)")
        st.success(f"🚍 Best Vehicle on this Route: **{best_vehicle}** with just **{best_delay} min delay**")
    else:
        st.error("No data found for this route.")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center;'>✨ Made by Iman ✨</div>", unsafe_allow_html=True)
