from time import time
import os.path
import pandas as pd

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

# Работа с QUIK из Python через LUA скрипты QuikSharp
from QuikPy import QuikPy


def save_candels(class_code: str = 'TQBR', sec_codes: tuple = ('SBER',),
                 time_frame: str = 'D', compression: int = 1, skip_first_date: bool = False,
                 skip_last_date: bool = False, four_price_doji: bool = False):
    """Получение баров, объединение с имеющимися барами в файле (если есть), сохранение баров в файл

    class_code: Код площадки
    sec_codes: Коды тикеров в виде кортежа
    time_frame: Временной интервал 'M'-Минуты, 'D'-дни, 'W'-недели, 'MN'-месяцы
    compression: Кол-во минут для минутного графика:
        0 (тик), 1, 2, 3, 4, 5, 6, 10, 15, 20, 30, 60 (1 час),
        120 (2 часа), 240 (4 часа). Для остальных = 1
    skip_first_date: Убрать бары на первую полученную дату
    skip_last_date: Убрать бары на последнюю полученную дату
    four_price_doji: Оставить бары с дожи 4-х цен
    """
    # Для минутных временнЫх интервалов ставим кол-во минут
    interval = compression
    # Все в минутах
    if time_frame == 'D':  # Дневной временной интервал
        interval = 1440
    elif time_frame == 'W':  # Недельный временной интервал
        interval = 10080
    elif time_frame == 'MN':  # Месячный временной интервал
        interval = 23200

    # Пробегаемся по всем тикерам
    for sec_code in sec_codes:
        # Дальше будем пытаться получить бары из файла
        file_bars = None
        file_name = f'{datapath}{class_code}.{sec_code}_{time_frame}{compression}.txt'
        file_exists = os.path.isfile(file_name)  # Существует ли файл

        if file_exists:
            print(f'Получение файла {file_name}')
            file_bars = pd.read_csv(file_name, sep='\t', index_col='datetime')
            # Переводим индекс в формат datetime
            file_bars.index = pd.to_datetime(file_bars.index, format='%d.%m.%Y %H:%M')
            print(f'- Первая запись файла: {file_bars.index[0]}\n'
                  f'- Последняя запись файла: {file_bars.index[-1]}\n'
                  f'- Кол-во записей в файле: {len(file_bars)}')
        else:
            print(f'Файл {file_name} не найден и будет создан')

        print(f'Получение истории {class_code}.{sec_code} '
              f'{time_frame}{compression} из QUIK')
        # Получаем все бары из QUIK
        new_bars = qp_provider.get_candles_ds(class_code, sec_code, interval, 0)

        if not new_bars:
            print(f'Данных по {class_code}.{sec_code} нету')
            continue
        # Переводим список баров в pandas DataFrame
        pd_bars = pd.json_normalize(new_bars)
        # Чтобы получить дату/время переименовываем колонки
        pd_bars.rename(columns={'datetime.year': 'year', 'datetime.month': 'month',
                                'datetime.day': 'day', 'datetime.hour': 'hour',
                                'datetime.min': 'minute', 'datetime.sec': 'second'},
                       inplace=True)

        # Собираем дату/время из колонок
        pd_bars.index = pd.to_datetime(pd_bars[['year', 'month', 'day',
                                                'hour', 'minute', 'second']])
        # Отбираем нужные колонки
        pd_bars = pd_bars[['open', 'high', 'low', 'close', 'volume']]
        # Ставим название индекса даты/времени
        pd_bars.index.name = 'datetime'
        # Объемы могут быть только целыми
        pd_bars.volume = pd.to_numeric(pd_bars.volume, downcast='integer')

        # Если файла нет, и убираем бары на первую дату
        if not file_exists and skip_first_date:
            # Кол-во баров до удаления на первую дату
            len_with_first_date = len(pd_bars)
            first_date = pd_bars.index[0].date()  # Первая дата
            pd_bars.drop(pd_bars[(pd_bars.index.date == first_date)].index,
                         inplace=True)  # Удаляем их
            print(f'- Удалено баров на первую дату {first_date}: '
                  f'{len_with_first_date - len(pd_bars)}')

        # Если убираем бары на последнюю дату
        if skip_last_date:
            # Кол-во баров до удаления на последнюю дату
            len_with_last_date = len(pd_bars)
            last_date = pd_bars.index[-1].date()  # Последняя дата
            pd_bars.drop(pd_bars[(pd_bars.index.date == last_date)].index,
                         inplace=True)  # Удаляем их
            print(f'- Удалено баров на последнюю дату {last_date}: '
                  f'{len_with_last_date - len(pd_bars)}')

        if not four_price_doji:  # Если удаляем дожи 4-х цен
            len_with_doji = len(pd_bars)  # Кол-во баров до удаления дожи
            # Удаляем их по условию High == Low
            pd_bars.drop(pd_bars[(pd_bars.high == pd_bars.low)].index, inplace=True)
            print('- Удалено дожи 4-х цен:', len_with_doji - len(pd_bars))

        if len(pd_bars) == 0:  # Если нечего объединять
            print('Новых записей нет')
            continue  # то переходим к следующему тикеру, дальше не продолжаем
        print('- Первая запись в QUIK:', pd_bars.index[0])
        print('- Последняя запись в QUIK:', pd_bars.index[-1])
        print('- Кол-во записей в QUIK:', len(pd_bars))

        if file_exists:
            # Объединяем файл с данными из QUIK, убираем дубликаты, сортируем заново
            pd_bars = pd.concat([file_bars, pd_bars]).drop_duplicates(keep='last').sort_index()
        pd_bars.to_csv(file_name, sep='\t', date_format='%d.%m.%Y %H:%M')
        print(f'- В файл {file_name} сохранено записей: {len(pd_bars)}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    start_time = time()  # Время начала запуска скрипта
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    class_code = 'TQBR'  # Акции ММВБ
    # class_code = 'SPBFUT'  # Фьючерсы
    # TOP 40 акций ММВБ
    sec_codes = ('SBER', 'VTBR', 'GAZP', 'MTLR', 'LKOH', 'PLZL', 'SBERP', 'BSPB', 'POLY', 'RNFT',
                 'GMKN', 'AFLT', 'NVTK', 'TATN', 'YNDX', 'MGNT', 'ROSN', 'AFKS', 'NLMK', 'ALRS',
                 'MOEX', 'SMLT', 'MAGN', 'CHMF', 'CBOM', 'MTLRP', 'SNGS', 'BANEP', 'MTSS', 'IRAO',
                 'SNGSP', 'SELG', 'UPRO', 'RUAL', 'TRNFP', 'FEES', 'SGZH', 'BANE', 'PHOR', 'PIKK')

    # sec_codes = ('SBER',)  # Для тестов
    # Формат фьючерса: <Тикер>
    #                  <Месяц экспирации>
    #                  <Последняя цифра года> Месяц экспирации: 3-H, 6-M, 9-U, 12-Z
    # sec_codes = ('SiU3', 'RIU3')

    # Путь сохранения файлов для Windows/Linux
    datapath = os.path.join('..', '..', 'Data', '')

    # Если получаем данные внутри сессии, то не берем бары за дату незавершенной сессии
    skip_last_date = True

    # Если получаем данные, когда рынок не работает, то берем все бары
    # skip_last_date = False
    # TODO: Проверить информацию по тикерам прежде чем отправлять
    save_candels(class_code, sec_codes, four_price_doji=True)  # Дневные бары
    save_candels(class_code, sec_codes, 'M', 60,
                 skip_last_date=skip_last_date)  # часовые бары
    save_candels(class_code, sec_codes, 'M', 15,
                 skip_last_date=skip_last_date)  # 15-и минутные бары
    save_candels(class_code, sec_codes, 'M', 5,
                 skip_last_date=skip_last_date)  # 5-и минутные бары
    save_candels(class_code, sec_codes, 'M', 1,
                 skip_last_date=skip_last_date, four_price_doji=True)  # минутные бары

    qp_provider.close_connection()  # Перед выходом закрываем соединение и поток QuikPy
    print(f'Скрипт выполнен за {(time() - start_time):.2f}с')
