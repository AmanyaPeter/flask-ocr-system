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

                file_processing_result = None # To store result or error info

                try:
                    # Process the file
                    processed_data_from_util = process_file(actual_disk_path, lang=language)

                    file_processing_result = processed_data_from_util
                    file_processing_result["original_filename"] = filename
                    file_processing_result["status"] = "Complete" # Explicitly set status for this entry
                    file_processing_result["lang"] = language


                    # Update log
                    log.status = "Complete"
                    log.pages_processed = processed_data_from_util.get("page_count", 0)
                    log.save()
                    messages.success(request, f"Successfully processed {filename}.")

                except Exception as e:
                    error_message_str = str(e)
                    log.status = f"Error: {error_message_str}"
                    log.save()
                    messages.error(request, f"An error occurred while processing {filename}: {error_message_str}")

                    file_processing_result = {
                        "original_filename": filename,
                        "status": "Error",
                        "error_message": error_message_str,
                        "pages": [], # No pages to show if processing failed
                        "page_count": 0,
                        "lang": language
                    }
                finally:
                    # Clean up the temporarily saved uploaded file
                    if default_storage.exists(saved_file_path_full): # Check existence before deleting
                        try: # Adding try-except for delete operation
                            default_storage.delete(saved_file_path_full)
                        except Exception as del_e:
                            messages.warning(request, f"Could not delete temp file {saved_file_path_full}: {del_e}")

                if file_processing_result: # Ensure it's not None
                    all_results_data.append(file_processing_result)
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

    # Construct full URLs for preview images and process text tokens
    for file_result_data in results: # 'results' is the list loaded from JSON
        # Construct preview_image_url (existing logic)
        for page_data in file_result_data.get("pages", []):
            if page_data.get("preview_image_path"):
                preview_path = page_data["preview_image_path"]
                if preview_path.startswith(settings.MEDIA_URL):
                    page_data["preview_image_url"] = preview_path
                else:
                    media_url = settings.MEDIA_URL.rstrip('/')
                    preview_path_cleaned = preview_path.lstrip('/')
                    page_data["preview_image_url"] = f"{media_url}/{preview_path_cleaned}"

        # Add the processed_text_tokens logic:
        if file_result_data.get("status") == "Complete": # Only process tokens if overall file status is Complete
            for page_data in file_result_data.get("pages", []):
                processed_tokens = []
                ocr_text_list = page_data.get("ocr_data", {}).get("text", [])
                ocr_conf_list = page_data.get("ocr_data", {}).get("conf", [])
                min_conf_for_highlight = 60

                for i, text_token in enumerate(ocr_text_list):
                    # Ensure text_token is a string, as Tesseract can return None
                    text_token_str = str(text_token) if text_token is not None else ""

                    confidence = -1 # Default for missing or invalid confidence
                    try:
                        # Tesseract confidences can be strings like '95.432...' or int/float
                        # It's safer to convert to float first, then int.
                        confidence_val_from_list = ocr_conf_list[i]
                        if confidence_val_from_list is not None and str(confidence_val_from_list).strip() != "":
                            confidence = int(float(confidence_val_from_list))
                        else: # Handle cases where confidence is None or empty string
                            confidence = -1
                    except (ValueError, TypeError, IndexError): # Catch various issues
                        confidence = -1 # Keep -1 if conversion fails or index is out of bounds

                    is_low_confidence = 0 <= confidence < min_conf_for_highlight # 0 is valid, -1 is not processed

                    processed_tokens.append({
                        "text": text_token_str,
                        "conf": confidence if confidence != -1 else "N/A", # Display N/A for unprocessed
                        "is_low": is_low_confidence
                    })
                page_data["processed_text_tokens"] = processed_tokens
        # If status is "Error", the template will use file_result_data.get("error_message")
        # which should have been set in the upload_files view.

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
