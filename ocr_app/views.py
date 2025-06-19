# ocr_app/views.py
import os
import json
import uuid
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from werkzeug.utils import secure_filename # Can keep this for filename security initially

from .models import UploadLog
from .ocr_utils import process_file, create_downloadable_file, PREVIEWS_DIR_NAME

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
JOB_RESULTS_DIR_NAME = "job_results" # Directory within MEDIA_ROOT for job outputs

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def index(request):
    # Later, this will render 'ocr_app/index.html'
    # For now, a placeholder or direct template name:
    return render(request, "ocr_app/index.html")

def upload_files(request):
    if request.method == "POST":
        if "files[]" not in request.FILES:
            messages.error(request, "No file part")
            return redirect(request.META.get('HTTP_REFERER', reverse('ocr_app:index')))

        files = request.FILES.getlist("files[]")
        language = request.POST.get("language", "eng")

        if not files or files[0].name == "":
            messages.error(request, "No selected file")
            return redirect(request.META.get('HTTP_REFERER', reverse('ocr_app:index')))

        job_id = str(uuid.uuid4())
        # Define paths for job results and uploads within MEDIA_ROOT
        job_folder_relative = os.path.join(JOB_RESULTS_DIR_NAME, job_id)
        job_folder_full = os.path.join(settings.MEDIA_ROOT, job_folder_relative)
        os.makedirs(job_folder_full, exist_ok=True)

        # Define path for temporary uploads within MEDIA_ROOT
        # These are the files Tesseract will process directly
        uploads_temp_dir_relative = "temp_uploads_for_processing"
        uploads_temp_dir_full = os.path.join(settings.MEDIA_ROOT, uploads_temp_dir_relative)
        os.makedirs(uploads_temp_dir_full, exist_ok=True)

        all_results_data = []

        for uploaded_file in files:
            if uploaded_file and allowed_file(uploaded_file.name):
                filename = secure_filename(uploaded_file.name)

                # Save uploaded file temporarily for processing
                # Ensure unique name for temp file to avoid clashes if multiple users upload same filename
                temp_filename = f"{job_id}_{uuid.uuid4().hex}_{filename}"
                saved_file_path_relative = os.path.join(uploads_temp_dir_relative, temp_filename)
                saved_file_path_full = default_storage.save(saved_file_path_relative, uploaded_file)
                actual_disk_path = os.path.join(settings.MEDIA_ROOT, saved_file_path_full)

                log = UploadLog(filename=filename, status="Processing", language=language)
                log.save()

                try:
                    result_data = process_file(actual_disk_path, lang=language) # process_file needs the actual disk path
                    result_data["original_filename"] = filename
                    # Ensure preview_image_path is relative to MEDIA_ROOT (already handled by ocr_utils)
                    all_results_data.append(result_data)

                    log.status = "Complete"
                    log.pages_processed = result_data.get("page_count", 0)
                    log.save()
                    messages.success(request, f"Successfully processed {filename}.")

                except Exception as e:
                    log.status = f"Error: {str(e)}"
                    log.save()
                    messages.error(request, f"An error occurred while processing {filename}: {e}")
                finally:
                    # Clean up the temporarily saved uploaded file
                    if default_storage.exists(saved_file_path_full): # Check existence before deleting
                        try: # Adding try-except for delete operation
                            default_storage.delete(saved_file_path_full)
                        except Exception as del_e:
                            messages.warning(request, f"Could not delete temp file {saved_file_path_full}: {del_e}")
            else:
                if uploaded_file and uploaded_file.name: # Check if there's a name
                    messages.warning(request, f"File type not allowed for {uploaded_file.name}")
                else: # Handle cases where file object might be None or have no name
                    messages.warning(request, "An invalid file was encountered.")

        if not all_results_data: # If no files were successfully processed
            messages.error(request, "No files were processed.")
            return redirect(reverse('ocr_app:index'))

        results_file_path_relative = os.path.join(job_folder_relative, "results.json")
        results_file_path_full = os.path.join(settings.MEDIA_ROOT, results_file_path_relative)

        # Use default_storage.open to ensure it works with different storage backends
        with default_storage.open(results_file_path_full, "w") as f:
            json.dump(all_results_data, f)

        request.session["job_id"] = job_id
        return redirect(reverse("ocr_app:show_results"))

    return redirect(reverse("ocr_app:index")) # Redirect if not POST

