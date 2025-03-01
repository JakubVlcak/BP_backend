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
import datetime

from .serializers import RegisterSerializer


from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

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
            # Use the fitparse library to parse the FIT file
            fitfile = FitFile(fit_file)
            user = request.user
            
            new_activity = Activities.objects.create(user=user, timeCreated=now())
        
            records_to_create = []
            for record in fitfile.get_messages('record'):
                data = {}
                for field in record:
                    data[field.name] = field.value
                records_to_create.append(Record(
                    activity = new_activity,
                    timestamp=data.get('timestamp'),
                    position_lat=data.get('position_lat'),
                    position_long=data.get('position_long'),
                    cadence=data.get('cadence'),
                    distance= data.get('distance'),
                    power = data.get('power'),
                    temperature = data.get('temperature'),
                    altitude=data.get('altitude'),
                    heartRate=data.get('heart_rate'),
                    speed=data.get('speed')
                ))
            if records_to_create:
                first = records_to_create[0].timestamp
                last = records_to_create[-1].timestamp
                new_activity.elapsed_time = last - first
                new_activity.distance = records_to_create[-1].distance
                new_activity.save()
        

            # Bulk create records
            Record.objects.bulk_create(records_to_create)
            return Response({"message": "File parsed and data saved successfully."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




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
