from django.db import models
from django.contrib.auth.models import User



class Activities(models.Model):
    ActivityID = models.BigAutoField(primary_key=True)  
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    timeCreated = models.DateTimeField(auto_now_add=True)
    distance = models.DecimalField(max_digits=15, decimal_places=1, blank=True, null=True)
    elapsed_time = models.DurationField()
    time_started = models.DateTimeField(null=True)
    avg_power = models.BigIntegerField(null=True)
    avg_speed = models.DecimalField(max_digits=15, decimal_places=1, blank=True, null=True)
    avg_heartrate = models.BigIntegerField(null=True)
    avg_cadence = models.BigIntegerField(null=True)
    avg_temperature = models.BigIntegerField(null=True)
    max_power = models.BigIntegerField(null=True)
    max_speed = models.DecimalField(max_digits=15, decimal_places=1, blank=True, null=True)
    max_heartrate = models.BigIntegerField(null=True)
    max_cadence = models.BigIntegerField(null=True)
    max_temperature = models.BigIntegerField(null=True)
    ascended_elevation = models.BigIntegerField(null=True)
    total_work_kJ = models.BigIntegerField(null=True)

    def __str__(self):
        return f"Activity {self.ActivityID} by {self.user.userName}"

class Record(models.Model):
    RecordID = models.BigAutoField(primary_key=True)  
    activity = models.ForeignKey(Activities, on_delete=models.CASCADE, related_name='records')  
    timestamp = models.DateTimeField()
    position_lat = models.BigIntegerField(blank=True, null=True) 
    position_long = models.BigIntegerField(blank=True, null=True)  
    cadence = models.BigIntegerField(blank=True, null=True)
    distance = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True)
    power = models.BigIntegerField(blank=True, null=True)
    temperature = models.BigIntegerField(blank=True, null=True)
    altitude = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    speed = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    heartRate = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Record {self.RecordID} for Activity {self.activity.ActivityID}"

class FitFile(models.Model):
    file = models.FileField(upload_to='fit_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name