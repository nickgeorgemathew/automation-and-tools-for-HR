from pathlib import Path
import pandas as pd
from config import settings
import shutil
import logging
from Schema_validator import HRISRecord,PayrollRegister,FinanceLedger



files=[settings.name_gl,settings.name_hris,settings.name_payroll]
quarentine_path=Path(settings.quarentine_path)
expected_cols=settings.EXPECTED_COLUMNS


schema_map={
     "hris_export": HRISRecord,
    "payroll_register": PayrollRegister,
    "gl_dump": FinanceLedger,
}


logging.basicConfig(
    filename="logs/pipeline_errors.log",
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("pipeline")





class Validation():
    def __init__(self):
        pass

    @staticmethod
    def detect_metadata(file_path):
        """
        Returns basic details about the file so we can reject empty, missing,
        or wrong-format files before trying to process them.
        """
        file_path = Path(file_path)  # Convert string path to Path object

        # If the file does not exist, stop immediately.
        if not file_path.exists():
            logger.critical(f"File Not Found Error: {file_path} doesnot exist ")
            raise FileNotFoundError(f"{file_path} does not exist")
            

        # Get filesystem metadata like size and modification time.
        file_metadata = file_path.stat()
        metadata={
            "name": file_path.name,          # "hris_export.csv"
            "suffix": file_path.suffix.lower(),  # ".csv"
            "size_bytes": file_metadata.st_size, # file size in bytes
            "modified_time": file_metadata.st_mtime,  # last modified timestamp
            "is_file": file_path.is_file(),  # True if it's actually a file
        }
        # Return a dictionary with useful metadata.
        logger.info(f"{file_path} metadata : {metadata}")
        return metadata

    
    @staticmethod
    def validate_file(path):
            file_path=Path(path)
            file_name=file_path.name
            file_type=file_path.suffix
            print(f"file name:{file_name}")
            print(f"file type:{file_type}")
            logger.info(f"file name:{file_name}")
            logger.info(f"file type:{file_type}")
           
                             
            if file_name not in files:
                quarantine_path = Path(settings.quarentine_path)
                quarantine_path.mkdir(exist_ok=True)
                dest = quarantine_path / file_path.name
                shutil.copy2(file_path, dest)        
                file_path.unlink()
                msg=f"{file_path} quarentined, validate manually"
                ok=False
                logger.debug(f"{msg}, file name;{file_name},file type:{file_type}")
                return ok,msg,file_name,file_type
            
            else:
                msg=f"{file_path} Validated"
                ok=True
                logger.info(f"{msg}")
                return ok,msg,file_name,file_type
            


    @staticmethod
    def read_csv(file_path):

        try:
            return pd.read_csv(file_path)
        except Exception as e:
            logger.error(f"error:{e}")
            return None
        
        
    @staticmethod
    def validate_rows(feedtype,df):
        schema=schema_map.get(feedtype)
        if schema is None:
            return [], [{"error": f"No schema for feedtype: {feedtype}"}]

        valid_rows=[]
        invalid_rows=[]

        for index,row in df.iterrows():
            try:
                record=schema(**row.to_dict())
                valid_rows.append(record.model_dump())
            except Exception as e:
                invalid_rows.append({
                    "row_index": index,
                    "error": str(e)
                })
                logger.warning(f"Row {index} failed validation: {e}")

        return valid_rows, invalid_rows


    @staticmethod
    def validate_cols(file_path):
        file_path=Path(file_path)
        feedtype=file_path.stem
        msg_dict=None
        data_frame=None
        
        ok,msg,file_name,file_type=Validation.validate_file(file_path)
        if not ok:
          logger.debug(f"file is valid: False, reason: {msg}")
          return False, {"reason": msg}, None
        if feedtype not in expected_cols:
            bool_return=False
            msg_dict=f"unknown feedtype: {feedtype}"
            data_frame=None
            logger.info(f"Feedtype is valid:{bool_return}, message:{msg_dict},DataFrame:{data_frame}")
            return bool_return,msg_dict,data_frame
        
        df = Validation.read_csv(file_path)
        if df is None:
            logger.error("'reason': 'CSV parse failed'")
            return False, {"reason": "CSV parse failed"}, None
        expected=expected_cols[feedtype]
        actual=list(df.columns)
        missing=[col for col in expected if col not in actual]
        extra=[col for col in actual if col not in expected]


        if missing or extra:
            quarantine_path = Path(settings.quarentine_path)
            quarantine_path.mkdir(exist_ok=True)
            dest = quarantine_path / file_path.name
            shutil.copy2(file_path, dest)        
            file_path.unlink()              
            bool_return=False
            msg_dict={
                "feedtype": feedtype,
                "missing": missing,
                "extra": extra
            }
            data_frame=None
            logger.error(f"Feedtype is valid:{bool_return}, message:{msg_dict},DataFrame:{data_frame}")
            return bool_return,msg_dict,data_frame
        bool_return=True
        msg_dict=f"{feedtype} columns are valid"
        data_frame=df
        logger.info(f"Feedtype is valid:{bool_return}, message:{msg_dict},DataFrame:{data_frame}")
        valid_rows, invalid_rows = Validation.validate_rows(feedtype, df)
        logger.info(f"{feedtype}: {len(valid_rows)} valid rows, {len(invalid_rows)} invalid rows")
        return bool_return, {
            "message":msg_dict,
            "valid_rows": valid_rows,
            "invalid_rows": invalid_rows
            }, data_frame
            
    
def run_main():
    logger.info("Validation begin")
    incoming_dir = Path(settings.incoming_feeds)  
    
    for file_path in incoming_dir.glob("*.csv"):
        metadata=validation.detect_metadata(file_path)
        print(f"file:{file_path} \n metadata:{metadata}")
        logger.info(f"Processing: {file_path.name}")
        ok, result, df = Validation.validate_cols(file_path)
        
        if not ok:
            print(f"{file_path.name} — FAILED: {result}")
        else:
            valid = len(result["valid_rows"])
            invalid = len(result["invalid_rows"])
            print(f"{file_path.name} — {valid} valid rows, {invalid} invalid rows")
            return df
    
    logger.info("Validation complete")

if __name__=="__main__":
    validation=Validation()
