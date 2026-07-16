# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
from frappe.utils import getdate, today
from contextlib import contextmanager


# ==========================================================
# CART & QUOTATION PERSISTENCE HELPERS
# ==========================================================

@contextmanager
def run_as_system_user():
    """Temporarily elevate internal ERPNext work without changing the web session."""
    session_state = {
        "user": frappe.local.session.user,
        "sid": frappe.local.session.sid,
        "data": frappe.local.session.data,
    }
    local_state = {
        field: getattr(frappe.local, field, None)
        for field in (
            "cache",
            "form_dict",    
            "jenv_restricted",
            "jenv_unrestricted",
            "role_permissions",
            "new_doc_templates",
            "user_perms",
        )
    }

    frappe.set_user("Administrator")
    try:
        yield
    finally:
        # Do not call frappe.set_user() here: it replaces the active session
        # id with the username and would log the portal user out.
        frappe.local.session.user = session_state["user"]
        frappe.local.session.sid = session_state["sid"]
        frappe.local.session.data = session_state["data"]
        for field, value in local_state.items():
            setattr(frappe.local, field, value)

def ensure_custom_fields():
    if not frappe.db.exists("Custom Field", {"dt": "Quotation", "fieldname": "custom_shopping_cart"}):
        custom_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Quotation",
            "fieldname": "custom_shopping_cart",
            "label": "Is Shopping Cart",
            "fieldtype": "Check",
            "insert_after": "customer_name"
        })
        custom_field.insert(ignore_permissions=True)
        frappe.db.commit()

def get_customer(user=None):
    if not user:
        user = frappe.session.user
    if not user or user == "Guest":
        return None
    customer = frappe.db.get_value("Portal User", {"user": user}, "parent")
    if not customer:
        customer = frappe.db.get_value("Customer", {"email_id": user}, "name")
    return customer

def get_active_quotation(customer, create_if_missing=False):
    if not customer:
        return None

    # This field is part of the cart compatibility layer. Ensure it exists
    # before querying it, including on a freshly installed site.
    ensure_custom_fields()

    quotation_name = frappe.db.get_value(
        "Quotation",
        {
            "quotation_to": "Customer",
            "party_name": customer,
            "docstatus": 0,
            "custom_shopping_cart": 1
        },
        "name"
    )
    if quotation_name:
        return frappe.get_doc("Quotation", quotation_name)
    
    if create_if_missing:
        ensure_custom_fields()
        q = frappe.new_doc("Quotation")
        q.quotation_to = "Customer"
        q.party_name = customer
        # Get Company safely
        company = frappe.db.get_default("Company")
        if not company:
            companies = frappe.get_all("Company")
            if companies:
                company = companies[0].name
        q.company = company
        q.transaction_date = today()
        q.valid_till = frappe.utils.add_days(today(), 30)
        q.custom_shopping_cart = 1
        q.order_type = "Sales"
        q.flags.ignore_mandatory = True
        q.flags.ignore_validate = True
        q.insert(ignore_permissions=True)
        return q


def get_or_create_draft_quotation(customer):
    """Return the customer's active cart quotation, creating it when needed."""
    if not customer:
        return None

    return get_active_quotation(customer, create_if_missing=True)

def sync_quotation_to_shopping_cart(user):
    """Restore a legacy quotation only when this user has no open cart.

    The Shopping Cart document is the live cart used by the website. It must
    never be overwritten at login/page load: doing so can replace newly added
    items with an older quotation and make the cart appear empty.
    """
    if not user or user == "Guest":
        return

    customer = get_customer(user)
    if not customer:
        return

    quotation = get_active_quotation(customer)
    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": user,
            "status": "Open"
        },
        "name"
    )

    # An open cart belongs to this user and is already persisted. Keep it
    # intact across logout/login and normal page requests.
    if cart_name:
        return frappe.get_doc("Shopping Cart", cart_name)

    # Backward-compatible one-time restore for carts that predate the
    # Shopping Cart doctype and only exist as draft quotations.
    if not quotation:
        return None

    cart = frappe.new_doc("Shopping Cart")
    cart.user = user
    cart.customer = customer
    cart.status = "Open"
    cart.order_date = today()

    total = 0
    for item in quotation.items:
        rate = item.rate or frappe.db.get_value(
            "Item Price",
            {"item_code": item.item_code, "price_list": "Standard Selling"},
            "price_list_rate"
        ) or 0

        cart.append("cart_items", {
            "item": item.item_code,
            "quantity": item.qty,
            "rate": rate,
            "amount": item.qty * rate
        })
        total += item.qty * rate

    cart.total_amount = total
    cart.save(ignore_permissions=True)
    frappe.db.commit()
    return cart

