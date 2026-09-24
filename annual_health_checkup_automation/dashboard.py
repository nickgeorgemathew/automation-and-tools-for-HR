import streamlit as st
import yaml
import os
import json
import pandas as pd
from pathlib import Path


def highlight_rows(row):
    
    status = row['checkup_status']
    
    
    if status == "Overdue":
        return ['background-color: #ffcccc; color: #800000;'] * len(row)
    elif status == "Due soon":
        return ['background-color: #FFE5CC; color: #B35900;'] * len(row)
    elif status == "Okay":
        return ['background-color: #E2EFDA; color: #2E5B2E;'] * len(row)
    
    
    return [''] * len(row)




with open(os.path.join(os.path.dirname(__file__),"config.yaml"),"r") as f:
    config=yaml.safe_load(f)

st.set_page_config(page_title="Notice Period Tracker", layout="wide")


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


if not Path(config["Path"]["processed_path"]).exists():
    st.error(
        f"{config['Path']['processed_path']} not found."        
    )
    st.stop()

df=pd.DataFrame(config["Path"]["processed_path"])

st.title("Annual Health Checkup Reminder ")


st.subheader("People in this week")
people_cols = ["Employee ID","Employee Name","Department","Designation / Cadre","Reporting Manager / HOD","Date of Joining (DOJ)"
]
styled_df = df.style.apply(highlight_rows, axis=1)
st.dataframe(styled_df)


st.divider()
