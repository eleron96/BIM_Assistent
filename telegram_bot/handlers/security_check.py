# security_check.py

WHITE_LIST_USER_IDS = [413382827, 176049024]


def is_user_whitelisted(user_id):
    """
    Проверяет, находится ли пользователь в белом списке.

    :param user_id: ID пользователя для проверки.
    :return: True, если пользователь в белом списке, иначе False.
    """
    return user_id in WHITE_LIST_USER_IDS
