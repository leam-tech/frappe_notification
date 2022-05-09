from .test_get_me import TestGetMe
from .test_create_client import TestCreateClient
from .test_get_client import TestGetClient
from .test_get_clients import TestGetClients
from .test_update_client import TestUpdateClient
from .test_validate_client_access import TestValidateClientAccess


def get_clients_controller_tests():
    return [
        TestGetMe,
        TestCreateClient,
        TestGetClient,
        TestGetClients,
        TestUpdateClient,
        TestValidateClientAccess,
    ]
