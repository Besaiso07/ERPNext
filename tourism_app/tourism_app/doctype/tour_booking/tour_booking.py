# Copyright (c) 2026, Tourism App
# License: MIT

import re
import frappe
from frappe.model.document import Document


class TourBooking(Document):

    def validate(self):
        """
        Auto-calculate all prices, costs and profit.
        Runs on every save (draft or submitted).
        """
        # --- Flights ---
        for flight in self.flights:
            fare = flight.fare or 0
            tax = flight.tax or 0
            
            if flight.commission_type == "Fixed Amount":
                flight.supplier_commission = flight.commission_rate or 0
            else:
                flight.supplier_commission = fare * ((flight.commission_rate or 0) / 100)
                
            commission = flight.supplier_commission or 0
            markup = flight.agency_markup or 0

            flight.net_purchase_price = (fare + tax) - commission
            flight.selling_price = (fare + tax) + markup
            flight.profit = flight.selling_price - flight.net_purchase_price

            # --- Airport Code Validation ---
            if flight.flight_route:
                flight.flight_route = flight.flight_route.upper().strip()
                codes = flight.flight_route.split('-')
                for code in codes:
                    code = code.strip()
                    if code and not frappe.db.exists("Airport", code):
                        frappe.throw(
                            f"خطأ: كود المطار ({code}) غير معرف في النظام. يرجى إضافته في جدول المطارات أولاً قبل استخدامه في خط السير.",
                            title="Airport Not Found"
                        )

        # --- Hotels ---
        for hotel in self.hotels:
            purchase = hotel.purchase_price or 0
            markup = hotel.agency_markup or 0
            hotel.selling_price = purchase + markup

        # --- Totals ---
        self.total_cost = (
            sum(f.net_purchase_price or 0 for f in self.flights)
            + sum(h.purchase_price or 0 for h in self.hotels)
        )

        self.total_selling_amount = (
            sum(f.selling_price or 0 for f in self.flights)
            + sum(h.selling_price or 0 for h in self.hotels)
        )

        self.total_profit = self.total_selling_amount - self.total_cost

    @frappe.whitelist()
    def create_sales_invoice(self):
        """
        1. Check if invoice is already created.
        2. Create a Sales Invoice for the customer.
        3. Create Draft Purchase Invoice(s) for each unique supplier
           (airlines and hotels), grouped by supplier name.
        """
        # We only want to process items where is_reported == 0
        unreported_flights = [f for f in self.flights if not f.is_reported]
        unreported_hotels = [h for h in self.hotels if not h.is_reported]

        if not unreported_flights and not unreported_hotels:
            frappe.throw("All items in this booking have already been reported.")

        # Calculate selling amount for only unreported items
        selling_amount = (
            sum(f.selling_price or 0 for f in unreported_flights) +
            sum(h.selling_price or 0 for h in unreported_hotels)
        )

        # ------------------------------------------------------------------
        # 1. Sales Invoice
        # ------------------------------------------------------------------
        self._ensure_travel_service_item()

        si_items = []
        for flight in unreported_flights:
            si_items.append({
                "item_code": "Travel Service",
                "item_name": "Flight Ticket",
                "description": f"Flight: {flight.pax_name} - {flight.ticket_number}",
                "qty": 1,
                "rate": flight.selling_price or 0,
                "uom": "Nos",
                "custom_passenger_name": flight.pax_name,
                "custom_ticket_number": flight.ticket_number,
                "custom_route": flight.flight_route,
                "custom_airline": flight.airline,
            })
            
        for hotel in unreported_hotels:
            si_items.append({
                "item_code": "Travel Service",
                "item_name": "Hotel Booking",
                "description": f"Hotel: {hotel.hotel_name}",
                "qty": 1,
                "rate": hotel.selling_price or 0,
                "uom": "Nos",
            })

        company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value('Global Defaults', 'default_company')

        sales_invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": company,
            "customer": self.customer,
            "posting_date": self.booking_date or frappe.utils.today(),
            "due_date": self.booking_date or frappe.utils.today(),
            "items": si_items,
            "custom_tour_booking": self.name,
        })
        sales_invoice.flags.ignore_permissions = True
        sales_invoice.set_missing_values()
        sales_invoice.insert()

        # ------------------------------------------------------------------
        # 2. Group supplier costs
        # ------------------------------------------------------------------
        supplier_costs = {}

        # Flight rows — key: airline_supplier, value: net_purchase_price
        for flight in unreported_flights:
            supplier = flight.supplier
            if not supplier:
                continue
            cost = flight.net_purchase_price or 0
            supplier_costs[supplier] = supplier_costs.get(supplier, 0) + cost

        # Hotel rows — key: hotel_supplier, value: purchase_price
        for hotel in unreported_hotels:
            supplier = hotel.hotel_supplier
            if not supplier:
                continue
            cost = hotel.purchase_price or 0
            supplier_costs[supplier] = supplier_costs.get(supplier, 0) + cost

        # ------------------------------------------------------------------
        # 3. Create one Draft Purchase Invoice per unique supplier
        # ------------------------------------------------------------------
        self._ensure_travel_service_item()

        purchase_invoices_created = {}
        for supplier, total_cost in supplier_costs.items():
            if total_cost <= 0:
                continue

            company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value('Global Defaults', 'default_company')

            pi = frappe.get_doc({
                "doctype": "Purchase Invoice",
                "company": company,
                "supplier": supplier,
                "posting_date": self.booking_date or frappe.utils.today(),
                "due_date": self.booking_date or frappe.utils.today(),
                "items": [
                    {
                        "item_code": "Travel Service",
                        "item_name": "Travel Service",
                        "description": f"Tour Booking: {self.name} — Supplier: {supplier}",
                        "qty": 1,
                        "rate": total_cost,
                        "uom": "Nos",
                    }
                ],
                "custom_tour_booking": self.name,
            })
            pi.flags.ignore_permissions = True
            pi.set_missing_values()
            pi.insert()   # Saved as Draft — NOT submitted intentionally
            purchase_invoices_created[supplier] = pi.name

        # ------------------------------------------------------------------
        # 4. Save reference & User feedback
        # ------------------------------------------------------------------
        # Update unreported items to is_reported = 1
        for f in unreported_flights:
            f.is_reported = 1
            f.sales_invoice = sales_invoice.name
            if f.supplier and f.supplier in purchase_invoices_created:
                f.purchase_invoice = purchase_invoices_created[f.supplier]
        
        for h in unreported_hotels:
            h.is_reported = 1
            h.sales_invoice = sales_invoice.name
            if h.hotel_supplier and h.hotel_supplier in purchase_invoices_created:
                h.purchase_invoice = purchase_invoices_created[h.hotel_supplier]

        self.db_set("sales_invoice_reference", sales_invoice.name)
        
        # Save without triggering validations that might cause recursion
        self.flags.ignore_validate = True
        self.save()

        pi_list = ", ".join(f"<b>{p}</b>" for p in purchase_invoices_created.values())
        frappe.msgprint(
            f"Sales Invoice <b>{sales_invoice.name}</b> and "
            f"Draft Purchase Invoice(s) {pi_list if pi_list else '(none — no suppliers found)'} "
            "have been successfully created.",
            title="Invoices Created",
            indicator="green",
        )
        return sales_invoice.name

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_travel_service_item(self):
        """Creates a generic 'Travel Service' Item in ERPNext if it does not exist for both Sales and Purchasing."""
        if frappe.db.exists("Item", "Travel Service"):
            item = frappe.get_doc("Item", "Travel Service")
            if not item.is_sales_item or not item.is_purchase_item:
                item.is_sales_item = 1
                item.is_purchase_item = 1
                item.save(ignore_permissions=True)
                frappe.db.commit()
            return

        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": "Travel Service",
            "item_name": "Travel Service",
            "item_group": "Services",
            "is_sales_item": 1,
            "is_purchase_item": 1,
            "is_stock_item": 0,
            "stock_uom": "Nos",
        })
        item.flags.ignore_permissions = True
        item.insert()
        frappe.db.commit()

