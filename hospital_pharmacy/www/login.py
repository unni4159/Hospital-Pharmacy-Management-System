# pyrefly: ignore [missing-import]
import frappe

no_cache = 1

def get_context(context):
    context.title = "Sign In"
    context.force_guest = False
    context.redirect_to = frappe.form_dict.get("redirect-to") or "/home"

    if frappe.form_dict.get("logged_out"):
        frappe.local.login_manager.logout()
        frappe.db.commit()
        frappe.local.login_manager.clear_cookies()
        frappe.local.login_manager.login_as_guest()
        frappe.local.session = frappe._dict({"user": "Guest", "sid": ""})
        frappe.local.session_obj = None
        frappe.local.login_manager.user = "Guest"
        frappe.session.user = "Guest"
        frappe.local.session_obj = None
        context.force_guest = True
        return

    if frappe.session.user != "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = context.redirect_to
