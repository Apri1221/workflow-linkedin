# from keycloak.keycloak_admin import KeycloakAdmin as KcAdmin
# from keycloak.keycloak_openid import KeycloakOpenID as KcOpenID
# from schema.dto.request.index import AuthConfiguration
# from dotenv import dotenv_values, load_dotenv
# import os

# load_dotenv()
# config = dotenv_values(".env")

# # server_url = config['KEYCLOAK_BASE_URL'] or os.environ['KEYCLOAK_BASE_URL']
# # realm = config['REALM'] or os.environ['REALM']
# # client_id = config['CLIENT_ID'] or os.environ['CLIENT_ID']

# settings = AuthConfiguration(
#     server_url=server_url,
#     realm=realm,
#     client_id=client_id,
#     client_secret="",
#     authorization_url=f"{server_url}/realms/{realm}/protocol/openid-connect/auth",
#     token_url=f"{server_url}/realms/{realm}/protocol/openid-connect/token",
# )


# class MyKeycloakAdmin:
#     def __init__(self):
#         self.keycloak_admin = KcAdmin(
#             server_url=f"{settings.server_url}/admin",
#             realm_name=f"{settings.realm}",
#             client_id=f"{settings.client_id}",
#             username="admin",
#             password="bniMM1234",
#             client_secret_key=settings.client_secret,  # your backend client secret
#             verify=False  # SSL cert
#         )


# class MyKeycloakOpenID:
#     def __init__(self):
#         self.keycloak_openid = KcOpenID(
#             server_url=settings.server_url,
#             client_id=settings.client_id,  # backend-client-id
#             realm_name=settings.realm,  # example-realm
#             client_secret_key=settings.client_secret,  # your backend client secret
#             verify=False  # SSL cert
#         )
