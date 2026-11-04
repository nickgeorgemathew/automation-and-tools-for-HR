from pathlib import Path
import filetype
import filetype

class Validation():
    def __init__(self):
        pass
    def detect_type(file_stream):
        head = file_stream.read(2048)
        file_stream.seek(0)
        
        kind = filetype.guess(head)
        if kind is None:
            return "Unknown"
            
        return kind.mime  # e.g., 'image/png'


    def detect_metadata():
        """Stat the metadata to ensure the file is trustable"""
