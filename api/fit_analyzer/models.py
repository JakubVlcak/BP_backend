from django.db import models
from django.contrib.auth.models import User



class Activities(models.Model):
    ActivityID = models.BigAutoField(primary_key=True)  
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    timeCreated = models.DateTimeField()
    distance = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True)
    elapsed_time = models.DurationField()
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