from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class CoordinateField(serializers.Field):
    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                parts = list(map(float, data.split(",")))
                if len(parts) != 2:
                    raise ValueError
                lat, lng = parts
            except (ValueError, TypeError):
                raise ValidationError(
                    "Invalid coordinate format. Use 'lat,lng' or {lat: x, lng: y}"
                )

        elif isinstance(data, dict):
            try:
                lat = float(data.get("lat"))
                lng = float(data.get("lng"))
            except (TypeError, ValueError):
                raise ValidationError(
                    "Invalid coordinate object. Must contain lat and lng"
                )

        else:
            raise ValidationError("Coordinates must be string or object")

        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise ValidationError(
                "Invalid coordinate values (lat: -90-90, lng: -180-180)"
            )

        return (lng, lat)

    def to_representation(self, value):
        return {"lat": value[0], "lng": value[1]}


class RouteOptimizerSerializer(serializers.Serializer):
    start = CoordinateField(help_text="Start coordinates (object or 'lat,lng' string)")
    end = CoordinateField(help_text="End coordinates (object or 'lat,lng' string)")


class FuelStopSerializer(serializers.Serializer):
    distance = serializers.IntegerField()
    price = serializers.FloatField()
    Truckstop_Name = serializers.CharField()
    Address = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class StepSerializer(serializers.Serializer):
    distance = serializers.FloatField()
    duration = serializers.FloatField()
    type = serializers.IntegerField()
    instruction = serializers.CharField()
    name = serializers.CharField()
    way_points = serializers.ListSerializer(child=serializers.IntegerField())


class SegmentSerializer(serializers.Serializer):
    distance = serializers.FloatField()
    duration = serializers.FloatField()
    steps = serializers.ListSerializer(child=StepSerializer())


class SummarySeriealizer(serializers.Serializer):
    distance = serializers.FloatField()
    duration = serializers.FloatField()


class RouteSerializer(serializers.Serializer):
    summary = SummarySeriealizer()
    segments = serializers.ListSerializer(child=SegmentSerializer())
    geometry = serializers.CharField()


class RouteOptimizerResponseSerializer(serializers.Serializer):
    route = RouteSerializer()
    stops = FuelStopSerializer(many=True)
    total_cost = serializers.FloatField()
    total_distance_meters = serializers.FloatField()


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
