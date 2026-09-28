from datetime import datetime
import pandas as pd
import numpy as np
import utils

class Compute:
    def __init__(self):
        pass
    def calculate_due_date(self,df) -> pd.Timestamp:
        
        def cal(row):
            date=row["Checkup Date"]+pd.DateOffset(years=row["validity"])
            return date
        df["Due Date"] = pd.to_datetime(df.apply(cal,axis=1))
            
        return df


        
   

    def checkup_status_pd(self,df,as_of_date):
        def calculate_days_left(row):
            due_date = pd.to_datetime(row["Due Date"])
            if pd.isna(due_date):
                return np.nan
            return (due_date - as_of_date).days
        as_of_date=pd.to_datetime(as_of_date)
        df['days_left'] = df.apply(calculate_days_left,axis=1)

        
        
        def determine_status(row):
            days = row['days_left']
            if days <= 0:
                return "Overdue"
            elif 0 <= days <= 30:
                return "Due Soon"
            else:
                return "OK"
            
        df["checkup_status"]=df.apply(determine_status,axis=1)
        return df