import logging
import sys
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


class UnexpectedStatus(Exception):
    pass


class ServerFailure(Exception):
    pass


logger = logging.getLogger(__file__)


def parse_homework_status(homework):
    if homework['status'] not in STATUSES_VERDICTS:
        raise UnexpectedStatus(
            STATUS_UNEXPECTED.format(status=homework['status'])
        )
    return STATUS_SUMMARY.format(
        name=homework['homework_name'],
        verdict=STATUSES_VERDICTS[homework['status']]
    )


def get_homework_statuses(current_timestamp):
    REQUEST_PARAMS = dict(url=API_URL, headers=REQUEST_HEADERS,
                          params={'from_date': current_timestamp})

    try:
        response = requests.get(**REQUEST_PARAMS)

    except requests.exceptions.RequestException as error:
        tb = sys.exc_info()[2]
        raise KeyError(
            NETWORK_FAILURE_MSG.format(error=error, **REQUEST_PARAMS)
        ).with_traceback(tb)

    homework = response.json()
    if 'error' in homework or 'code' in homework:
        errors = [homework.get('error'), homework.get('code')]
        for error in errors:
            if error:
                raise ServerFailure(
                    SERVER_FAILURE_MSG.format(errors=error, **REQUEST_PARAMS)
                )
    return homework


def send_message(message, bot_client):
    logger.info(msg=SEND_MESSAGE_LOG.format(message=message))
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    logger.debug(msg='{:*^40}'.format(' Инициализация бота '))
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
                err_msg = f'Бот столкнулся с ошибкой: {error}'
                logging.error(msg=err_msg, exc_info=True)
                send_message(err_msg, bot)

            except Exception as error:
                logger.error(
                    msg=(f'При выполнении {send_message.__name__} '
                         f'произошла ошибка {error}'),
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
