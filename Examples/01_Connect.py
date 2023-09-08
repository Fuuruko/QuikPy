from datetime import datetime

# Для импортирования QuikPy
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

# Работа с QUIK из Python через LUA скрипты QuikSharp
from QuikPy import QuikPy


if __name__ == '__main__':
    # Подключение к локальному запущенному терминалу QUIK по портам по умолчанию
    qp_provider = QuikPy()

    # Подключение к удаленному QUIK по портам по умолчанию
    # qp_provider = QuikPy(host='<Адрес IP>')
    # Подключение к удаленному QUIK по другим портам
    # qp_provider = QuikPy(host='<Адрес IP>',
    #                      requests_port='<Порт запросов>',
    #                      callbacks_port='<Порт подписок>')
    print(f"Терминал QUIK подключен к серверу: {qp_provider.isConnected() == 1}")
    # Проверка работы скрипта QuikSharp. Должен вернуть Pong
    print(f"Отклик QUIK на команду Ping: {qp_provider.ping()}")

    # Проверяем работу запрос/ответ

    # Дата на сервере в виде строки dd.mm.yyyy
    trade_date = qp_provider.getInfoParam('TRADEDATE')
    # Время на сервере в виде строки hh:mi:ss
    server_time = qp_provider.getInfoParam('SERVERTIME')
    if not qp_provider.isConnected():
        server_time = qp_provider.getInfoParam('LOCALTIME')

    # Переводим строки в дату и время
    dt = datetime.strptime(f'{trade_date}{server_time}', '%d.%m.%Y%H:%M:%S')
    print(f'Дата и время на сервере: {dt}')
    msg = 'Hello from Python!'
    # Проверка работы QUIK. Сообщение в QUIK должно показаться как информационное
    print(f"Отправка сообщения в QUIK: {msg}{qp_provider.message(msg)}")

    # Нажимаем кнопку "Установить соединение" в QUIK
    qp_provider.OnConnected = lambda data: print(data)
    # Нажимаем кнопку "Разорвать соединение" в QUIK
    qp_provider.OnDisconnected = lambda data: print(data)
    # Текущие параметры изменяются постоянно. Будем их смотреть, пока не нажмем Enter в консоли
    qp_provider.OnParam = lambda data: print(data)

    input('Enter - выход\n')
    # Перед выходом закрываем соединение и поток QuikPy
    qp_provider.CloseConnectionAndThread()