@frappe.whitelist()
def create_invoice_from_report(selected_items):
    """
    selected_items: List of dicts with {name, item_type, booking_ref}
    """
    if isinstance(selected_items, str):
        import json
        selected_items = json.loads(selected_items)

    if not selected_items:
        return "No items selected."

    # Group items by Customer (from Tour Booking)
    customer_items = {} # customer -> list of items info
    
    for item_info in selected_items:
        booking_name = item_info.get("booking_ref")
        if not booking_name:
            continue
            
        customer = frappe.db.get_value("Tour Booking", booking_name, "customer")
        if not customer:
            continue
            
        if customer not in customer_items:
            customer_items[customer] = []
        customer_items[customer].append(item_info)

    created_invoices = []

    for customer, items in customer_items.items():
        # Calculate total selling price for these items
        total_selling = 0
        item_descriptions = []
        
        # Prepare to update items after SI creation
        items_to_update = [] # list of (doctype, name)

        si_items = []

        for item in items:
            dt = "Flight Ticket Item" if item["item_type"] == "Flight Ticket" else "Hotel Reservation Item"
            doc = frappe.get_doc(dt, item["name"])
            
            total_selling += doc.selling_price or 0
            
            if item["item_type"] == "Flight Ticket":
                si_items.append({
                    "item_code": "Travel Service",
                    "item_name": "Flight Ticket",
                    "description": f"Flight: {doc.pax_name} - {doc.ticket_number} (Ref: {item['booking_ref']})",
                    "qty": 1,
                    "rate": doc.selling_price or 0,
                    "uom": "Nos",
                    "custom_passenger_name": doc.pax_name,
                    "custom_ticket_number": doc.ticket_number,
                    "custom_route": doc.flight_route,
                    "custom_airline": doc.airline,
                })
            else:
                si_items.append({
                    "item_code": "Travel Service",
                    "item_name": "Hotel Booking",
                    "description": f"Hotel: {doc.hotel_name} (Ref: {item['booking_ref']})",
                    "qty": 1,
                    "rate": doc.selling_price or 0,
                    "uom": "Nos",
                })
            
            items_to_update.append((dt, item["name"]))

        if total_selling <= 0:
            continue

        company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value('Global Defaults', 'default_company')

        # Create Sales Invoice
        si = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": company,
            "customer": customer,
            "posting_date": frappe.utils.today(),
            "due_date": frappe.utils.today(),
            "items": si_items
        })
        si.set_missing_values()
        si.insert(ignore_permissions=True)
        created_invoices.append(si.name)

        # Update items
        for dt, name in items_to_update:
            frappe.db.set_value(dt, name, {
                "is_reported": 1,
                "sales_invoice": si.name
            })

    if not created_invoices:
        return "No invoices were created (check total amounts)."

    return f"Successfully created {len(created_invoices)} Sales Invoice(s): {', '.join(created_invoices)}"