def sync_quotation_from_shopping_cart(cart):
    if not cart or cart.user == "Guest":
        return

    customer = cart.customer or get_customer(cart.user)
    if not customer:
        return

    quotation = get_active_quotation(customer, create_if_missing=True)
    quotation.set("items", [])
    for item in cart.cart_items:
        quotation.append("items", {
            "item_code": item.item,
            "qty": item.quantity,
            "rate": item.rate
        })
    quotation.flags.ignore_validate = True
    quotation.flags.ignore_mandatory = True
    quotation.save(ignore_permissions=True)
    frappe.db.commit()


def parse_address_lines(address_text):
    if not address_text:
        return {
            "address_line1": "",
            "address_line2": ""
        }

    lines = [line.strip() for line in address_text.strip().splitlines() if line.strip()]
    if not lines:
        return {
            "address_line1": address_text.strip()[:240],
            "address_line2": ""
        }

    return {
        "address_line1": lines[0][:240],
        "address_line2": " ".join(lines[1:])[:240] if len(lines) > 1 else ""
    }


def get_customer_shipping_address(customer, delivery_address, phone_number=None):
    if not customer or not delivery_address:
        return None

    address_data = parse_address_lines(delivery_address)
    address_line1 = address_data["address_line1"] or delivery_address.strip()[:240]

    existing = frappe.get_all(
        "Address",
        fields=["name"],
        filters=[
            ["Dynamic Link", "link_doctype", "=", "Customer"],
            ["Dynamic Link", "link_name", "=", customer],
            ["address_type", "=", "Shipping"],
            ["address_line1", "=", address_line1],
        ],
        limit_page_length=1,
    )
    if existing:
        return existing[0].name

    country = frappe.db.get_value("Country", {}, "name")
    if not country:
        country = frappe.db.get_value("Country", {"name": "India"}, "name")

    address = frappe.new_doc("Address")
    address.address_title = f"{customer} Shipping Address"
    address.address_type = "Shipping"
    address.address_line1 = address_line1
    address.address_line2 = address_data["address_line2"]
    address.city = "Not Set"
    address.country = country
    address.phone = phone_number
    address.is_shipping_address = 1
    address.append("links", {
        "link_doctype": "Customer",
        "link_name": customer
    })
    address.flags.ignore_permissions = True
    address.insert(ignore_permissions=True)
    return address.name


def on_login(login_manager):
    """Resolve the user's pending quotation without changing cart data."""
    customer = get_customer(login_manager.user)
    if not customer:
        return None

    return get_active_quotation(customer)


# ==========================================================
# ADD TO CART
# ==========================================================

