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
    # request from openroutesapi
    client = openrouteservice.Client(key=token)
    route = directions(client, coords, profile="driving-car", radiuses=5000)

    # extract line geometry
    encoded_polyline = route["routes"][0]["geometry"]
    decoded_polyline = decode_polyline(encoded_polyline)

    line = LineString(decoded_polyline["coordinates"])
    return line, route


def find_stations_on_route(route_line: LineString, max_distance=100000):
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
