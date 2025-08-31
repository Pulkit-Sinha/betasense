import os
import PyPDF2
from typing import List, Dict, Any
from pathlib import Path


class PDFService:
    def __init__(self, data_directory: str = "../data"):
        self.data_directory = data_directory
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a single PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def get_all_pdfs(self) -> List[Dict[str, Any]]:
        """Get all PDF files with metadata"""
        pdfs = []
        data_path = Path(self.data_directory)
        
        if not data_path.exists():
            print(f"Data directory {self.data_directory} not found")
            return pdfs
            
        for pdf_file in data_path.rglob("*.pdf"):
            # Extract metadata from file path
            relative_path = pdf_file.relative_to(data_path)
            path_parts = relative_path.parts
            
            category = path_parts[0] if len(path_parts) > 0 else "unknown"
            subcategory = path_parts[1] if len(path_parts) > 1 else "unknown"
            
            pdfs.append({
                "file_path": str(pdf_file),
                "relative_path": str(relative_path),
                "filename": pdf_file.name,
                "category": category,
                "subcategory": subcategory,
                "size": pdf_file.stat().st_size,
                "modified_time": pdf_file.stat().st_mtime
            })
        
        return pdfs
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for better search"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundaries
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > start + chunk_size // 2:
                    chunk = text[start:break_point + 1]
                    end = break_point + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
            
        return chunks
    
    def process_all_pdfs(self) -> List[Dict[str, Any]]:
        """Process all PDFs and return chunks with metadata"""
        all_chunks = []
        pdfs = self.get_all_pdfs()
        
        for pdf_info in pdfs:
            print(f"Processing: {pdf_info['filename']}")
            text = self.extract_text_from_pdf(pdf_info['file_path'])
            
            if text:
                chunks = self.chunk_text(text)
                for i, chunk in enumerate(chunks):
                    all_chunks.append({
                        "chunk_id": f"{pdf_info['filename']}_{i}",
                        "text": chunk,
                        "source_file": pdf_info['filename'],
                        "file_path": pdf_info['file_path'],
                        "category": pdf_info['category'],
                        "subcategory": pdf_info['subcategory'],
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    })
        
        return all_chunks