def sync_financials_with_invoices(doc, method=None):
    """
    Syncs financial updates from the Tour Booking directly to Draft Sales and Purchase Invoices.
    Triggered on_update.
    """
    # Auto-create Sales Invoice on save if not exists (and has items)
    if not doc.sales_invoice_reference and (doc.flights or doc.hotels):
        # Only auto-create if we are not newly created without a name yet
        if doc.name:
            doc.create_sales_invoice()
            # create_sales_invoice saves the doc internally which triggers this again
            return
            
    # 1. Sync Sales Invoice
    if doc.sales_invoice_reference and frappe.db.exists("Sales Invoice", doc.sales_invoice_reference):
        si = frappe.get_doc("Sales Invoice", doc.sales_invoice_reference)
        if si.docstatus == 1:
            frappe.throw(f"Sales Invoice {si.name} is submitted. Please cancel it first to apply financial changes.")
        elif si.docstatus == 0:
            si.set("items", [])
            for flight in doc.flights:
                si.append("items", {
                    "item_code": "Travel Service",
                    "item_name": "Travel Service",
                    "description": f"Ticket No: {flight.ticket_number} | Passenger: {flight.pax_name} | Route: {flight.flight_route}",
                    "qty": 1,
                    "rate": flight.selling_price or 0,
                    "uom": "Nos",
                    "custom_passenger_name": flight.pax_name,
                    "custom_ticket_number": flight.ticket_number,
                    "custom_route": flight.flight_route,
                    "custom_airline": flight.airline,
                })
            for hotel in doc.hotels:
                si.append("items", {
                    "item_code": "Travel Service",
                    "item_name": "Hotel Booking",
                    "description": f"Hotel: {hotel.hotel_name}",
                    "qty": 1,
                    "rate": hotel.selling_price or 0,
                    "uom": "Nos",
                })
            si.set_missing_values()
            si.save(ignore_permissions=True)
            # Use frappe.msgprint directly to signal update
            frappe.msgprint(f"Synced changes to Sales Invoice <b>{si.name}</b>", indicator="green", alert=True)

    # 2. Sync Purchase Invoices
    # Group by (supplier, currency)
    supplier_currency_costs = {}
    for flight in doc.flights:
        sup = flight.supplier
        curr = flight.currency or "LYD" # Default to LYD if not specified
        if sup:
            key = (sup, curr)
            supplier_currency_costs[key] = supplier_currency_costs.get(key, 0.0) + float(flight.net_purchase_price or 0)
            
    for hotel in doc.hotels:
        sup = hotel.hotel_supplier
        curr = hotel.currency or "LYD" # Default to LYD if not specified
        if sup:
            key = (sup, curr)
            supplier_currency_costs[key] = supplier_currency_costs.get(key, 0.0) + float(hotel.purchase_price or 0)

    # Store created/updated PI names for linking
    created_or_updated_pis = {} # (supplier, currency) -> pi_name

    for (supplier, curr), total_cost in supplier_currency_costs.items():
        if total_cost <= 0:
            continue
            
        # Check if PI exists for THIS supplier AND THIS currency
        pi_list = frappe.get_all("Purchase Invoice", filters={
            "custom_tour_booking": doc.name, 
            "supplier": supplier,
            "currency": curr
        })
        
        created_pi_name = None
        if pi_list:
            pi = frappe.get_doc("Purchase Invoice", pi_list[0].name)
            if pi.docstatus == 1:
                frappe.throw(f"Purchase Invoice {pi.name} ({curr}) is submitted. Please cancel it first to apply financial changes.")
            elif pi.docstatus == 0:
                # Update existing draft
                pi.currency = curr # Ensure currency is set correctly
                pi.items = [] # Rebuild items to ensure only one item with updated total cost
                pi.append("items", {
                    "item_code": "Travel Service",
                    "item_name": "Travel Service",
                    "description": f"Tour Booking: {doc.name} — Supplier: {supplier} ({curr})",
                    "qty": 1,
                    "rate": total_cost,
                    "uom": "Nos",
                })
                pi.set_missing_values()
                pi.save(ignore_permissions=True)
                frappe.msgprint(f"Synced changes to Purchase Invoice <b>{pi.name}</b> ({curr})", indicator="green", alert=True)
                created_pi_name = pi.name
        else:
            company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value('Global Defaults', 'default_company')

            # Create new Purchase Invoice if it doesn't exist
            if hasattr(doc, '_ensure_travel_service_item'):
                doc._ensure_travel_service_item()
            
            pi_dict = {
                "doctype": "Purchase Invoice",
                "company": company,
                "supplier": supplier,
                "currency": curr,
                "posting_date": doc.booking_date or frappe.utils.today(),
                "due_date": doc.booking_date or frappe.utils.today(),
                "items": [
                    {
                        "item_code": "Travel Service",
                        "item_name": "Travel Service",
                        "description": f"Tour Booking: {doc.name} — Supplier: {supplier} ({curr})",
                        "qty": 1,
                        "rate": total_cost,
                        "uom": "Nos",
                    }
                ],
                "custom_tour_booking": doc.name,
            }
            
            # --- Auto-Account Selection (Multi-Currency) ---
            # If currency is foreign, ERPNext usually handles it if the supplier has a default account
            # or it uses the company's default payable.
            
            pi = frappe.get_doc(pi_dict)
            pi.flags.ignore_permissions = True
            pi.set_missing_values()
            pi.insert()
            frappe.msgprint(f"Created new Purchase Invoice <b>{pi.name}</b> ({curr})", indicator="green", alert=True)
            created_pi_name = pi.name
            
        # Update row links to point to the correct purchase invoice matching supplier AND currency
        if created_pi_name:
            for flight in doc.flights:
                f_curr = flight.currency or "LYD"
                if flight.supplier == supplier and f_curr == curr:
                    flight.purchase_invoice = created_pi_name
            for hotel in doc.hotels:
                if hotel.hotel_supplier == supplier:
                    hotel.purchase_invoice = created_pi_name

    frappe.db.commit()

