# flask-ocr-system
# Commercial-Scale Flask OCR System

This is a complete Python Flask web application designed for a commercial-scale Optical Character Recognition (OCR) system. It allows users to upload images and PDFs, processes them using a robust pipeline involving OpenCV and Tesseract, and provides the extracted text in various downloadable formats.

## Features

-   **Multi-Format Upload**: Supports single or multiple file uploads for `PNG`, `JPG`, and `PDF` formats.
-   **Advanced OCR Processing**:
    -   Automatically handles both image and PDF files.
    -   Converts PDF pages to images for processing.
    -   Improves OCR accuracy with image preprocessing (Grayscale, Thresholding) using OpenCV.
    -   Uses the powerful Tesseract OCR engine.
    -   Supports multiple languages (e.g., English, French, Swahili), selectable by the user.
-   **Interactive Results Page**:
    -   Displays extracted text side-by-side with a preview of the original file.
    -   Highlights words with low OCR confidence scores for easy review.
    -   Allows one-click download of results as `.txt`, `.docx`, or a searchable `.pdf`.
-   **Batch Processing**:
    -   Handles multiple file uploads in a single batch.
    -   Displays results for each file in an organized, collapsible view.
-   **Admin Dashboard**:
    -   Logs every upload attempt with filename, timestamp, status, and page count.
    -   Allows administrators to export all logs to a `.csv` file.
-   **Modern UI**:
    -   Clean and responsive user interface built with Bootstrap.
    -   Includes an optional dark mode toggle.
-   **Robust and Scalable**:
    -   Built with a Flask Blueprint structure for maintainability.
    -   Includes graceful error handling for unsupported formats or processing failures.

## Technology Stack

-   **Backend**: Python, Flask
-   **OCR Engine**: Tesseract OCR
-   **Image Processing**: OpenCV, Pillow
-   **PDF Handling**: `pdf2image`, `reportlab`
-   **Database**: SQLite (via Flask-SQLAlchemy)
-   **Document Export**: `python-docx`
-   **Frontend**: HTML, Jinja2, Bootstrap 5, JavaScript
-   **WSGI Server (Production)**: Gunicorn

## System Dependencies (Prerequisites)

Before installing the Python packages, you must install Tesseract and Poppler on your system.

### For Linux (Debian/Ubuntu)

1.  **Update Package List**:
    ```bash
    sudo apt-get update
    ```

2.  **Install Tesseract OCR**:
    ```bash
    sudo apt-get install -y tesseract-ocr
    ```

3.  **Install Tesseract Language Packs**:
    Install the language packs you need. For the languages included in the app (English, French, Swahili):
    ```bash
    # English is usually included by default
    sudo apt-get install -y tesseract-ocr-fra  # French
    sudo apt-get install -y tesseract-ocr-swa  # Swahili
    ```

4.  **Install Poppler**:
    `pdf2image` requires `poppler-utils` to convert PDFs to images.
    ```bash
    sudo apt-get install -y poppler-utils
    ```

### For macOS

1.  **Install Homebrew** (if you don't have it).

2.  **Install Tesseract and Languages**:
    ```bash
    brew install tesseract
    brew install tesseract-lang # Installs all available language packs
    ```

3.  **Install Poppler**:
    ```bash
    brew install poppler
    ```

### For Windows

1.  **Install Tesseract**:
    -   Download the installer from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
    -   **Crucially, during installation, make sure to check the box to add Tesseract to your system's `PATH`**. If you forget, you must add it manually.

2.  **Install Poppler**:
    -   Download the latest Poppler binary from [this page](https://github.com/oschwartz10612/poppler-windows/releases/).
    -   Extract the archive (e.g., to `C:\poppler-23.11.0\`).
    -   Add the `bin` subfolder (e.g., `C:\poppler-23.11.0\bin\`) to your system's `PATH`.

## Setup and Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/flask-ocr-system.git
    cd flask-ocr-system
    ```

2.  **Create and Activate a Virtual Environment**:

    -   **On Linux/macOS**:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    -   **On Windows**:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application (Development Mode)**:
    ```bash
    flask run
    ```
    The application will be available at `http://127.0.0.1:5000`.

## How to Use

1.  **Homepage**: Navigate to `http://127.0.0.1:5000`.
2.  **Upload**: Click "Select Files", choose one or more supported files, select the OCR language, and click "Upload and Process".
3.  **Results**: You will be redirected to the results page where you can view the extracted text, see the original image preview, and download the results.
4.  **Admin Dashboard**: Navigate to `http://127.0.0.1:5000/admin/dashboard` to view and export upload logs.

## Project Structure

```
flask-ocr-system/
├── app/
│   ├── __init__.py           # App factory, DB setup #
│   ├── admin/
│   │   ├── __init__.py       # Admin blueprint #
│   │   └── routes.py         # Admin dashboard routes #
│   ├── main/
│   │   ├── __init__.py       # Main blueprint
│   │   └── routes.py         # Core app routes (upload, results)#
│   ├── models.py             # SQLAlchemy models (for logs) #
│   ├── static/                                            #
│   │   ├── css/					   #
│   │   │   └── styles.css    # Custom styles		   #
│   │   └── js/						   #
│   │       └── theme-toggle.js # Dark mode logic	   #
│   ├── templates/					   #
│   │   ├── admin/					   #
│   │   │   └── dashboard.html # Admin dashboard page      #
│   │   ├── main/					   #
│   │   │   ├── index.html    # Homepage		   #
│   │   │   └── results.html  # Results page		   #
│   │   └── base.html         # Base template with Bootstrap#
│   └── utils.py              # OCR processing, file handling logic #
├── instance/							    #						
│   └── app.db                # SQLite database will be created here
├── processed/                # Stores generated images from PDFs, and output files#
├── uploads/                  # Stores user-uploaded files 	    #
├── .gitignore
├── requirements.txt						     #
└── run.py                    # Main script to run the application   #
```

## Running in Production (Linux)

For a production environment, it is recommended to use a proper WSGI server like Gunicorn instead of Flask's built-in development server.

```bash
# Make sure you are in the project root with the venv activated
gunicorn --workers 3 --bind 0.0.0.0:8000 run:app
```

This command starts Gunicorn with 3 worker processes, making the app available on port 8000 to all network interfaces. You would typically run this behind a reverse proxy like NGINX.
