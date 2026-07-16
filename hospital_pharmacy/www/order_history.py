import frappe


def get_context(context):
    user = frappe.session.user

    if user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        return

    roles = frappe.get_roles(user)
    filters = {
        "docstatus": 1
    }

    if "Administrator" not in roles:
        filters["owner"] = user

    context.orders = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=[
            "name",
            "posting_date",
            "customer",
            "grand_total",
            "status"
        ],
        order_by="posting_date desc"
    )