import frappe


def execute():
    # Changing FieldType and removing Index on a single migration can issues
    # OperationalError: (1170, "BLOB/TEXT column 'channel_id' used in key specification without a key length")  # noqa
    # Hence we drop the index first. DataType will be updated by frappe migration.
    try:
        frappe.db.sql("ALTER TABLE `tabNotification Outbox Recipient Item` DROP INDEX `channel_id`;")
    except BaseException:
        log = frappe.log_error(
            title="Patch Error: Remove Outbox Channel ID Index",
            message=frappe.get_traceback()
        )
        print("Failed Executing patch. Please check the ErrorLog:", log.name)