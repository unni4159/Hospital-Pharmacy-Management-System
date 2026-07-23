# pyrefly: ignore [missing-import]
import frappe


def get_context(context):
    user = frappe.session.user

    context.orders = frappe.get_all(
        "Sales Invoice",
        filters={
            "owner": user,
            "docstatus": 1
        },
        fields=[
            "name",
            "posting_date",
            "customer",
            "grand_total",
            "status"
        ],
        order_by="posting_date desc"
    )