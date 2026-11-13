Here are all 10 rules in the same format, then pandas examples for four of them. The other six use the same moves, so you'll write those.

## How to read each rule

Every rule has the same five parts:
- **Question:** the English version.
- **Data:** which tables and columns it needs.
- **Condition:** when a row is "guilty".
- **Trap:** the way people usually get it wrong.
- **Severity:** a suggestion, and your call.

Before the rules, look at your real data for these two:
- The distinct values of `Employment_Status`, `Payment_Status`, `Payroll_Run_ID`, `Posted_By` and `GL_Remarks`. Rules 1 and 10 depend on what these really contain.
- Which `GL_Account_Code` rows exist per employee-period. Rule 4 depends on this.

## The 10 rules

**1. CRITICAL_TERMINATED_PAID**
- **Question:** Was someone paid for a period after they left?
- **Data:** E `Date_Of_Leaving`, `Employment_Status`; P `Pay_Period`, `Net_pay`, `Payment_Status`.
- **Condition:** P row exists, E `Date_Of_Leaving` is not null, and the pay period starts after the leaving date.
- **Trap:** If someone leaves on the 15th, March is legitimately paid (partly). Compare against the *start* of the pay period, or you'll flag final salaries. Also decide how to treat `Payment_Status` (a "failed" payment isn't money gone).
- **Severity:** CRITICAL.

**2. ORPHAN_PAYROLL_RECORD**
- **Question:** Was someone paid who doesn't exist in HR?
- **Data:** P left-joined to E on `Employee_ID`.
- **Condition:** The E side is NULL.
- **Trap:** Don't filter E before the join, or you'll create fake orphans (the bug in your first view).
- **Severity:** HIGH. Could be fraud, or an HR export that's incomplete.

**3. DUPLICATE_PAYMENT**
- **Question:** Was the same person paid twice for one period?
- **Data:** raw `fact_payroll`.
- **Condition:** more than one row per (`Employee_ID`, `Pay_Period`).
- **Trap:** Run it on raw P, not on a joined dataset (a join may already have multiplied or hidden the rows). Also ask whether two rows with different `Payroll_Run_ID` are a duplicate or a legitimate off-cycle run (that links to rule 10).
- **Severity:** HIGH.

**4. GL_NET_MISMATCH**
- **Question:** Does what Finance booked equal what payroll paid?
- **Data:** P `Net_pay`; G `GL_Amount_Posted` summed per employee-period.
- **Condition:** G is missing (not posted) or `ABS(net - posted) > tolerance`.
- **Trap:** Aggregate G first, then join. If G has deduction or tax rows, filter by `GL_Account_Code` to the net-pay account only, or every employee will mismatch. This is the case where "G is missing" (Scenario A) and "G disagrees" are two different messages.
- **Severity:** HIGH.

**5. BASE_RATE_MISMATCH**
- **Question:** Did payroll use a different base salary than HR holds?
- **Data:** E `Base_Salary_HRIS`, P `Base_Salary_Payroll`, joined on `Employee_ID`.
- **Condition:** `ABS(difference) > tolerance`.
- **Trap:** HR may record a raise effective mid-period; decide whether you tolerate that. Compare as money, not with `==`.
- **Severity:** MEDIUM.

