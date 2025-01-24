from django.contrib.auth.models import Group, User
from django.utils.timezone import now
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from api.fit_analyzer.serializers import GroupSerializer, UserSerializer
from .models import Activities, Record
from .serializers import ActivitiesSerializer, RecordSerializer
import io
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from fitparse import FitFile 
from decimal import Decimal
from decimal import ROUND_HALF_UP

from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

class ActivitiesViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Activities.
    Provides CRUD operations.
    """
    queryset = Activities.objects.all()
    serializer_class = ActivitiesSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Records.
    Provides CRUD operations.
    """
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    permission_classes = [permissions.IsAuthenticated]

class FitFileParseView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        file_obj = request.data.get('file')

        if not file_obj:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            fit_file = io.BytesIO(file_obj.read())  # File read as binary data

            # Use the fitparse library to parse the FIT file
            fitfile = FitFile(fit_file)
            
            user = User.objects.first()
            # user = request.user
            # if not user.is_authenticated:
            #     return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)


            new_activity = Activities.objects.create(user=user, timeCreated=now())
            new_activity.save
            records_to_create = []
            for record in fitfile.get_messages('record'):
                data = {}
                for field in record:
                    data[field.name] = field.value

                # Create a new record instance for each entry
                records_to_create.append(Record(
                    activity = new_activity,
                    timestamp=data.get('timestamp'),
                    position_lat=data.get('position_lat'),
                    position_long=data.get('position_long'),
                    cadence=data.get('cadence'),
                    distance= round_to_3(data.get('distance')),
                    power = round_to_3(data.get('power')),
                    temperature = round_to_3(data.get('temperature')),
                    altitude=round_to_3(data.get('altitude')),
                    heartRate=round_to_3(data.get('heart_rate')),
                    speed=round_to_3(data.get('speed'))
                ))

            # Bulk create records
            Record.objects.bulk_create(records_to_create)

            return Response({"message": "File parsed and data saved successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

def round_to_3(value):
    if value is not None:
        # Convert value to Decimal for precise rounding and check bounds
        value = Decimal(value).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        
        # If value exceeds the allowed range, you can either truncate it or raise an error
        max_value = Decimal('999.999')  # Since scale is 12, total value must be < 1000
        if abs(value) > max_value:
            value = max_value  # Or handle as per your requirements (e.g., raise an error)
        return value
    return value



class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key})
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
