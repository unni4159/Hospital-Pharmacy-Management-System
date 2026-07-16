# pyrefly: ignore [missing-import]
import frappe


def get_context(context):

    context.sales = frappe.get_all(
        "Sales Invoice",
        fields=[
            "name",
            "customer",
            "posting_date",
            "grand_total",
            "status"
        ],
        order_by="posting_date desc"
    )