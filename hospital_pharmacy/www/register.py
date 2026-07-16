import frappe


def get_context(context):
    context.title = "Customer Registration"
    context.redirect_to = frappe.form_dict.get("redirect-to") or "/home"
    if frappe.session.user != "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = context.redirect_to