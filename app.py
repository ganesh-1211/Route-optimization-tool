from flask import Flask, request, jsonify, send_from_directory
import requests
from geopy.geocoders import Nominatim

app = Flask(__name__, static_folder="frontend")

API_KEY = "R1sl2YkY4yZG8mnpUf1nsUujDMtk8tCA"

# Function to get latitude and longitude from a location name
def get_coordinates(location_name):
    geolocator = Nominatim(user_agent="route_opt_app")
    location = geolocator.geocode(location_name)

    if location:
        return f"{location.latitude},{location.longitude}"
    return None

# Function to fetch traffic data
def get_traffic_data(location):
    traffic_url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point={location}&key={API_KEY}"
    response = requests.get(traffic_url)

    if response.status_code == 200:
        traffic_data = response.json()
        current_speed = traffic_data["flowSegmentData"]["currentSpeed"]
        free_flow_speed = traffic_data["flowSegmentData"]["freeFlowSpeed"]
        congestion = (free_flow_speed - current_speed) / free_flow_speed * 100

        return {"current_speed": current_speed, "free_flow_speed": free_flow_speed, "congestion": congestion}
    
    return None

@app.route("/")
def serve_index():
    return send_from_directory("frontend", "Webpage.html")

@app.route("/route", methods=["GET"])
def get_route():
    source = request.form["source"]
    destination = request.form["destination"]

    if not source or not destination:
        return jsonify({"error": "Missing source or destination"}), 400

    # Get coordinates
    start_coords = get_coordinates(source)
    end_coords = get_coordinates(destination)

    if not start_coords or not end_coords:
        return jsonify({"error": "Invalid location names"}), 400

    # Fetch route from TomTom
    route_url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coords}:{end_coords}/json?key={API_KEY}"
    response = requests.get(route_url)

    if response.status_code == 200:
        route_data = response.json()
        distance = route_data["routes"][0]["summary"]["lengthInMeters"] / 1000
        travel_time = route_data["routes"][0]["summary"]["travelTimeInSeconds"] / 60

        # Get traffic data
        source_traffic = get_traffic_data(start_coords)
        destination_traffic = get_traffic_data(end_coords)

        return jsonify({
            "source": source,
            "destination": destination,
            "distance_km": round(distance, 2),
            "eta_minutes": round(travel_time, 2),
            "traffic_source": source_traffic,
            "traffic_destination": destination_traffic
        })

    return jsonify({"error": "Route API request failed"}), 500

if __name__ == "__main__":
    app.run(debug=True)
