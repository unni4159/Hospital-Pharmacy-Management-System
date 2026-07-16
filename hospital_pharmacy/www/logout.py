# pyrefly: ignore [missing-import]
import frappe


def get_context(context):
    frappe.local.login_manager.logout()
    frappe.db.commit()
    frappe.local.login_manager.clear_cookies()
    frappe.local.cookie_manager.delete_cookie([
        "full_name",
        "user_id",
        "sid",
        "user_image",
        "user_lang",
        "system_user",
    ])
    frappe.local.login_manager.login_as_guest()
    frappe.local.session = frappe._dict({"user": "Guest", "sid": ""})
    frappe.local.session_obj = None
    frappe.local.login_manager.user = "Guest"
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/login?logged_out=1"
    frappe.local.response["http_status_code"] = 302
    return