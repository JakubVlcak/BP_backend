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


class RegisterSerializer(serializers.ModelSerializer):
    # Define password field explicitly to ensure write-only behavior
    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["is_staff", "is_active", "date_joined"]  # Prevent modifications on these fields

    def validate(self, data):
        # Check if password and confirm_password match
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        # Remove confirm_password before creating the user
        validated_data.pop("confirm_password")
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            email=validated_data["email"],
        )
        return user