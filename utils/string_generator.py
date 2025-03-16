import random
import string
import re
from cryptography.fernet import Fernet
from typing import Optional
import base64
import hashlib
import secrets

default_salt = b'apriaja'
hashed_salt = hashlib.sha256(default_salt).digest()
key = base64.urlsafe_b64encode(hashed_salt[:32])
cipher = Fernet(key)


def generate_code(name) -> str:
    name = name.upper()
    letter_mapping = {
        'I': '1',
        'A': '4',
        'O': '0',
        'J': '7',
        'B': '3',
        'E': '3',
        'L': '1',
        'S': '5',
        '2': 'Z'
    }

    code = ''
    for char in name:
        if char in letter_mapping:
            code += letter_mapping[char]
        else:
            code += char

    # If the length of the code is less than 6, pad it with random characters
    if len(code) < 6:
        pad_length = 6 - len(code)
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=pad_length))
        code += random_chars

    return code[:6]


def remove_domain(email) -> str:
    clean_email = re.sub(r'@.*$', '', email)
    return clean_email


def generate_api_keys(user_id, space_id, name: Optional[str] = None) -> str:
    data = f"{user_id}:{space_id}".encode()
    if name:
        data += f":{name}".encode()
    cipher = Fernet(key)
    encrypted_data = cipher.encrypt(data)
    return encrypted_data.decode()


def retrieve_api_keys(encrypted_data):
    decrypted_data = cipher.decrypt(encrypted_data)
    data = str(decrypted_data.decode()).split(':')
    return data[0], data[1]


def generate_random_token(length=40) -> str:
    return secrets.token_urlsafe(length)


def generate_random_code(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(
        random.choice(characters)
        for _ in range(length)
    )
