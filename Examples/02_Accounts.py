# Для импортирования QuikPy
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

# Работа с QUIK из Python через LUA скрипты QuikSharp
from QuikPy import QuikPy


def get_all_accounts(prov):
    """Получение всех торговых счетов"""
    # Фирма для фьючерсов. Измените, если требуется,
    # на фирму, которую для фьючерсов поставил ваш брокер
    futures_firm_id = 'SPBFUT'
    """
    1. Список классов
    2. Все торговые счета
    3. Все денежные лимиты (остатки на счетах)
    4. Все лимиты по бумагам (позиции по инструментам)
    5. Все заявки
    6. Все стоп заявки
    """
    class_codes = prov.getClassesList()  # 1
    trade_accounts = prov.getTradeAccounts()  # 2
    money_limits = prov.getMoneyLimits()  # 3
    depo_limits = prov.get_depo_limits()  # 4
    orders = prov.get_orders()  # 5
    stop_orders = prov.get_stop_orders()  # 6

    # Удаляем последнюю запятую, разбиваем значения по запятой
    class_codes_list = class_codes[:-1].split(',')

    # Коды клиента / Фирмы / Счета
    # Пробегаемся по всем счетам
    for trd_acc in trade_accounts:
        firm_id = trd_acc['firmid']  # Фирма
        tr_acc_id = trd_acc['trdaccid']  # Счет

        # Уникальные коды клиента по фирме
        client_code = set()
        for money_limit in money_limits:
            if money_limit['firmid'] == firm_id:
                client_code.add(money_limit['client_code'])
        print(f'Код клиента {list(client_code)[0] if client_code else "не задан"}, '
              f'Фирма {firm_id}, Счет {tr_acc_id} ({trd_acc["description"]})')

        # Классы торгового счета.
        # Удаляем первую вертикальную черту, разбиваем значения по вертикальной черте
        trd_acc_cls_codes = trd_acc['class_codes'][1:].split('|')

        # Классы, которые есть и в списке и в торговом счете
        intersect_cls_codes = list(set(trd_acc_cls_codes).intersection(class_codes_list))

        # Классы
        for cls_code in intersect_cls_codes:
            cls_info = prov.getClassInfo(cls_code)  # Информация о классе
            print(f'- Класс {cls_code} ({cls_info["name"]}), Тикеров {cls_info["nsecs"]}')
            # Инструменты. Если выводить на экран, то занимают много места.
            # Список инструментов класса. Удаляем последнюю запятую, разбиваем значения по запятой
            # class_securities = qpProvider.getClassSecurities(classCode)[:-1].split(',')
            # print(f'  - Тикеры ({class_securities})')
        print()

        # Для фьючерсов свои расчеты
        if firm_id == futures_firm_id:
            # Лимиты
            limits = prov.getFuturesLimit(firm_id, tr_acc_id, 0, "SUR")
            print(f'- Фьючерсный лимит {limits["cbplimit"]} SUR')
            # Позиции
            futures_holdings = prov.getFuturesHolding()  # Все фьючерсные позиции
            # Активные фьючерсные позиции
            active_futures_holdings = []
            for fut_hold in futures_holdings:
                if fut_hold['totalnet'] != 0:
                    active_futures_holdings.append(fut_hold)
                    print(f'- Фьючерсная позиция {fut_hold["sec_code"]} '
                          f'{fut_hold["totalnet"]} @ '
                          f'{fut_hold["cbplused"]}')

        else:  # Для остальных фирм
            # Лимиты

            # Денежные лимиты по фирме
            firm_money_limits = []
            for money_limit in money_limits:
                if money_limit['firmid'] == firm_id:
                    firm_money_limits.append(money_limit)
                    limit_kind = money_limit['limit_kind']  # День лимита
                    print(f'- Денежный лимит {money_limit["tag"]} на T{limit_kind}: '
                          f'{money_limit["currentbal"]} {money_limit["currcode"]}')

                # Позиции
                firm_kind_depo_limits = []
                for depo_limit in depo_limits:
                    # Берем только открытые позиции по фирме и дню
                    if (depo_limit['firmid'] == firm_id
                            and depo_limit['limit_kind'] == limit_kind
                            and depo_limit['currentbal'] != 0):
                        firm_kind_depo_limits.append(depo_limit)

                # Пробегаемся по всем позициям
                for f_k_d_l in firm_kind_depo_limits:
                    sec_code = f_k_d_l["sec_code"]  # Код тикера
                    cls_code = prov.getSecurityClass(class_codes, sec_code)
                    entry_price = float(f_k_d_l["wa_position_price"])
                    # Последняя цена сделки
                    last_price = float(prov.getParamEx(cls_code, sec_code, 'LAST')['param_value'])
                    if cls_code == 'TQOB':  # Для рынка облигаций
                        last_price *= 10
                    print(f'- Позиция {cls_code}.{sec_code} '
                          f'{f_k_d_l["currentbal"]} @ '
                          f'{entry_price:.2f}/{last_price:.2f}')

        # Заявки
        print()
        firm_orders = []
        for order in orders:
            # Активные заявки по фирме
            # TODO: Необходимость (order['flags'] & 0b1 == 0b1)?
            if order['firmid'] == firm_id and order['flags'] & 0b1 == 0b1:
                firm_orders.append(order)
                # Заявка на покупку
                buy = order['flags'] & 0b100 != 0b100
                print(f'- Заявка номер {order["order_num"]} '
                      f'{"Покупка" if buy else "Продажа"} '
                      f'{order["class_code"]}.{order["sec_code"]} '
                      f'{order["qty"]} @ {order["price"]}')
        print()
        # Стоп заявки
        firm_stop_orders = []
        for stop_order in stop_orders:
            # Активные стоп заявки по фирме
            # TODO: Необходимость (order['flags'] & 0b1 == 0b1)?
            if stop_order['firmid'] == firm_id and stop_order['flags'] & 0b1 == 0b1:
                firm_stop_orders.append(stop_order)
                # Заявка на покупку
                buy = stop_order['flags'] & 0b100 != 0b100
                print(f'- Стоп заявка номер {stop_order["order_num"]} '
                      f'{"Покупка" if buy else "Продажа"} '
                      f'{stop_order["class_code"]}.{stop_order["sec_code"]} '
                      f'{stop_order["qty"]} @ {stop_order["price"]}')
        print()


