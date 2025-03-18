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
from django.db.models import Sum, F, Max

from .serializers import RegisterSerializer

from django.http import JsonResponse
from django.middleware.csrf import get_token


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
        return Activities.objects.filter(user=self.request.user).order_by("-time_started")
        
    

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

class StatsView(APIView):
    """
    API view to retrieve user activity statistics.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user  # Get the logged-in user

        # Get user activities
        activities = Activities.objects.filter(user=user)

        # Aggregating statistics
        total_activities = activities.count()
        total_distance = activities.aggregate(total_distance=Sum("distance"))["total_distance"] or 0
        #total_time 
        total_elevation_gain = activities.aggregate(total_elevation_gain=Sum("ascended_elevation"))["total_elevation_gain"] or 0
        total_work_kJ = activities.aggregate(total_work_kJ=Sum("total_work_kJ"))["total_work_kJ"] or 0
        longest_ride = activities.aggregate(longest_ride=Max("distance"))["longest_ride"] or 0
        biggest_climb_elevation_gain = activities.aggregate(biggest_climb_elevation_gain=Max("ascended_elevation"))["biggest_climb_elevation_gain"] or 0
        best_5s_power = activities.aggregate(best_5s_power=Max("best_5s_power"))["best_5s_power"] or 0
        best_15s_power = activities.aggregate(best_15s_power=Max("best_15s_power"))["best_15s_power"] or 0
        best_1min_power = activities.aggregate(best_1min_power=Max("best_1min_power"))["best_1min_power"] or 0
        best_2min_power = activities.aggregate(best_2min_power=Max("best_2min_power"))["best_2min_power"] or 0
        best_5min_power = activities.aggregate(best_5min_power=Max("best_5min_power"))["best_5min_power"] or 0
        best_10min_power = activities.aggregate(best_10min_power=Max("best_10min_power"))["best_10min_power"] or 0
        best_20min_power = activities.aggregate(best_20min_power=Max("best_20min_power"))["best_20min_power"] or 0
        best_30min_power = activities.aggregate(best_30min_power=Max("best_30min_power"))["best_30min_power"] or 0
        best_1h_power = activities.aggregate(best_1h_power=Max("best_1h_power"))["best_1h_power"] or 0
        stats_data = {
            "total_activities": total_activities,
            "total_distance": total_distance,
            "total_elevation_gain": total_elevation_gain,
            "total_work_kJ": total_work_kJ,
            "longest_ride": longest_ride,
            "biggest_climb_elevation_gain": biggest_climb_elevation_gain,
            "best_5s_power": best_5s_power,
            "best_15s_power": best_15s_power,
            "best_1min_power": best_1min_power,
            "best_2min_power": best_2min_power,
            "best_5min_power": best_5min_power,
            "best_10min_power": best_10min_power,
            "best_20min_power": best_20min_power,
            "best_30min_power": best_30min_power,
            "best_1h_power": best_1h_power,
        }   
        return Response(stats_data, status=status.HTTP_200_OK)


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

            # Define power tracking variables
            durations = [5, 15, 60, 120, 300, 600, 1200, 1800, 3600]  # Durations in seconds
            power_windows = {d: [] for d in durations}
            power_sums = {d: 0 for d in durations}
            best_powers = {d: 0 for d in durations}

            for record in fitfile.get_messages('record'):
                data = {field.name: field.value for field in record}

                if "power" in data and data["power"] is not None:
                    power_value = data["power"]
                    total_power += power_value
                    power_count += 1
                    max_power = max(max_power, power_value)
                    total_work_kJ += power_value / 1000  # Convert W to kJ

                    # **Update Rolling Windows for Each Duration**
                    for d in durations:
                        power_windows[d].append(power_value)
                        power_sums[d] += power_value

                        if len(power_windows[d]) > d:  
                            power_sums[d] -= power_windows[d].pop(0)  # Remove oldest value
        
                        best_powers[d] = max(best_powers[d], power_sums[d] / min(len(power_windows[d]), d))


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
                first_position_lat = records_to_create[0].position_lat
                first_position_long = records_to_create[0].position_long
                new_activity.elapsed_time = last - first
                new_activity.distance = records_to_create[-1].distance / 1000
                new_activity.time_started = first
                
                new_activity.position_lat = first_position_lat * (180 / 2147483648)
                new_activity.position_long = first_position_long * (180 / 2147483648)
                
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

                new_activity.best_5s_power = best_powers[5]
                new_activity.best_15s_power = best_powers[15]
                new_activity.best_1min_power = best_powers[60]
                new_activity.best_2min_power = best_powers[120]
                new_activity.best_5min_power = best_powers[300]
                new_activity.best_10min_power = best_powers[600]
                new_activity.best_20min_power = best_powers[1200]
                new_activity.best_30min_power = best_powers[1800]
                new_activity.best_1h_power = best_powers[3600]


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
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)
            csrf_token = get_token(request)  
            
            response = Response({
                "token": token.key,
                "username": username,
                "csrfToken": csrf_token,  
            })
            
            response.set_cookie("csrftoken", csrf_token, httponly=True)  
            return response

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