@frappe.whitelist()
def add_to_cart(item_code, qty=1):
    if frappe.session.user == "Guest":
        frappe.throw("Please login first.")

    qty = int(qty)
    if qty <= 0:
        frappe.throw("Quantity must be greater than zero.")

    item = frappe.get_doc("Item", item_code)
    stock = frappe.db.sql("""
        SELECT COALESCE(SUM(actual_qty),0)
        FROM `tabBin`
        WHERE item_code=%s
    """, item_code)[0][0]

    if stock <= 0:
        frappe.throw("This medicine is currently Out of Stock.")

    rate = frappe.db.get_value(
        "Item Price",
        {
            "item_code": item_code,
            "price_list": "Standard Selling"
        },
        "price_list_rate"
    )

    if not rate:
        frappe.throw(f"Standard Selling Price not found for {item.item_name}")

    customer = get_customer(frappe.session.user)
    if not customer:
        frappe.throw("No Customer found.")

    # The quotation is the source of truth for the customer's pending order.
    quotation = get_or_create_draft_quotation(customer)
    quotation.flags.ignore_permissions = True

    quotation_item = next(
        (row for row in quotation.items if row.item_code == item.name),
        None
    )
    new_qty = (quotation_item.qty if quotation_item else 0) + qty
    if new_qty > stock:
        frappe.throw(f"Only {stock} item(s) available for {item.item_name}.")

    if quotation_item:
        quotation_item.qty = new_qty
        quotation_item.rate = rate
    else:
        quotation.append("items", {
            "item_code": item.name,
            "qty": qty,
            "rate": rate,
        })

    # Required quotation flow: update Quotation Item totals and then calculate
    # all quotation-level taxes and totals before saving the draft.
    quotation.calculate_taxes_and_totals()
    quotation.save(ignore_permissions=True)

    # Keep the existing Shopping Cart document in sync as a compatibility
    # projection for the current cart and checkout pages. The quotation above
    # remains the source of truth; no cart-to-quotation sync is performed.
    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user,
            "status": "Open"
        },
        "name"
    )

    if cart_name:
        cart = frappe.get_doc("Shopping Cart", cart_name)
    else:
        cart = frappe.new_doc("Shopping Cart")
        cart.user = frappe.session.user
        cart.customer = customer
        cart.status = "Open"
        cart.order_date = today()

    cart.set("cart_items", [])
    for quotation_item in quotation.items:
        cart.append("cart_items", {
            "item": quotation_item.item_code,
            "quantity": quotation_item.qty,
            "rate": quotation_item.rate,
            "amount": quotation_item.amount,
        })

    cart.total_amount = quotation.grand_total or quotation.total
    cart.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "status": "success",
        "message": "Item added to cart successfully.",
        "cart": cart.name,
        "quotation": quotation.name,
    }


@frappe.whitelist()
def update_cart(item_code, qty):
    """Set an item's quantity in the active draft quotation."""
    if frappe.session.user == "Guest":
        frappe.throw("Please login first.")

    qty = int(qty)
    if qty <= 0:
        frappe.throw("Quantity must be greater than zero.")

    customer = get_customer(frappe.session.user)
    if not customer:
        frappe.throw("No Customer found.")

    quotation = get_active_quotation(customer)
    if not quotation:
        frappe.throw("Your shopping cart is empty.")

    quotation.flags.ignore_permissions = True
    quotation_item = next(
        (row for row in quotation.items if row.item_code == item_code),
        None
    )
    if not quotation_item:
        frappe.throw("Item not found in your shopping cart.")

    stock = frappe.db.sql("""
        SELECT COALESCE(SUM(actual_qty), 0)
        FROM `tabBin`
        WHERE item_code=%s
    """, item_code)[0][0]
    if qty > stock:
        frappe.throw(f"Only {stock} quantity available for {item_code}.")

    # The quotation is the source of truth: update its Quotation Item, then
    # recalculate all item, tax, and grand-total values before saving.
    quotation_item.qty = qty
    quotation.calculate_taxes_and_totals()
    quotation.save(ignore_permissions=True)

    # Preserve the current cart and checkout pages by refreshing their
    # compatibility projection from the saved quotation.
    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {"user": frappe.session.user, "status": "Open"},
        "name"
    )
    if cart_name:
        cart = frappe.get_doc("Shopping Cart", cart_name)
    else:
        cart = frappe.new_doc("Shopping Cart")
        cart.user = frappe.session.user
        cart.customer = customer
        cart.status = "Open"
        cart.order_date = today()

    cart.set("cart_items", [])
    for row in quotation.items:
        cart.append("cart_items", {
            "item": row.item_code,
            "quantity": row.qty,
            "rate": row.rate,
            "amount": row.amount,
        })
    cart.total_amount = quotation.grand_total or quotation.total
    cart.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": "Cart quantity updated successfully.",
        "cart": cart.name,
        "quotation": quotation.name,
    }