**6. MOM_VARIANCE**
- **Question:** Did someone's pay jump or drop unusually versus last month?
- **Data:** P `Net_pay` (or `Gross_Pay`) for this and the previous period.
- **Condition:** `abs(current - previous) / previous > threshold` (from config).
- **Trap:** First month has no previous (skip it, don't flag it). Previous = 0 means divide by zero. "Previous period" should mean the previous *pay period*, not row order. Sort first.
- **Severity:** MEDIUM, a *review* flag rather than a proven error.

**7. HEADCOUNT_MISMATCH**
- **Question:** Do the three systems agree on how many people there are this period?
- **Data:** distinct `Employee_ID` count in E (active that period), P, G.
- **Condition:** the counts differ.
- **Trap:** The finding has no employee, so `employee_id` is None. "Active in E" needs your date logic (joined on or before the period end, not left before the period start). A count mismatch says *that* something's wrong, not *who*, so the message should say which pair differs.
- **Severity:** MEDIUM.

**8. ESI_BOUNDARY_RISK**
- **Question:** Is gross pay close to the ESI wage limit, where a small change flips eligibility?
- **Data:** P `Gross_Pay`, `ESI_deduction`.
- **Condition:** gross within a band around the statutory limit (check the current limit, commonly cited as ₹21,000/month, and put it in config along with your band width, such as ±5%).
- **Trap:** This is a *risk*, not a certain error. A second variant to consider: gross is above the limit but an ESI deduction was taken anyway, or below the limit with none taken.
- **Severity:** LOW or MEDIUM.

**9. OT_ANOMALY**
- **Question:** Is overtime unusually high?
- **Data:** P `Overtime`, `Basic_salary` or `Base_Salary_Payroll`, and optionally the employee's own history.
- **Condition:** your definition. Options: overtime above a fixed amount, above X% of basic, or far above that employee's own average.
- **Trap:** You must pick one definition and write it in config and in the message. The history-based version is stronger but needs previous periods (same technique as rule 6).
- **Severity:** MEDIUM.

**10. OFF_CYCLE_MANUAL_ADJ**
- **Question:** Was there a payment or posting outside the normal run?
- **Data:** P `Payroll_Run_ID`, G `Posted_By`, `GL_Remarks`, `Posting_Date`.
- **Condition:** depends on what you see in the data. Candidates: a `Payroll_Run_ID` that doesn't match the regular pattern, `Posted_By` is a person instead of a system user, `GL_Remarks` contains "manual" or "adjust", or `Posting_Date` is outside the usual window.
- **Trap:** This can't be designed from your desk. Query the distinct values first, then write the definition in one sentence, then code it.
- **Severity:** MEDIUM.

## Pandas: the pattern

In pandas, every rule is: get a DataFrame, filter to the guilty rows, convert to findings. DuckDB still holds the data, and you pull each table out with `.df()`.

```python
import pandas as pd

TOL = 0.01

def load(conn, pay_period):
    e = conn.execute("SELECT * FROM dim_employees").df()
    p = conn.execute("SELECT * FROM fact_payroll WHERE Pay_Period = ?", [pay_period]).df()
    g = conn.execute("SELECT * FROM fact_gl WHERE Pay_Period = ?", [pay_period]).df()
    return e, p, g

def to_findings(df, error_type, severity, message_fn):
    # every rule's guilty rows go through here, so the shape never varies
    return [Finding(error_type, severity, r.Employee_ID, ..., message_fn(r)) for r in df.itertuples()]
```

**Rule 2 (orphan): the `indicator` trick**
```python
m = p.merge(e[["Employee_ID"]], on="Employee_ID", how="left", indicator=True)
orphans = m[m["_merge"] == "left_only"]
```
The `_merge` column says `left_only`, `right_only` or `both` for each row. That is the NULL-pattern logic as a visible column, so you can print `m` and *see* your Scenario A, B and C rows.

**Rule 3 (duplicates)**
```python
dupes = p[p.duplicated(subset=["Employee_ID", "Pay_Period"], keep=False)]
```
Look up what `keep=False` does compared with `keep="first"`. Which one do you want for a finding?

**Rule 4 (GL mismatch): aggregate first, then merge**
```python
g_sum = g.groupby("Employee_ID", as_index=False)["GL_Amount_Posted"].sum()
m = p.merge(g_sum, on="Employee_ID", how="left")
bad = m[m["GL_Amount_Posted"].isna() | ((m["Net_pay"] - m["GL_Amount_Posted"]).abs() > TOL)]
```
This is the same principle as the SQL CTE. Merging before `groupby` would multiply rows exactly as the join did.

**Rule 6 (MoM): `shift` inside `groupby`**
```python
hist = conn.execute("SELECT Employee_ID, Pay_Period, Net_pay FROM fact_payroll").df()
hist = hist.sort_values(["Employee_ID", "Pay_Period"])
hist["prev"] = hist.groupby("Employee_ID")["Net_pay"].shift(1)
hist["chg"] = (hist["Net_pay"] - hist["prev"]).abs() / hist["prev"]
flagged = hist[(hist["Pay_Period"] == pay_period) & (hist["chg"] > MOM_THRESHOLD)]
```
Notice that you need *all* periods, then filter to the current one afterwards. Why? Consider what `shift` would return if you'd loaded only this month.

## Pandas traps specific to your project
- **IDs:** make sure `Employee_ID` stays a string everywhere (leading zeros).
- **NaN vs None:** `NaN != NaN`, so use `.isna()`, never `== None`.
- **Merge multiplication:** if the right side has duplicate keys, a merge multiplies rows silently. `merge(..., validate="many_to_one")` raises an error instead, which is a cheap safeguard.
- **Money:** compare with tolerance, as above. If DuckDB gives you `Decimal` objects, convert to float for the arithmetic.

## Which tool per rule (my suggestion, argue with it)
Pandas for 1, 2, 3, 5, 8, 9 (column comparisons and simple groups). Either for 4 and 7. Window logic for 6 reads naturally in both. 10 depends on your data. Whichever you choose, use one tool per rule.

## Quick summary
- 10 rules sort into: presence (2), column comparisons (1, 5, 8, 9), grouping (3, 7), aggregate-then-join (4), cross-period (6) and "define it first" (10).
- In pandas, each rule is load, filter to guilty rows, build findings.
- The traps repeat: filter placement, grain, tolerance and divide-by-zero.

## Check your understanding
1. In rule 6, why would loading only the current period make every MoM value come out as NaN?
2. Why does `merge(..., validate="many_to_one")` protect you in rule 4, and which earlier bug in your SQL was the same problem?

## Exercise
Pick `check_terminated_paid`. Write the English condition first, including your decision on someone who left mid-month. Then implement it in pandas yourself using the pattern above. Test it on a three-row DataFrame you build by hand (one guilty, one innocent, one who left mid-month) and send me the code and the output.