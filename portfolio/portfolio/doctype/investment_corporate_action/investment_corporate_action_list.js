// Copyright (c) 2026, Finbyz Tech Pvt Ltd and contributors
// For license information, please see license.txt

frappe.listview_settings['Investment Corporate Action'] = {
	onload: function(listview) {
		listview.page.clear_primary_action();
		if (listview.page.btn_primary) {
			listview.page.btn_primary.hide();
		}
	},
	refresh: function(listview) {
		listview.page.clear_primary_action();
		if (listview.page.btn_primary) {
			listview.page.btn_primary.hide();
		}
		// Also strip duplicate / new entry from menu
		setTimeout(() => {
			if (listview.page.btn_primary) {
				listview.page.btn_primary.hide();
			}
			if (listview.page.menu) {
				listview.page.menu.find(`[data-label="${__('New Investment Corporate Action')}"]`).parent().remove();
			}
		}, 100);
	}
};
