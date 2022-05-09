def get_frappe_notification_controllers_tests():
    from .templates.tests import get_template_controller_tests
    from .clients.tests import get_clients_controller_tests

    return [
        *get_template_controller_tests(),
        *get_clients_controller_tests(),
    ]
