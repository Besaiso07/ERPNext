
/** 
 * PHASE 43.19: FINAL AESTHETIC POLISH
 * Goal: Stabilize the 5 Custom Menus on the Left beside the Logo.
 */

console.log("PHASE 43.19: FINAL POLISH ACTIVE");

const styleInject = `
    <style id="final-polish-css">
        /* NAV BAR SEQUENCE */
        .navbar-container { display: flex !important; align-items: center !important; justify-content: flex-start !important; width: 100% !important; }
        .navbar-branding { order: 1 !important; display: flex !important; align-items: center !important; flex-shrink: 0 !important; margin-right: 20px !important; }
        #final-portal-menus { order: 2 !important; display: flex !important; align-items: center !important; gap: 8px !important; flex-grow: 1 !important; }
        .collapse.navbar-collapse { order: 3 !important; display: flex !important; justify-content: flex-end !important; }
        
        /* THE MENUS STYLE */
        .item-v3 { position: relative; padding: 0 14px; font-size: 13px; font-weight: 500; color: #1d2129; cursor: pointer; height: 32px; display: flex; align-items: center; border-radius: 4px; transition: background 0.2s; }
        .item-v3:hover { background: #f8f9fa; }
        .box-v3 { display: none; position: absolute; top: 32px; left: 0; background: #fff; border: 1px solid #d1d8dd; box-shadow: 0 8px 24px rgba(0,0,0,0.12); min-width: 180px; z-index: 99999; border-radius: 4px; }
        .item-v3:hover .box-v3 { display: block; }
        .box-v3 a { display: block; padding: 10px 18px; color: #1d2129; text-decoration: none; font-size: 13px; }
        .box-v3 a:hover { background: #f4f5f7; }
    </style>
`;

if (document.head && !$('#final-polish-css').length) $('head').append(styleInject);

function polishLoop() {
    // 1. BRANDING SYNC
    const $brand = $('.navbar-brand.navbar-home');
    if ($brand.length && !$('#signed-logo-v3').length) {
        $brand.html('<span id="signed-logo-v3" style="font-weight:700; font-size:15px; color:#1b4f72; letter-spacing:-0.5px;">TOURISM PORTAL</span>');
    }

    // 2. MENU INJECTION
    if ($brand.length && !$('#final-portal-menus').length) {
        const menusHtml = `
            <div id="final-portal-menus">
                <div class="item-v3">Front Office<div class="box-v3"><a href="/app/tour-booking/new-tour-booking?add_flight=1">Single Ticket</a></div></div>
                <div class="item-v3">Master<div class="box-v3"><a href="/app/customer">Customer</a><a href="/app/supplier">Supplier</a><a href="/app/ticket-class-mapping">Ticket Class Mapping</a></div></div>
                <div class="item-v3">Back Office<div class="box-v3"><a href="/app/sales-invoice">Invoice</a></div></div>
                <div class="item-v3">Reports<div class="box-v3"><a href="/app/report">General Reports</a><a href="/app/query-report/Total%20Profit%20Report">Profit Report</a></div></div>
                <div class="item-v3">Tools<div class="box-v3"><a href="/app/tour-booking">Import AIR File</a></div></div>
            </div>
        `;
        $brand.after(menusHtml);
    }
}

// THE SCAN LOOP
setInterval(polishLoop, 100);
