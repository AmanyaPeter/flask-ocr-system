# ocr_app/urls.py
from django.urls import path
from . import views

app_name = 'ocr_app' # Important for namespacing (e.g., ocr_app:index)

urlpatterns = [
    path("", views.index, name="index"),
    path("upload/", views.upload_files, name="upload_files"),
    path("results/", views.show_results, name="show_results"),
    path("download/<str:job_id>/<int:file_index>/<str:file_format>/", views.download_file, name="download_file"),
]
