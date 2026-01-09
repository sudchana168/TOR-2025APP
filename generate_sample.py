import pandas as pd
from datetime import date, timedelta

data = [
    {
        "Task ID": "1.1",
        "Task": "Project Kick-off",
        "Start Date": (date.today() + timedelta(days=7)).strftime("%d/%m/%Y"), # Starts in 7 days (should trigger reminder)
        "End Date": (date.today() + timedelta(days=14)).strftime("%d/%m/%Y"),
        "Responsible": "Team A",
        "Progress (%)": 0
    },
    {
        "Task ID": "2.1",
        "Task": "Design Phase",
        "Start Date": (date.today() - timedelta(days=30)).strftime("%d/%m/%Y"),
        "End Date": date.today().strftime("%d/%m/%Y"), # Ends today (should trigger reminder)
        "Responsible": "Team B",
        "Progress (%)": 50
    },
    {
        "Task ID": "3.0",
        "Task": "Warranty Item",
        "Start Date": "01/01/2022",
        "End Date": (date.today() - timedelta(days=365*3)).strftime("%d/%m/%Y"), # Warranty expires today (End + 3 years)
        "Responsible": "Team C",
        "Progress (%)": 100
    }
]

df = pd.DataFrame(data)
df.to_excel("sample_tor.xlsx", index=False)
print("sample_tor.xlsx created.")
