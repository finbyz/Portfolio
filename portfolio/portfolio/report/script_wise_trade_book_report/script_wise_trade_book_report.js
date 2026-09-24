// Copyright (c) 2026, finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Script-Wise Trade Book Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company"
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "script",
			"label": __("Script"),
			"fieldtype": "Link",
			"options": "Script"
		},
		{
			"fieldname": "segment",
			"label": __("Segment"),
			"fieldtype": "Link",
			"options": "Investment Segment"
		},
		{
			"fieldname": "category",
			"label": __("Category"),
			"fieldtype": "Link",
			"options": "Category"
		},
		{
			"fieldname": "holding_account",
			"label": __("Capital Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function () {
				var company = frappe.query_report.get_filter_value("company");
				var filters = { is_group: 0 };
				if (company) filters.company = company;
				return {
					filters: filters
				};
			}
		},
		{
			"fieldname": "portfolio",
			"label": __("Investment Portfolio"),
			"fieldtype": "Link",
			"options": "Investment Portfolio",
			"get_query": function () {
				var company = frappe.query_report.get_filter_value("company");
				var script = frappe.query_report.get_filter_value("script");
				var filters = { docstatus: 1 };
				if (company) filters.company = company;
				if (script) filters.script = script;
				return { filters: filters };
			}
		}
	],

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "transaction_type") {
			if (value === "Purchase" || value === "Split In") {
				value = `<span class="indicator-pill green">${value}</span>`;
			} else if (value === "Exit / Sale" || value === "Split Out") {
				value = `<span class="indicator-pill orange">${value}</span>`;
			} else if (value === "Opening") {
				value = `<span class="indicator-pill blue">${value}</span>`;
			}
		}

		if (column.fieldname === "balance_qty" && data && data.balance_qty > 0) {
			value = `<strong>${value}</strong>`;
		}

		return value;
	}
};
