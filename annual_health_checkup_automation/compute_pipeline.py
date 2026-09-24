from datetime import datetime
import pandas as pd

class Compute:
    def __init__(self):
        pass
    def calculate_due_date(self,date:datetime,valid:int=1)-> pd.Timestamp:
        due_date=date+pd.DateOffset(years=valid)
        return due_date


        
    def checkup_status(self,last_checkup_date, frequency_days,frequency_years, as_of_date):
        """
        pass frequency days if cycle is day wise or years if years wise
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
        
        elif 0<timeleft<=30:

            return "Due Soon"
        
        else:

            return "OK"




    def checkup_status_pd(self,df,last_checkup_date, as_of_date):
        df['days_left'] = (df['due_date'] - df['as_of_date']).dt.days
        if df['days_left'] <=0:
            df['checkup_status']="Overdue"
            return df

        
        elif 0<df['days_left']<=30:
            df['checkup_status']="Due Soon"
            return df
        
            
        
        else:
            df['checkup_status']="OK"
            return df
