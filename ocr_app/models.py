from django.db import models
from django.utils import timezone # For default timestamp

class UploadLog(models.Model):
    filename = models.CharField(max_length=200)
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50)
    language = models.CharField(max_length=10)
    pages_processed = models.IntegerField(default=0)

    def __str__(self):
        return self.filename

    class Meta:
        ordering = ['-timestamp'] # Optional: to match Flask app's ordering in admin
