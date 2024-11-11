import requests
import base64
import time
import os

# Ваши учетные данные (замените заглушки на ваши реальные данные)
client_id = 'YOUR_CLIENT_ID'        # Замените на ваш App key
client_secret = 'YOUR_CLIENT_SECRET'  # Замените на ваш Secret (рекомендуется хранить в переменной окружения)
redirect_uri = 'https://github.com/eleron96/BIM_Assistent'  # Ваш Redirect URI

# Код авторизации (после декодирования из URL)
authorization_code = 'YOUR_AUTHORIZATION_CODE'  # Замените на ваш код авторизации

def get_access_token():
    # Закодируйте client_id и client_secret в Base64
    credentials = f'{client_id}:{client_secret}'
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8').strip()

    # Заголовки и данные запроса
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'redirect_uri': redirect_uri
    }

    response = requests.post('https://api.plan.toggl.com/api/v5/authenticate/token', headers=headers, data=data)

    if response.status_code == 200:
        token_info = response.json()
        access_token = token_info.get('access_token')
        refresh_token = token_info.get('refresh_token')
        expires_in = token_info.get('expires_in')
        expires_at = time.time() + expires_in

        print('Токен доступа получен успешно.')
        return access_token, refresh_token, expires_at
    else:
        print('Ошибка при получении токена доступа:', response.status_code, response.text)
        return None, None, None

def refresh_access_token(refresh_token):
    # Закодируйте client_id и client_secret в Base64
    credentials = f'{client_id}:{client_secret}'
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8').strip()

    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'redirect_uri': redirect_uri
    }

    response = requests.post('https://api.plan.toggl.com/api/v5/authenticate/token', headers=headers, data=data)

    if response.status_code == 200:
        token_info = response.json()
        access_token = token_info.get('access_token')
        refresh_token = token_info.get('refresh_token')  # Обновляем refresh_token
        expires_in = token_info.get('expires_in')
        expires_at = time.time() + expires_in

        print('Токен доступа успешно обновлен.')
        return access_token, refresh_token, expires_at
    else:
        print('Ошибка при обновлении токена доступа:', response.status_code, response.text)
        return None, None, None

# Инициализация токенов
access_token, refresh_token, expires_at = get_access_token()

# Проверяем, успешно ли получены токены
if not access_token or not refresh_token or not expires_at:
    print('Не удалось получить токены доступа. Проверьте правильность данных и повторите попытку.')
    exit(1)

# Функция для выполнения API-запросов с автоматическим обновлением токена
def api_request(url, method='GET', data=None):
    global access_token, refresh_token, expires_at
    if time.time() >= expires_at:
        # Токен истек, обновляем
        access_token, refresh_token, expires_at = refresh_access_token(refresh_token)
        if not access_token:
            print('Не удалось обновить токен доступа.')
            return None

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    if method.upper() == 'GET':
        response = requests.get(url, headers=headers)
    elif method.upper() == 'POST':
        response = requests.post(url, headers=headers, data=data)
    else:
        print('Неподдерживаемый метод запроса.')
        return None

    return response

# Пример использования
response = api_request('https://api.plan.toggl.com/api/v5/me')
if response and response.status_code == 200:
    user_info = response.json()
    print('Информация о пользователе:', user_info)
else:
    print('Ошибка при выполнении запроса:', response.status_code, response.text)
