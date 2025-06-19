# ocr_app/admin.py
import csv
from django.http import HttpResponse
from django.contrib import admin
from .models import UploadLog

def export_selected_logs_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="upload_logs.csv"'

    writer = csv.writer(response)
    # Write header from model fields, respecting list_display if possible or defining explicitly
    fields_to_export = ['id', 'filename', 'timestamp', 'status', 'language', 'pages_processed']
    writer.writerow([field.replace('_', ' ').title() for field in fields_to_export]) # Or get verbose_name

    # Write data rows
    for log in queryset.values_list(*fields_to_export):
        writer.writerow(log)
    return response

export_selected_logs_as_csv.short_description = "Export Selected Logs as CSV"

class UploadLogAdmin(admin.ModelAdmin):
    list_display = ('filename', 'timestamp', 'status', 'language', 'pages_processed', 'id')
    list_filter = ('status', 'language', 'timestamp')
    search_fields = ('filename', 'status', 'language')
    ordering = ('-timestamp',) # Already in model Meta, but can be explicit here too
    actions = [export_selected_logs_as_csv]

admin.site.register(UploadLog, UploadLogAdmin)
