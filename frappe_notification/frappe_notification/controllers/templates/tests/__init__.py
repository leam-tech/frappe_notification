from .test_create_template import TestCreateTemplate
from .test_delete_template import TestDeleteTemplate
from .test_fork_template import TestForkTemplate
from .test_get_template import TestGetTemplate
from .test_get_templates import TestGetTemplates
from .test_send_notification import TestSendNotification, TestGetTargetTemplate
from .test_update_template import TestUpdateTemplate
from .test_validate_template_access import TestValidateTemplateAccess


def get_template_controller_tests():
    return [
        TestCreateTemplate, TestDeleteTemplate, TestForkTemplate, TestGetTemplate,
        TestGetTemplates, TestSendNotification, TestGetTargetTemplate,
        TestUpdateTemplate, TestValidateTemplateAccess
    ]
