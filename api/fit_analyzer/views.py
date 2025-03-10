import logging
from django.contrib.auth.models import Group, User
from django.utils.timezone import now
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from api.fit_analyzer.serializers import GroupSerializer, UserSerializer
from .models import Activities, Record
from .serializers import ActivitiesListSerializer, RecordSerializer
import io
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from fitparse import FitFile 
from decimal import Decimal
from decimal import ROUND_HALF_UP
from datetime import datetime

from .serializers import RegisterSerializer


from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
logger = logging.getLogger(__name__)
class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class ActivitiesViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Activities.
    Provides CRUD operations.
    """
    serializer_class = ActivitiesListSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Activities.objects.none()  

    def get_queryset(self):
        # Filter activities for the authenticated user
        return Activities.objects.filter(user=self.request.user)
    

class RecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Records.
    Provides CRUD operations.
    """
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    lookup_field = 'activity_id' 
    lookup_url_kwarg = 'activity_id'

    def get_queryset(self):
        activity_id = self.kwargs.get(self.lookup_url_kwarg)

        if not activity_id:
            return Record.objects.none() 

        
        try:
            activity = Activities.objects.get(ActivityID=activity_id)
            if activity.user != self.request.user:
                return Response({"error": "Forbidden activity"}, status=status.HTTP_403_FORBIDDEN)
        except Activities.DoesNotExist:
            return Response({"error": "Activity not found"}, status=status.HTTP_404_NOT_FOUND)

        queryset = Record.objects.filter(activity_id=activity_id)
        return queryset


class FitFileParseView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        file_obj = request.data.get('file')
        if not file_obj:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            fit_file = io.BytesIO(file_obj.read())  
            fitfile = FitFile(fit_file)
            user = request.user

            new_activity = Activities.objects.create(user=user, timeCreated=now())

            records_to_create = []

            total_power = total_speed = total_heartrate = total_cadence = total_temperature = 0
            max_power = max_speed = max_heartrate = max_cadence = max_temperature = float('-inf')
            total_ascended_elevation = 0  
            last_altitude = None  
            power_count = speed_count = heartrate_count = cadence_count = temperature_count = 0
            total_work_kJ = 0

            for record in fitfile.get_messages('record'):
                data = {field.name: field.value for field in record}

                if "power" in data and data["power"] is not None:
                    total_power += data["power"]
                    power_count += 1
                    max_power = max(max_power, data["power"])

                    total_work_kJ += data["power"] / 1000  # (W) * 1 sec / 1000

                if "speed" in data and data["speed"] is not None:
                    total_speed += data["speed"]
                    speed_count += 1
                    max_speed = max(max_speed, data["speed"])

                if "heart_rate" in data and data["heart_rate"] is not None:
                    total_heartrate += data["heart_rate"]
                    heartrate_count += 1
                    max_heartrate = max(max_heartrate, data["heart_rate"])

                if "cadence" in data and data["cadence"] is not None:
                    total_cadence += data["cadence"]
                    cadence_count += 1
                    max_cadence = max(max_cadence, data["cadence"])

                if "temperature" in data and data["temperature"] is not None:
                    total_temperature += data["temperature"]
                    temperature_count += 1
                    max_temperature = max(max_temperature, data["temperature"])

                if "altitude" in data and data["altitude"] is not None:
                    current_altitude = data["altitude"]
                    if last_altitude is not None and current_altitude > last_altitude:
                        total_ascended_elevation += (current_altitude - last_altitude)
                    last_altitude = current_altitude

                self.append_record(new_activity, records_to_create, data)

            if records_to_create:
                first = records_to_create[0].timestamp
                last = records_to_create[-1].timestamp
                new_activity.elapsed_time = last - first
                new_activity.distance = records_to_create[-1].distance / 1000
                new_activity.time_started = first
                
                
                new_activity.avg_power = total_power / power_count if power_count > 0 else 0
                new_activity.avg_heartrate = total_heartrate / heartrate_count if heartrate_count > 0 else 0
                new_activity.avg_speed = (total_speed * 3.6) / speed_count if speed_count > 0 else 0
                new_activity.avg_cadence = total_cadence / cadence_count if cadence_count > 0 else 0
                new_activity.avg_temperature = total_temperature / temperature_count if temperature_count > 0 else 0

                
                new_activity.max_power = max_power if max_power != float('-inf') else 0
                new_activity.max_speed = max_speed * 3.6 if max_speed != float('-inf') else 0
                new_activity.max_heartrate = max_heartrate if max_heartrate != float('-inf') else 0
                new_activity.max_cadence = max_cadence if max_cadence != float('-inf') else 0
                new_activity.max_temperature = max_temperature if max_temperature != float('-inf') else 0

                new_activity.total_work_kJ = total_work_kJ
                new_activity.ascended_elevation = total_ascended_elevation
                new_activity.save()

            Record.objects.bulk_create(records_to_create)
            return Response({"message": "File parsed and data saved successfully."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def append_record(self, new_activity, records_to_create, data):
        records_to_create.append(Record(
            activity=new_activity,
            timestamp=data.get('timestamp'),
            position_lat=data.get('position_lat'),
            position_long=data.get('position_long'),
            cadence=data.get('cadence'),
            distance=data.get('distance'),
            power=data.get('power'),
            temperature=data.get('temperature'),
            altitude=data.get('altitude'),
            heartRate=data.get('heart_rate'),
            speed=data.get('speed')
        ))
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key,
                             "username":username})
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Save the new user
            return Response(
                {"message": "User registered successfully!", "user": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
