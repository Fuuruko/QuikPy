import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

# Работа с QUIK из Python через LUA скрипты QuikSharp
from QuikPy import QuikPy


def on_trans_reply(data):
    """Обработчик события ответа на транзакцию пользователя"""
    print('OnTransReply')
    print(data)

def on_order(data):
    """Обработчик события получения новой / изменения существующей заявки"""
    print('OnOrder')
    print(data)


def on_trade(data):
    """Обработчик события получения новой / изменения существующей сделки
    Не вызывается при закрытии сделки
    """
    print('OnTrade')
    print(data)


def on_futures_client_holding(data):
    """Обработчик события изменения позиции по срочному рынку"""
    print('OnFuturesClientHolding')
    print(data)


def on_depo_limit(data):
    """Обработчик события изменения позиции по инструментам"""
    print('OnDepoLimit')
    print(data)


def on_depo_limit_delete(data):
    """Обработчик события удаления позиции по инструментам"""
    print('OnDepoLimitDelete')
    print(data)


if __name__ == '__main__':
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK
    '''
    1. Ответ на транзакцию пользователя. Если транзакция выполняется из QUIK, то не вызывается
    2. Получение новой / изменение существующей заявки
    3. Получение новой / изменение существующей сделки
    4. Изменение позиции по срочному рынку
    5. Изменение позиции по инструментам
    6. Удаление позиции по инструментам
    '''
    qp_provider.OnTransReply = on_trans_reply
    qp_provider.OnOrder = on_order
    qp_provider.OnTrade = on_trade
    qp_provider.OnFuturesClientHolding = on_futures_client_holding
    qp_provider.OnDepoLimit = on_depo_limit
    qp_provider.OnDepoLimitDelete = on_depo_limit_delete

    class_code = 'SPBFUT'  # Код площадки
    sec_code = 'SiU3'  # Код тикера
    trans_id = 12345  # Номер транзакции
    price = 77000  # Цена входа/выхода
    quantity = 1  # Кол-во в лотах

    '''
    # Новая лимитная/рыночная заявка
    transaction = {  # Все значения должны передаваться в виде строк
        'TRANS_ID': str(trans_id),  # Номер транзакции задается клиентом
        'CLIENT_CODE': '',  # Код клиента. Для фьючерсов его нет
        'ACCOUNT': 'SPBFUT00PST',  # Счет
        'ACTION': 'NEW_ORDER',  # Тип заявки: Новая лимитная/рыночная заявка
        'CLASSCODE': class_code,  # Код площадки
        'SECCODE': sec_code,  # Код тикера
        'OPERATION': 'S',  # B = покупка, S = продажа
         Цена исполнения. Для рыночных фьючерсных заявок наихудшая цена в зависимости от направления.
         Для остальных рыночных заявок цена = 0
        'PRICE': str(price),  
        'QUANTITY': str(quantity),  # Кол-во в лотах
        'TYPE': 'L'}  # L = лимитная заявка (по умолчанию), M = рыночная заявка
    print(f'Новая лимитная/рыночная заявка отправлена на рынок: '
          f'{qp_provider.sendTransaction(transaction)}')
    '''

    '''
    # Удаление существующей лимитной заявки
    orderNum = 1234567890123456789  # 19-и значный номер заявки
    transaction = {
        'TRANS_ID': str(trans_id),  # Номер транзакции задается клиентом
        'ACTION': 'KILL_ORDER',  # Тип заявки: Удаление существующей заявки
        'CLASSCODE': class_code,  # Код площадки
        'SECCODE': sec_code,  # Код тикера
        'ORDER_KEY': str(orderNum)}  # Номер заявки
    print(f'Удаление заявки отправлено на рынок: '
          f'{qp_provider.sendTransaction(transaction)}')
    '''

    # Новая стоп заявка

    # Размер проскальзывания в шагах цены
    StopSteps = 10
    # Размер проскальзывания в деньгах
    slippage = float(qp_provider.getSecurityInfo(
        class_code, sec_code)['min_price_step']) * StopSteps
    # Целое значение проскальзывания мы должны отправлять без десятичных знаков
    if slippage.is_integer():
        slippage = int(slippage)  # поэтому, приводим такое проскальзывание к целому числу

    # Все значения должны передаваться в виде строк
    input('Transation\n')
    transaction = {
        'TRANS_ID': str(trans_id),  # Номер транзакции задается клиентом
        'CLIENT_CODE': '',  # Код клиента. Для фьючерсов его нет
        'ACCOUNT': 'SPBFUT00PST',  # Счет
        'ACTION': 'NEW_STOP_ORDER',  # Тип заявки: Новая стоп заявка
        'CLASSCODE': class_code,  # Код площадки
        'SECCODE': sec_code,  # Код тикера
        'OPERATION': 'B',  # B = покупка, S = продажа
        'PRICE': str(price),  # Цена исполнения
        'QUANTITY': str(quantity),  # Кол-во в лотах
        'STOPPRICE': str(price + slippage),  # Стоп цена исполнения
        'EXPIRY_DATE': 'GTC'}  # Срок действия до отмены
    print(f'Новая стоп заявка отправлена на рынок: '
          f'{qp_provider.sendTransaction(transaction)}')

    # Удаление существующей стоп заявки
    # orderNum = 1234567  # Номер заявки
    # transaction = {
    #     'TRANS_ID': str(trans_id),  # Номер транзакции задается клиентом
    #     'ACTION': 'KILL_STOP_ORDER',  # Тип заявки: Удаление существующей заявки
    #     'CLASSCODE': class_code,  # Код площадки
    #     'SECCODE': sec_code,  # Код тикера
    #     'STOP_ORDER_KEY': str(orderNum)}  # Номер заявки
    # print(f'Удаление стоп заявки отправлено на рынок: '
    #       f'{qp_provider.sendTransaction(transaction)}')

    input('Enter - отмена\n')  # Ждем исполнение заявки
    qp_provider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy
