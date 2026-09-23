import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn

df=pd.read_csv("automation-and-tools-for-HR/employee_records_dummy.xlsx")
df=df.copy()
df.info()
df.describe()
attrition_rate=df[""]
df["employee_status"]=np.where(df["Left"]=="Smiley","onroll","left")
