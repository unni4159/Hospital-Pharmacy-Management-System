# pyrefly: ignore [missing-import]
import frappe

no_cache = 1

def get_context(context):

    if frappe.session.user == "Guest":
        frappe.throw("Please login.")

    customer = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user
        },
        "customer"
    )

    context.orders = []

    if customer:
        orders = frappe.get_all(
            "Sales Invoice",
            filters={
                "customer": customer
            },
            fields=[
                "name",
                "posting_date",
                "grand_total",
                "status"
            ],
            order_by="creation desc"
        )

        for order in orders:
            items = frappe.get_all(
                "Sales Invoice Item",
                filters={"parent": order.name},
                fields=["item_code", "item_name"]
            )
            for item in items:
                item.image = frappe.db.get_value("Item", {"item_code": item.item_code}, "image") or ""
            order.order_items = items

        context.orders = orders