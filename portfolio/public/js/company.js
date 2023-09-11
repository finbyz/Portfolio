frappe.ui.form.on('Company', {
    refresh: function(frm) {
		frm.set_query('bank_account', () => {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.name,
					"account_type": "Bank"
				}
			};
		});
        frm.set_query('capital_account', () => {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.name,
					"root_type": "Asset"
				}
			};
		});
        frm.set_query('investment_charges_account', () => {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.name,
					"account_type": "Expense Account"
				}
			};
		});
        frm.set_query('investment_income_account', () => {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.name,
					"account_type": "Income Account"
				}
			};
		});
    }
});