@frappe.whitelist()
def manual_sync_invoices(docname):
    doc = frappe.get_doc("Tour Booking", docname)
    sync_financials_with_invoices(doc)
    return "Synced Successfully"



@frappe.whitelist()
def process_air_file(file_url=None):
    from tourism_app.tourism_app.api import process_air_file as api_process
    return api_process(file_url)

@frappe.whitelist()
def import_air_file(content, docname):
    if not content:
        return
    
    doc = frappe.get_doc("Tour Booking", docname)
    rows = parse_air_file(content)
    
    for row in rows:
        # Match Airline Code (e.g., 8U, NB) using the "IATA Code" field
        airline_code = row.get("airline_code")
        airline_name = None

        if airline_code:
            # Correct Search Query: Find the record name (e.g., Air Afriqyah) using iata_code (e.g., 8U)
            airline_name = frappe.db.get_value("Airline", {"iata_code": airline_code}, "name")
            
            if not airline_name:
                # Fallback: check if the name itself is the code (just in case)
                airline_name = frappe.db.get_value("Airline", {"name": airline_code}, "name")
            
            if not airline_name:
                frappe.throw(
                    f"Please ensure an Airline exists with <b>IATA Code: {airline_code}</b> in the Airline master before uploading.", 
                    title="Missing Airline"
                )

        doc.append("flights", {
            "pax_name": row.get("pax_name"),
            "ticket_number": row.get("ticket_number"),
            "ticket_pnr": row.get("pnr"),
            "flight_route": row.get("route"),
            "flight_number": row.get("flight_no"),
            "airline": airline_name,
            "flight_class": row.get("flight_class"),
            "departure_date": row.get("departure_date"),
            "fare": row.get("fare"),
            "tax": row.get("tax"),
            "commission_type": "Percentage",
            "commission_rate": row.get("commission_rate", 0)
        })
    
    doc.save()
    return "Imported Successfully"

