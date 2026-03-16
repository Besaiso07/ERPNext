// Copyright (c) 2026, Tourism App and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tour Booking', {
    refresh: function(frm) {
        // Show "Create Sales Invoice" button if no reference exists and document is saved
        if (!frm.doc.__islocal && !frm.doc.sales_invoice_reference) {
            frm.add_custom_button(__('Create Sales Invoice'), function() {
                frappe.call({
                    method: 'create_sales_invoice',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Creating Invoices...'),
                    callback: function(r) {
                        if (!r.exc && r.message) {
                            frm.reload_doc();
                            frappe.set_route('Form', 'Sales Invoice', r.message);
                        }
                    }
                });
            }).addClass('btn-primary');
        }

        // Show "Unlink Invoice" button if reference exists
        if (!frm.doc.__islocal && frm.doc.sales_invoice_reference) {
            frm.add_custom_button(__('Unlink Invoice'), function() {
                frappe.db.get_value('Sales Invoice', frm.doc.sales_invoice_reference, 'docstatus', function(r) {
                    if (r && r.docstatus === 2) {
                        frm.set_value('sales_invoice_reference', '');
                        frm.save().then(() => {
                            frm.reload_doc();
                        });
                    } else {
                        frappe.msgprint(__('You must Cancel the linked Sales Invoice in the Accounting module before unlinking it here.'));
                    }
                });
            }).addClass('btn-danger');
        }
    }
});
