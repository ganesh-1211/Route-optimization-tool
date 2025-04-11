from flask import Flask, request, render_template, jsonify
import requests
from geopy.geocoders import Nominatim
import os
import json
from datetime import datetime

app = Flask(__name__)

# Your TomTom API key
API_KEY = "UPQVCVoVnTCeXndejK5mUCSa0JDrXPsN"

# Function to get latitude and longitude from a location name
def get_coordinates(location_name):
    geolocator = Nominatim(user_agent="MyGeocodingApp",timeout=10)
    location = geolocator.geocode(location_name)

    if location:
        return {
            "formatted": f"{location.latitude},{location.longitude}",
            "lat": location.latitude,
            "lng": location.longitude
        }
    return None

@app.route("/", methods=['GET'])
def index():
    return render_template("index.html")

@app.route("/route", methods=['POST'])
def calculate_route():
    source = request.form.get("source")
    destination = request.form.get("destination")
    traffic_option = request.form.get("traffic") == "on"  # Check if traffic checkbox is on
    
    # Format departure time properly if provided
    departure_time = request.form.get("departureTime")
    if departure_time:
        # Convert to proper format for TomTom API
        try:
            dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
            departure_time = dt.strftime("%Y-%m-%dT%H:%M:%S")
        except:
            departure_time = None

    if not source or not destination:
        return render_template("index.html", error="Please provide both source and destination")

    # Get coordinates
    start_coords = get_coordinates(source)
    end_coords = get_coordinates(destination)

    if not start_coords or not end_coords:
        return render_template("index.html", error="Invalid location names")

    # Fetch route from TomTom
    route_url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coords['formatted']}:{end_coords['formatted']}/json?key={API_KEY}&routeRepresentation=polyline"
    
    # Add traffic parameter if traffic is enabled
    if traffic_option:
        route_url += "&traffic=true"
        if departure_time:
            route_url += f"&departAt={departure_time}"
    
    print(f"Requesting route: {route_url}")  # Debug print
    
    response = requests.get(route_url)
    
    if response.status_code == 200:
        route_data = response.json()
        distance = route_data["routes"][0]["summary"]["lengthInMeters"] / 1000
        travel_time = route_data["routes"][0]["summary"]["travelTimeInSeconds"] / 3600
        
        # Get traffic data if available
        traffic_delay = 0
        if traffic_option and "trafficDelayInSeconds" in route_data["routes"][0]["summary"]:
            traffic_delay = route_data["routes"][0]["summary"]["trafficDelayInSeconds"] / 60
        
        # Get route geometry points
        legs = route_data["routes"][0]["legs"]
        points = []
        for leg in legs:
            for point in leg["points"]:
                points.append([point["latitude"], point["longitude"]])
        
        # Prepare traffic segments - simple version that will always work
        traffic_segments = []
        if traffic_option and traffic_delay > 0:
            # Create simplified traffic segments for visualization
            segment_count = min(5, len(points) - 1)
            step = len(points) // segment_count
            
            for i in range(segment_count):
                idx = min(i * step, len(points) - 1)
                # Assign traffic intensity based on position (just for visualization)
                intensity = "low"
                if traffic_delay > 5:
                    intensity = "moderate"
                if traffic_delay > 10:
                    intensity = "high"
                if traffic_delay > 20:
                    intensity = "severe"
                    
                traffic_segments.append({
                    "position": idx,
                    "point": points[idx],
                    "intensity": intensity
                })

        route_info = {
            "source": source,
            "destination": destination,
            "source_coords": start_coords,
            "dest_coords": end_coords,
            "distance_km": round(distance, 2),
            "eta": round(travel_time, 2),
            "traffic_delay_minutes": round(traffic_delay, 2),
            "has_traffic": traffic_delay > 0,
            "traffic_segments": json.dumps(traffic_segments),
            "route_points": json.dumps(points),
            "traffic_enabled": traffic_option
        }

        return render_template("index.html", route_info=route_info)
    else:
        error_message = f"Could not calculate route. Status code: {response.status_code}"
        try:
            error_data = response.json()
            error_message += f". Details: {json.dumps(error_data)}"
        except:
            pass
        
        print(f"Error: {error_message}")  # Debug print
        return render_template("index.html", error=error_message)

if __name__ == "__main__":
    app.run(debug=True)