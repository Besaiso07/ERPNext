# Copyright (c) 2026, Tourism App
# License: MIT

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
            commission = flight.supplier_commission or 0
            markup = flight.agency_markup or 0

            flight.net_purchase_price = (fare + tax) - commission
            flight.selling_price = flight.net_purchase_price + markup
            flight.profit = flight.selling_price - flight.net_purchase_price

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
        if self.sales_invoice_reference:
            frappe.throw("An invoice is already linked to this booking.")

        # ------------------------------------------------------------------
        # 1. Sales Invoice
        # ------------------------------------------------------------------
        self._ensure_tour_package_item()

        sales_invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": self.customer,
            "posting_date": self.booking_date or frappe.utils.today(),
            "due_date": self.booking_date or frappe.utils.today(),
            "items": [
                {
                    "item_code": "Tour Package",
                    "item_name": "Tour Package",
                    "description": f"Tour Booking: {self.name}",
                    "qty": 1,
                    "rate": self.total_selling_amount or 0,
                    "uom": "Nos",
                }
            ],
            "custom_tour_booking": self.name,
        })
        sales_invoice.flags.ignore_permissions = True
        sales_invoice.insert()

        # ------------------------------------------------------------------
        # 2. Group supplier costs
        # ------------------------------------------------------------------
        supplier_costs = {}

        # Flight rows — key: airline_supplier, value: net_purchase_price
        for flight in self.flights:
            supplier = flight.airline_supplier
            if not supplier:
                continue
            cost = flight.net_purchase_price or 0
            supplier_costs[supplier] = supplier_costs.get(supplier, 0) + cost

        # Hotel rows — key: hotel_supplier, value: purchase_price
        for hotel in self.hotels:
            supplier = hotel.hotel_supplier
            if not supplier:
                continue
            cost = hotel.purchase_price or 0
            supplier_costs[supplier] = supplier_costs.get(supplier, 0) + cost

        # ------------------------------------------------------------------
        # 3. Create one Draft Purchase Invoice per unique supplier
        # ------------------------------------------------------------------
        self._ensure_tour_cost_item()

        purchase_invoices_created = []
        for supplier, total_cost in supplier_costs.items():
            if total_cost <= 0:
                continue

            pi = frappe.get_doc({
                "doctype": "Purchase Invoice",
                "supplier": supplier,
                "posting_date": self.booking_date or frappe.utils.today(),
                "due_date": self.booking_date or frappe.utils.today(),
                "items": [
                    {
                        "item_code": "Tour Cost",
                        "item_name": "Tour Cost",
                        "description": f"Tour Booking: {self.name} — Supplier: {supplier}",
                        "qty": 1,
                        "rate": total_cost,
                        "uom": "Nos",
                    }
                ],
            })
            pi.flags.ignore_permissions = True
            pi.insert()   # Saved as Draft — NOT submitted intentionally
            purchase_invoices_created.append(pi.name)

        # ------------------------------------------------------------------
        # 4. Save reference & User feedback
        # ------------------------------------------------------------------
        self.db_set("sales_invoice_reference", sales_invoice.name)

        pi_list = ", ".join(f"<b>{p}</b>" for p in purchase_invoices_created)
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
    def _ensure_tour_package_item(self):
        """Creates a generic 'Tour Package' Item in ERPNext if it does not exist."""
        if frappe.db.exists("Item", "Tour Package"):
            return

        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": "Tour Package",
            "item_name": "Tour Package",
            "item_group": "Services",
            "is_sales_item": 1,
            "is_stock_item": 0,
            "stock_uom": "Nos",
        })
        item.flags.ignore_permissions = True
        item.insert()
        frappe.db.commit()

    def _ensure_tour_cost_item(self):
        """Creates a generic 'Tour Cost' Item in ERPNext if it does not exist (used for Purchase Invoices)."""
        if frappe.db.exists("Item", "Tour Cost"):
            return

        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": "Tour Cost",
            "item_name": "Tour Cost",
            "item_group": "Services",
            "is_purchase_item": 1,
            "is_stock_item": 0,
            "stock_uom": "Nos",
        })
        item.flags.ignore_permissions = True
        item.insert()
        frappe.db.commit()
