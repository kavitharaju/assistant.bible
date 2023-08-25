'''Functions for Authentication for the Apps'''
import os
from functools import wraps
from custom_exceptions import PermissionException
import gotrue.errors
from supabase import create_client, Client
from fastapi import WebSocket

from core.auth.supabase import supa
from log_configs import log
import schema


def admin_auth_check_decorator(func):
    '''For all data managment APIs'''
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract the access token from the request headers
        access_token = kwargs.get('token')
        if not access_token:
            raise ValueError("Access token is missing")
        access_token_str = access_token.get_secret_value()
        # Verify the access token using Supabase secret
        try:
            user_data = supa.auth.get_user(access_token_str)
        except gotrue.errors.AuthApiError as e:
            raise PermissionException("Unauthorized access. Invalid token.") from e

        if 'admin' not in user_data.user_metadata.get('user_types'):
            raise PermissionException("Unauthorized access. User is not admin.")

        return await func(*args, **kwargs)

    return wrapper


def chatbot_auth_check_decorator(func):
    '''checks a predefined token in request header, and checks it is a
    valid, logged in, user.
    '''
    @wraps(func)
    async def wrapper(websocket: WebSocket, *args, **kwargs):
        # Extract the access token from the request headers
        access_token = kwargs.get('token')
        if not access_token:
            raise ValueError("Access token is missing")
        access_token_str = access_token.get_secret_value()

        # Verify the access token using Supabase secret
        try:
            supa.auth.get_user(access_token_str)
        except gotrue.errors.AuthApiError as e:
            await websocket.accept()
            json_response = schema.BotResponse(sender=schema.SenderType.BOT,
                    message='Please sign in first, and then I will look forward to answering your question.', type=schema.ChatResponseType.ANSWER,
                    sources=[],
                    media=[])
            await websocket.send_json(json_response.dict())
            return
        return await func(websocket, *args, **kwargs)

    return wrapper


def chatbot_get_labels_decorator(func):
    '''checks a predefined token in request header, and returns available sources.
    '''
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract the access token from the request headers
        access_token = kwargs.get('token')
        if not access_token:
            labels = []
        else:
            access_token_str = access_token.get_secret_value()

            # Verify the access token using Supabase secret
            try:
                user_data = supa.auth.get_user(access_token_str)

            except gotrue.errors.AuthApiError as e: # The user is not logged in
                labels = []

            else:
                result = supa.table('userTypes').select('''
                        sources
                        '''
                    ).in_(
                    'user_type', user_data.user.user_metadata.get('user_types')
                    ).execute()
                labels = []
                for data in result.data:
                    labels.extend(data.get('sources'))
        labels = list(set(labels))
        kwargs['labels'] = labels
        # Proceed with the original function call and pass the sources to it
        return await func(*args, **kwargs)

    return wrapper
