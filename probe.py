import textwrap

message = ('Сбой соединения с сервером.'
           'URL: .'
           'Заголовок: .'
           'Параметры: .'
           'Ошибка: .')

print('\n'.join(textwrap.wrap(message)))
