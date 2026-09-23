import pandas as pd
import pyarrow
import openpyxl
import yaml


with open("annual_health_checkup_automation/config.yaml","r") as f:
    config=yaml.safe_load(f)
class load:
    def load_data(self):
        df=pd.read_excel(config['Filepath'])
        return df

class processing:
    def compute_eligibility(self,df):
        
        df_eligible=df[ df[config['column']['last working date']].isna() | df[config['column']['last working date']] > pd.Timestamp.now().normalize()]
           
        return df_eligible


    
class reminder:
    pass


