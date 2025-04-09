from django.contrib.auth.models import Group, User
from rest_framework import serializers
from .models import Activities, Record
from django.db.models import Avg



class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password1",
            "password2",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["is_staff", "is_active", "date_joined"] 

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
    records = RecordSerializer(many=True, read_only=True)

    class Meta:
        model = Activities
        fields = [
            "ActivityID",
            "user",
            "timeCreated",
            "records", 
        ]


    def validate(self, data):
        # Check if 'password' and 'confirm_password' exist before using them
        if "password" in data and "confirm_password" in data:
            if data["password"] != data["confirm_password"]:
                raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            email=validated_data["email"],
        )
        return user
    
class ActivitiesListSerializer(serializers.ModelSerializer):
    avg_power = serializers.SerializerMethodField()
    class Meta:
        model = Activities
        fields = [
            "ActivityID",
            "user",
            "timeCreated",
            "distance",
            "elapsed_time",
            "time_started",
            "avg_power",
            "avg_speed",
            "avg_heartrate",
            "avg_cadence",
            "avg_temperature",
            "max_power",
            "max_speed",
            "max_heartrate",
            "max_cadence",
            "max_temperature",
            "ascended_elevation",
            "total_work_kJ",
            "position_lat",
            "position_long",
            "biggest_climb",
            "best_5s_power",
            "best_15s_power",
            "best_1min_power",
            "best_2min_power",
            "best_5min_power",
            "best_10min_power",
            "best_20min_power",
            "best_30min_power",
            "best_1h_power"
        ]

    def get_avg_power(self, obj):
        avg_power = obj.records.aggregate(avg_power=Avg("power"))["avg_power"]
        return avg_power if avg_power is not None else 0

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            email=validated_data["email"],
        )
        return user
class StatsSerializer(serializers.Serializer):
    total_activities = serializers.IntegerField()
    total_distance = serializers.IntegerField()
    total_elevation_gain = serializers.IntegerField()
    total_work_kJ = serializers.IntegerField()
    longest_ride = serializers.IntegerField()
    best_5s_power = serializers.IntegerField()
    best_15s_power = serializers.IntegerField()
    best_1min_power = serializers.IntegerField()
    best_2min_power = serializers.IntegerField()
    best_5min_power = serializers.IntegerField()
    best_10min_power = serializers.IntegerField()
    best_20min_power = serializers.IntegerField()
    best_30min_power = serializers.IntegerField()
    best_1h_power = serializers.IntegerField()