import pandas as pd
import glob
import csv
from datetime import datetime, timedelta

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def round_seconds(time):
    if time.microsecond >= 500_000:
        time += timedelta(0, 1)
    return time.replace(microsecond=0)

#Assumes log file is of format 'XXXX-XX-XX xx:xx:xx.xxx,power' on each line with no header
#If there is a header may need to manually remove it
def get_df_format1(power_log):
    return pd.read_csv(power_log, sep=',', names=['datetime', 'power'], dtype={'datetime': "string", "power": "float16"}, usecols=(0, 1), low_memory=False)


def get_log_times(header_info, size):
    date = header_info[3][1]
    time = header_info[4][1]

    datetime_str = f"{date} {time}"

    # Convert date from string to datetime object
    timedate = datetime.strptime(datetime_str, DATETIME_FORMAT)

    # Create array of log times, one log/second
    log_times = [timedate + timedelta(0, delta) for delta in range(size)]

    return log_times

# Old format - this is for files of format XX-XX-XX.CSV
def get_df_format2(power_log):
    # Want to extract header info to get start time
    header_info = []
    with open(power_log) as f:
        csv_reader = csv.reader(f)

        for i, row in enumerate(csv_reader):
            header_info.append(row)

            if i == 4:
                break

    # Skipping header as already read
    df = pd.read_csv(power_log, low_memory=False, skiprows=7, names=['power'], usecols=[1])

    # Insert calculated log times
    df.insert(0, "datetime", get_log_times(header_info, df.size))
    df.set_index('datetime', inplace=True)

    return df


def fill_time_gaps(df):
    # Find delta between consecutive logs
    deltas = df['datetime'].diff()

    gaps = deltas[deltas > timedelta(0, 1)]
    gaps = [gaps < timedelta(0, 3)]
    print(gaps)

    return df


def combine_logs(power_logs):
    power_logs_list = []

    # Read each log and combine into list
    for power_log in power_logs:

        if "power_log" in power_log:
            print(f"working on {power_log}, format 1")
            df = get_df_format1(power_log)
        else:
            print(f"working on {power_log}, format 2")
            df = get_df_format2(power_log)

        power_logs_list.append(df)
        print(f"added {power_log}")

    # Turn list into df, more efficient to do so this way rather than append to existing df
    df = pd.concat(power_logs_list, axis=0, ignore_index=True)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values(by=['datetime'], ignore_index=True)

    # Drop ms, decided not to do this as accuracy is lost but left in incase plans change
    # df['datetime'] = df['datetime'].apply(lambda x: round_seconds(x))

    # Average when multiple values at same time - should only happen when log files overlap so no loss of accuracy
    df = df.groupby('datetime').mean().reset_index()

    # Removing standard index saves LOTS of space
    df.set_index('datetime', inplace=True)

    return df


def load_combined_csv(name):
    df = pd.read_csv(name, dtype={'datetime': "string", "power": "float16"}, low_memory=False)
    df['datetime'] = pd.to_datetime(df['datetime'])
    # df.set_index('datetime', inplace=True)

    return df


if __name__ == '__main__':
    #power_logs is array of all logs to combine
    power_logs = glob.glob("power/power_log*.csv")
    df = combine_logs(power_logs)
    print("complete")

    #Change CSV name here if needed
    df.to_csv("grouped_unrounded.csv")
