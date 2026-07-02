import frappe

def get_context(context):
    user = frappe.session.user

    context.user = frappe.get_doc("User", user)
    context.roles = frappe.get_roles(user)