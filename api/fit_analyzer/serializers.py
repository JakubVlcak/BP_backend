from django.contrib.auth.models import Group, User
from rest_framework import serializers
from .models import Activities, Record


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Record
        fields = [
            "RecordID",
            "activity",
            "timestamp",
            "position_lat",
            "position_long",
            "cadence",
            "distance",
            "power",
            "temperature",
            "altitude",
            "speed",
            "heartRate",
        ]


class ActivitiesSerializer(serializers.ModelSerializer):
    # Nested serialization to include related records
    records = RecordSerializer(many=True, read_only=True)

    class Meta:
        model = Activities
        fields = [
            "ActivityID",
            "user",
            "timeCreated",
            "records",  # Includes all related records
        ]
