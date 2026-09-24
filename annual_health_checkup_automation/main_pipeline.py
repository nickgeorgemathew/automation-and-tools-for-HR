import pandas as pd
import pyarrow
import openpyxl
import yaml
import compute_pipeline
import json
import os

compute=compute_pipeline.Compute()

with open("annual_health_checkup_automation/config.yaml","r") as f:
    config=yaml.safe_load(f)

    

class processing:


    def load_data(self):
                df=pd.read_excel(config['Path']['Filepath'])
                return df

    
    def compute_eligibility_status(self,df):
        """process df and returns eligible and checkup status df"""
        
        df_eligible=df[( df[config['column']['last working date']].isna() ) | (df[config['column']['last working date']] > pd.Timestamp.now().normalize())]
        df_status=compute.checkup_status_pd(df_eligible,df_eligible[config['column']['last checkup date']],as_of_date=pd.Timestamp.now().normalize())
           
        return df_eligible,df_status


    def load_reminder_log(self) -> pd.DataFrame:
        """Read the persisted 'who was already reminded, for which cycle' log."""
        try :
                with open(config['Path']['reminder_log'],'r') as f:
                    reminder_log=json.load(f)

                if not reminder_log:
                    reminder_log={} 
                df_log=pd.DataFrame(reminder_log)
                return df_log
        except Exception as e:
             return(f"{e}")
            

    def filter_already_reminded(self,df, log_df) -> pd.DataFrame:
        """This is your dedup answer from last turn — pure, but depends on persisted state."""



    def send_reminders(self,df, test_mode=True) -> pd.DataFrame:
        """The ONLY impure stage. Returns what was actually sent, for logging."""


    def update_reminder_log(self,sent_df, df_log) -> None:
        """Persist stage — writes back so tomorrow's run knows what already happened."""
        df_log=pd.concat([df_log,sent_df],ignore_index=True)
        with open(config["Path"]["reminder_log"],"w"):
             json.dump(df_log)





        

    

    


    



def load_source_data(excel_path) -> pd.DataFrame:
    """Read raw checkup tracker + exit tracker. Pure-ish (file I/O, but no side effects on the world)."""

def compute_status(df, as_of_date) -> pd.DataFrame:
    """Vectorized checkup_status applied across the whole DataFrame. Pure."""

def apply_eligibility_filter(df, exit_tracker_df) -> pd.DataFrame:
    """Drop anyone with LWD in the past. Pure."""



def filter_already_reminded(df, log_df) -> pd.DataFrame:
    """This is your dedup answer from last turn — pure, but depends on persisted state."""



def main():
    df = load_source_data(...)
    df = compute_status(df, as_of_date=pd.Timestamp.now())
    df = apply_eligibility_filter(df, exit_df)
    log = load_reminder_log()
    to_remind = filter_already_reminded(df, log)
    sent = send_reminders(to_remind, test_mode=True)
    update_reminder_log(sent, log)