import logging
from os import getenv
from random import randint
import time

from dotenv import load_dotenv
import requests
from telegram import Bot

load_dotenv()

TESTING = True

PRAKTIKUM_TOKEN = getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
CHAT_ID = getenv('TELEGRAM_CHAT_ID')
API_URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
LOG_FILE = 'homework.log'
HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
STATUSES_VERDICTS = {
    'rejected': 'К сожалению в работе нашлись ошибки.',
    'reviewing': 'Работу взяли на проверку.',
    'approved': ('Ревьюеру всё понравилось, можно приступать'
                 ' к следующему уроку.')
}

logging.basicConfig(
    level=logging.DEBUG,
    filename=LOG_FILE,
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)


class UnexpectedStatus(Exception):
    pass


class NetworkFailure(Exception):
    pass


class ServerFailure(Exception):
    pass


def parse_homework_status(homework):
    SUMMARY = 'У вас проверили работу "{name}"!\n\n{verdict}'
    LOG = 'Работа {name}. Вердикт {verdict}'

    name, status = homework['homework_name'], homework['status']
    if status not in STATUSES_VERDICTS:
        raise UnexpectedStatus(f'Получен неожиданный статус: {status}')
    verdict = STATUSES_VERDICTS[status]
    logger.debug(msg=LOG.format(name=name, verdict=verdict))
    return SUMMARY.format(name=name, verdict=verdict)


def get_homework_statuses(current_timestamp):
    ERROR_MESSAGE = ('Сбой соединения с сервером.\n'
                     'URL: {url}.\n'
                     'Заголовок: {headers}.\n'
                     'Параметры: {timestamp}.\n'
                     'Описание/код ошибки: {error}.')

    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params={'from_date': current_timestamp}
        )
    except Exception as error:
        logger.error(exc_info=True, msg='Сбой соединения')
        raise NetworkFailure(
            ERROR_MESSAGE.format(
                url=API_URL,
                headers=HEADERS,
                timestamp=current_timestamp,
                error=error
            )
        )
    homework = response.json()
    if 'error' in homework:
        logger.error(exc_info=True, msg='Отказ сервера')
        raise ServerFailure(
            ERROR_MESSAGE.format(
                url=API_URL,
                headers=HEADERS,
                timestamp=current_timestamp,
                error=homework.get('error')
            )
        )
    if 'code' in homework:
        logger.error(exc_info=True, msg='Отказ сервера')
        raise ServerFailure(
            ERROR_MESSAGE.format(
                url=API_URL,
                headers=HEADERS,
                timestamp=current_timestamp,
                error=homework.get('code')
            )
        )
    return homework


def send_message(message, bot_client):
    logger.info(msg=f'Сообщение "{message}" отправлено', exc_info=True)
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    logger.debug(msg='{:-^40}'.format(' Инициализация бота '))
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
                send_message(f'Бот столкнулся с ошибкой: {error}', bot)
                time.sleep(5)

            except Exception as error:
                logger.error(
                    msg=(f'При выполнении функции {send_message.__name__} '
                         f'произошла ошибка {error}'),
                    exc_info=True
                )


if __name__ == '__main__':
    if TESTING is True:
        import unittest
        from unittest import TestCase, mock
        RegEx = requests.RequestException
        options = [
            {'error': 'testing'},
            {'homeworks': [{'homework_name': 'test', 'status': 'test'}]},
            {'homeworks': 1}
        ]
        JSON = options[randint(0, 2)]

        class TestReqServerFailure(TestCase):
            @mock.patch('requests.get')
            def test_raised(self, rq_get):
                resp = mock.Mock()
                resp.json = mock.Mock(return_value=JSON)
                rq_get.return_value = resp
                main()
        unittest.main()
    main()
