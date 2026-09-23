from datetime import datetime
import pandas as pd

class Compute:
    def __init__(self):
        pass
    def calculate_due_date(self,date:datetime,valid:int)-> pd.Timestamp:
        due_date=date+pd.DateOffset(years=valid)
        return due_date


        
    def checkup_status(self,last_checkup_date, frequency_days,frequency_years, as_of_date):
        """
        pass frequency days if cycle is day wise or years if years wise
        Returns 'Overdue', 'Due Soon', or 'OK' based on how far
        as_of_date is past last_checkup_date + frequency_days.
        """
        #         1. If you are comparing single datetime objects
        # Use the .days property to extract the integer number of days:
        # python
        # from datetime import datetime

        # due_date = datetime(2031, 9, 23)
        # as_of_date = datetime(2026, 9, 23)

        # timeleft = due_date - as_of_date

        # # Extract total days as an integer
        # days_remaining = timeleft.days
        # print(days_remaining)  # Output: 1826
        # Use code with caution.
        # 2. If you are operating on a Pandas DataFrame column
        # If you are doing this calculation across an entire spreadsheet or DataFrame column, use the .dt.days accessor to convert the entire column to integers at once:
        # python
        # import pandas as pd

        # # Example DataFrame
        # df = pd.DataFrame({
        #     'due_date': pd.to_datetime(['2026-10-15', '2027-01-01']),
        #     'as_of_date': pd.to_datetime(['2026-09-23', '2026-09-23'])
        # })

        # # Calculate the difference and force it to a clean integer column
        # df['days_left'] = (df['due_date'] - df['as_of_date']).dt.days

        # print(df)
        # # Output:
        # #     due_date as_of_date  days_left
        # # 0 2026-10-15 2026-09-23         22
        # # 1 2027-01-01 2026-09-23        100
        # Use code with caution.
        # Pro-Tip for HR Reminders (The Warning Trigger)
        # Once you convert timeleft to a number of days, you can easily use it to trigger automated alert emails:
        # python
        # # Trigger email alerts for any certifications expiring within the next 30 days
        # if days_remaining <= 30 and days_remaining > 0:
        #     print("Trigger reminder: Certification is expiring soon!")
        # elif days_remaining <= 0:
        #     print("Trigger alert: Certification has expired!")
        # Use code with caution.
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
            return "Overdue"
        
        elif 0<df['days_left']<=30:
        
            return "Due Soon"
        
        else:
        
            return "OK"
