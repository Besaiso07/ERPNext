import frappe

def scaffold_doctypes():
    create_flight_ticket_item()
    create_hotel_reservation_item()
    create_tour_booking()
    frappe.db.commit()
    print("Scaffolding Complete")

def create_flight_ticket_item():
    if not frappe.db.exists("DocType", "Flight Ticket Item"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Flight Ticket Item",
            "module": "Tourism App",
            "custom": 1,
            "istable": 1,
            "naming_rule": "Random",
            "autoname": "hash",
            "fields": [
                {"fieldname": "ticket_pnr", "label": "Ticket Number / PNR", "fieldtype": "Data"},
                {"fieldname": "airline_supplier", "label": "Airline/Supplier", "fieldtype": "Link", "options": "Supplier"},
                {"fieldname": "flight_route", "label": "Route e.g., TIP-IST", "fieldtype": "Data"},
                {"fieldname": "departure_date", "label": "Departure Date", "fieldtype": "Date"},
                {"fieldname": "return_date", "label": "Return Date", "fieldtype": "Date"},
                {"fieldname": "flight_class", "label": "Flight Class", "fieldtype": "Select", "options": "\nEconomy\nBusiness\nFirst"},
                {"fieldname": "flight_number", "label": "Flight Number", "fieldtype": "Data"},
                {"fieldname": "flight_time", "label": "Flight Time", "fieldtype": "Time"},
                {"fieldname": "fare", "label": "Fare", "fieldtype": "Currency"},
                {"fieldname": "tax", "label": "Tax", "fieldtype": "Currency"},
                {"fieldname": "supplier_commission", "label": "Supplier Commission", "fieldtype": "Currency"},
                {"fieldname": "net_purchase_price", "label": "Net Purchase Price", "fieldtype": "Currency", "read_only": 1},
                {"fieldname": "agency_markup", "label": "Agency Commission/Markup", "fieldtype": "Currency"},
                {"fieldname": "selling_price", "label": "Selling Price", "fieldtype": "Currency", "read_only": 1}
            ],
            "permissions": []
        })
        doc.insert(ignore_permissions=True)
        print("Created Flight Ticket Item DocType")

def create_hotel_reservation_item():
    if not frappe.db.exists("DocType", "Hotel Reservation Item"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Hotel Reservation Item",
            "module": "Tourism App",
            "custom": 1,
            "istable": 1,
            "naming_rule": "Random",
            "autoname": "hash",
            "fields": [
                {"fieldname": "hotel_supplier", "label": "Hotel Supplier", "fieldtype": "Link", "options": "Supplier"},
                {"fieldname": "hotel_name", "label": "Hotel Name", "fieldtype": "Data"},
                {"fieldname": "check_in", "label": "Check In", "fieldtype": "Datetime"},
                {"fieldname": "check_out", "label": "Check Out", "fieldtype": "Datetime"},
                {"fieldname": "room_type", "label": "Room Type", "fieldtype": "Data"},
                {"fieldname": "purchase_price", "label": "Net Cost", "fieldtype": "Currency"},
                {"fieldname": "agency_markup", "label": "Agency Commission/Markup", "fieldtype": "Currency"},
                {"fieldname": "selling_price", "label": "Selling Price", "fieldtype": "Currency", "read_only": 1}
            ],
            "permissions": []
        })
        doc.insert(ignore_permissions=True)
        print("Created Hotel Reservation Item DocType")

def create_tour_booking():
    if not frappe.db.exists("DocType", "Tour Booking"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "Tour Booking",
            "module": "Tourism App",
            "custom": 1,
            "is_submittable": 1,
            "naming_rule": "By \"Naming Series\" field",
            "autoname": "naming_series:",
            "fields": [
                {"fieldname": "naming_series", "label": "Naming Series", "fieldtype": "Select", "options": "TOUR-.YYYY.-"},
                {"fieldname": "customer", "label": "Customer", "fieldtype": "Link", "options": "Customer", "reqd": 1},
                {"fieldname": "booking_date", "label": "Booking Date", "fieldtype": "Date", "default": "Today"},
                {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Draft\nConfirmed\nCancelled", "default": "Draft"},
                {"fieldname": "flights_section", "fieldtype": "Section Break", "label": "Flights"},
                {"fieldname": "flights", "label": "Flights", "fieldtype": "Table", "options": "Flight Ticket Item"},
                {"fieldname": "hotels_section", "fieldtype": "Section Break", "label": "Hotels"},
                {"fieldname": "hotels", "label": "Hotels", "fieldtype": "Table", "options": "Hotel Reservation Item"},
                {"fieldname": "totals_section", "fieldtype": "Section Break", "label": "Totals"},
                {"fieldname": "total_cost", "label": "Total Cost", "fieldtype": "Currency", "read_only": 1},
                {"fieldname": "total_selling_amount", "label": "Total Selling Amount", "fieldtype": "Currency", "read_only": 1},
                {"fieldname": "total_profit", "label": "Total Profit", "fieldtype": "Currency", "read_only": 1}
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1}]
        })
        doc.insert(ignore_permissions=True)
        print("Created Tour Booking DocType")
