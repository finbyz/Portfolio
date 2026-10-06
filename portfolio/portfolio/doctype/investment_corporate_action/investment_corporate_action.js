// Copyright (c) 2026, Finbyz Tech Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investment Corporate Action", {
	refresh(frm) {
		// When document is cancelled, remove the primary "Amend" button
		if (frm.doc.docstatus === 2) {
			frm.page.clear_primary_action();
			frm.page.clear_secondary_action();
			if (frm.page.btn_primary) {
				frm.page.btn_primary.hide();
			}
		}

		// Remove Amend and Delete buttons/menus across all states
		frm.page.remove_inner_button(__("Amend"));
		if (frm.page.btn_secondary) {
			frm.page.btn_secondary.filter(function() {
				return $(this).text().trim() === __("Amend");
			}).remove();
		}

		setTimeout(() => {
			if (frm.doc.docstatus === 2 && frm.page.btn_primary) {
				frm.page.btn_primary.hide();
			}
			if (frm.page.menu) {
				frm.page.menu.find(`[data-label="${__('Delete')}"]`).parent().remove();
				frm.page.menu.find(`[data-label="${__('Amend')}"]`).parent().remove();
				frm.page.menu.find(`[data-label="${__('Duplicate')}"]`).parent().remove();
				frm.page.menu.find(`[data-label="${__('New Investment Corporate Action')}"]`).parent().remove();
			}
		}, 100);
	}
});
