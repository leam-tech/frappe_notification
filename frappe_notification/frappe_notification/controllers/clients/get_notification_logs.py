import frappe
from frappe_notification import (
    NotificationClientNotFound,
    InvalidRequest,
    get_active_notification_client)
from typing import Optional
from frappe_notification.utils.cursor_paginator import CursorPaginator, \
    CursorPaginatorExecutionArgs, CursorPaginatorSortBy, CursorPaginatorSortByField, \
    CursorPaginatorSortByDirection


class NotificationLogsFilters(frappe._dict):
    channel: Optional[str]
    channel_id: Optional[str]
    user_identifier: Optional[str]


class NotificationLogsSortByEnum(CursorPaginatorSortByField):
    CREATION = "outbox.creation"


class NotificationLogSortBy(CursorPaginatorSortBy):
    field: NotificationLogsSortByEnum


class GetNotificationLogsExecutionArgs(CursorPaginatorExecutionArgs):
    before: Optional[str]
    after: Optional[str]
    first: Optional[int]
    last: Optional[int]
    sort_by: Optional[NotificationLogSortBy]
    filters: NotificationLogsFilters


def get_notification_logs(args: GetNotificationLogsExecutionArgs):
    filters = args.pop('filters', None)

    # TODO: Find a better way to resolve these values..
    sort_by = args.pop("sort_by", None)
    if sort_by:
        sort_by = NotificationLogSortBy({
            "direction": CursorPaginatorSortByDirection[sort_by.field],
            "field": NotificationLogsSortByEnum[sort_by.direction]
        })
        args.sort_by = sort_by

    r = CursorPaginator(
        doctype="Notification Outbox",
        skip_process_filters=True,
        count_resolver=get_notification_logs_count_resolver,
        node_resolver=get_notification_logs_node_resolver,
        default_sorting_fields=["outbox.creation"],
        default_sorting_direction="desc",
        extra_args={"filters": filters}
    )
    return r.execute(args)


def get_notification_logs_count_resolver(paginator: CursorPaginator, filters):
    client = get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()
    filters = paginator.extra_args.get("filters") if paginator.extra_args else None
    conditions = get_notifications_logs_filters(NotificationLogsFilters(filters or {}))

    return frappe.db.sql(f"""
    SELECT
        count(distinct(outbox.name))
    FROM
        `tabNotification Outbox` outbox
    JOIN `tabNotification Outbox Recipient Item` recipient_item
        ON recipient_item.parent = outbox.name AND recipient_item.parenttype = 'Notification Outbox'
    WHERE
        outbox.notification_client = %(client)s
        AND outbox.docstatus = 1
        {conditions}
        AND recipient_item.status = 'Success'
        """, {
        "client": client
    }, as_list=1, debug=0)[0][0]


def get_notification_logs_node_resolver(paginator: CursorPaginator, filters, fields, sorting_fields,
                                        sort_dir, limit):
    client = get_active_notification_client()
    if not client:
        raise NotificationClientNotFound()

    extra_sorting_fields = f", {', '.join(sorting_fields)}"
    order_by = ', '.join([f'{x} {sort_dir}' for x in sorting_fields])

    filters = paginator.extra_args.get("filters") if paginator.extra_args else None
    conditions = get_notifications_logs_filters(NotificationLogsFilters(filters or {}))

    return frappe.db.sql(f"""
    SELECT
        outbox.name as outbox,
        recipient_item.name as outbox_recipient_row,
        outbox.subject,
        outbox.content,
        recipient_item.time_sent,
        recipient_item.user_identifier,
        recipient_item.channel,
        recipient_item.channel_id,
        recipient_item.seen
        {extra_sorting_fields}
    FROM
        `tabNotification Outbox` outbox
    JOIN `tabNotification Outbox Recipient Item` recipient_item
        ON recipient_item.parent = outbox.name AND recipient_item.parenttype = 'Notification Outbox'
    WHERE
        outbox.notification_client = %(client)s
        AND outbox.docstatus = 1
        {conditions}
        AND recipient_item.status = "Success"
    ORDER BY %(order_by)s
    LIMIT %(limit_page_length)s
    """, {
        "client": client,
        "order_by": order_by,
        "limit_page_length": limit
    }, as_dict=1, debug=0)


def get_notifications_logs_filters(filters: NotificationLogsFilters):
    channel = filters.channel
    channel_id = filters.channel_id
    user_identifier = filters.user_identifier

    if not ((channel and channel_id) or user_identifier):
        raise InvalidRequest(message=frappe._(
            "Please specify either (channel, channel_id) or user_identifier"
        ))

    conditions = []
    if channel:
        conditions.append(f"recipient_item.channel = '{channel}'")

    if channel_id:
        conditions.append(f"recipient_item.channel_id = '{channel_id}'")

    if user_identifier:
        conditions.append(f"recipient_item.user_identifier = '{user_identifier}'")

    return f' AND {" AND ".join(conditions)}' if len(conditions) else ""
