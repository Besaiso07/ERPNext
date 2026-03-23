import re
import frappe
from frappe import _

@frappe.whitelist()
def process_air_file(file_url=None, customer=None):
    # Try to get file_url/customer from Various sources if not provided as argument
    if not file_url:
        file_url = frappe.form_dict.get('file_url')
    if not customer:
        customer = frappe.form_dict.get('customer')
    
    # Check if we have file content directly in local (for direct upload calls)
    uploaded_content = getattr(frappe.local, 'uploaded_file', None)
    
    if not file_url and not uploaded_content:
        frappe.throw(_("No file data or URL provided for AIR processing. Please ensure the file was uploaded correctly."))
        return
    
    try:
        # Debugging: Log the source
        source = "URL" if file_url else "Direct Upload"
        frappe.log_error(f"Processing AIR file from {source}: {file_url or 'content cached'}", "AIR Upload Debug")
        
        # Read the file content
        content = None
        if uploaded_content:
            if isinstance(uploaded_content, bytes):
                content = uploaded_content.decode('utf-8', errors='ignore')
            else:
                content = uploaded_content
        
        if not content and file_url:
            if file_url.startswith('http'):
                import requests
                content = requests.get(file_url).text
            else:
                from frappe.utils.file_manager import get_file_path
                file_path = get_file_path(file_url)
                
                # Fallback for common Frappe site structures
                if not file_path:
                    if file_url.startswith('/files/'):
                        file_path = frappe.get_site_path('public', file_url.lstrip('/'))
                    elif file_url.startswith('/private/files/'):
                        file_path = frappe.get_site_path('private', file_url.replace('/private/', ''))
                
                if not file_path:
                    frappe.throw(_("Could not locate the file on server for URL: {0}").format(file_url))

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

        if not content:
            frappe.throw(_("AIR file content is empty or unreadable."))

        # 1. Automated Customer Identification (RM*AN Code)
        extracted_customer_code = None
        lines = content.split('\n')
        for line in lines:
            if "RM*AN" in line:
                # Extract string after AN (e.g. RM*AN0917615501 -> 0917615501)
                match = re.search(r'RM\*AN([A-Z0-9]+)', line)
                if match:
                    extracted_customer_code = match.group(1).strip()
                    break
        
        if extracted_customer_code:
            found_customer = frappe.db.get_value("Customer", {"air_customer_code": extracted_customer_code}, "name")
            if found_customer:
                customer = found_customer
                frappe.msgprint(_("Automated Customer Match: <b>{0}</b> identified via code {1}").format(customer, extracted_customer_code), alert=True)
            else:
                if not customer:
                    frappe.throw(_("Customer with code <b>{0}</b> was not found in the system. Please link it in the Customer master or select manually.").format(extracted_customer_code))

        if not customer:
            frappe.throw(_("No Customer selected or identified. Please select a customer before uploading or ensure the AIR file contains a recognized RM*AN code."))

        # 2. Parse Rows
        from tourism_app.tourism_app.doctype.tour_booking.tour_booking import parse_air_file
        row_data = parse_air_file(content)
        
        if not row_data:
            frappe.throw(_("Could not parse any valid flight data from the AIR file. Please check the file format."))

        # 3. Create new Tour Booking
        doc = frappe.new_doc("Tour Booking")
        doc.booking_date = frappe.utils.today()
        doc.customer = customer
        
        for row in row_data:
            airline_code = row.get("airline_code")
            airline_name = None

            if airline_code:
                # Use the new IATA Code linking logic
                airline_name = frappe.db.get_value("Airline", {"iata_code": airline_code}, "name")
                if not airline_name:
                    airline_name = frappe.db.get_value("Airline", {"name": airline_code}, "name")
                
                if not airline_name:
                    frappe.throw(_("Please ensure an Airline exists with <b>IATA Code: {0}</b> in the Airline master before uploading.").format(airline_code), title=_("Missing Airline"))
                
                row["airline"] = airline_name

                # --- Step B: Airline as Supplier (Automated Mapping) ---
                # Check if a Supplier exists with the SAME name as the Airline
                supplier_name = frappe.db.get_value("Supplier", {"supplier_name": airline_name}, "name")
                
                if not supplier_name:
                    # Fallback: Create new Supplier
                    new_sup = frappe.get_doc({
                        "doctype": "Supplier",
                        "supplier_name": airline_name,
                        "supplier_group": "Airlines", # Ensure this group exists or fallback to Services
                        "supplier_type": "Company",
                        "is_transporter": 1
                    })
                    # Check if Airline group exists
                    if not frappe.db.exists("Supplier Group", "Airlines"):
                        new_sup.supplier_group = "All Supplier Groups"
                    
                    new_sup.insert(ignore_permissions=True)
                    supplier_name = new_sup.name
                
                row["supplier"] = supplier_name

            # --- Base Currency Calculation (LYD) ---
            # published_fare and tax are in 'currency'
            currency = row.get("currency", "LYD")
            fare = row.get("fare", 0)
            tax = row.get("tax", 0)
            total_foreign = fare + tax
            
            base_amount = total_foreign
            if currency != "LYD":
                # Get exchange rate
                rate = frappe.db.get_value("Currency Exchange", {"from_currency": currency, "to_currency": "LYD"}, "exchange_rate")
                if not rate:
                    rate = 5.0 # Fallback for demo or if not configured
                base_amount = total_foreign * rate

            doc.append("flights", {
                "pax_name": row.get("pax_name"),
                "ticket_number": row.get("ticket_number"),
                "ticket_pnr": row.get("pnr"),
                "flight_route": row.get("route"),
                "flight_number": row.get("flight_no"),
                "airline": airline_name,
                "supplier": row.get("supplier"),
                "flight_class": row.get("flight_class"),
                "departure_date": row.get("departure_date"),
                "return_date": row.get("return_date"),
                "fare": fare,
                "tax": tax,
                "currency": currency,
                "base_currency_amount": base_amount,
                "commission_type": "Percentage",
                "commission_rate": row.get("commission_rate", 0)
            })
        
        try:
            doc.insert()
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Tour Booking Insertion Error")
            frappe.throw(_("Value missing or validation failed during Tour Booking creation: {0}").format(str(e)))
        
        # Return success message and ID
        frappe.msgprint(_("Success! Tour Booking <b>{0}</b> has been created.").format(doc.name), title=_("Upload Complete"), indicator="green")
        return doc.name

    except Exception as e:
        if not isinstance(e, frappe.ValidationError):
            frappe.log_error(frappe.get_traceback(), "AIR Upload Error")
        raise e
