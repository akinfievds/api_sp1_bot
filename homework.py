import logging
import socket
import time
from os import getenv

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

PRAKTIKUM_TOKEN = getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
CHAT_ID = getenv('TELEGRAM_CHAT_ID')

API_URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'

REQUEST_HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
REQUEST_DESCR = ('Параметры запроса:\n'
                 'response = requests.get(url={url}, '
                 'headers={headers}, params={params})')
NETWORK_ERR_MSG = 'Сбой соединения. Ошибка: {error}\n'
NETWORK_FAILURE_MSG = NETWORK_ERR_MSG + REQUEST_DESCR
SERVER_ERR_MSG = 'Отказ сервера. Ошибка: {error}\n'
SERVER_FAILURE_MSG = SERVER_ERR_MSG + REQUEST_DESCR
STATUSES_VERDICTS = {
    'rejected': 'К сожалению в работе нашлись ошибки.',
    'reviewing': 'Работу взяли на проверку.',
    'approved': 'Ревьюеру всё понравилось, можно приступать'
                ' к следующему уроку.'
}
STATUS_SUMMARY = 'У вас проверили работу "{name}"!\n\n{verdict}'
STATUS_LOG = 'Работа {name}. Вердикт {verdict}'
STATUS_UNEXPECTED = 'Получен неожиданный статус: {status}'
SEND_MESSAGE_LOG = 'Бот пытается отправить сообщение "{message}"'

INITIALIZATION_LOG = '{:*^40}'.format(' Инициализация бота ')
SEND_ERROR_MESSAGE = 'Бот столкнулся с ошибкой: {error}'
SEND_ERROR_LOG = 'При выполнении {function} произошла ошибка {error}'


class UnexpectedStatus(Exception):
    pass


class ServerFailure(Exception):
    pass


logger = logging.getLogger(__file__)


def parse_homework_status(homework):
    status = homework['status']
    if status not in STATUSES_VERDICTS:
        raise UnexpectedStatus(
            STATUS_UNEXPECTED.format(status=status)
        )
    return STATUS_SUMMARY.format(
        name=homework['homework_name'],
        verdict=STATUSES_VERDICTS[status]
    )


def get_homework_statuses(current_timestamp):
    REQUEST_PARAMS = dict(url=API_URL, headers=REQUEST_HEADERS,
                          params={'from_date': current_timestamp})

    try:
        response = requests.get(**REQUEST_PARAMS)

    except requests.exceptions.RequestException as error:
        raise socket.error(
            NETWORK_FAILURE_MSG.format(error=error, **REQUEST_PARAMS)
        ) from error

    homework = response.json()
    for key in ['error', 'code']:
        if key in homework:
            raise ServerFailure(
                SERVER_FAILURE_MSG.format(
                    error=homework[key],
                    **REQUEST_PARAMS
                )
            )
    return homework


def send_message(message, bot_client):
    logger.info(msg=SEND_MESSAGE_LOG.format(message=message))
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    logger.debug(msg=INITIALIZATION_LOG)
    current_timestamp = int(time.time())

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get('homeworks'):
                send_message(
                    parse_homework_status(new_homework.get('homeworks')[0]),
                    bot
                )
            current_timestamp = new_homework.get(
                'current_date',
                current_timestamp
            )
            time.sleep(1200)

        except Exception as error:
            try:
                logging.error(
                    msg=SEND_ERROR_MESSAGE.format(error=error),
                    exc_info=True
                )
                send_message(SEND_ERROR_MESSAGE.format(error=error), bot)

            except Exception as error:
                logger.error(
                    msg=SEND_ERROR_LOG.format(
                        function=send_message.__name__,
                        error=error
                    ),
                    exc_info=True
                )
            time.sleep(5)


if __name__ == '__main__':
    LOG_FILE = __file__ + '.log'

    logging.basicConfig(
        filename=LOG_FILE,
        filemode='a',
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
