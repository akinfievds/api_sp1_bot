import os
import time
import logging

import requests
import telegram
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


load_dotenv()


PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
API_URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
LOG_FILE = 'homework.log'


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_format = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
handler = RotatingFileHandler(
    filename=LOG_FILE,
    maxBytes=50 * 1024,
    backupCount=5
)
handler.setFormatter(logger_format)
logger.addHandler(handler)


def parse_homework_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status == 'rejected':
        verdict = 'К сожалению в работе нашлись ошибки.'
        logger.debug(msg=f'В работе {homework_name} найдены ошибки.')
    elif homework_status == 'reviewing':
        verdict = 'Работу взяли на проверку.'
        logger.debug(msg=f'Работу {homework_name} взяли в работу.')
    else:
        verdict = ('Ревьюеру всё понравилось, можно приступать'
                   ' к следующему уроку.')
        logger.debug(msg=f'Работа {homework_name} принята')
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homework_statuses(current_timestamp):
    homework_statuses = requests.get(
        API_URL,
        headers={'Authorization': 'OAuth {}'.format(PRAKTIKUM_TOKEN)},
        params={'from_date': current_timestamp}
    )
    if not homework_statuses.json().get('homeworks'):
        logger.debug(msg='Изменений в статусе работ нет')
    return homework_statuses.json()


def send_message(message, bot_client):
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.debug(msg='Инициализация')
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
