import frappe


def get_context(context):

    context.purchases = frappe.get_all(
        "Purchase Receipt",
        fields=[
            "name",
            "supplier",
            "posting_date",
            "grand_total"
        ],
        order_by="posting_date desc"
    )