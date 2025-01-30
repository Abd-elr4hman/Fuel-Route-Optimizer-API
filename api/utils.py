import ast
import math
import os

import openrouteservice
import pandas as pd
from dotenv import load_dotenv
from openrouteservice.directions import directions
from shapely.geometry import LineString, Point

load_dotenv()
token = os.getenv("token")

FUEL_STATIONS = pd.read_csv("./api/data/test.csv", delimiter=";")
FUEL_STATIONS = FUEL_STATIONS.dropna(subset=["Geocode"])
FUEL_STATIONS["Geocode"] = FUEL_STATIONS["Geocode"].apply(ast.literal_eval)


def decode_polyline(polyline, is3d=False):
    """Decodes a Polyline string into a GeoJSON geometry.
    :param polyline: An encoded polyline, only the geometry.
    :type polyline: string
    :param is3d: Specifies if geometry contains Z component.
    :type is3d: boolean
    :returns: GeoJSON Linestring geometry
    :rtype: dict
    """
    points = []
    index = lat = lng = z = 0

    while index < len(polyline):
        result = 1
        shift = 0
        while True:
            b = ord(polyline[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1F:
                break
        lat += (~result >> 1) if (result & 1) != 0 else (result >> 1)

        result = 1
        shift = 0
        while True:
            b = ord(polyline[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1F:
                break
        lng += ~(result >> 1) if (result & 1) != 0 else (result >> 1)

        if is3d:
            result = 1
            shift = 0
            while True:
                b = ord(polyline[index]) - 63 - 1
                index += 1
                result += b << shift
                shift += 5
                if b < 0x1F:
                    break
            if (result & 1) != 0:
                z += ~(result >> 1)
            else:
                z += result >> 1

            points.append(
                [
                    round(lng * 1e-5, 6),
                    round(lat * 1e-5, 6),
                    round(z * 1e-2, 1),
                ]
            )

        else:
            points.append([round(lng * 1e-5, 6), round(lat * 1e-5, 6)])

    geojson = {"type": "LineString", "coordinates": points}

    return geojson


def get_route(coords):
    """
    Retrieves a route between the provided coordinates using the OpenRouteService API and returns the route's geometry and details.

    Args:
        coords (list of tuples): A list of coordinate tuples (longitude, latitude) representing the start and end points of the route.

    Returns:
        tuple: A tuple containing:
            - line (LineString): A Shapely LineString object representing the geometry of the route.
            - route (dict): The full response from the OpenRouteService API containing detailed route information.

    Example:
        >>> coords = [(8.681495, 49.41461), (8.687872, 49.420318)]
        >>> line, route = get_route(coords)
        >>> print(line)
        LINESTRING (8.681495 49.41461, 8.682 49.415, ...)
        >>> print(route['routes'][0]['summary'])
        {'distance': 1234.5, 'duration': 567.8}

    Notes:
        - Requires a valid OpenRouteService API token stored in the `token` variable.
        - The `radiuses` parameter is set to 5000 meters, meaning the route will snap to the nearest road within 5 km of the provided coordinates.
        - The function uses the `driving-car` profile for routing.
    """
    # request from openroutesapi
    client = openrouteservice.Client(key=token)
    route = directions(client, coords, profile="driving-car", radiuses=5000)

    # extract line geometry
    encoded_polyline = route["routes"][0]["geometry"]
    decoded_polyline = decode_polyline(encoded_polyline)

    line = LineString(decoded_polyline["coordinates"])
    return line, route


def find_stations_on_route(route_line: LineString, max_distance=100000):
    """
    Finds fuel stations located near a given route and calculates their distance along the route.

    Args:
        route_line (LineString): A Shapely LineString object representing the geometry of the route.
        max_distance (float, optional): The maximum allowable distance (in meters) between a station and the route
                                        for the station to be considered. Defaults to 100,000 meters (100 km).

    Returns:
        list of dict: A list of dictionaries, where each dictionary contains information about a fuel station near the route.
                      Each dictionary includes the following keys:
                        - "distance" (int): The distance along the route to the station (in meters).
                        - "price" (float): The retail price of fuel at the station.
                        - "Truckstop_Name" (str): The name of the truck stop or fuel station.
                        - "Address" (str): The address of the station.
                        - "lat" (float): The latitude of the station's projected point on the route.
                        - "lng" (float): The longitude of the station's projected point on the route.
                      The list is sorted by the "distance" key in ascending order.

    Notes:
        - The function assumes the existence of a global `FUEL_STATIONS` DataFrame containing fuel station data.
        - The `FUEL_STATIONS` DataFrame must have the following columns:
            - "Geocode": A tuple or list containing the station's longitude and latitude.
            - "Retail Price": The price of fuel at the station.
            - "Truckstop Name": The name of the station.
            - "Address": The address of the station.
        - The function calculates the geometric distance between the station and the route, projects the station onto the route,
          and computes the distance along the route to the projected point.
        - Distances are converted from degrees to meters using Earth's radius (6,371,000 meters).

    Example:
        >>> route_line = LineString([(8.681495, 49.41461), (8.687872, 49.420318)])
        >>> stations = find_stations_on_route(route_line, max_distance=5000)
        >>> for station in stations:
        ...     print(station["Truckstop_Name"], station["distance"])
        "Station A" 1234
        "Station B" 5678
    """
    # Constants
    EARTH_RADIUS = 6371000  # Earth's radius in meters
    DEG_TO_M = (2 * math.pi * EARTH_RADIUS) / 360  # Meters per degree

    stations = []
    for _, row in FUEL_STATIONS.iterrows():
        lat = row["Geocode"][1]
        lng = row["Geocode"][0]
        station_point = Point(lng, lat)
        distance = (
            route_line.distance(station_point) * DEG_TO_M
        )  # in geometric distance in degrees --> to meters
        if distance <= max_distance:
            projected_point = route_line.interpolate(route_line.project(station_point))
            distance_along = (
                route_line.project(projected_point) * DEG_TO_M
            )  # Convert to meters
            stations.append(
                {
                    "distance": int(distance_along),
                    "price": row["Retail Price"],
                    "Truckstop_Name": row["Truckstop Name"],
                    "Address": row["Address"],
                    "lat": projected_point.y,
                    "lng": projected_point.x,
                }
            )
    return sorted(stations, key=lambda x: x["distance"])


def calculate_optimal_stops(stations, total_distance):
    """
    Calculates the optimal fuel stops along a route based on fuel price and vehicle range.

    Args:
        stations (list of dict): A list of fuel station dictionaries, where each dictionary contains:
            - "distance" (int): The distance along the route to the station (in meters).
            - "price" (float): The retail price of fuel at the station.
            - Other keys (e.g., "Truckstop_Name", "Address", etc.) are ignored in this function.
        total_distance (float): The total distance of the route in meters.

    Returns:
        tuple: A tuple containing:
            - stops (list of dict): A list of selected fuel stations where the vehicle should stop.
                                    Each dictionary contains the same keys as the input `stations`.
            - total_cost (float): The estimated total cost of fuel for the trip, based on the selected stops.

            If no valid stops are found (e.g., no stations within range), returns `(None, None)`.

    Notes:
        - The function assumes a maximum vehicle range of 804,672 meters (500 miles).
        - The fuel consumption rate is assumed to be 10 miles per gallon (mpg).
        - The function iteratively selects the cheapest fuel station within the vehicle's range for each segment of the trip.
        - If the total distance is less than the vehicle's range, no stops are needed, and the function returns an empty list and a cost of 0.0.
        - If no stations are found within the vehicle's range at any point, the function returns `(None, None)`.

    Example:
        >>> stations = [
        ...     {"distance": 100000, "price": 3.50, "Truckstop_Name": "Station A", "Address": "123 Main St"},
        ...     {"distance": 300000, "price": 3.20, "Truckstop_Name": "Station B", "Address": "456 Elm St"},
        ...     {"distance": 600000, "price": 3.40, "Truckstop_Name": "Station C", "Address": "789 Oak St"},
        ... ]
        >>> total_distance = 1000000  # 1,000 km
        >>> stops, total_cost = calculate_optimal_stops(stations, total_distance)
        >>> for stop in stops:
        ...     print(stop["Truckstop_Name"], stop["distance"])
        Station B 300000
        Station C 600000
        >>> print(f"Total cost: ${total_cost:.2f}")
        Total cost: $64.50
    """
    MAX_DISTANCE = 804672  # in meters

    # if the trip is less than range
    if total_distance <= MAX_DISTANCE:
        return [], 0.0

    stops = []
    total_cost = 0.0
    current_position = 0.0

    # loop over the whole trip in 500 mile segmanets
    while current_position + MAX_DISTANCE < total_distance:
        # select candidate stations from all the nearby stations
        candidates = [
            s
            for s in stations
            if current_position < s["distance"] <= current_position + MAX_DISTANCE
        ]

        # if there is no candidates then return empty stops and cost
        if len(candidates) == 0:
            return None, None  # No stations in range

        # select the cheapest candidate in the next 500 miles
        cheapest = min(candidates, key=lambda x: x["price"])

        # calculate the distance along the line of route to said candidate
        segment_distance = cheapest["distance"] - current_position
        segment_distance_miles = segment_distance * 0.000621371192

        # calculate how much fuel would it take to travel the segment at the current price
        total_cost += (segment_distance_miles / 10) * cheapest["price"]

        # append the stop to stops list
        stops.append(cheapest)

        # update current position
        current_position = cheapest["distance"]

    # Add cost for remaining distance
    remaining = total_distance - current_position
    if remaining > 0 and stops:
        remaining_miles = remaining * 0.000621371192
        total_cost += (remaining_miles / 10) * stops[-1]["price"]

    return stops, total_cost
