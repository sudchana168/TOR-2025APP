import pandas as pd

try:
    df = pd.read_excel("Redesign.xlsx", header=2)
    # Print all values in Unnamed: 0
    print(df['Unnamed: 0'].to_string())
except Exception as e:
    print(f"Error reading file: {e}")
