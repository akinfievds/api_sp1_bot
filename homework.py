import logging
import time
from json import JSONDecodeError
from os import getenv

import requests
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

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
ERROR_MESSAGE = ('Сбой соединения с сервером.\n'
                 'URL: {url}.\n'
                 'Заголовок: {headers}.\n'
                 'Параметры: {timestamp}.\n'
                 'Описание/код ошибки: {error}.')

logging.basicConfig(
    level=logging.DEBUG,
    filename=LOG_FILE,
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)


class UnexpectedStatus(Exception):
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
    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params={'from_date': current_timestamp}
        )
    except Exception as error:
        logger.error(exc_info=True, msg='Сбой соединения')
        raise JSONDecodeError(
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
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    logger.debug(msg='{:-^40}'.format(' Инициализация бота '))
    current_timestamp = int(time.time())

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get('homeworks'):
                text_message = parse_homework_status(
                    new_homework.get('homeworks')[0]
                )
                send_message(text_message, bot)
                logger.info(
                    msg=f'Сообщение отправлено в чат (Текст {text_message})'
                )
            current_timestamp = new_homework.get(
                'current_date', current_timestamp
            )
            time.sleep(1200)

        except Exception as error:
            msg = f'Бот столкнулся с ошибкой: {error}'
            send_message(msg, bot)
            logger.error(msg=msg)
            time.sleep(5)


if __name__ == '__main__':
    main()
