# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
from frappe.utils import today


def get_context(context):

    if frappe.session.user == "Guest":
        frappe.flags.redirect_location = "/login"
        raise frappe.Redirect

    item_code = frappe.form_dict.get("item")
    quantity = int(frappe.form_dict.get("qty") or 1)

    if not item_code:
        frappe.throw("Medicine not selected.")

    from hospital_pharmacy.api import add_to_cart
    try:
        add_to_cart(item_code, quantity)
    except Exception as e:
        import urllib.parse
        error_msg = str(e).replace("ValidationError: ", "").strip()
        frappe.flags.redirect_location = f"/cart_view?error={urllib.parse.quote(error_msg)}"
        raise frappe.Redirect

    # Redirect to cart view
    frappe.flags.redirect_location = "/cart_view"
    raise frappe.Redirect