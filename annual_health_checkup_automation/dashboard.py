import streamlit as st
import yaml
import os
import json
import pandas as pd
from pathlib import Path

with open(os.path.join(os.path.dirname(__file__),"config.yaml"),"r") as f:
    config=json.load(f)






st.set_page_config(page_title="Notice Period Tracker", layout="wide")


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


if not Path(config["Path"]["processed_path"]).exists():
    st.error(
        f"'{config["Path"]["processed_path"]}' not found. Run data_pipeline.py first:\n\n"
        f"    python data_pipeline.py --input employee_resignation.xlsx --output {config["Path"]["processed_path"]}"
    )
    st.stop()

df=pd.DataFrame(config["Path"]["processed_path"])

st.title("Annual Health Checkup Reminder ")

st.dataframe(df.sort_values())