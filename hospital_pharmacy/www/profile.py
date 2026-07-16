# pyrefly: ignore [missing-import]
import frappe

def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        return

    context.user = frappe.get_doc("User", user)
    context.roles = frappe.get_roles(user)