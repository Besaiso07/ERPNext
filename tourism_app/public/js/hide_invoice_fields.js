frappe.ui.form.on(cur_frm.doctype, {
    refresh: function(frm) {
        if (!frappe.user.has_role('System Manager') && !frappe.user.has_role('Administrator')) {
            // For regular users, if this invoice is linked to a Tour Booking, disable the form
            // so they are forced to use the Tour Booking interface.
            if (frm.doc.custom_tour_booking) {
                frm.set_intro(__("This Invoice is fully managed via Tour Booking. Editing is disabled here to ensure financial sync."), 'blue');
                frm.disable_form();
            }
        }
    }
});
