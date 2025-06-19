import os
import cv2
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pytesseract import Output
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid # For generating unique filenames for previews

PREVIEWS_DIR_NAME = "processed_previews"

# If Tesseract is not in your PATH, include the following line
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image):
    """Preprocesses an image for better OCR results."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply thresholding
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # Optional: Apply denoising
    denoised = cv2.fastNlMeansDenoising(thresh, h=30)
    return denoised

def get_ocr_data(image, lang="eng"):
    """Performs OCR and returns text and confidence data."""
    # Use image_to_data to get detailed information
    data = pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT)
    return data

def process_file(filepath, lang='eng'):
    results = {"pages": [], "page_count": 0, "lang": lang}
    filename = os.path.basename(filepath)

    if filename.lower().endswith((".png", ".jpg", ".jpeg")):
        image_cv = cv2.imread(filepath)
        if image_cv is None:
            raise ValueError(f"Could not read image: {filepath}")
        processed_image = preprocess_image(image_cv)
        ocr_data = get_ocr_data(processed_image, lang)

        original_pil_image = Image.open(filepath)
        preview_filename = f"preview_{uuid.uuid4().hex}_{filename}"
        preview_save_path_relative = os.path.join(PREVIEWS_DIR_NAME, preview_filename)
        preview_save_path_full = os.path.join(settings.MEDIA_ROOT, preview_save_path_relative)

        os.makedirs(os.path.dirname(preview_save_path_full), exist_ok=True)
        original_pil_image.save(preview_save_path_full)

        results["pages"].append(
            {
                "page_num": 1,
                "text": " ".join(filter(None, ocr_data["text"])).strip(),
                "ocr_data": ocr_data,
                "preview_image_path": preview_save_path_relative,
            }
        )
        results["page_count"] = 1
    elif filename.lower().endswith(".pdf"):
        images_from_pdf = convert_from_path(filepath)
        results["page_count"] = len(images_from_pdf)

        for i, pil_image in enumerate(images_from_pdf):
            page_num = i + 1

            temp_image_for_cv_path = os.path.join(settings.MEDIA_ROOT, PREVIEWS_DIR_NAME, f"temp_cv_{uuid.uuid4().hex}.png")
            os.makedirs(os.path.dirname(temp_image_for_cv_path), exist_ok=True)
            pil_image.save(temp_image_for_cv_path, "PNG")

            image_cv = cv2.imread(temp_image_for_cv_path)
            if image_cv is None:
                results["pages"].append({
                    "page_num": page_num,
                    "text": "Error processing page.",
                    "ocr_data": {},
                    "preview_image_path": None
                })
                if os.path.exists(temp_image_for_cv_path):
                    os.remove(temp_image_for_cv_path)
                continue

            processed_image = preprocess_image(image_cv)
            ocr_data = get_ocr_data(processed_image, lang)

            preview_filename = f"preview_page_{page_num}_{uuid.uuid4().hex}_{filename}.png"
            preview_save_path_relative = os.path.join(PREVIEWS_DIR_NAME, preview_filename)
            preview_save_path_full = os.path.join(settings.MEDIA_ROOT, preview_save_path_relative)

            os.makedirs(os.path.dirname(preview_save_path_full), exist_ok=True)
            pil_image.save(preview_save_path_full, "PNG")

            results["pages"].append(
                {
                    "page_num": page_num,
                    "text": " ".join(filter(None, ocr_data["text"])).strip(),
                    "ocr_data": ocr_data,
                    "preview_image_path": preview_save_path_relative,
                }
            )
            if os.path.exists(temp_image_for_cv_path):
                os.remove(temp_image_for_cv_path)
    else:
        # Handle other file types or raise an error
        raise ValueError(f"Unsupported file type: {filename}")

    return results

def create_downloadable_file(results, file_format):
    if file_format == "txt":
        all_text = "\n\n".join([page["text"] for page in results["pages"]])
        return all_text.encode("utf-8"), "text/plain"
    elif file_format == "docx":
        doc = Document()
        for page_num, page in enumerate(results["pages"]):
            doc.add_paragraph(page["text"])
            if page_num < len(results["pages"]) - 1:
                doc.add_page_break()

        # Save docx to a byte stream
        from io import BytesIO
        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif file_format == "pdf": # Searchable PDF
        pdf_bytes_list = []
        lang_for_pdf = results.get("lang", "eng") # Get lang from results
        for page in results["pages"]:
            if page.get("preview_image_path"):
                original_image_full_path = os.path.join(settings.MEDIA_ROOT, page["preview_image_path"])
                if os.path.exists(original_image_full_path):
                    try:
                        # It's important that the image exists and is a valid image file.
                        # Also, Tesseract needs to be able to process it.
                        pdf_page_bytes = pytesseract.image_to_pdf_or_hocr(
                            original_image_full_path, extension="pdf", lang=lang_for_pdf
                        )
                        pdf_bytes_list.append(pdf_page_bytes)
                    except Exception as e:
                        # Log error or handle page-specific PDF conversion failure
                        print(f"Error converting page to PDF: {e}") # Basic error logging
                        # Optionally add a blank page or placeholder text to the PDF
                        # For simplicity, we'll skip this page in case of an error.
                        pass
                else:
                    # Handle missing image file
                    print(f"Missing image file for PDF creation: {original_image_full_path}")
                    pass

        if not pdf_bytes_list:
            # Handle case where no pages could be converted to PDF
            # Return a simple text message in a PDF or raise an error
            # For now, return empty bytes and let the caller handle it or raise error
            # This indicates that something went wrong in PDF generation.
            # A more robust solution would generate a PDF with an error message.
            return b"", "application/pdf" # Or raise an error

        return b"".join(pdf_bytes_list), "application/pdf"
    else:
        return b"Unsupported format", "text/plain"