def get_account(prov, client_code='', firm_id='SPBFUT', trd_acc_id='SPBFUT00PST',
                limit_kind=0, currency_code='SUR', futures=True):
    """Получение торгового счета. По умолчанию выдается счет срочного рынка"""
    class_codes = prov.getClassesList()  # Список классов
    money_limits = prov.getMoneyLimits()  # Все денежные лимиты (остатки на счетах)

    # Все лимиты по бумагам (позиции по инструментам)
    depo_limits = prov.get_depo_limits()
    orders = prov.get_orders()  # Все заявки
    stop_orders = prov.get_stop_orders()  # Все стоп заявки

    print(f'Код клиента {client_code}, Фирма {firm_id}, '
          f'Счет {trd_acc_id}, T{limit_kind}, {currency_code}')

    if futures:  # Для фьючерсов свои расчеты
        # input(prov.getFuturesLimit('SPBFUT589000', trd_acc_id, 0, "SUR"))
        fut_limits = prov.getFuturesLimit(firm_id, trd_acc_id, 0, "SUR")["cbplimit"]
        print(f'- Фьючерсный лимит {fut_limits} SUR')
        futures_holdings = prov.getFuturesHolding()  # Все фьючерсные позиции

        # Активные фьючерсные позиции
        active_futures_holdings = []
        for fut_hold in futures_holdings:
            if fut_hold['totalnet'] != 0:
                active_futures_holdings.append(fut_hold)
                print(f'- Фьючерсная позиция {fut_hold["sec_code"]} '
                      f'{fut_hold["totalnet"]} @ {fut_hold["cbplused"]}')

    else:  # Для остальных фирм
        acc_money_limit = []
        for money_limit in money_limits:
            # Берем только открытые позиции по фирме и дню
            if (money_limit['client_code'] == client_code  # Выбираем по коду клиента
                    and money_limit['firmid'] == firm_id  # Фирме
                    and money_limit['limit_kind'] == limit_kind  # Дню лимита
                    and money_limit["currcode"] == currency_code):  # Валюте
                acc_money_limit.append(money_limit)

        acc_money_limit = acc_money_limit[0]
        print(f'- Денежный лимит {acc_money_limit["currentbal"]}')

        acc_depo_limits = []
        for depo_limit in depo_limits:
            # Берем только открытые позиции по фирме и дню
            if (depo_limit['client_code'] == client_code  # Выбираем по коду клиента
                    and depo_limit['firmid'] == firm_id  # Фирме
                    and depo_limit['limit_kind'] == limit_kind  # Дню лимита
                    and depo_limit["currentbal"] == 0):  # Позиции открытые только по фирме и дню
                acc_depo_limits.append(depo_limit)

        for firm_kind_depo_limit in acc_depo_limits:  # Пробегаемся по всем позициям
            sec_code = firm_kind_depo_limit["sec_code"]  # Код тикера
            entry_price = float(firm_kind_depo_limit["wa_position_price"])
            class_code = prov.getSecurityClass(class_codes, sec_code)
            # Последняя цена сделки
            last_price = float(prov.getParamEx(class_code, sec_code, 'LAST')['param_value'])
            if class_code == 'TQOB':  # Для рынка облигаций
                last_price *= 10

            print(f'- Позиция {class_code}.{sec_code} '
                  f'{firm_kind_depo_limit["currentbal"]} '
                  f'@ {entry_price:.2f}/{last_price:.2f}')
    print()
    acc_orders = []
    for order in orders:
        # Берем только открытые позиции по фирме и дню
        if ((order['client_code'] == client_code or client_code == '')  # Выбираем по коду клиента
                and order['firmid'] == firm_id  # Фирме
                and order['account'] == trd_acc_id  # Дню лимита
                and order['flags'] & 0b1 == 0b1):  # Валюте
            acc_orders.append(order)
            # Заявка на покупку
            buy = order['flags'] & 0b100 != 0b100
            print(f'- Заявка номер {order["order_num"]} '
                  f'{"Покупка" if buy else "Продажа"} '
                  f'{order["class_code"]}.{order["sec_code"]} '
                  f'{order["qty"]} @ {order["price"]}')

    print()
    acc_stop_orders = []
    for stop_order in stop_orders:
        # Берем только открытые позиции по фирме и дню
        if ((stop_order['client_code'] == client_code or client_code == '')  # Выбираем по коду клиента
                and stop_order['firmid'] == firm_id  # Фирме
                and stop_order['account'] == trd_acc_id  # Счету
                and stop_order['flags'] & 0b1 == 0b1):  # Активные стоп заявки
            acc_stop_orders.append(order)
            # Заявка на покупку
            buy = order['flags'] & 0b100 != 0b100
            print(f'- Стоп заявка номер {order["order_num"]} '
                  f'{"Покупка" if buy else "Продажа"} '
                  f'{order["class_code"]}.{order["sec_code"]} '
                  f'{order["qty"]} @ {order["price"]}')
    print()


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    # Получаем все счета. По ним можно будет сформировать список счетов для торговли
    get_all_accounts(qp_provider)
    print()
    # Российские фьючерсы и опционы (счет по умолчанию)
    get_account(qp_provider, firm_id='SPBFUT589000', trd_acc_id='SPBFUTK5GUE')
    # По списку полученных счетов обязательно проверьте каждый!
    # get_account('<Код клиента>', '<Код фирмы>', '<Счет>',
    #             <Номер дня лимита> , '<Валюта>',
    #             <Счет фьючерсов=True, иначе=False>)

    # Выход
    qp_provider.close_connection()  # Перед выходом закрываем соединение и поток QuikPy
