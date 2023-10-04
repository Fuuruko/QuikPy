# Обращаться к LUA скриптам QuikSharp будем через соединения
from socket import socket, AF_INET, SOCK_STREAM
# Результат работы функций обратного вызова будем получать в отдельном потоке
from threading import current_thread, Thread
# Принимать данные в QUIK будем через JSON
from json import loads as json_loads, dumps as json_dumps
# Multiple times faster than standard json lib
# from orjson import loads as json_loads, dumps as json_dumps, OPT_APPEND_NEWLINE
# Ошибка декодирования JSON
from json.decoder import JSONDecodeError
from sys import _getframe


class QuikPy:
    """Работа с Quik из Python через LUA скрипты QuikSharp

        https://github.com/finsight/QUIKSharp/tree/master/src/QuikSharp/lua
        На основе Документации по языку LUA в QUIK из https://arqatech.com/ru/support/files/
    """

    BUFFER_SIZE = 1048576  # Размер буфера приема в байтах (1 МБайт)

    @staticmethod
    def _get_cmd(up=2):
        """
        Возращает имя ф-ции вызывающей process_request
        Имя ф-ции является коммандой вызываемой в Lua
        """
        return _getframe(up).f_code.co_name

    def default_handler(self, data):
        """Пустой обработчик события по умолчанию.

        Можно заменить на пользовательский
        """
        pass

    def _callback_handler(self):
        """Поток обработки результатов функций обратного вызова"""
        thread = current_thread()
        fragments = []
        while getattr(thread, 'process', True):
            while True:
                fragment = self.callbacks.recv(self.BUFFER_SIZE)
                # Декодирование из Windows-1251
                fragments.append(fragment.decode('cp1251'))
                # Если в принятом фрагменте данных меньше чем размер буфера
                # то, возможно, это был последний фрагмент, выходим из чтения буфера
                if len(fragment) < self.BUFFER_SIZE:
                    break
            data = ''.join(fragments)
            # Одновременно могут прийти несколько функций обратного вызова, разбираем их по одной
            data_list = data.split('\n')
            # Если последнюю строку не сможем разобрать, то занесем ее сюда
            fragments = []
            # Пробегаемся по всем функциям обратного вызова
            for data in data_list:
                if not data:
                    continue
                try:
                    # Преобразуем из формата JSON
                    data = json_loads(data)
                # Если разобрать не смогли (пришла не вся строка)
                except JSONDecodeError:
                    fragments.append(data)
                    # Т.к. неполной может быть только последняя строка,
                    # то выходим из разбора функций обратного выходва
                    break
                # Вызов ф-ции обратного вызова
                eval(f'self.{data["cmd"]}(data["data"])')

        self.callbacks.close()

    def _process_request(self, trans_id, *data_args):
        """Отправляем запрос в QUIK, получаем ответ из QUIK"""
        # TODO: delete if/else and remain (data_args = [arg for arg in data_args if arg != ''] or '')
        if len(data_args) == 1:
            data_args = data_args[0]
        else:
            data_args = [arg for arg in data_args if arg != ''] or ''

        # TODO: Delete (id, t) as useless?
        request = {'data': data_args,
                   'cmd': self._get_cmd(),
                   'id': trans_id,
                   't': ''}

        # Переводим в формат JSON
        # NOTE: 5x faster without decode/encode, but without russian language
        # raw_data = json_dumps(request, option=OPT_APPEND_NEWLINE).decode('utf-8').encode('cp1251')
        raw_data = ''.join([json_dumps(request),'\n']).encode('cp1251')

        # Отправляем запрос в QUIK
        self.socket_req.sendall(raw_data)

        fragments = []
        # Пока фрагменты есть в буфере
        while True:
            fragment = self.socket_req.recv(self.BUFFER_SIZE)
            fragments.append(fragment.decode('cp1251'))
            if len(fragment) < self.BUFFER_SIZE:
                data = ''.join(fragments)
                try:
                    # Преобразуем из формата JSON
                    return json_loads(data)['data']
                # Бывает ситуация, когда данных приходит меньше, но это еще не конец данных
                # Если это еще не конец данных то ждем фрагментов в буфере дальше
                except JSONDecodeError:
                    pass

    def __init__(self, host='127.0.0.1', requests_port=34130, callbacks_port=34131):
        """Инициализация"""
        """Ф-ции обратного вызова
            1. Новая фирма
            2. Получение обезличенной сделки
            3. Получение новой / изменение существующей сделки
            4. Получение новой / изменение существующей заявки
            5. Изменение позиций по счету
            6. Изменение ограничений по срочному рынку
            7. Удаление ограничений по срочному рынку
            8. Изменение позиции по срочному рынку
            9. Изменение денежной позиции
            10. Удаление денежной позиции
            11. Изменение позиций по инструментам
            12. Удаление позиции по инструментам
            13. Изменение денежных средств
            14. Получение новой / изменение существующей стоп-заявки
            15. Ответ на транзакцию пользователя
            16. Изменение текущих параметров
            17. Изменение стакана котировок
            18. Отключение терминала от сервера QUIK
            19. Соединение терминала с сервером QUIK
            20. Закрытие терминала QUIK
            21. Остановка LUA скрипта в терминале QUIK / закрытие терминала QUIK
            22. Запуск LUA скрипта в терминале QUIK
            23. Получение новой свечки
            24. Сообщение об ошибке

            Не реализовано
            OnNegDeal - 25. Получение новой / изменение существующей внебиржевой заявки
            OnNegTrade - 26. Получение новой / изменение существующей сделки для исполнения
            OnCleanUp - 27. Смена сервера QUIK / Пользователя / Сессии
        """
        (
            self.OnFirm,  # 1
            self.OnAllTrade,  # 2
            self.OnTrade,  # 3
            self.OnOrder,  # 4
            self.OnAccountBalance,  # 5
            self.OnFuturesLimitChange,  # 6
            self.OnFuturesLimitDelete,  # 7
            self.OnFuturesClientHolding,  # 8
            self.OnMoneyLimit,  # 9
            self.OnMoneyLimitDelete,  # 10
            self.OnDepoLimit,  # 11
            self.OnDepoLimitDelete,  # 12
            self.OnAccountPosition,  # 13
            self.OnStopOrder,  # 14
            self.OnTransReply,  # 15
            self.OnParam,  # 16
            self.OnQuote,  # 17
            self.OnDisconnected,  # 18
            self.OnConnected,  # 19
            self.OnClose,  # 20
            self.OnStop,  # 21
            self.OnInit,  # 22
            self.OnNewCandle,  # 23
            self.OnError,  # 24
        ) = (self.default_handler,) * 24

        # IP адрес или название хоста
        # Порт для отправки запросов и получения ответов
        # Порт для функций обратного вызова
        self.host = host
        self.req_port = requests_port
        self.cb_port = callbacks_port

        # Соединение для запросов и обратного вызова
        self.socket_req = socket(AF_INET, SOCK_STREAM)
        self.callbacks = socket(AF_INET, SOCK_STREAM)

        self.socket_req.connect((self.host, self.req_port))
        self.callbacks.connect((self.host, self.cb_port))

        # Поток обработки функций обратного вызова
        self.callback_thread = Thread(target=self._callback_handler, name='CallbackThread')
        self.callback_thread.start()

    def __enter__(self):
        """Вход в класс, например, с with"""
        return self

    # Фукнции связи с QuikSharp

    def ping(self, trans_id=0):
        """Проверка соединения. Отправка ping. Получение pong"""
        return self._process_request(trans_id, 'Ping')

    def echo(self, message: str, trans_id=0):
        """Эхо. Отправка и получение одного и того же сообщения"""
        return self._process_request(trans_id, message)

    def divide_string_by_zero(self, trans_id=0):
        """Тест обработки ошибок. Выполняется деление на 0 с выдачей ошибки"""
        return self._process_request(trans_id)

    def is_quik(self, trans_id=0):
        """Скрипт запущен в Квике"""
        return self._process_request(trans_id)

    # 2.1 Сервисные функции

    def isConnected(self, trans_id=0):  # 1
        """Состояние подключения терминала к серверу QUIK.

        Возвращает 1 - подключено / 0 - не подключено
        """
        return self._process_request(trans_id)

    def getScriptPath(self, trans_id=0):  # 2
        """Путь скрипта без завершающего обратного слэша"""
        return self._process_request(trans_id)

    def getInfoParam(self, params: str, trans_id=0):  # 3
        """Значения параметров информационного окна

            params:
            VERSION             Версия программы
            TRADEDATE           Дата торгов
            SERVERTIME          Время сервера
            LASTRECORDTIME      Время последней записи
            NUMRECORDS          Число записей
            LASTRECORD          Последняя запись
            LATERECORD          Отставшая запись
            CONNECTION          Соединение
            IPADDRESS           IP-адрес сервера
            IPPORT              Порт сервера
            IPCOMMENT           Описание соединения
            SERVER              Описание сервера
            SESSIONID           Идентификатор сессии
            USER                Пользователь
            USERID              ID пользователя
            ORG                 Организация
            MEMORY              Занято памяти
            LOCALTIME           Текущее время
            CONNECTIONTIME      Время на связи
            MESSAGESSENT        Передано сообщений
            ALLSENT             Передано всего байт
            BYTESSENT           Передано полезных байт
            BYTESPERSECSENT     Передано за секунду
            MESSAGESRECV        Принято сообщений
            BYTESRECV           Принято полезных байт
            ALLRECV             Принято всего байт
            BYTESPERSECRECV     Принято за секунду
            AVGSENT             Средняя скорость передачи
            AVGRECV             Средняя скорость приема
            LASTPINGTIME        Время последней проверки связи
            LASTPINGDURATION    Задержка данных при обмене с сервером
            AVGPINGDURATION     Средняя задержка данных
            MAXPINGTIME         Время максимальной задержки
            MAXPINGDURATION     Максимальная задержка данных
        """
        return self._process_request(trans_id, params)

    # message - 4. Сообщение в терминале QUIK. Реализовано в виде 3-х отдельных функций в QuikSharp

    def sleep(self, time, trans_id=0):  # 5
        """Приостановка скрипта. Время в миллисекундах"""
        return self._process_request(trans_id, time)

    def getWorkingFolder(self, trans_id=0):  # 6
        """Путь к info.exe, исполняющего скрипт без завершающего обратного слэша"""
        return self._process_request(trans_id)

    def debug_message(self, message: str, trans_id=0):  # 7
        """Вывод отладочной информации. Можно посмотреть с помощью DebugView"""
        return self._process_request(trans_id, message)

    # sysdate - 8. Системные дата и время
    # isDarkTheme - 9. Тема оформления. true - тёмная, false - светлая

    # Сервисные функции QuikSharp

    def message(self, message: str, trans_id=0):  # В QUIK LUA message icon_type=1
        """Отправка информационного сообщения в терминал QUIK"""
        return self._process_request(trans_id, message)

    def warning_message(self, message: str, trans_id=0):  # В QUIK LUA message icon_type=2
        """Отправка сообщения с предупреждением в терминал QUIK"""
        return self._process_request(trans_id, message)

    def error_message(self, message: str, trans_id=0):  # В QUIK LUA message icon_type=3
        """Отправка сообщения об ошибке в терминал QUIK"""
        return self._process_request(trans_id, message)

    # 3.1. Функции для обращения к строкам произвольных таблиц

    """
    getItem           Строка таблицы
    getOrderByNumber  Заявка
    getNumberOf       Кол-во записей в таблице
    SearchItems       Быстрый поиск по таблице заданной функцией поиска
    """

    # Функции для обращения к строкам произвольных таблиц QuikSharp

    def getTradeAccounts(self, trans_id=0):
        """Торговые счета, у которых указаны поддерживаемые классы инструментов"""
        return self._process_request(trans_id)

    def getTradeAccount(self, class_code: str, trans_id=0):
        """Торговый счет для запрашиваемого кода класса"""
        return self._process_request(trans_id, class_code)

    def get_orders(self, class_code: str = '', sec_code: str = '', trans_id=0):
        """Таблица заявок (вся) / (по инструменту(оба кода должны присутствовать))"""
        return self._process_request(trans_id, class_code, sec_code)

    def get_order_by_num(self, order_id: int, trans_id=0):
        """Заявка по номеру"""
        return self._process_request(trans_id, order_id)

    def get_order_by_cls_num(self, class_code: str, order_id: int, trans_id=0):
        """Заявка по классу инструмента и номеру"""
        return self._process_request(trans_id, class_code, order_id)

    def getOrder_by_ID(self, class_code: str, sec_code: str, order_trans_id: int, trans_id=0):
        """Заявка по инструменту и Id транзакции"""
        return self._process_request(trans_id, class_code, sec_code, order_trans_id)

    def getMoneyLimits(self, trans_id=0):
        """Все денежные лимиты"""
        return self._process_request(trans_id)

    def getClientCode(self, trans_id=0):
        """Основной (первый) код клиента"""
        return self._process_request(trans_id)

    def getClientCodes(self, trans_id=0):
        """Все коды клиента"""
        return self._process_request(trans_id)

    def get_depo_limits(self, sec_code: str = '', trans_id=0):
        """Лимиты по бумагам (всем) / (по инструменту)"""
        return self._process_request(trans_id, sec_code)

    def get_trades(self, class_code: str = '', sec_code: str = '', trans_id=0):
        """Таблица сделок (вся) / (по инструменту(оба кода должны присутствовать))"""
        return self._process_request(trans_id, class_code, sec_code)

    def get_Trades_by_OrderNumber(self, order_num: int, trans_id=0):
        """Таблица сделок по номеру заявки"""
        return self._process_request(trans_id, order_num)

    def get_stop_orders(self, class_code: str = '', sec_code: str = '', trans_id=0):
        """Стоп заявки (все) / (по инструменту(оба кода должны присутствовать))"""
        return self._process_request(trans_id, class_code, sec_code)

    def get_all_trades(self, class_code: str = '', sec_code: str = '', trans_id=0):
        """Таблица обезличенных сделок (вся) / (по инструменту(оба кода должны присутствовать))"""
        return self._process_request(trans_id, class_code, sec_code)

    # 3.2 Функции для обращения к спискам доступных параметров

    def getClassesList(self, trans_id=0):  # 1
        """Список классов"""
        return self._process_request(trans_id)

    def getClassInfo(self, class_code: str, trans_id=0):  # 2
        """Информация о классе"""
        return self._process_request(trans_id, class_code)

    def getClassSecurities(self, class_code: str, trans_id=0):  # 3
        """Список инструментов класса"""
        return self._process_request(trans_id, class_code)

    # Функции для обращения к спискам доступных параметров QuikSharp

    def getOptionBoard(self, class_code: str, sec_code: str, trans_id=0):
        """Доска опционов"""
        return self._process_request(trans_id, class_code, sec_code)

    # 3.3 Функции для получения информации по денежным средствам

    def getMoney(self, client_code: str, firm_id: str, tag: str, curr_code: str, trans_id=0):  # 1
        """Денежные позиции"""
        return self._process_request(trans_id, client_code, firm_id, tag, curr_code)

    def getMoneyEx(self, firm_id: str, client_code: str, tag: str, curr_code: str, limit_kind: int, trans_id=0):  # 2
        """Денежные позиции указанного типа"""
        return self._process_request(trans_id, firm_id, client_code, tag, curr_code, limit_kind)

    # 3.4 Функции для получения позиций по инструментам

    def getDepo(self, client_code: str, firm_id: str, sec_code: str, trd_acc_id: str, trans_id=0):  # 1
        """Позиции по инструментам"""
        return self._process_request(trans_id, client_code, firm_id, sec_code, trd_acc_id)

    def getDepoEx(self, firm_id: str, client_code: str, sec_code: str,
                  trd_acc_id: str, limit_kind: int, trans_id=0):  # 2
        """Позиции по инструментам указанного типа"""
        return self._process_request(trans_id, firm_id, client_code,
                                     sec_code, trd_acc_id, limit_kind)

    # 3.5 Функция для получения информации по фьючерсным лимитам

    def getFuturesLimit(self, firm_id: str, trd_acc_id: str, limit_type: int, curr_code: str, trans_id=0):  # 1
        """Фьючерсные лимиты"""
        return self._process_request(trans_id, firm_id, trd_acc_id, limit_type, curr_code)

    # Функция для получения информации по фьючерсным лимитам QuikSharp

    def getFuturesClientLimits(self, trans_id=0):
        """Все фьючерсные лимиты"""
        return self._process_request(trans_id)

    # 3.6 Функция для получения информации по фьючерсным позициям

    def getFuturesHolding(self, firm_id: str = '', trd_acc_id: str = '', sec_code: str = '',
                          position_type: int = '', trans_id=0):  # 1
        """Фьючерсные позиции"""
        return self._process_request(trans_id, firm_id, trd_acc_id, sec_code, position_type)

    # Функция для получения информации по фьючерсным позициям QuikSharp

    def getFuturesClientHoldings(self, trans_id=0):
        """Все фьючерсные позиции"""
        return self._process_request(trans_id)

    # 3.7 Функция для получения информации по инструменту

    def getSecurityInfo(self, class_code: str, sec_code: str, trans_id=0):  # 1
        """Информация по инструменту"""
        return self._process_request(trans_id, class_code, sec_code)

    # Функция для получения информации по инструменту QuikSharp

    def getSecurityInfoBulk(self, class_codes, sec_codes, trans_id=0):
        """Информация по инструментам"""
        return self._process_request(trans_id, class_codes, sec_codes)

    def getSecurityClass(self, classes_list, sec_code, trans_id=0):
        """Класс по коду инструмента из заданных классов"""
        return self._process_request(trans_id, classes_list, sec_code)

    # 3.8 Функция для получения даты торговой сессии

    # getTradeDate - 1. Дата текущей торговой сессии

    # 3.9 Функция для получения стакана по указанному классу и инструменту

    def GetQuoteLevel2(self, class_code: str, sec_code: str, trans_id=0):  # 1
        """Стакан по классу и инструменту"""
        return self._process_request(trans_id, class_code, sec_code)

    # 3.10 Функции для работы с графиками

    # getLinesCount - 1. Кол-во линий в графике

    def get_num_candles(self, tag: str, trans_id=0):  # 2
        """Кол-во свечей по тэгу"""
        return self._process_request(trans_id, tag)

    # getCandlesByIndex - 3. Информация о свечках (реализовано в get_candles)
    # CreateDataSource - 4. Создание источника данных c функциями
    #                       (реализовано в get_candles_ds)
    # - SetUpdateCallback - Привязка функции обратного вызова на изменение свечи
    # - O, H, L, C, V, T - Функции получения цен, объемов и времени
    # - Size - Функция кол-ва свечек в источнике данных
    # - Close - Функция закрытия источника данных. Терминал прекращает получать данные с сервера
    # - SetEmptyCallback - Функция сброса функции обратного вызова на изменение свечи

    # Функции для работы с графиками QuikSharp

    def get_candles(self, tag: str, line: int, first_candle: int, count: int, trans_id=0):
        """Свечки по идентификатору графика"""
        return self._process_request(trans_id, tag, line, first_candle, count)

    # ichechet - Добавлен выход по таймауту
    def get_candles_ds(self, class_code: str, sec_code: str, interval: int, count: int, trans_id=0):
        """Свечки"""
        return self._process_request(trans_id, class_code, sec_code, interval, count)

    def subs_to_candles(self, class_code: str, sec_code: str, interval: int, trans_id=0):
        """Подписка на свечки"""
        return self._process_request(trans_id, class_code, sec_code, interval)

    def is_subs(self, class_code: str, sec_code: str, interval: int, trans_id=0):
        """Есть ли подписка на свечки"""
        return self._process_request(trans_id, class_code, sec_code, interval)

    def unsubs_from_candles(self, class_code: str, sec_code: str, interval: int, trans_id=0):
        """Отмена подписки на свечки"""
        return self._process_request(trans_id, class_code, sec_code, interval)

    # 3.11 Функции для работы с заявками

    def sendTransaction(self, transaction: dict, trans_id=0):  # 1
        """Отправка транзакции в торговую систему"""
        return self._process_request(trans_id, transaction)

    # CalcBuySell - 2. Максимальное кол-во лотов в заявке

    # 3.12 Функции для получения значений таблицы "Текущие торги"

    def getParamEx(self, class_code: str, sec_code: str, param_name: str, trans_id=0):  # 1
        """Таблица текущих торгов"""
        return self._process_request(trans_id, class_code, sec_code, param_name)

    def getParamEx2(self, class_code: str, sec_code: str, param_name: str, trans_id=0):  # 2
        """Таблица текущих торгов по инструменту с возможностью отказа от получения"""
        return self._process_request(trans_id, class_code, sec_code, param_name)

    # Функция для получения значений таблицы "Текущие торги" QuikSharp

    def getParamEx2Bulk(self, class_codes, sec_codes, param_names, trans_id=0):
        """Таблица текущих торгов по инструментам с возможностью отказа от получения"""
        return self._process_request(trans_id, class_codes, sec_codes, param_names)

    # 3.13 Функции для получения параметров таблицы "Клиентский портфель"

    def getPortfolioInfo(self, firm_id: str, client_code: str, trans_id=0):  # 1
        """Клиентский портфель"""
        return self._process_request(trans_id, firm_id, client_code)

    def getPortfolioInfoEx(self, firm_id: str, client_code: str, limit_kind: int, trans_id=0):  # 2
        """Клиентский портфель по сроку расчетов"""
        return self._process_request(trans_id, firm_id, client_code, limit_kind)

    # 3.14 Функции для получения параметров таблицы "Купить/Продать"

    # getBuySellInfo - 1. Параметры таблицы купить/продать
    # getBuySellInfoEx - 2. Параметры таблицы купить/продать с дополнительными полями вывода

    # 3.15 Функции для работы с таблицами Рабочего места QUIK
    """
        AddColumn - 1. Добавление колонки в таблицу
        AllocTable - 2. Структура, описывающая таблицу
        Clear - 3. Удаление содержимого таблицы
        CreateWindow - 4. Создание окна таблицы
        DeleteRow - 5. Удаление строки из таблицы
        DestroyTable - 6. Закрытие окна таблицы
        InsertRow - 7. Добавление строки в таблицу
        IsWindowClosed - 8. Закрыто ли окно с таблицей
        GetCell - 9. Данные ячейки таблицы
        GetTableSize - 10. Кол-во строк и столбцов таблицы
        GetWindowCaption - 11. Заголовок окна таблицы
        GetWindowRect - 12. Координаты верхнего левого и правого нижнего углов таблицы
        SetCell - 13. Установка значения ячейки таблицы
        SetWindowCaption - 14. Установка заголовка окна таблицы
        SetWindowPos - 15. Установка верхнего левого угла, и размеры таблицы
        SetTableNotificationCallback - 16. Установка функции обратного вызова
                                      для обработки событий в таблице
        RGB - 17. Преобразование каждого цвета в одно число для функци SetColor
        SetColor - 18. Установка цвета ячейки, столбца или строки таблицы
        Highlight - 19. Подсветка диапазона ячеек цветом фона и цветом текста
                   на заданное время с плавным затуханием
        SetSelectedRow - 20. Выделение строки таблицы
    """

    # 3.16 Функции для работы с метками

    def addLabel(self, price, cur_date, cur_time, qty, path,
                 label_id, alignment, background, trans_id=0):  # 1
        """Добавление метки на график"""
        return self._process_request(trans_id, price, cur_date, cur_time, qty,
                                     path, label_id, alignment, background)

    def delLabel(self, chart_tag, label_id, trans_id=0):  # 2
        """Удаление метки с графика"""
        return self._process_request(trans_id, chart_tag, label_id)

    def delAllLabels(self, chart_tag, trans_id=0):  # 3
        """Удаление всех меток с графика"""
        return self._process_request(trans_id, chart_tag)

    def getLabelParams(self, chart_tag, label_id, trans_id=0):  # 4
        """Получение параметров метки"""
        return self._process_request(trans_id, chart_tag, label_id)

    # SetLabelParams - 5. Установка параметров метки

    # 3.17 Функции для заказа стакана котировок

    def subs_level_II_quotes(self, class_code: str, sec_code: str, trans_id=0):  # 1
        """Подписка на стакан по Классу|Коду бумаги"""
        return self._process_request(trans_id, class_code, sec_code)

    def unsubs_level_II_quotes(self, class_code: str, sec_code: str, trans_id=0):  # 2
        """Отмена подписки на стакан по Классу|Коду бумаги"""
        return self._process_request(trans_id, class_code, sec_code)

    def is_subs_level_II_quotes(self, class_code: str, sec_code: str, trans_id=0):  # 3
        """Есть ли подписка на стакан по Классу|Коду бумаги"""
        return self._process_request(trans_id, class_code, sec_code)

    # 3.18 Функции для заказа параметров Таблицы текущих торгов

    def paramRequest(self, class_code: str, sec_code: str, param_name: str, trans_id=0):  # 1
        """Заказ получения таблицы текущих торгов по инструменту"""
        return self._process_request(trans_id, class_code, sec_code, param_name)

    def cancelParamRequest(self, class_code: str, sec_code: str, param_name: str, trans_id=0):  # 2
        """Отмена заказа получения таблицы текущих торгов по инструменту"""
        return self._process_request(trans_id, class_code, sec_code, param_name)

    # Функции для заказа параметров Таблицы текущих торгов QuikSharp

    def paramRequestBulk(self, class_codes, sec_codes, param_names, trans_id=0):
        """Заказ получения таблицы текущих торгов по инструментам"""
        return self._process_request(trans_id, class_codes, sec_codes, param_names)

    def cancelParamRequestBulk(self, class_codes, sec_codes, param_names, trans_id=0):
        """Отмена заказа получения таблицы текущих торгов по инструментам"""
        return self._process_request(trans_id, class_codes, sec_codes, param_names)

    # 3.19 Функции для получения информации по единой денежной позиции

    def GetTrdAccByClientCode(self, firm_id: str, client_code: str, trans_id=0):  # 1
        """Торговый счет срочного рынка по коду клиента фондового рынка"""
        return self._process_request(trans_id, firm_id, client_code)

    def GetClientCodeByTrdAcc(self, firm_id: str, trd_acc_id: str, trans_id=0):  # 2
        """Код клиента фондового рынка с единой денежной позицией по торговому счету срочного рынка"""
        return self._process_request(trans_id, firm_id, trd_acc_id)

    # Выход и закрытие

    def close_connection(self):
        """Закрытие соединения для запросов и потока обработки функций обратного вызова"""
        self.socket_req.close()  # Закрываем соединение для запросов
        # Поток обработки функций обратного вызова больше не нужен
        self.callback_thread.process = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из класса, например, с with"""
        # Закрываем соединение для запросов и поток обработки функций обратного вызова
        self.close_connection()

    def __del__(self):
        # Закрываем соединение для запросов и поток обработки функций обратного вызова
        self.close_connection()
