# Document Processors

from pathlib import Path
from typing import List, Dict, Any
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
    
    def process(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract data from CSV and convert to text chunks with metadata"""
        import pandas as pd
        
        df = pd.read_csv(file_path)
        chunks = []
        
        # Detect entity type from filename
        filename_lower = file_path.stem.lower()
        if 'business' in filename_lower:
            entity_type = 'business'
        elif 'personnel' in filename_lower or 'person' in filename_lower:
            entity_type = 'personnel'
        elif 'resource' in filename_lower:
            entity_type = 'resource'
        elif 'facilit' in filename_lower:
            entity_type = 'facility'
        else:
            entity_type = 'general'
        
        # Convert each row to structured text with metadata
        for idx, row in df.iterrows():
            # Create readable text description
            row_text = self._format_row(row, entity_type)
            
            # Extract metadata
            metadata = {
                'filename': file_path.name,
                'row_index': int(idx),
                'entity_type': entity_type
            }
            
            # Add entity-specific metadata
            if 'id' in row:
                metadata['entity_id'] = str(row['id'])
            if 'name' in row:
                metadata['entity_name'] = str(row['name'])
            if 'type' in row:
                metadata['sub_type'] = str(row['type'])
            if 'latitude' in row and 'longitude' in row:
                try:
                    metadata['latitude'] = float(row['latitude'])
                    metadata['longitude'] = float(row['longitude'])
                except:
                    pass
            
            chunks.append({
                'text': row_text,
                'metadata': metadata
            })
        
        return chunks
    
    def _format_row(self, row, entity_type: str) -> str:
        """Format row data into readable text based on entity type"""
        if entity_type == 'business':
            return self._format_business(row)
        elif entity_type == 'personnel':
            return self._format_personnel(row)
        elif entity_type == 'resource':
            return self._format_resource(row)
        elif entity_type == 'facility':
            return self._format_facility(row)
        else:
            return " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
    
    def _format_business(self, row) -> str:
        """Format business entity"""
        import pandas as pd
        parts = []
        
        if 'name' in row:
            parts.append(f"Business: {row['name']}")
        if 'type' in row:
            parts.append(f"Type: {row['type']}")
        if 'address' in row:
            parts.append(f"Location: {row['address']}")
        if 'owner_name' in row:
            parts.append(f"Owner: {row['owner_name']}")
        if 'owner_phone' in row and pd.notna(row['owner_phone']):
            parts.append(f"Contact: {row['owner_phone']}")
        if 'products_services' in row and pd.notna(row['products_services']):
            products = str(row['products_services']).replace('|', ', ')
            parts.append(f"Products/Services: {products}")
        if 'emergency_resources' in row and pd.notna(row['emergency_resources']):
            resources = str(row['emergency_resources']).replace('|', ', ')
            parts.append(f"Emergency Resources Available: {resources}")
        if 'notes' in row and pd.notna(row['notes']):
            parts.append(f"Notes: {row['notes']}")
        
        return ". ".join(parts) + "."
    
    def _format_personnel(self, row) -> str:
        """Format personnel entity"""
        import pandas as pd
        parts = []
        
        if 'name' in row:
            parts.append(f"Person: {row['name']}")
        if 'role' in row:
            parts.append(f"Role: {row['role']}")
        if 'organization' in row:
            parts.append(f"Organization: {row['organization']}")
        if 'expertise' in row and pd.notna(row['expertise']):
            expertise = str(row['expertise']).replace('|', ', ')
            parts.append(f"Expertise: {expertise}")
        if 'phone_primary' in row and pd.notna(row['phone_primary']):
            parts.append(f"Phone: {row['phone_primary']}")
        if 'radio_callsign' in row and pd.notna(row['radio_callsign']):
            parts.append(f"Radio: {row['radio_callsign']}")
        if 'emergency_role' in row and pd.notna(row['emergency_role']):
            parts.append(f"Emergency Role: {row['emergency_role']}")
        if 'response_time' in row and pd.notna(row['response_time']):
            parts.append(f"Response Time: {row['response_time']}")
        if 'notes' in row and pd.notna(row['notes']):
            parts.append(f"Notes: {row['notes']}")
        
        return ". ".join(parts) + "."
    
    def _format_resource(self, row) -> str:
        """Format resource entity"""
        import pandas as pd
        parts = []
        
        if 'name' in row:
            parts.append(f"Resource: {row['name']}")
        if 'type' in row:
            parts.append(f"Type: {row['type']}")
        if 'available' in row and 'unit' in row:
            parts.append(f"Available: {row['available']} {row['unit']}")
        if 'facility' in row and pd.notna(row['facility']):
            parts.append(f"Location: {row['facility']}")
        if 'status' in row:
            parts.append(f"Status: {row['status']}")
        if 'owner_organization' in row and pd.notna(row['owner_organization']):
            parts.append(f"Owner: {row['owner_organization']}")
        if 'contact_person' in row and pd.notna(row['contact_person']):
            parts.append(f"Contact: {row['contact_person']}")
        if 'notes' in row and pd.notna(row['notes']):
            parts.append(f"Notes: {row['notes']}")
        
        return ". ".join(parts) + "."
    
    def _format_facility(self, row) -> str:
        """Format facility entity"""
        import pandas as pd
        parts = []
        
        if 'name' in row:
            parts.append(f"Facility: {row['name']}")
        if 'type' in row:
            parts.append(f"Type: {row['type']}")
        if 'address' in row:
            parts.append(f"Location: {row['address']}")
        if 'capacity_people' in row and pd.notna(row['capacity_people']):
            parts.append(f"Capacity: {row['capacity_people']} people")
        if 'vehicle_access' in row and row['vehicle_access']:
            parts.append("Vehicle access available")
        if 'helicopter_landing' in row and row['helicopter_landing']:
            parts.append("Helicopter landing available")
        if 'electricity' in row and row['electricity']:
            parts.append("Has electricity")
        if 'generator_backup' in row and row['generator_backup']:
            parts.append("Has backup generator")
        if 'suitable_for' in row and pd.notna(row['suitable_for']):
            suitable = str(row['suitable_for']).replace('|', ', ')
            parts.append(f"Suitable for: {suitable}")
        if 'notes' in row and pd.notna(row['notes']):
            parts.append(f"Notes: {row['notes']}")
        
        return ". ".join(parts) + "."

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
