import json
from datetime import datetime
import yfinance as yf
import matplotlib.pyplot as plt

# Загружаем JSON-данные из файла
file_path = "ft_userdata/user_data/backtest_results/backtest-result-2024-01-30_17-19-03.json"
with open(file_path, 'r') as file:
    json_data = file.read()

# Разбираем JSON
data = json.loads(json_data)

# Извлекаем данные о транзакциях
trades = data['strategy']['DaniilStrategyLong']['trades']

# Создаем списки для хранения данных
open_dates = []
close_dates = []
open_rates = []
close_rates = []

# Извлекаем данные о датах и ценах открытия и закрытия транзакций
for trade in trades:
    open_dates.append(datetime.strptime(trade['open_date'], '%Y-%m-%d %H:%M:%S+00:00'))
    close_dates.append(datetime.strptime(trade['close_date'], '%Y-%m-%d %H:%M:%S+00:00'))
    open_rates.append(trade['open_rate'])
    close_rates.append(trade['close_rate'])

# Получаем исторические данные о цене биткоина
bitcoin_data = yf.download('BTC-USD', start='2019-03-01', end='2023-01-01', interval='1d')

# Строим график
plt.figure(figsize=(12, 8))

# График цены биткоина
plt.plot(bitcoin_data.index, bitcoin_data['Close'], label='Bitcoin Price', color='orange')

# График транзакций
plt.plot(open_dates, open_rates, label='Open Rate', marker='o')
plt.plot(close_dates, close_rates, label='Close Rate', marker='x')

# Настройки графика
plt.xlabel('Date')
plt.ylabel('Price / Rate')
plt.title('Bitcoin Price and Transaction Rates')
plt.legend()
plt.grid(True)
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()
