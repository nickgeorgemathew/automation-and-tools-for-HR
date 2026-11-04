from pathlib import Path
import filetype
import pandas as pd
from config import settings
import shutil
from logging import log

files=[settings.name_gl,settings.name_hris,settings.name_payroll]
quarentine_path=Path(settings.quarentine_path)
expected_cols=settings.EXPECTED_COLUMNS
class Validation():
    def __init__(self):
        pass

    @staticmethod
    def detect_metadata(file_path):
            """Stat the metadata to ensure the file is trustable"""
            file_path=Path(file_path)
            file_metadata=file_path.stat()
            return file_metadata
    
    @staticmethod
    def detect_type(file_stream):
        head = file_stream.read(2048)
        file_stream.seek(0)
        
        kind = filetype.guess(head)
        if kind is None:
            return "Unknown"
            
        return kind.mime 

    @staticmethod
    def validate_file(path):
            file_path=Path(path)
            file_name=file_path.name
            file_type=file_path.suffix
            print(f"file name:{file_name}")
            print(f"file type:{file_type}")
            if file_name not in files:
                shutil.move(src=file_path,dst=quarentine_path)
                return(f"{file_path} quarentined, validate manually")
            elif file_type!="csv":
                 return (f"File type is {file_type} not csv")
            else:
                return(f"{file_path} validated")
            


    @staticmethod
    def read_csv(file_path):
         try:
            file_csv=pd.read_csv(file_path)
            return file_csv
         except Exception as e:
              return(f"error: {e}")


    @staticmethod
    def validate_cols(file_path):
        file_path=Path(file_path)
        feedtype=file_path.stem
        if feedtype not in expected_cols:
            return False,f"unknown feedtype: {feedtype}"
        df=pd.read_csv(file_path)
        expected=expected_cols[feedtype]
        actual=list(df.columns)
        missing=[col for col in expected if col not in actual]
        extra=[col for col in actual if col not in expected]


        if missing or extra:
            quarantine_path = Path(settings.quarentine_path)
            quarantine_path.mkdir(exist_ok=True)
            shutil.move(str(file_path), str(quarantine_path / file_path.name))
            return False, {
                "feedtype": feedtype,
                "missing": missing,
                "extra": extra
            }

        return True, f"{feedtype} columns are valid",df
    
         


    
   
            




