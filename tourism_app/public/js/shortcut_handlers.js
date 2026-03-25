/**
 * Tourism App: Global Shortcut Handlers
 * Intercepts workspace shortcut clicks for custom actions like AIR File Import.
 */
$(document).on('click', '.shortcut-widget-box', function(e) {
    var label = $(this).find('.ellipsis').text().trim();
    
    if (label === 'Import AIR File') {
        e.preventDefault();
        e.stopPropagation();
        
        let d = new frappe.ui.Dialog({
            title: __('Upload AIR File'),
            fields: [
                {
                    label: __('Customer (Optional)'),
                    fieldname: 'customer',
                    fieldtype: 'Link',
                    options: 'Customer',
                    description: __('Leave blank if the AIR file contains an RM*AN code for auto-detection.')
                },
                {
                    label: __('AIR File'),
                    fieldname: 'air_file',
                    fieldtype: 'Attach',
                    reqd: 1,
                    description: __('Upload the .txt AIR file from your ticketing system.')
                }
            ],
            primary_action_label: __('Process & Create Booking'),
            primary_action(values) {
                if (!values.air_file) {
                    frappe.msgprint(__('Please attach an AIR file.'));
                    return;
                }
                d.hide();
                frappe.call({
                    method: 'tourism_app.tourism_app.api.process_air_file',
                    args: {
                        file_url: values.air_file,
                        customer: values.customer || ''
                    },
                    freeze: true,
                    freeze_message: __('Processing AIR File...'),
                    callback: function(r) {
                        if (r.message) {
                            frappe.set_route('Form', 'Tour Booking', r.message);
                        }
                    }
                });
            }
        });
        d.show();
        return false;
    }
});
