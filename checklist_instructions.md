




how to add conditional formatting in power bi
You can apply conditional formatting in Power BI by following the official Microsoft Learn Guide to format backgrounds, fonts, icons, or data bars based on your data. 

Microsoft Learn
 +1
Step-by-Access Conditional Formatting
Select your Table or Matrix visual.
Go to the Visualizations pane and click the Format your visual (paintbrush) icon.
Expand Cell elements, choose the specific series/column you want to format, and click the fx button next to Background color or Font color. Alternatively, right-click the field name in the visual bucket and select Conditional formatting. 

Microsoft Learn
 +2
Choose a Format Style
Power BI gives you three main ways to format your visuals: 

YouTube
·Fernan | Power BI
 +2
Gradient: Creates a smooth color scale based on the minimum and maximum values (with an optional middle color).
Rules: Sets specific color conditions based on numerical or percentage thresholds (e.g., green if greater than 50).
Field value: Uses a custom DAX measure that returns text hex codes (like #00FF00) or color names to drive dynamic logic. 

YouTube
·Paying it Forward
 +5
Learn how to apply background and font color rules using a quick walkthrough:

5m
Power BI VISUALS Get Conditional Formatting in SECONDS!
1.6K views · 1 year ago

YouTube · ITsEasyTraining1st
If you want, tell me:
Are you formatting a table, matrix, or chart?
Do you want to use rules or write a DAX measure?
I can give you the exact steps or formula you need.





Microsoft Learn
Apply Conditional Table Formatting in Power BI
Apply conditional formatting in Power BI. You can apply conditional formatting to any text or data field, as long as you base the ...


Microsoft Learn
Conditional formatting in Power BI visuals - Microsoft Learn
Use the fx button in the Format pane. For most visuals, you access conditional formatting through the Format pane: * Select the vi...


YouTube
·
Fernan | Power BI
BEGINNERS GUIDE TO CONDITIONAL FORMATTING in ...
maybe you want to show the head count is increasing or decreasing over time or maybe you want to show if the sales that you have a...

10m
Show all
i want to add a condition in power bi ,where if date is present it becomes as 'left' or else 'onroll'  and creates a pi chart showing employee atrition
10 sites
Here are top web results for exploring this topic:

Fabric Community
·
https://community.fabric.microsoft.com
Track movement of employees - Attrition and movers
ReportCollapse Thread. Good to hear! I had a bit more thought about it and I think the calculated column approach at the end of my post would be the cleanest. Create multiple TRUE/FALSE columns like "

YouTube
·
https://www.youtube.com
POWER BI Hr Attrition Dashboard | Beginner to ... - YouTube
POWER BI Hr Attrition Dashboard | Beginner to Advanced Hr Power BI Report-Power BI Desktop Analyze HR Attrition Data in Power BI. This is a Power BI Desktop video to guide you on how to create an Hr A

Agile HR Analytics
·
https://www.agile-hr-analytics.com
Power BI HR Dashboard Tutorial: Build a Live Attrition Report
Create a line chart showing attrition rate over time: Insert a Line Chart visual; Drag “Month-Year” from the Date table to the X-axis; Drag “Attrition Rate” to the Y-axis; Set the title to “Attrition

LinkedIn
·
https://www.linkedin.com
How to conditionally format pie charts in Power BI - LinkedIn
Pie Charts Conditional Formatting (fx) in Power BI ! ⏳ Pie charts don't support conditional formatting. Here's a workaround. Step 1: Start with a bar chart. Step 2: Apply conditional formatting to the

YouTube
·
https://www.youtube.com
POWER BI Hr Attrition Dashboard - YouTube
Share your videos with friends, family, and the world.

YouTube
·
https://www.youtube.com
How to use IF in Power BI | Conditional Functions - YouTube
In this lesson I will cover how to use the conditional function IF( in Power BI. You find often you will have to use AND / OR when you want to further add some conditions to an IF statement. The purpo

Chandoo.org
·
https://chandoo.org
Employee Turnover Dashboard - Power BI for HR - Chandoo.org
Start with data. Typical staff recruitment and turnover data looks like this: Employee details (name, designation etc.) Where they work (department, branch etc.) Date of join; Date of leaving; Reason

Medium
·
https://medium.com
Employee Attrition Rate Analysis on Power bi | by Sophie Atieno
Analyzing the IBM Employee Attrition Dataset. Definition: “Attrition is the departure of employees from the organization for any reason (voluntary or involuntary), including resignation, termination,

Scribd
·
https://www.scribd.com
HR Data Analysis with Power BI Insights | PDF | Pie Chart - Scribd
1. Create a Bar Chart: ○ From the Visualizations Pane, select the Clustered Bar Chart icon. ○ Drag Age Group (you might need to create an age group dimension if it doesnʼt exist) to the Axis section.

LinkedIn
·
https://www.linkedin.com
How to build an HR Attrition Dashboard in Power BI - LinkedIn
Here's what our data looks like. We have each employees ID, the department they belong to, their gender, whether or not they've left the company, and the number of years that they were actually at the


i want to add a condition in power bi ,where if date is present it becomes as 'left' or else 'onroll'  and creates a pi chart showing employee atrition
To achieve this, you need to create a new Calculated Column using DAX to categorize your employees, and then build a Pie Chart to visualize the attrition.
Step 1: Create the 'Left' vs 'OnRoll' Status Column
You can use the ISBLANK function in DAX. If the exit date field is empty, the employee is "OnRoll"; if a date is present, they have "Left".
In Power BI Desktop, go to the Data view on the left sidebar (or right-click your employee table in the Data pane).
Click New column from the top ribbon.
Paste the following DAX formula (replace YourTableName and ExitDate with your actual table and column names):
dax
Employee Status = IF(ISBLANK('YourTableName'[ExitDate]), "OnRoll", "Left")
Use code with caution.
Press Enter. You will now see a new column showing "OnRoll" or "Left" for each row.
Step 2: Build the Attrition Pie Chart
Now that your data is categorized, you can build your visual in the Report view:
Select the Pie chart icon from the Visualizations pane.
Drag your newly created Employee Status column into the Legend bucket.
Drag your unique identifier—such as Employee ID (set to Count or Count (Distinct))—into the Values bucket.
Your pie chart will immediately display the proportion of active employees versus those who have left.
If you want to take this further, let me know:
Would you like a DAX measure to calculate the attrition rate percentage?
Do you need help filtering this chart by departments or years?




how to change name of visualisation
You can change the name (title) of a visualization in Power BI by modifying its title text or by renaming the visual itself for your internal selection pane.
Method 1: Change the Title visible on the Report
This changes the header text that your users see at the top of the chart.
Click on the visual you want to rename.
Go to the Visualizations pane on the right and click the Format your visual (paintbrush) icon.
Switch from the Visual tab to the General tab at the top of that pane.
Expand the Title card.
Type your new name into the Text box.
Method 2: Rename the Visual for internal tracking (Selection Pane)
This changes how the visual is named in your layer list, which is helpful for keeping your report organized or when building bookmarks.
Go to the top ribbon and select the View tab.
Check the box for Selection to open the Selection pane on the right side of your screen.
Double-click the visual's current name in the Selection list, type the new name, and press Enter.
Would you like help with formatting the title (like changing the font size and color) or renaming the data fields inside the chart's legend?




what visualisations do i need for an employee roll  dashboard
To build an effective Employee Roll & Attrition Dashboard, you need a mix of high-level overview metrics and deeper demographic breakdowns.
The ideal layout uses KPI cards at the top for immediate context, followed by specialized charts to show trends, distributions, and structural data.
1. High-Level Summary (KPI Cards)
Place these at the very top of your dashboard to give an instant health check of your workforce.
Total Headcount: A Card visual showing the count of active ("OnRoll") employees.
Attrition Rate (%): A Card visual showing (Employees Left / Total Employees) * 100.
New Hires (YTD): A Card visual tracking onboarding momentum for the current year.
2. Workforce Demographics & Structure
These visuals help you understand who makes up your workforce and where they are located.
Headcount by Department: A Clustered Bar Chart showing which departments are the largest.
Gender & Diversity Split: A Donut Chart mapping headcount by gender or demographic categories.
Age or Tenure Distribution: A Histogram or Grouped Column Chart showing how long employees stay or their age brackets (e.g., 0–2 years, 2–5 years, 5+ years).
3. Attrition & Trend Analysis
Use these to spot patterns in why and when people are leaving your company.
Attrition over Time: A Line Chart displaying monthly or quarterly exit trends to spot seasonal turnover.
Attrition by Department: A 100% Stacked Bar Chart comparing "OnRoll" vs. "Left" statuses across different departments. This instantly highlights high-turnover teams.
Top Reasons for Leaving: A Treemap or Horizontal Bar Chart ranking exit interview reasons (e.g., career growth, salary, management).
Suggested Dashboard Layout
Visual Type	Field / Metric	Dashboard Placement
Slicers (Filters)	Department, Location, Year/Month	Top or Left Sidebar
KPI Cards	Headcount, Active Employees, Attrition %	Top Row
Pie / Donut Chart	Employee Status (OnRoll vs. Left)	Middle Left
Clustered Bar Chart	Headcount by Department	Middle Right
Line Chart	Exit Date Trends (Over Time)	Bottom Full-Width
Would you like the DAX formulas to calculate the Total Active Headcount or the Attrition Rate % so your KPI cards update automatically?




yes
Here are the exact DAX formulas you need to set up your core KPI cards.
For these formulas to work seamlessly, make sure you have already created the Employee Status column we set up earlier (which outputs "OnRoll" or "Left").
1. Total Active Headcount ("OnRoll")
This measure counts only the employees who are currently active in the company.
dax
Active Headcount = 
CALCULATE(
    COUNT('YourTableName'[Employee ID]), 
    'YourTableName'[Employee Status] = "OnRoll"
)
Use code with caution.
2. Total Employees Who Left
This measure counts the total number of historical exits.
dax
Employees Left = 
CALCULATE(
    COUNT('YourTableName'[Employee ID]), 
    'YourTableName'[Employee Status] = "Left"
)
Use code with caution.
3. Attrition Rate (%)
This calculates your overall turnover percentage. By using the DIVIDE function, you protect your chart from displaying an error if your total headcount ever hits zero.
dax
Attrition Rate = 
DIVIDE(
    [Employees Left], 
    COUNT('YourTableName'[Employee ID]), 
    0
)
Use code with caution.
💡 Tip: After pasting the Attrition Rate formula, click on the measure name in your data pane, go to the Measure tools tab at the top, and click the % icon to format it as a percentage.
Would you like help setting up a Date Table next so you can track how these metrics change month-over-month or year-over-year?




what all would i need for this??
To build an Employee Roll & Attrition Dashboard with your specific data, you have all the necessary raw components ready to map directly into Power BI.
Based on your columns, here is exactly what fields you need to match up to build the dashboard visuals we discussed.
1. Data Cleaning & Foundation Fields
Before building your charts, you will need to map these fields to handle the core logic:
Employee ID: Use the Empno. column as your unique identifier to count employees.
The Conditional Logic Field: Look at your Left column. Notice that it either contains a termination date (e.g., 2023-08-20) or the text "Smiley" / "waiting" if they are active.
Update your column formula: Since your column is named Left and contains mixed data types, build your conditional formatting status column like this:
dax
Employee Status = IF('YourTableName'[Left] = "Smiley" || 'YourTableName'[Left] = "waiting", "OnRoll", "Left")
Use code with caution.
2. High-Level Summary (KPI Cards)
Drag your new Employee Status column and Empno. field into these measures:
Total Active Headcount: Count of Empno. where Employee Status = "OnRoll".
Total Exits: Count of Empno. where Employee Status = "Left".
Attrition Rate (%): Exits divided by total employee count.
3. Visualizations Configuration
Here is how you populate your visual slots using your exact column headers:
📊 Employee Status Proportion (Pie/Donut Chart)
Legend: Employee Status (Your new calculated column)
Values: Empno. (Set to Count)
📈 Headcount distribution by Department (Clustered Bar Chart)
Y-Axis: Department (or Department Group for a higher-level summary view)
X-Axis: Empno. (Set to Count, filtered to only show "OnRoll")
🌟 Gender Diversity Breakdown (Donut Chart)
Legend: Gender
Values: Empno. (Set to Count)
📌 Attrition hotspots across Segments (100% Stacked Bar Chart)
This chart will tell you exactly which divisions or roles are struggling with turnover.
Y-Axis: Division or Designation
X-Axis: Empno. (Set to Count)
Legend: Employee Status (This splits each bar cleanly by active vs. resigned employees)
🗒 Interactive Slicers (Filters)
Place these at the top or side pane of the page so you can drill down into specific areas:
Slicer 1: Location
Slicer 2: Category (e.g., Entry Level vs. waiting)
Slicer 3: Grade
Would you like help writing a advanced DAX measure to calculate the Average Tenure (how many months/years employees stay before leaving) using your DOJ column?




what all should i build
Based on the dataset you shared, you have a wealth of hospital/clinical staff data (including categories like Clinical, Non-Clinical, Clinical Support, specific Divisions, and Salary data).
To build a professional, industry-standard HR Workforce & Attrition Dashboard, you should build a 2-Page Report Layout. This keeps the dashboard clean, specialized, and highly scannable.
Page 1: Workforce Overview (Current Status)
Focuses entirely on your active "Onroll" staff to show the current state of the organization.
Top Row KPI Cards:
Total Active Headcount: Distinct Count of Empno. filtered to "Onroll".
Monthly Gross Fixed Cost: A sum of the Fixed Gross column to show active payroll burden.
Average Age: Calculated using the DOB (Date of Birth) column to check workforce maturity.
Workforce Breakdown (Donut Chart):
Legend: Gender
Values: Count of Empno.
Staff Distribution by Group (Clustered Bar Chart):
Y-Axis: Department Group (Shows the balance between Clinical, Non-Clinical, and Clinical Support).
X-Axis: Count of Empno.
Top Cost Centers (Treemap):
Category: Department or Division
Values: Sum of Fixed Gross (Instantly flags which hospital wings consume the most budget).
Page 2: Attrition & Retention Insights
Focuses on analyzing the staff that have "Left" to help HR fix turnover problems.
Top Row KPI Cards:
Total Historical Exits: Count of Empno. where status is "Left".
Overall Attrition Rate (%): Total Left divided by Total Ever Hired.
Attrition Source (Pie Chart):
Legend: Employee Status ("Onroll" vs "Left" column we created).
Values: Count of Empno.
Turnover Risk Zone (100% Stacked Bar Chart):
Y-Axis: Designation or Grade (e.g., Staff Nurse, Executive).
X-Axis: Count of Empno.
Legend: Employee Status (This reveals if specific grades like 5C or 4A are leaving faster than others).
Exit Timeline Trend (Line Chart):
X-Axis: Left (Set to Year/Month hierarchy)
Y-Axis: Count of Empno. (Shows spikes in resignations over time).
Global Filters to Include on Both Pages (Slicers)
Place these in a top bar or a collapsible left pane so users can filter the entire dashboard:
Location (e.g., Front Office, Ward)
Wunit / Punit (e.g., KMH)
Category (e.g., Entry Level)
Would you like me to give you the step-by-step layout design instructions for Page 1 (Workforce Overview) first, or would you like the DAX formula to calculate the Average Employee Age using your DOB column?




what all shud i do for analysis with pandas and numpy
Before you load your data into Power BI, doing a preliminary analysis using Pandas and NumPy in Python is a fantastic way to clean your data, uncover deep insights, and double-check your calculations.
Here is a comprehensive checklist of analyses and data-cleaning steps you should perform using Pandas and NumPy:
1. Data Cleaning & Status Mapping
Your Left column contains mixed data types (dates, "Smiley", and "waiting"). You need to clean this first to establish your target variables.
python
import pandas as pd
import numpy as np

# Load your data
df = pd.read_csv('your_file.csv')

# 1. Clean the 'Left' column and create an 'Employee_Status' column
df['Employee_Status'] = np.where(df['Left'].isin(['Smiley', 'waiting']), 'Onroll', 'Left')

# 2. Convert date strings to actual datetime objects for analysis
df['DOJ'] = pd.to_datetime(df['DOJ'])
df['DOB'] = pd.to_datetime(df['DOB'])

# Extract exit dates where applicable, setting non-dates (Smiley/waiting) to NaT (Not a Time)
df['Exit_Date'] = pd.to_datetime(df['Left'], errors='coerce')
Use code with caution.
2. Basic Descriptive Analytics
Get a snapshot of the health of your workforce using basic aggregation.
python
# 1. Headcount Breakdowns
total_hired = len(df)
active_headcount = np.sum(df['Employee_Status'] == 'Onroll')
total_exits = np.sum(df['Employee_Status'] == 'Left')
attrition_rate = (total_exits / total_hired) * 100

print(f"Active Headcount: {active_headcount} | Attrition Rate: {attrition_rate:.2f}%")

# 2. Financial Overview (Payroll Breakdown)
total_payroll = df[df['Employee_Status'] == 'Onroll']['Fixed Gross'].sum()
avg_salary_by_dept = df.groupby('Department')['Fixed Gross'].mean()
Use code with caution.
3. Demographic & Age Analysis
Calculate the exact age of your workforce using numpy and pandas datetime calculations to see if age correlates with turnover.
python
# Calculate current age based on the current date (September 2026)
current_date = pd.to_datetime('2026-09-19')
df['Age'] = (current_date - df['DOB']).dt.days // 365.25

# Segment ages into brackets using pandas.cut
age_bins = [0, 25, 35, 45, 55, 100]
age_labels = ['Under 25', '25-34', '35-44', '45-54', '55+']
df['Age_Group'] = pd.cut(df['Age'], bins=age_bins, labels=age_labels)

# Analyze attrition rate by Age Group
age_attrition = df.groupby('Age_Group')['Employee_Status'].value_counts(normalize=True).unstack().fillna(0) * 100
print(age_attrition)
Use code with caution.
4. Attrition Risk & Hotspot Identification
Identify which departments, gender cohorts, or management layers are experiencing structural issues.
python
# 1. Attrition by Department Group (Clinical vs Non-Clinical)
dept_group_attrition = df.groupby('Department Group')['Employee_Status'].value_counts(normalize=True).unstack() * 100

# 2. Attrition by Gender
gender_attrition = df.groupby('Gender')['Employee_Status'].value_counts(normalize=True).unstack() * 100

# 3. Manager Turn-around (Which managers have the highest team turnover?)
manager_turnover = df[df['Employee_Status'] == 'Left'].groupby('Reporting to')['Empno.'].count().sort_values(ascending=False)
Use code with caution.
5. Tenure / Survival Analysis
For the employees who left, how long did they stay before resigning?
python
# Calculate tenure in months for employees who left
df_left = df[df['Employee_Status'] == 'Left'].copy()
df_left['Tenure_Months'] = (df_left['Exit_Date'] - df_left['DOJ']).dt.days / 30.44

print("Average tenure before leaving (Months):", df_left['Tenure_Months'].mean())
print("Median tenure before leaving (Months):", df_left['Tenure_Months'].median())

# Find out if tenure changes based on Grade level
print(df_left.groupby('Grade')['Tenure_Months'].mean())
Use code with caution.
Would you like me to help you generate a Matplotlib / Seaborn visualization script to plot these trends natively in Python, or do you want to move straight to generating the clean CSV export to pull into Power BI?




give it as a checklist for both the python and powerbi one
Something went wrong and the content wasn't generated.
give it as a checklist for both the python and powerbi one
Here is your complete, step-by-step implementation checklist for both Python (Data Exploration & Validation) and Power BI (Dashboard Building).
🐍 Part 1: Python (Pandas & NumPy) Checklist
Use this checklist to clean the data, find hidden patterns, and validate numbers before visualization.
🛠️ 1. Data Cleaning & Type Casting
Load Dataset: Read your CSV file into a Pandas DataFrame (pd.read_csv).
Standardise Statuses: Create a uniform Employee_Status column using np.where() to map "Smiley" and "waiting" to "Onroll", and everything else to "Left".
Fix Date Types: Convert DOB (Date of Birth) and DOJ (Date of Joining) columns into actual datetime objects using pd.to_datetime().
Extract Exits: Create a clean Exit_Date column by running pd.to_datetime() on the Left column with errors='coerce' to turn text flags into blank datetime slots (NaT).
📊 2. High-Level Descriptive Analytics
Headcount Verification: Calculate baseline metrics (len(df)) for total hired, active staff, and total historical exits to check dataset integrity.
Payroll Aggregation: Sum the Fixed Gross column for active employees to find the current active payroll baseline.
Department Payroll Averages: Run a .groupby('Department')['Fixed Gross'].mean() to calculate average salary expenditures per business unit.
🧮 3. Advanced Demographics & Metrics
Calculate Exact Age: Subtract DOB from the current date (2026-09-19), divide by 365.25, and use numpy to truncate to exact integer ages.
Create Age Brackets: Use pd.cut() to segment staff ages into clean categorical bins (e.g., Under 25, 25–34, 35–44, etc.).
Cross-Tabulate Attrition: Run cross-tabulations on Age_Group, Gender, and Department Group against Employee_Status to calculate relative group turnover percentages.
🔍 4. Retention & Leadership Deep Dives
Calculate Lifecycle Tenure: For staff marked as "Left", calculate the duration between DOJ and Exit_Date in months.
Determine Retention Metrics: Compute both the mean and median tenure months to identify when the average employee drops out.
Flag Leadership Turnover Hotspots: Group the data by Reporting to and count exits to discover which manager codes are experiencing the highest attrition spikes.
Export Verified Data: Run .to_csv('Cleaned_Employee_Data.csv', index=False) to output a spotless file for Power BI.
📊 Part 2: Power BI Checklist
Use this checklist once you import your cleaned dataset to configure your dashboard reporting layers.
📐 1. DAX Setup (Measures & Columns)
Import Clean Dataset: Pull your verified CSV into Power BI Desktop.
Active Headcount Measure: Write a CALCULATE measure using COUNT('Table'[Empno.]) filtered strictly to [Employee Status] = "Onroll".
Exits Measure: Write a CALCULATE measure counting Empno. where [Employee Status] = "Left".
Dynamic Attrition Rate: Write an Attrition Rate = DIVIDE([Employees Left], COUNT('Table'[Empno.]), 0) measure.
Format Percentages: Select the Attrition measure and explicitly change its formatting category to % in the top ribbon menu.
🎨 2. Page 1 Layout: Workforce Overview (Active Status)
KPI Summary Cards: Place three card visuals at the top showing Active Headcount, Total Monthly Gross Cost (Fixed Gross), and Average Age.
Workforce Balance (Donut Chart): Map Gender into the Legend and Empno. (Count) into the Values field.
Operational Allocation (Clustered Bar Chart): Add Department Group to the Y-axis and Empno. (Count) to the X-axis to display organizational balance.
Cost Matrix Visualization (Treemap): Drag Division or Department into Category, and sum Fixed Gross into Values to build a structural cost tracker.
📉 3. Page 2 Layout: Attrition & Trend Analysis
Historical Summary Cards: Place cards at the top displaying Total Exits and the Overall Attrition Rate (%).
Attrition Breakdown Visual (Pie Chart): Place your Employee Status column in the Legend and Empno. (Count) in the Values section.
Turnover Risk Analysis (100% Stacked Bar Chart): Put Designation or Grade on the Y-axis, Empno. on the X-axis, and your Employee Status field into the Legend to see exactly where structural dropouts happen.
Exit Timeline Tracking (Line Chart): Pull your clean exit dates to the X-axis (Year/Month hierarchy) and map Empno. (Count) to the Y-axis to map historical spikes.
🎛️ 4. Global Filters & Polish
Universal Filter Placement (Slicers): Build a sidebar or top menu containing slicers for Location, Category, and Grade.
Configure Interactivity: Check that clicking a slicer successfully updates both pages correctly.
Visual Renaming: Update chart headers via Format Visual -> General -> Title to ensure user-friendly dashboard labels.
Would you like the exact Python code blocks to generate the Matplotlib/Seaborn turnover graphs, or do you need the advanced DAX syntax to build a dynamic Month-over-Month headcount tracker in Power BI?




