import frappe

def get_context(context):

    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        return

    customer = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user
        },
        "customer"
    )

    context.orders = []

    if customer:
        context.orders = frappe.get_all(
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