# Copyright (c) 2026, finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate
import erpnext


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	data, report_summary = get_data(filters)
	chart = get_chart(data, filters)
	return columns, data, None, chart, report_summary


def get_columns(filters):
	currency = get_company_currency(filters.get("company"))
	return [
		{
			"label": _("Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 105,
		},
		{
			"label": _("Script"),
			"fieldname": "script",
			"fieldtype": "Link",
			"options": "Script",
			"width": 140,
		},
		{
			"label": _("Script Name"),
			"fieldname": "script_name",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Link",
			"options": "Investment Portfolio",
			"width": 120,
		},
		{
			"label": _("Transaction Type"),
			"fieldname": "transaction_type",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 130,
		},
		{
			"label": _("Segment"),
			"fieldname": "segment",
			"fieldtype": "Link",
			"options": "Investment Segment",
			"width": 120,
		},
		{
			"label": _("Category"),
			"fieldname": "category",
			"fieldtype": "Link",
			"options": "Category",
			"width": 110,
		},
		{
			"label": _("Capital Account"),
			"fieldname": "holding_account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 140,
		},
		{
			"label": _("In Qty"),
			"fieldname": "in_qty",
			"fieldtype": "Float",
			"precision": 4,
			"width": 90,
		},
		{
			"label": _("In Rate"),
			"fieldname": "in_rate",
			"fieldtype": "Currency",
			"options": "currency",
			"precision": 4,
			"width": 100,
		},
		{
			"label": _("In Value"),
			"fieldname": "in_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 115,
		},
		{
			"label": _("Out Qty"),
			"fieldname": "out_qty",
			"fieldtype": "Float",
			"precision": 4,
			"width": 90,
		},
		{
			"label": _("Out Rate"),
			"fieldname": "out_rate",
			"fieldtype": "Currency",
			"options": "currency",
			"precision": 4,
			"width": 100,
		},
		{
			"label": _("Out Value"),
			"fieldname": "out_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 115,
		},
		{
			"label": _("Balance Qty"),
			"fieldname": "balance_qty",
			"fieldtype": "Float",
			"precision": 4,
			"width": 105,
		},
		{
			"label": _("Valuation / Avg Rate"),
			"fieldname": "balance_rate",
			"fieldtype": "Currency",
			"options": "currency",
			"precision": 4,
			"width": 135,
		},
		{
			"label": _("Balance Value"),
			"fieldname": "balance_value",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 125,
		},
		{
			"label": _("JV Reference"),
			"fieldname": "jv_reference",
			"fieldtype": "Link",
			"options": "Journal Entry",
			"width": 125,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]


def get_data(filters):
	company_currency = get_company_currency(filters.get("company"))
	from_date = getdate(filters.get("from_date")) if filters.get("from_date") else None
	to_date = getdate(filters.get("to_date")) if filters.get("to_date") else None

	all_raw_entries = get_all_raw_transactions(filters)
	script_names_map = get_script_names_map()

	# Group raw entries by script
	entries_by_script = {}
	for row in all_raw_entries:
		s = row.get("script") or "Unknown"
		entries_by_script.setdefault(s, []).append(row)

	data = []
	total_in_qty = 0.0
	total_in_amount = 0.0
	total_out_qty = 0.0
	total_out_amount = 0.0
	total_realized_pnl = 0.0
	final_bal_qty = 0.0
	final_bal_val = 0.0

	# Sort scripts alphabetically for consistent reporting
	for scrip in sorted(entries_by_script.keys()):
		script_entries = entries_by_script[scrip]
		# Sort by posting_date asc, inward before outward on same date, voucher_no asc
		script_entries.sort(
			key=lambda x: (
				getdate(x.get("posting_date")) if x.get("posting_date") else getdate("1900-01-01"),
				0 if x.get("is_inward") else 1,
				str(x.get("voucher_no")),
			)
		)

		running_qty = 0.0
		running_value = 0.0
		avg_rate = 0.0

		opening_qty = 0.0
		opening_value = 0.0
		opening_avg_rate = 0.0

		visible_entries = []

		for entry in script_entries:
			e_date = getdate(entry.get("posting_date")) if entry.get("posting_date") else None
			in_qty = flt(entry.get("in_qty"))
			in_rate = flt(entry.get("in_rate"))
			in_amount = flt(entry.get("in_amount")) or (in_qty * in_rate)
			out_qty = flt(entry.get("out_qty"))
			out_rate = flt(entry.get("out_rate"))
			out_amount = flt(entry.get("out_amount")) or (out_qty * out_rate)
			realized_pnl = 0.0

			# Calculate running balances
			if in_qty > 0:
				running_qty += in_qty
				running_value += in_amount
				avg_rate = running_value / running_qty if running_qty > 0 else 0.0
			elif out_qty > 0:
				# Cost basis of outward shares
				cost_of_out = out_qty * avg_rate
				realized_pnl = flt(entry.get("net_exit_amount") or out_amount) - cost_of_out
				running_qty -= out_qty
				if running_qty <= 0.00001:
					running_qty = 0.0
					running_value = 0.0
					avg_rate = 0.0
				else:
					running_value -= out_amount
					if running_value < 0:
						running_value = 0.0
					avg_rate = running_value / running_qty if running_qty > 0 else 0.0

			# Check if before from_date
			if from_date and e_date and e_date < from_date:
				opening_qty = running_qty
				opening_value = running_value
				opening_avg_rate = avg_rate
				continue

			# Check if after to_date
			if to_date and e_date and e_date > to_date:
				continue

			row = {
				"posting_date": entry.get("posting_date"),
				"script": scrip,
				"script_name": script_names_map.get(scrip, scrip),
				"voucher_type": entry.get("voucher_type"),
				"voucher_no": entry.get("voucher_no"),
				"transaction_type": entry.get("transaction_type"),
				"company": entry.get("company"),
				"segment": entry.get("segment"),
				"category": entry.get("category"),
				"holding_account": entry.get("holding_account"),
				"in_qty": in_qty if in_qty else None,
				"in_rate": in_rate if in_qty else None,
				"in_amount": in_amount if in_qty else None,
				"out_qty": out_qty if out_qty else None,
				"out_rate": out_rate if out_qty else None,
				"out_amount": out_amount if out_qty else None,
				"balance_qty": running_qty,
				"balance_rate": avg_rate,
				"balance_value": running_value,
				"jv_reference": entry.get("jv_reference"),
				"currency": company_currency,
			}

			total_in_qty += in_qty
			total_in_amount += in_amount
			total_out_qty += out_qty
			total_out_amount += out_amount

			visible_entries.append(row)

		# If we have an opening balance and any visible entries or filters applied
		if (from_date and opening_qty > 0) or visible_entries:
			if from_date and opening_qty > 0:
				opening_row = {
					"posting_date": from_date,
					"script": scrip,
					"script_name": script_names_map.get(scrip, scrip),
					"voucher_type": _("Opening Balance"),
					"voucher_no": None,
					"transaction_type": _("Opening"),
					"company": filters.get("company"),
					"segment": visible_entries[0].get("segment") if visible_entries else None,
					"category": visible_entries[0].get("category") if visible_entries else None,
					"holding_account": visible_entries[0].get("holding_account") if visible_entries else None,
					"in_qty": None,
					"in_rate": None,
					"in_amount": None,
					"out_qty": None,
					"out_rate": None,
					"out_amount": None,
					"balance_qty": opening_qty,
					"balance_rate": opening_avg_rate,
					"balance_value": opening_value,
					"jv_reference": None,
					"currency": company_currency,
				}
				data.append(opening_row)

			data.extend(visible_entries)
			final_bal_qty += running_qty
			final_bal_val += running_value

	report_summary = [
		{
			"value": final_bal_qty,
			"label": _("Closing Balance Qty"),
			"datatype": "Float",
			"precision": 4,
		},
		{
			"value": final_bal_val,
			"label": _("Closing Balance Value"),
			"datatype": "Currency",
			"currency": company_currency,
		},
		{
			"value": total_in_qty,
			"label": _("Total Inward Qty"),
			"datatype": "Float",
			"precision": 4,
		},
		{
			"value": total_in_amount,
			"label": _("Total Inward Amount"),
			"datatype": "Currency",
			"currency": company_currency,
		},
		{
			"value": total_out_qty,
			"label": _("Total Outward Qty"),
			"datatype": "Float",
			"precision": 4,
		},
		{
			"value": total_out_amount,
			"label": _("Total Outward Amount"),
			"datatype": "Currency",
			"currency": company_currency,
		},
	]

	return data, report_summary


def get_all_raw_transactions(filters):
	"""
	Collects both inward transactions (from tabInvestment Portfolio)
	and outward transactions (from tabInvestment Portfolio Segment and Split).
	"""
	entries = []

	# Build filters for Investment Portfolio
	conditions = ["p.docstatus = 1"]
	query_params = {}

	if filters.get("company"):
		conditions.append("p.company = %(company)s")
		query_params["company"] = filters.get("company")

	if filters.get("script"):
		conditions.append("p.script = %(script)s")
		query_params["script"] = filters.get("script")

	if filters.get("segment"):
		conditions.append("p.segment = %(segment)s")
		query_params["segment"] = filters.get("segment")

	if filters.get("category"):
		conditions.append("p.category = %(category)s")
		query_params["category"] = filters.get("category")

	if filters.get("holding_account"):
		conditions.append("p.holding_account = %(holding_account)s")
		query_params["holding_account"] = filters.get("holding_account")

	if filters.get("portfolio"):
		conditions.append("p.name = %(portfolio)s")
		query_params["portfolio"] = filters.get("portfolio")

	where_clause = " AND ".join(conditions)

	# 1. Inward Purchases / Investments
	inward_query = f"""
		SELECT
			p.name AS voucher_no,
			'Investment Portfolio' AS voucher_type,
			p.posting_date,
			p.script,
			p.company,
			p.segment,
			p.category,
			p.holding_account,
			p.qty AS in_qty,
			p.entry_price AS in_rate,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS in_amount,
			0.0 AS out_qty,
			0.0 AS out_rate,
			0.0 AS out_amount,
			p.jv_of_entry AS jv_reference,
			CASE
				WHEN p.split_from IS NOT NULL AND p.split_from != '' THEN 'Split In'
				ELSE 'Purchase'
			END AS transaction_type,
			1 AS is_inward
		FROM `tabInvestment Portfolio` p
		WHERE {where_clause}
	"""

	inwards = frappe.db.sql(inward_query, query_params, as_dict=True)
	entries.extend(inwards)

	# 2. Outward Sales / Exits from child table tabInvestment Portfolio Segment
	exit_query = f"""
		SELECT
			p.name AS voucher_no,
			'Portfolio Exit' AS voucher_type,
			s.exit_date AS posting_date,
			p.script,
			p.company,
			p.segment,
			p.category,
			p.holding_account,
			0.0 AS in_qty,
			0.0 AS in_rate,
			0.0 AS in_amount,
			s.exit_qty AS out_qty,
			s.exit_price AS out_rate,
			COALESCE(s.exit_amount, s.exit_qty * s.exit_price) AS out_amount,
			s.net_exit_amount,
			s.jv_of_exit AS jv_reference,
			'Exit / Sale' AS transaction_type,
			0 AS is_inward
		FROM `tabInvestment Portfolio Segment` s
		INNER JOIN `tabInvestment Portfolio` p ON s.parent = p.name
		WHERE {where_clause}
	"""

	exits = frappe.db.sql(exit_query, query_params, as_dict=True)
	entries.extend(exits)

	# 3. Handle Split Out (when an investment is split into new portfolios)
	split_query = f"""
		SELECT
			p.name AS voucher_no,
			'Portfolio Split' AS voucher_type,
			DATE(p.modified) AS posting_date,
			p.script,
			p.company,
			p.segment,
			p.category,
			p.holding_account,
			0.0 AS in_qty,
			0.0 AS in_rate,
			0.0 AS in_amount,
			p.qty AS out_qty,
			p.entry_price AS out_rate,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS out_amount,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS net_exit_amount,
			p.jv_of_entry AS jv_reference,
			'Split Out' AS transaction_type,
			0 AS is_inward
		FROM `tabInvestment Portfolio` p
		WHERE {where_clause}
			AND p.status = 'Exited'
			AND (SELECT COUNT(*) FROM `tabInvestment Portfolio Split` sp WHERE sp.parent = p.name) > 0
			AND (SELECT COUNT(*) FROM `tabInvestment Portfolio Segment` seg WHERE seg.parent = p.name) = 0
	"""

	try:
		splits = frappe.db.sql(split_query, query_params, as_dict=True)
		entries.extend(splits)
	except Exception:
		pass

	return entries


def get_script_names_map():
	res = frappe.get_all("Script", fields=["name", "script_name"])
	return {r.name: (r.script_name or r.name) for r in res}


def get_company_currency(company):
	if company:
		return erpnext.get_company_currency(company)
	return frappe.db.get_single_value("Global Defaults", "default_currency") or "INR"


def get_chart(data, filters):
	if not data:
		return None

	# Balance quantity or value by script
	script_values = {}
	for row in data:
		scrip = row.get("script")
		if scrip and row.get("balance_value") is not None:
			script_values[scrip] = flt(row.get("balance_value"))

	# Sort and take top 10
	top_scripts = sorted(script_values.items(), key=lambda x: x[1], reverse=True)[:10]
	if not top_scripts:
		return None

	labels = [x[0] for x in top_scripts]
	values = [x[1] for x in top_scripts]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Balance Value"),
					"values": values,
				}
			],
		},
		"type": "bar",
		"colors": ["#5e64ff"],
	}
