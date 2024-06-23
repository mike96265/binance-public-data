import pandas as pd

pd.set_option('display.max_rows', 500)

data = pd.read_feather("./data/BTCUSDT_klines_1d.feather")
data["delta"] = data["close"] - data["open"]
data["delta_percent"] = data["delta"] / data["close"] * 100
data["datetime"] = pd.to_datetime(data["open_time"], unit="ms")

t = 1714435200000
