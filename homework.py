import logging
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

RQ_HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
STATUSES_VERDICTS = {
    'rejected': 'К сожалению в работе нашлись ошибки.',
    'reviewing': 'Работу взяли на проверку.',
    'approved': 'Ревьюеру всё понравилось, можно приступать'
                ' к следующему уроку.'
}
STATUS_SUMMARY = 'У вас проверили работу "{name}"!\n\n{verdict}'
STATUS_LOG = 'Работа {name}. Вердикт {verdict}'
STATUS_UNEXPECTED = 'Получен неожиданный статус: {status}'

LOG_FILE = __file__ + '.log'


class UnexpectedStatus(Exception):
    pass


class ServerFailure(Exception):
    pass


logger = logging.getLogger(__file__)


def parse_homework_status(homework):
    name, status = homework['homework_name'], homework['status']
    if status not in STATUSES_VERDICTS:
        raise UnexpectedStatus(STATUS_UNEXPECTED.format(status=status))
    verdict = STATUSES_VERDICTS[status]
    return STATUS_SUMMARY.format(name=name, verdict=verdict)


def get_homework_statuses(current_timestamp):
    RQ_PARAMS = dict(url=API_URL, headers=RQ_HEADERS,
                     params={'from_date': current_timestamp})
    RQ_DESCR = ('Параметры запроса:\n'
                'response = requests.get(\n'
                '  url={url}.\n'
                '  headers={headers}.\n'
                '  params={params}).\n'
                ')')
    NETWORK_ERR_MSG = 'Сбой соединения. Ошибка: {error}\n'
    SERVER_ERR_MSG = 'Отказ сервера. Ошибка: {error}\n'

    try:
        response = requests.get(**RQ_PARAMS)

    except requests.exceptions.RequestException as error:
        raise requests.exceptions.ConnectionError(
            NETWORK_ERR_MSG.format(error=error) + RQ_DESCR.format(**RQ_PARAMS)
        )
    homework = response.json()
    if 'error' in homework or 'code' in homework:
        error = homework.get('error') or homework.get('code')
        logger.error(msg=SERVER_ERR_MSG.format(error=error))
        raise ServerFailure(
            SERVER_ERR_MSG.format(error=error) + RQ_DESCR.format(**RQ_PARAMS)
        )
    return homework


def send_message(message, bot_client):
    logger.info(msg=f'Произведена попытка отправить сообщение "{message}"')
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
    logging.basicConfig(
        filename=LOG_FILE,
        filemode='w',
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
