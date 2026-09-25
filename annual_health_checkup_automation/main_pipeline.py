import json
import os
import pandas as pd
import yaml
from compute_pipeline import Compute
from datetime import datetime
import utils


compute=Compute()

config = utils.load_config(config_path=os.path.join(os.path.dirname(__file__), "config.yaml"))




# def load_source_data(path=None) -> pd.DataFrame:
#     """Read the raw checkup tracker Excel."""
#     path = path or os.path.join(os.path.dirname(__file__), config["Path"]["Filepath"])
#     return pd.read_excel(path)


def apply_eligibility_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Drop anyone whose Last Working Date is in the past (already exited)."""

    lwd = pd.to_datetime(df["Last Working Day (LWD)"])
    today = pd.Timestamp.now().normalize()
    eligible_mask = lwd.isna() | (lwd >= today)
    return df[eligible_mask].copy()


def load_reminder_log(path=None) -> dict:
    """
    Read the persisted dedup log. Keyed on '<empid>_<due_date>'.
    Returns {} on first-ever run (file doesn't exist yet).
    """
    path = path or os.path.join(os.path.dirname(__file__), config["Path"]["reminder_log"])
    return utils.load_json(file_path=path)
   


def build_reminder_key(empid, due_date) -> str:
    """One key per (employee, cycle). A new due_date after a completed
    checkup naturally produces a new key -> dedup resets on its own."""
    due_date_str = pd.to_datetime(due_date).strftime("%Y-%m-%d") if pd.notna(due_date) else "none"
    return f"{empid}_{due_date_str}"


def filter_already_reminded(df: pd.DataFrame, log: dict) -> pd.DataFrame:
    """Drop rows whose (empid, due_date) key is already in the log."""
    df = df.copy()
    df["_reminder_key"] = [
        build_reminder_key(empid, due_date)
        for empid, due_date in zip(df["Employee ID"], df["Due Date"])
    ]
    already_reminded_mask = df["_reminder_key"].isin(log.keys())
    return df[~already_reminded_mask].copy()


def compute_due_date(df):
    if "Due Date" not in df.columns:

        df=compute.calculate_due_date(df=df)
    df=compute.checkup_status_pd(df,as_of_date=datetime.now().date())
    return df


def save_processed(processed_df):
    if os.path.exists(config["Path"]["processed_path"]):
        with open(config["Path"]["processed_path"],"r") as f:
                
                content = f.read().strip()
                processed_df_old=pd.read_json(content)
                
                processed_df_old=pd.to_datetime(processed_df_old["Due Date"])
                return json.loads(content) if content else {}
                
        
        with open(config["Path"]["processed_path"],"w") as f:
            concated_df=pd.concat([processed_df_old,processed_df])
            concated_df.to_json(f,orient="records")
            
        
        print(f"Saved processed file to {config["Path"]["processed_path"]} ")
        return concated_df
    else:
        with open(config["Path"]["processed_path"],"w")as f:
            processed_df=pd.DataFrame(processed_df)
            processed_df.to_json(f,orient="records")
        return processed_df






def send_reminders(df: pd.DataFrame, test_mode: bool = True) -> pd.DataFrame:
    """
    Sends (or, in test_mode, simulates) a reminder to everyone in df
    whose status is 'Due Soon' or 'Overdue'. Returns the subset that
    was actually sent, so update_reminder_log knows what to record.
    """
    to_send = df[df["status"].isin(["Due Soon", "Overdue"])].copy()

    if test_mode:
        for _, row in to_send.iterrows():
            print(f"[TEST MODE] Would email {row[config["column"]['email']]} "
                  f"({row[config["column"]['empid']]}) — status: {row['status']}, "
                  f"due {row['due_date'].date() if pd.notna(row['due_date']) else 'N/A'}")
    else:
        import smtplib
        from email.mime.text import MIMEText

        # NOTE: fill in real SMTP credentials via environment variables
        # before ever flipping test_mode=False. Left unimplemented here
        # on purpose -- wire this up yourself once steps 1-8 are proven.
        raise NotImplementedError(
            "Real sending isn't wired up yet. Fill in smtplib config "
            "and remove this guard once you've tested with test_mode=True."
        )

    to_send["reminded_on"] = pd.Timestamp.now().normalize()
    return to_send


def update_reminder_log(sent_df: pd.DataFrame, log: dict, path=None) -> dict:
    """Adds every sent row's key to the log and writes it back to disk."""
    path = path or os.path.join(os.path.dirname(__file__), config["Path"]["reminder_log"])


    for _, row in sent_df.iterrows():
        key = build_reminder_key(row[config["column"]["empid"]], row["Due Date"])
        log[key] = {
            "empid": row[config["column"]["empid"]],
            "due_date": str(row["Due Date"].date()) if pd.notna(row["Due Date"]) else None,
            
        }
    utils.dump_json(data=log,file_path=path)

       
    return log





def main():
    print("loading source data")
    df=utils.read_excel(file_path=os.path.join(os.path.dirname(__file__), config["Path"]["Filepath"]))
    columns=df.columns.to_list()
    print(columns)
    print("Filtering  data for eligiblility")
    filtered_df=apply_eligibility_filter(df)
    print("loading reminder log")
    reminder_log=load_reminder_log()
    print(reminder_log)
    print("filtering already reminded employees")
    print("computing due date for the employee")
    due_df=compute_due_date(filtered_df)
    print(due_df)
    filtered_df=filter_already_reminded(due_df,reminder_log)
    print(filtered_df)
    print("saving processed data")
    processed_df=save_processed(due_df)
    print(processed_df)
    print("updating reminder log")
    update_reminder_log(processed_df,reminder_log)





if __name__=="__main__":
    main()
