from .test_get_me import TestGetMe
from .test_create_client import TestCreateClient
from .test_get_client import TestGetClient
from .test_get_clients import TestGetClients
from .test_update_client import TestUpdateClient
from .test_validate_client_access import TestValidateClientAccess
from .test_get_notification_logs import TestGetNotificationLogs
from .test_mark_log_seen import TestMarkLogSeen


def get_clients_controller_tests():
    return [
        TestGetMe,
        TestCreateClient,
        TestGetClient,
        TestGetClients,
        TestUpdateClient,
        TestValidateClientAccess,
        TestGetNotificationLogs,
        TestMarkLogSeen,
    ]
