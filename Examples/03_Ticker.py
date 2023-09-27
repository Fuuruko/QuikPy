import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

# Работа с QUIK из Python через LUA скрипты QuikSharp
from QuikPy import QuikPy


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    cls_code = 'TQBR'  # Класс тикера
    sec_code = 'SBER'  # Тикер

    # cls_code = 'SPBFUT'  # Класс тикера
    # sec_code = 'SiU3'  # Для фьючерсов: <Код тикера>
    #                                     <Месяц экспирации: 3-H, 6-M, 9-U, 12-Z>
    #                                     <Последняя цифра года>

    # Данные тикера
    # Интерпретатор языка Lua, Таблица 4.21 Инструменты
    sec_inf = qp_provider.getSecurityInfo(cls_code, sec_code)
    # print(f'Ответ от сервера: {sec_inf}')
    # Короткое наименование инструмента
    print(f'Информация о тикере {cls_code}.{sec_code} ({sec_inf["short_name"]}):')
    # Торговый счет для класса тикера
    trd_acc = qp_provider.getTradeAccount(cls_code)
    print('Торговый счет:', trd_acc)
    # Последняя цена сделки
    last_price = float(qp_provider.getParamEx(cls_code, sec_code, 'LAST')['param_value'])
    print('Последняя цена сделки:', last_price)
    print('Валюта:', sec_inf['face_unit'])  # Валюта номинала
    print('Лот:', sec_inf['lot_size'])  # Размер лота
    print('Цифр после запятой:', sec_inf['scale'])  # Точность (кол-во значащих цифр после запятой)
    print('Шаг цены:', sec_inf['min_price_step'])  # Минимальный шаг цены

    # Выход
    qp_provider.close_connection()  # Перед выходом закрываем соединение и поток QuikPy