def show_results(request):
    job_id = request.session.get("job_id")
    if not job_id:
        messages.warning(request, "No job ID found in session.")
        return redirect(reverse("ocr_app:index"))

    job_folder_relative = os.path.join(JOB_RESULTS_DIR_NAME, job_id)
    results_file_path_relative = os.path.join(job_folder_relative, "results.json")
    results_file_path_full = os.path.join(settings.MEDIA_ROOT, results_file_path_relative)

    if not default_storage.exists(results_file_path_full):
        messages.error(request, "Results not found. Please try uploading again.")
        request.session.pop("job_id", None) # Clear invalid job_id
        return redirect(reverse("ocr_app:index"))

    with default_storage.open(results_file_path_full, "r") as f:
        results = json.load(f)

    # Construct full URLs for preview images
    for file_result in results:
        for page in file_result.get("pages", []):
            if page.get("preview_image_path"):
                # Ensure that preview_image_path is treated as relative to MEDIA_ROOT
                # os.path.join on a URL base and a potentially absolute-looking path might be tricky
                # if settings.MEDIA_URL ends with / and page["preview_image_path"] starts with /
                # it's better to ensure preview_image_path is always relative.
                # Assuming PREVIEWS_DIR_NAME and filenames don't start with /
                preview_path = page["preview_image_path"]
                if preview_path.startswith(settings.MEDIA_URL): # If it's somehow already a full URL
                    page["preview_image_url"] = preview_path
                else:
                    # Ensure no double slashes if MEDIA_URL ends with / and preview_path is not empty
                    media_url = settings.MEDIA_URL.rstrip('/')
                    preview_path = preview_path.lstrip('/')
                    page["preview_image_url"] = f"{media_url}/{preview_path}"

    # This will render 'ocr_app/results.html'
    return render(request, "ocr_app/results.html", {"results": results, "job_id": job_id})

def download_file(request, job_id, file_index, file_format):
    job_folder_relative = os.path.join(JOB_RESULTS_DIR_NAME, job_id)
    results_file_path_relative = os.path.join(job_folder_relative, "results.json")
    results_file_path_full = os.path.join(settings.MEDIA_ROOT, results_file_path_relative)

    if not default_storage.exists(results_file_path_full):
        messages.error(request, "Cannot find results to download.")
        # Try to redirect to results page if job_id is still in session, else to index
        if request.session.get("job_id") == job_id:
            return redirect(reverse("ocr_app:show_results"))
        return redirect(reverse("ocr_app:index"))

    try:
        with default_storage.open(results_file_path_full, "r") as f:
            results_data = json.load(f)

        # file_index is 0-based from URL, ensure it's int
        file_index = int(file_index)
        if not (0 <= file_index < len(results_data)):
            raise IndexError("File index out of range.")

        file_result_to_download = results_data[file_index]
        # Pass the language to create_downloadable_file
        # The language should be part of the result_data from process_file
        # If not, fallback to request or a default.
        if "lang" not in file_result_to_download:
             # This attempts to get language from the initial POST request if available,
             # or defaults to 'eng'. This part might be fragile if the session/POST data isn't persisted
             # or relevant here. Ideally, 'lang' is reliably stored in results.json.
             file_result_to_download["lang"] = request.POST.get("language", "eng")


        content, mimetype = create_downloadable_file(file_result_to_download, file_format)

        if content is None or mimetype is None:
            messages.error(request, "Invalid download format or error creating file.")
            # Redirect to results page if job_id is still in session
            if request.session.get("job_id") == job_id:
                 return redirect(reverse("ocr_app:show_results"))
            return redirect(reverse("ocr_app:index"))


        original_filename = file_result_to_download.get("original_filename", "download")
        base_filename, _ = os.path.splitext(original_filename)
        download_filename = f"{base_filename}.{file_format}"

        response = HttpResponse(content, content_type=mimetype)
        # Make sure the filename is properly encoded for Content-Disposition
        # Simple quoting for now, but more robust encoding might be needed for special characters.
        response["Content-Disposition"] = f"attachment; filename=\"{download_filename}\""
        return response

    except (FileNotFoundError, IndexError, TypeError) as e: # Added TypeError for safety
        messages.error(request, f"Could not find or process the file to download: {e}")
        if request.session.get("job_id") == job_id:
            return redirect(reverse("ocr_app:show_results"))
        return redirect(reverse("ocr_app:index"))
    except Exception as e:
        # Log the exception e for server-side review
        print(f"Unexpected error in download_file: {e}") # Basic logging
        messages.error(request, f"An unexpected error occurred during download.")
        return redirect(reverse("ocr_app:index"))
