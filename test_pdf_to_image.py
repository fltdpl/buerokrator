from pdf2image import convert_from_path
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

images = convert_from_path(
    "examples/Rechnung_Zahnarzt_OCR.pdf",
    poppler_path=r"C:\Program Files\poppler\poppler-26.02.0\Library\bin"
)

text = pytesseract.image_to_string(
    images[0],
    lang="deu+eng"
)

print(text)