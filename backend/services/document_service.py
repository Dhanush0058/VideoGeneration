import re
import fitz  # PyMuPDF

class DocumentProcessor:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extracts text from a local PDF file using PyMuPDF."""
        try:
            doc = fitz.open(file_path)
            full_text = []
            for page in doc:
                text = page.get_text("text")
                full_text.append(text)
            
            combined_text = "\n".join(full_text)
            return DocumentProcessor.clean_text(combined_text)
        except Exception as e:
            raise ValueError(f"Failed to parse PDF document: {str(e)}")

    @staticmethod
    def extract_text_from_bytes(file_bytes: bytes) -> str:
        """Extracts text from PDF bytes."""
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            full_text = []
            for page in doc:
                text = page.get_text("text")
                full_text.append(text)
            
            combined_text = "\n".join(full_text)
            return DocumentProcessor.clean_text(combined_text)
        except Exception as e:
            raise ValueError(f"Failed to parse PDF stream: {str(e)}")

    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans and formatting-normalizes text by stripping whitespace and extra lines."""
        if not text:
            return ""
        
        # Remove repeated whitespaces and linebreaks
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        # Clean control characters
        text = "".join(ch for ch in text if ch.isprintable() or ch in ['\n', '\r', '\t'])
        
        return text.strip()

    @staticmethod
    def get_summary_context(text: str, max_chars: int = 15000) -> str:
        """Truncates text to fit within model context limitations while preserving structure."""
        if len(text) <= max_chars:
            return text
        
        # Keep the beginning and end of document if it exceeds capacity
        half_limit = max_chars // 2
        prefix = text[:half_limit]
        suffix = text[-half_limit:]
        
        return f"{prefix}\n\n... [TRUNCATED FOR CONTENT SIZE] ...\n\n{suffix}"