@frappe.whitelist()
def submit_sales_order_for_checkout():
    if frappe.session.user == "Guest":
        frappe.throw("Please login first.")

    sync_quotation_to_shopping_cart(frappe.session.user)

    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user,
            "status": "Open"
        },
        "name"
    )

    if not cart_name:
        frappe.throw("Shopping Cart not found.")

    cart = frappe.get_doc("Shopping Cart", cart_name)

    if not cart.cart_items:
        frappe.throw("Shopping Cart is empty.")

    for row in cart.cart_items:
        stock = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_qty),0)
            FROM `tabBin`
            WHERE item_code=%s
        """, row.item)[0][0]

        if stock <= 0:
            frappe.throw(f"{row.item} is Out of Stock.")

        if row.quantity > stock:
            frappe.throw(f"Only {stock} quantity available for {row.item}.")

    cart.save(ignore_permissions=True)
    return {
        "status": "success"
    }


# ==========================================================
# CREATE ORDER FROM SHOPPING CART
# ==========================================================

@frappe.whitelist()
def create_order_from_cart(delivery_address, phone_number, payment_method=None, delivery_date=None, reference_no=None, reference_date=None):
    if frappe.session.user == "Guest":
        frappe.throw("Please login first.")

    if not delivery_date:
        frappe.throw("Please enter Delivery Date")

    if reference_date:
        try:
            reference_date = getdate(reference_date)
        except (TypeError, ValueError):
            frappe.throw("Please enter a valid Reference Date")

    try:
        delivery_date = getdate(delivery_date)
    except (TypeError, ValueError):
        frappe.throw("Please enter a valid Delivery Date")

    if delivery_date < getdate(today()):
        frappe.throw("Delivery Date cannot be in the past")

    if not payment_method:
        frappe.throw("Please select a payment method.")

    if frappe.db.exists("Mode of Payment", payment_method):
        payment_mode_type = frappe.db.get_value("Mode of Payment", payment_method, "type")
        if payment_mode_type == "Bank":
            if not reference_no or not reference_date:
                frappe.throw("Reference No and Reference Date are mandatory for Bank payment methods.")

    customer = get_customer(frappe.session.user)
    if not customer:
        frappe.throw("No Customer found.")

    # The draft quotation is the source of the order. It is already scoped to
    # this customer by get_active_quotation(), so no Shopping Cart data is
    # read to build the invoice or delivery order.
    quotation = get_active_quotation(customer)
    if not quotation or not quotation.items:
        frappe.throw("Your shopping cart is empty.")

    # ===========================================
    # Validate Stock Before Creating Invoice
    # ===========================================

    for row in quotation.items:

        stock = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_qty),0)
            FROM `tabBin`
            WHERE item_code=%s
        """, row.item_code)[0][0]

        if stock <= 0:
            frappe.throw(f"{row.item_code} is Out of Stock.")

        if row.qty > stock:
            frappe.throw(
                f"Only {stock} quantity available for {row.item_code}."
            )

    shipping_address_name = get_customer_shipping_address(
        customer,
        delivery_address,
        phone_number
    )

    with run_as_system_user():
        # Ensure Stock Settings are correctly configured for automatic batch/serial allocation
        stock_settings = frappe.get_doc("Stock Settings")
        updated = False
        if not stock_settings.auto_create_serial_and_batch_bundle_for_outward:
            stock_settings.auto_create_serial_and_batch_bundle_for_outward = 1
            updated = True
        if not stock_settings.use_serial_batch_fields:
            stock_settings.use_serial_batch_fields = 1
            updated = True
        if updated:
            stock_settings.flags.ignore_permissions = True
            stock_settings.save(ignore_permissions=True)

        # Submit this validated draft quotation, then use ERPNext's standard
        # mappers so the Sales Order, Delivery Note, Invoice and Payment Entry
        # are all created under Administrator privileges.
        quotation.flags.ignore_permissions = True
        quotation.custom_shopping_cart = 0
        for row in quotation.items:
            row.delivery_date = delivery_date
        quotation.submit()

        from erpnext.selling.doctype.quotation.quotation import _make_sales_order

        sales_order = _make_sales_order(quotation.name, ignore_permissions=True)
        sales_order.flags.ignore_permissions = True
        sales_order.mode_of_payment = (payment_method or "").strip()
        sales_order.delivery_date = delivery_date
        for row in sales_order.items:
            row.delivery_date = delivery_date

        if sales_order.mode_of_payment and not frappe.db.exists("Mode of Payment", sales_order.mode_of_payment):
            from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

            cash_account = get_default_bank_cash_account(
                sales_order.company,
                "Cash",
                mode_of_payment=None,
                account=None,
            )
            bank_account = get_default_bank_cash_account(
                sales_order.company,
                "Bank",
                mode_of_payment=None,
                account=None,
            )

            payment_account = None
            payment_type = None
            if cash_account and cash_account.get("account"):
                payment_account = cash_account.account
                payment_type = "Cash"
            elif bank_account and bank_account.get("account"):
                payment_account = bank_account.account
                payment_type = "Bank"

            if payment_account:
                mode_doc = frappe.get_doc({
                    "doctype": "Mode of Payment",
                    "mode_of_payment": sales_order.mode_of_payment,
                    "type": payment_type,
                    "enabled": 1,
                    "accounts": [
                        {
                            "company": sales_order.company,
                            "default_account": payment_account,
                        }
                    ],
                })
                mode_doc.flags.ignore_permissions = True
                mode_doc.insert(ignore_permissions=True)
            else:
                frappe.throw(
                    f"Configure a default Cash or Bank account in Company {sales_order.company} before checkout."
                )

        sales_order.insert(ignore_permissions=True)
        sales_order.submit()

        from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

        payment_account = frappe.db.get_value(
            "Mode of Payment Account",
            {
                "parent": sales_order.mode_of_payment,
                "company": sales_order.company,
            },
            "default_account",
        )

        if not payment_account:
            bank_account = get_default_bank_cash_account(
                sales_order.company,
                "Bank",
                mode_of_payment=None,
                account=None,
            )
            if bank_account and bank_account.get("account"):
                payment_account = bank_account.account
            else:
                cash_account = get_default_bank_cash_account(
                    sales_order.company,
                    "Cash",
                    mode_of_payment=None,
                    account=None,
                )
                if cash_account and cash_account.get("account"):
                    payment_account = cash_account.account

        if not payment_account:
            frappe.throw(
                f"Configure a payment account for {sales_order.mode_of_payment} before checkout."
            )

        if not frappe.db.exists("Mode of Payment", sales_order.mode_of_payment):
            account_type = frappe.db.get_value("Account", payment_account, "account_type")
            payment_type = "Cash" if account_type == "Cash" else "Bank"
            mode_doc = frappe.get_doc({
                "doctype": "Mode of Payment",
                "mode_of_payment": sales_order.mode_of_payment,
                "type": payment_type,
                "enabled": 1,
                "accounts": [
                    {
                        "company": sales_order.company,
                        "default_account": payment_account,
                    }
                ],
            })
            mode_doc.flags.ignore_permissions = True
            mode_doc.insert(ignore_permissions=True)

        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        payment_entry = get_payment_entry(
            "Sales Order", sales_order.name, bank_account=payment_account
        )
        payment_entry.mode_of_payment = sales_order.mode_of_payment
        if reference_no:
            payment_entry.reference_no = reference_no
        if reference_date:
            payment_entry.reference_date = reference_date
        payment_entry.flags.ignore_permissions = True
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()

        from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

        delivery_note = make_delivery_note(sales_order.name)
        if not delivery_note or not delivery_note.items:
            frappe.throw("Unable to create Delivery Note for this Sales Order.")

        delivery_note.flags.ignore_permissions = True
        delivery_note.insert(ignore_permissions=True)
        delivery_note.submit()

        from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

        invoice = make_sales_invoice(sales_order.name, ignore_permissions=True)
        if not invoice or not invoice.items:
            frappe.throw("Unable to create Sales Invoice for this Sales Order.")

        invoice.flags.ignore_permissions = True
        invoice.update_stock = 0
        if shipping_address_name:
            invoice.shipping_address_name = shipping_address_name
            invoice.customer_address = shipping_address_name

        for invoice_item in invoice.items:
            delivery_note_item = next(
                (item for item in delivery_note.items if item.so_detail == invoice_item.so_detail),
                None,
            )
            if not delivery_note_item:
                frappe.throw(f"Unable to link {invoice_item.item_code} to the Delivery Note.")

            invoice_item.delivery_note = delivery_note.name
            invoice_item.dn_detail = delivery_note_item.name

        invoice.set_advances()
        invoice.set_missing_values()
        invoice.insert(ignore_permissions=True)
        invoice.submit()

        delivery = frappe.new_doc("Delivery Order")
        delivery.customer = customer
        delivery.sales_invoice = invoice.name
        delivery.delivery_address = delivery_address
        delivery.phone_number = phone_number
        delivery.delivery_date = delivery_date
        delivery.delivery_status = "Pending"
        delivery.insert(ignore_permissions=True)

    # ===========================================
    # Close the existing Shopping Cart compatibility projection, if one is
    # present. The quotation and Sales Order above are the order source.
    # ===========================================
    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {"user": frappe.session.user, "status": "Open"},
        "name"
    )
    if cart_name:
        cart = frappe.get_doc("Shopping Cart", cart_name)
        cart.status = "Ordered"
        cart.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "status": "success",
        "invoice": invoice.name,
        "sales_order": sales_order.name,
        "payment_entry": payment_entry.name,
        "delivery_note": delivery_note.name,
        "delivery_order": delivery.name,
        "message": "Order placed successfully."
    }


