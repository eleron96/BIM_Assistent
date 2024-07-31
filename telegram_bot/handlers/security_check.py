# security_check.py
import os
from dotenv import load_dotenv

load_dotenv()

white_list_user_ids = os.getenv('WHITE_LIST_USER_IDS')
white_list_user_ids = [int(x) for x in white_list_user_ids.strip('[]').split(',')]



def is_user_whitelisted(user_id):
    """
    Проверяет, находится ли пользователь в белом списке.

    :param user_id: ID пользователя для проверки.
    :return: True, если пользователь в белом списке, иначе False.
    """
    return user_id in white_list_user_ids
