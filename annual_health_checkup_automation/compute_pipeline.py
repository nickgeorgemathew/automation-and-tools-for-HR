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
        df["Due Date"]=df.apply(cal,axis=1)
        result = df.apply(cal, axis=1)
        print(type(result), result.dtype if hasattr(result, "dtype") else "no dtype")
        df["Due Date"] = pd.to_datetime(result)
            
        return df


        
    def checkup_status(self,last_checkup_date, frequency, as_of_date):
        """
        pass frequency in years
        Returns 'Overdue', 'Due Soon', or 'OK' based on how far
        as_of_date is past last_checkup_date + frequency_days.
        """
        
        if last_checkup_date is None:
        
            return("cannot calculate on empty last_checkup_date")
        

        if as_of_date is None:

            as_of_date = pd.to_datetime(datetime.now().date())
        else:

            as_of_date = pd.to_datetime(as_of_date)

        if frequency_days:
            

            due_date=last_checkup_date+pd.DateOffset(days=frequency_days)
            timeleft=(due_date-as_of_date).days
            

        elif frequency_years:

            due_date=last_checkup_date+pd.DateOffset(years=frequency_years)
            timeleft=(due_date-as_of_date).days
            
        else:

            raise ValueError("You must provide either frequency_days or frequency_years.")


        if timeleft <=0:
            return "Overdue"
        
        elif 0<=timeleft<=30:

            return "Due Soon"
        
        else:

            return "OK"




    def checkup_status_pd(self,df,as_of_date):
        def calculate_days_left(row):
            days_left=(pd.to_datetime(row['Checkup Date']) - pd.to_datetime(as_of_date)).days
            return days_left

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