# ==========================================================
# REMOVE ITEM FROM SHOPPING CART
# ==========================================================

@frappe.whitelist()
def remove_from_cart(item_code):
    if frappe.session.user == "Guest":
        frappe.throw("Please login first.")

    customer = get_customer(frappe.session.user)
    if not customer:
        frappe.throw("No Customer found.")

    quotation = get_active_quotation(customer)
    if not quotation:
        frappe.throw("Your shopping cart is empty.")

    quotation.flags.ignore_permissions = True
    quotation_item = next(
        (row for row in quotation.items if row.item_code == item_code),
        None
    )
    if not quotation_item:
        frappe.throw("Item not found in cart.")

    # The quotation is the source of truth: remove its Quotation Item and
    # recalculate taxes and totals before saving the draft quotation.
    quotation.remove(quotation_item)
    quotation.calculate_taxes_and_totals()
    quotation.save(ignore_permissions=True)

    # Keep the existing Shopping Cart document synchronized for the current
    # cart display and checkout flow without using it as the source of truth.
    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user,
            "status": "Open"
        },
        "name"
    )

    if cart_name:
        cart = frappe.get_doc("Shopping Cart", cart_name)
        cart.set("cart_items", [])
        for row in quotation.items:
            cart.append("cart_items", {
                "item": row.item_code,
                "quantity": row.qty,
                "rate": row.rate,
                "amount": row.amount,
            })
        cart.total_amount = quotation.grand_total or quotation.total
        cart.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "status": "success",
        "message": "Item removed successfully."
    }


