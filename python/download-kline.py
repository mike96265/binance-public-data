#!/usr/bin/env python

"""
  script to download klines.
  set the absolute path destination folder for STORE_DIRECTORY, and run

  e.g. STORE_DIRECTORY=/data/ ./download-kline.py

"""
import os
import sys
import tempfile
import zipfile

import pandas as pd

from enums import *
from utility import download_file, get_all_symbols, get_parser, convert_to_date_object, \
    get_path, upload_to_aws


def download_monthly_klines(trading_type, symbols, num_symbols, intervals, years, months, start_date, end_date, folder,
                            checksum):
    current = 0
    date_range = None

    if start_date and end_date:
        date_range = start_date + " " + end_date

    if not start_date:
        start_date = START_DATE
    else:
        start_date = convert_to_date_object(start_date)

    if not end_date:
        end_date = END_DATE
    else:
        end_date = convert_to_date_object(end_date)

    print("Found {} symbols".format(num_symbols))
    names = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count",
             "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
    for symbol in symbols:
        print("[{}/{}] - start download monthly {} klines ".format(current + 1, num_symbols, symbol))
        for interval in intervals:
            dfs = []
            for year in years:
                for month in months:
                    current_date = convert_to_date_object('{}-{}-01'.format(year, month))
                    if current_date >= start_date and current_date <= end_date:
                        path = get_path(trading_type, "klines", "monthly", symbol, interval)
                        file_name = "{}-{}-{}-{}.zip".format(symbol.upper(), interval, year, '{:02d}'.format(month))

                        with tempfile.NamedTemporaryFile(dir="/dev/shm", delete=False) as temp_file:
                            tmp_name = temp_file.name

                        download_file(path, file_name, date_range, folder, tmp_name)
                        try:
                            with zipfile.ZipFile(tmp_name) as zip_file:
                                for file_name in zip_file.namelist():
                                    with zip_file.open(file_name) as f:
                                        df = pd.read_csv(f, header=None, names=names)
                                    dfs.append(df)
                        except zipfile.BadZipFile:
                            continue
                        finally:
                            os.remove(tmp_name)

                        if checksum == 1:
                            checksum_path = get_path(trading_type, "klines", "monthly", symbol, interval)
                            checksum_file_name = "{}-{}-{}-{}.zip.CHECKSUM".format(symbol.upper(), interval, year,
                                                                                   '{:02d}'.format(month))
                            download_file(checksum_path, checksum_file_name, date_range, folder)
            concat = pd.concat(dfs, ignore_index=True)
            feather_file = f"{symbol}-{interval}.feather"
            concat.to_feather(feather_file, compression="zstd")
            upload_to_aws(feather_file, f"{symbol}/klines/{interval}.feather")

        current += 1


def download_daily_klines(trading_type, symbols, num_symbols, intervals, dates, start_date, end_date, folder, checksum):
    print("Downloading klines")
    current = 0
    date_range = None

    if start_date and end_date:
        date_range = start_date + " " + end_date

    if not start_date:
        start_date = START_DATE
    else:
        start_date = convert_to_date_object(start_date)

    if not end_date:
        end_date = END_DATE
    else:
        end_date = convert_to_date_object(end_date)

    # Get valid intervals for daily
    intervals = list(set(intervals) & set(DAILY_INTERVALS))
    print("Found {} symbols".format(num_symbols))
    names = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count",
             "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
    for symbol in symbols:
        print("[{}/{}] - start download daily {} klines ".format(current + 1, num_symbols, symbol))
        for interval in intervals:
            dfs = []
            for date in dates:
                current_date = convert_to_date_object(date)
                if current_date >= start_date and current_date <= end_date:
                    path = get_path(trading_type, "klines", "daily", symbol, interval)
                    file_name = "{}-{}-{}.zip".format(symbol.upper(), interval, date)
                    with tempfile.NamedTemporaryFile(dir="/dev/shm", delete=False) as temp_file:
                        tmp_name = temp_file.name

                    download_file(path, file_name, date_range, folder, tmp_name)
                    try:
                        with zipfile.ZipFile(tmp_name) as zip_file:
                            for file_name in zip_file.namelist():
                                with zip_file.open(file_name) as f:
                                    df = pd.read_csv(f, header=None, names=names)
                                dfs.append(df)
                    except zipfile.BadZipFile:
                        continue
                    finally:
                        os.remove(tmp_name)
                    if checksum == 1:
                        checksum_path = get_path(trading_type, "klines", "daily", symbol, interval)
                        checksum_file_name = "{}-{}-{}.zip.CHECKSUM".format(symbol.upper(), interval, date)
                        download_file(checksum_path, checksum_file_name, date_range, folder)
            concat = pd.concat(dfs, ignore_index=True)
            feather_file = f"{symbol}-{interval}.feather"
            concat.to_feather(feather_file, compression="zstd")
            upload_to_aws(feather_file, f"{symbol}/klines/{interval}.feather")

        current += 1


if __name__ == "__main__":
    parser = get_parser('klines')
    args = parser.parse_args(sys.argv[1:])

    if not args.symbols:
        print("fetching all symbols from exchange")
        symbols = get_all_symbols(args.type)
        num_symbols = len(symbols)
    else:
        symbols = args.symbols
        num_symbols = len(symbols)

    if args.dates:
        dates = args.dates
    else:
        period = convert_to_date_object(datetime.today().strftime('%Y-%m-%d')) - convert_to_date_object(
            PERIOD_START_DATE)
        dates = pd.date_range(end=datetime.today(), periods=period.days + 1).to_pydatetime().tolist()
        dates = [date.strftime("%Y-%m-%d") for date in dates]
        if args.skip_monthly == 0:
            download_monthly_klines(args.type, symbols, num_symbols, args.intervals, args.years, args.months,
                                    args.startDate, args.endDate, args.folder, args.checksum)
    if args.skip_daily == 0:
        download_daily_klines(args.type, symbols, num_symbols, args.intervals, dates, args.startDate, args.endDate,
                              args.folder, args.checksum)
