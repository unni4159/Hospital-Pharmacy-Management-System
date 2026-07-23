# pyrefly: ignore [missing-import]
import frappe

no_cache = 1

def get_context(context):
    context.is_admin = False
    context.user_roles = frappe.get_roles()
    
    if "System Manager" in context.user_roles or frappe.session.user == "Administrator":
        context.is_admin = True