# ==========================================================
# USER REGISTRATION
# ==========================================================

@frappe.whitelist(allow_guest=True)
def register_portal_user(customer_name, email, password, mobile=None):
    if not customer_name or not email or not password:
        frappe.throw("Full Name, Email and Password are required.")

    if frappe.db.exists("User", email):
        frappe.throw(f"Email {email} is already registered.")

    user = frappe.new_doc("User")
    user.email = email
    user.first_name = customer_name
    user.enabled = 1
    user.send_welcome_email = 0
    user.username = email
    user.user_type = "Website User"
    user.insert(ignore_permissions=True)
    user.add_roles("Customer", "All")
    user.save(ignore_permissions=True)

    # pyrefly: ignore [missing-import]
    from frappe.utils.password import update_password
    update_password(user.name, password)

    customer_name_exists = frappe.db.exists("Customer", customer_name)
    if customer_name_exists:
        local_part = email.split('@')[0]
        c_name = f"{customer_name} ({local_part})"
    else:
        c_name = customer_name

    customer = frappe.new_doc("Customer")
    customer.customer_name = c_name
    customer.customer_type = "Individual"
    customer.customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "Individual"
    customer.territory = frappe.db.get_default("Territory") or "All Territories"
    customer.append("portal_users", {"user": user.name})
    customer.insert(ignore_permissions=True)

    frappe.db.commit()

    # Use Frappe's standard session-based login flow for the new website user.
    login_manager = getattr(frappe.local, "login_manager", None)
    if not login_manager:
        # pyrefly: ignore [missing-import]
        from frappe.auth import LoginManager
        login_manager = LoginManager()
    login_manager.login_as(user.name)
    frappe.db.commit()

    return {
        "status": "success",
        "message": "User registered and logged in successfully."
    }

