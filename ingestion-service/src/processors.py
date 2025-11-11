# Document Processors

from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Process PDF documents"""
    
    def process(self, file_path: Path) -> List[str]:
        """Extract text from PDF and chunk it"""
        from pypdf import PdfReader
        
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        # Simple chunking (split by paragraphs)
        chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
        return chunks

class DOCXProcessor:
    """Process Word documents"""
    
    def process(self, file_path: Path) -> List[str]:
        """Extract text from DOCX and chunk it"""
        from docx import Document
        
        doc = Document(file_path)
        text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        
        chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
        return chunks

class ExcelProcessor:
    """Process Excel spreadsheets"""
    
    def process(self, file_path: Path) -> List[str]:
        """Extract data from Excel and convert to text chunks"""
        import pandas as pd
        
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        chunks = []
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            # Convert each row to a text description
            for idx, row in df.iterrows():
                row_text = f"Sheet: {sheet_name} | " + " | ".join([f"{col}: {val}" for col, val in row.items()])
                chunks.append(row_text)
        
        return chunks

class CSVProcessor:
    """Process CSV files"""
    
    def process(self, file_path: Path) -> List[str]:
        """Extract data from CSV and convert to text chunks"""
        import pandas as pd
        
        df = pd.read_csv(file_path)
        chunks = []
        
        # Convert each row to text
        for idx, row in df.iterrows():
            row_text = " | ".join([f"{col}: {val}" for col, val in row.items()])
            chunks.append(row_text)
        
        return chunks

class GeospatialProcessor:
    """Process geospatial files"""
    
    async def process(self, file_path: Path, mapping_service_url: str):
        """Process geospatial files and send to mapping service"""
        import httpx
        import json
        
        extension = file_path.suffix.lower()
        
        if extension == ".geojson":
            with open(file_path, 'r') as f:
                geojson_data = json.load(f)
            
            # Send to mapping service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{mapping_service_url}/layers",
                    json={
                        "id": file_path.stem,
                        "name": file_path.stem,
                        "type": "geojson",
                        "data": geojson_data
                    },
                    timeout=30.0
                )
            
            return {"status": "success", "layer_id": file_path.stem}
        
        # Handle other formats (shapefile, KML, etc.)
        # TODO: Implement converters for these formats
        logger.warning(f"Geospatial format {extension} not fully implemented yet")
        return {"status": "skipped", "reason": "Format not implemented"}

# Export processor instances
pdf_processor = PDFProcessor()
docx_processor = DOCXProcessor()
excel_processor = ExcelProcessor()
csv_processor = CSVProcessor()
geospatial_processor = GeospatialProcessor()