def parse_air_file(content):
    lines = content.split('\n')
    
    pax_list = []
    ticket_list = []
    segments = []
    pnr = ""
    published_fare = 0
    total_selling = 0
    commission_rate = 0
    flight_class = ""
    g_route = ""
    currency = ""

    months = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
    }
    current_year = frappe.utils.nowdate()[:4]

    airline_code = ""

    # 1. Parsing lines
    for line in lines:
        line = line.strip()
        if not line: continue

        # A-Line (Airline Primary Source)
        # Format: AFRIQIYAH AIRWAYS;8U
        if line.startswith('A-'):
            a_parts = line[2:].split(';')
            if len(a_parts) >= 2:
                airline_code = a_parts[1][:2].strip()
                print(f"Extracted Airline (A-Line): {airline_code}")

        # Header PNR
        pnr_match = re.search(r'([A-Z0-9]{2})\s+([A-Z0-9]{6})\b', line)
        if pnr_match:
            pnr = pnr_match.group(2)

        # I-Line (Passenger)
        if line.startswith('I-'):
            name_match = re.search(r'I-\d{3};\d{2}([^;]+)', line)
            if name_match:
                pax_name = name_match.group(1).strip()
                pax_name = re.sub(r'(MRS|MR|MSTR|MISS|MS)$', '', pax_name)
                pax_list.append(pax_name)

        # T-Line (Ticket)
        elif line.startswith('T-'):
            t_no = re.sub(r'^T-K', '', line)
            t_no = re.sub(r'[^0-9-]', '', t_no).strip()
            if t_no:
                ticket_list.append(t_no)

        # G-Line (Route - Smart Parsing)
        elif line.startswith('G-'):
            # G-X  ;;TUNMRA;
            g_parts = line[2:].split(';')
            for part in g_parts:
                part = part.strip()
                # A valid route segment should be a multiple of 3 and at least 6 long
                if len(part) >= 6 and len(part) % 3 == 0 and part.isalpha():
                    codes = [part[i:i+3] for i in range(0, len(part), 3)]
                    g_route = "-".join(codes)
                    # Validate codes (informational)
                    for code in codes:
                        if code and not frappe.db.exists("Airport", code):
                            frappe.log_error(f"Airport Code {code} not found in system (G-Line).", "AIR Parser Warning")
                    break

        # H-Line (Segments - Priority Source)
        elif line.startswith('H-'):
            # H-002;003OTUN;TUNIS;MRA;MISURATA;8U 0491 B B 24JUL1930 2250 24JUL;OK02...
            h_parts = line.split(';')
            if len(h_parts) >= 6:
                dep_raw = h_parts[1].strip()
                dep_code_match = re.search(r'([A-Z]{3})$', dep_raw)
                dep_code = dep_code_match.group(1) if dep_code_match else dep_raw[-3:]
                
                arr_code = h_parts[3].strip()[:3]
                
                # Flight Info in parts[5]
                flight_info = h_parts[5].strip()
                # Extremely robust match for: 8U 0491 B B 24JUL
                # Groups: 1: Airline, 2: Flight#, 3: Class, 4: Optional, 5: Day, 6: Month
                f_match = re.search(r'([A-Z0-9]{2})\s*(\d{4})\s*([A-Z])\s*([A-Z]?)\s*(\d{2})([A-Z]{3})', flight_info)
                
                if f_match:
                    found_airline = f_match.group(1)
                    if not airline_code:
                        airline_code = found_airline
                    
                    flight_no = f_match.group(2)
                    f_class_found = f_match.group(3)
                    day = f_match.group(5)
                    month_str = f_match.group(6)
                    
                    if not flight_class: flight_class = f_class_found
                    month_num = months.get(month_str, "01")
                    
                    seg_route = f"{dep_code}-{arr_code}"
                    segments.append({
                        "airline": found_airline,
                        "flight_no": flight_no,
                        "date": f"{current_year}-{month_num}-{day}",
                        "route": seg_route
                    })
                    print(f"DEBUG: Parsed Segment: {found_airline} {flight_no} {seg_route} {day}{month_str}")
            else:
                # Fallback Regex
                h_match = re.search(r';[0-9]*([A-Z]{3});[^;]*;([A-Z]{3});[^;]*;([A-Z0-9]{2})\s*(\d{4})\s*([A-Z])', line)
                if h_match:
                    origin = h_match.group(1)
                    dest = h_match.group(2)
                    a_code = h_match.group(3)
                    f_no = h_match.group(4)
                    segments.append({
                        "airline": a_code,
                        "flight_no": f_no,
                        "date": frappe.utils.today(), # Fallback date
                        "route": f"{origin}-{dest}"
                    })

        # K-Line (Financials)
        elif line.startswith('K-'):
            # Example: K-FTND277.000 ;LYD519.300 ;;;;;;;;;;;LYD694.350 ;1.87469385 ;;
            curr_match = re.findall(r'([A-Z]{3,4})([0-9, ]+\.[0-9]+)', line)
            
            # Map GDS prefixes: FLYD -> LYD, FTND -> TND
            gds_map = {"FLYD": "LYD", "FTND": "TND"}
            
            all_pairs = []
            for c_code, val in curr_match:
                final_curr = gds_map.get(c_code, c_code)
                all_pairs.append({"curr": final_curr, "val": float(val.replace(' ', ''))})
            
            # Priority: "Follow the LYD"
            has_lyd = any(p["curr"] == "LYD" for p in all_pairs)
            target_curr = "LYD" if has_lyd else (all_pairs[0]["curr"] if all_pairs else "")
            
            # Filter pairs by target currency
            relevant_pairs = [p for p in all_pairs if p["curr"] == target_curr]
            
            if len(relevant_pairs) >= 2:
                published_fare = relevant_pairs[0]["val"]
                total_selling = relevant_pairs[-1]["val"] # Usually the last one is the total
                currency = target_curr
            elif relevant_pairs:
                published_fare = relevant_pairs[0]["val"]
                currency = target_curr

        # KFTF-Line (Tax Details)
        elif line.startswith('KFTF'):
            # KFTF; LYD449.900 YQ VA;...
            tax_match = re.findall(r'([A-Z]{3,4})([0-9, ]+\.[0-9]+)', line)
            if tax_match:
                # Pick the tax amount that matches our chosen currency
                for c_code, val in tax_match:
                    final_curr = {"FLYD": "LYD", "FTND": "TND"}.get(c_code, c_code)
                    if final_curr == currency:
                        # We don't overwrite total_selling here, just extract for info if needed
                        pass

        # FM-Line (Commission)
        elif line.startswith('FM'):
            comm_match = re.search(r'FM\*M\*(\d+)', line)
            if comm_match:
                commission_rate = float(comm_match.group(1))

    # 3. Final logic
    # Published Fare: Set to 660.100 (from FLYD)
    # Final Selling Price: Set to 1110.000 (from LYD)
    # Tax Details: Extract 449.900 from 'KFTF; LYD449.900'
    tax = total_selling - published_fare if total_selling > published_fare else 0
    
    # Combined route: MJI-TUN-MJI
    if segments:
        route_nodes = []
        for s in segments:
            parts = s['route'].split('-')
            if not route_nodes:
                route_nodes.extend(parts)
            else:
                # Only add destination if it's different from the last node
                if parts[0] == route_nodes[-1]:
                    route_nodes.append(parts[1])
                else:
                    route_nodes.extend(parts)
        final_route = "-".join(route_nodes)
    else:
        final_route = g_route if g_route else ""

    primary_airline = segments[0]['airline'] if segments else airline_code
    primary_flight = segments[0]['flight_no'] if segments else ""
    primary_date = segments[0]['date'] if segments else None
    return_date = segments[-1]['date'] if len(segments) > 1 else None

    parsed_rows = []
    for i in range(len(pax_list)):
        row = {
            "pax_name": pax_list[i],
            "ticket_number": ticket_list[i] if i < len(ticket_list) else (ticket_list[0] if ticket_list else ""),
            "pnr": pnr,
            "route": final_route,
            "flight_no": primary_flight,
            "airline_code": primary_airline,
            "departure_date": primary_date,
            "return_date": return_date,
            "fare": published_fare,
            "tax": tax,
            "flight_class": flight_class,
            "currency": currency or "LYD",
            "commission_rate": commission_rate
        }
        parsed_rows.append(row)
        
    return parsed_rows
