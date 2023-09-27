from datetime import datetime
import time  # Подписка на события по времени

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

# Работа с QUIK из Python через LUA скрипты QuikSharp
from QuikPy import QuikPy


def print_callback(data):
    """Пользовательский обработчик событий:

    - Изменение стакана котировок
    - Получение обезличенной сделки
    - Получение новой свечки
    """
    print(f'{datetime.now().strftime("%d.%m.%Y %H:%M:%S")} - {data}')


def changed_connection(data):
    """Пользовательский обработчик событий:

    - Соединение установлено
    - Соединение разорвано
    """
    print(f'{datetime.now().strftime("%d.%m.%Y %H:%M:%S")} - {data}')


if __name__ == '__main__':
    qp_prov = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    cls_code = 'TQBR'  # Класс тикера
    sec_code = 'SBER'  # Тикер

    # cls_code = 'SPBFUT'  # Класс тикера
    # Для фьючерсов: <Код тикера>
    #                <Месяц экспирации: 3-H, 6-M, 9-U, 12-Z>
    #                <Последняя цифра года>
    # sec_code = 'SiU3'

    # Запрос текущего стакана.
    # Чтобы получать, в QUIK открыть Таблицу Котировки, указать тикер
    print(f'Текущий стакан {cls_code}.{sec_code}:',
          qp_prov.GetQuoteLevel2(cls_code, sec_code))

    # Стакан. Чтобы отмена подписки работала корректно,
    # в QUIK должна быть ЗАКРЫТА Таблица Котировки тикера
    qp_prov.OnQuote = print_callback  # Обработчик изменения стакана котировок
    print('Подписка на изменения стакана {cls_code}.{sec_code}:',
          qp_prov.subs_level_II_quotes(cls_code, sec_code))
    print('Статус подписки:', qp_prov.is_subs_level_II_quotes(cls_code, sec_code))
    sleep_sec = 1  # Кол-во секунд получения котировок
    print('Секунд котировок:', sleep_sec)
    time.sleep(sleep_sec)  # Ждем кол-во секунд получения котировок
    print('Отмена подписки на изменения стакана: ',
          qp_prov.unsubs_level_II_quotes(cls_code, sec_code))
    print('Статус подписки:',
          qp_prov.is_subs_level_II_quotes(cls_code, sec_code))
    qp_prov.OnQuote = qp_prov.default_handler  # Возвращаем обработчик по умолчанию

    # Обезличенные сделки. Чтобы получать, в QUIK открыть Таблицу обезличенных сделок, указать тикер
    # qp_prov.OnAllTrade = print_callback  # Обработчик получения обезличенной сделки
    # sleep_sec = 1  # Кол-во секунд получения обезличенных сделок
    # print('Секунд обезличенных сделок:', sleep_sec)
    # time.sleep(sleep_sec)  # Ждем кол-во секунд получения обезличенных сделок
    # qp_prov.OnAllTrade = qp_prov.default_handler  # Возвращаем обработчик по умолчанию

    # Просмотр изменений состояния соединения терминала QUIK с сервером брокера
    qp_prov.OnConnected = changed_connection
    qp_prov.OnDisconnected = changed_connection

    # Новые свечки. При первой подписке получим все свечки с начала прошлой сессии
    # TODO В QUIK 9.2.13.15 перестала работать повторная подписка на минутные бары. Остальные работают
    # Перед повторной подпиской нужно перезапустить скрипт QuikSharp.lua,
    # Подписка станет первой, все заработает
    qp_prov.OnNewCandle = print_callback  # Обработчик получения новой свечки
    for interval in (60,):  # (1, 60, 1440) = Минутки, часовки, дневки
        print(f'Подписка на интервал {interval}:',
              qp_prov.subs_to_candles(cls_code, sec_code, interval))
        print(f'Статус подписки на интервал {interval}:',
              qp_prov.is_subs(cls_code, sec_code, interval))
    input('Enter - отмена\n')
    for interval in (60,):  # (1, 60, 1440) = Минутки, часовки, дневки
        print(f'Отмена подписки на интервал {interval}',
              qp_prov.unsubs_from_candles(cls_code, sec_code, interval))
        print(f'Статус подписки на интервал {interval}:',
              qp_prov.is_subs(cls_code, sec_code, interval))

    # Перед выходом закрываем соединение и поток QuikPy
    qp_prov.close_connection()
