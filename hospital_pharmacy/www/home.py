import frappe

def get_context(context):

    context.user = frappe.session.user

    if frappe.session.user == "Guest":
        context.roles = []
        return

    roles = frappe.get_roles(frappe.session.user)
    context.roles = roles

    # Administrator
    context.is_admin = "Administrator" in roles

    # Manager
    context.is_manager = (
        "Sales Manager" in roles or
        "Purchase Manager" in roles or
        "Stock Manager" in roles
    )

    # Pharmacist
    context.is_pharmacist = (
        "Sales User" in roles or
        "Stock User" in roles or
        "Purchase User" in roles
    )

    # Customer
    context.is_customer = "Customer" in roles