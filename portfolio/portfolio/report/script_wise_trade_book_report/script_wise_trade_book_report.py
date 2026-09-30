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
			"label": _("Split / Bonus"),
			"fieldname": "split_bonus",
			"fieldtype": "Data",
			"width": 170,
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
			"label": _("Purchase Rate"),
			"fieldname": "purchase_rate",
			"fieldtype": "Currency",
			"options": "currency",
			"precision": 4,
			"width": 110,
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
			"label": _("Charges"),
			"fieldname": "charges",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110,
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

	# Group raw entries by (company, script)
	grouped_entries = {}
	for row in all_raw_entries:
		comp = row.get("company") or filters.get("company") or ""
		s = row.get("script") or "Unknown"
		key = (comp, s)
		grouped_entries.setdefault(key, []).append(row)

	data = []
	total_in_qty = 0.0
	total_in_amount = 0.0
	total_out_qty = 0.0
	total_out_amount = 0.0
	total_charges = 0.0
	final_bal_qty = 0.0
	final_bal_val = 0.0

	# Sort by company and script for consistent reporting
	for key in sorted(grouped_entries.keys(), key=lambda x: (x[0] or "", x[1] or "")):
		comp, scrip = key
		script_entries = grouped_entries[key]
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

		visible_entries = []
		opening_qty = 0.0
		opening_value = 0.0
		opening_rate = 0.0
		has_opening = False

		for entry in script_entries:
			e_date = getdate(entry.get("posting_date")) if entry.get("posting_date") else None
			if to_date and e_date and e_date > to_date:
				continue

			in_qty = flt(entry.get("in_qty"))
			in_rate = flt(entry.get("in_rate"))
			in_amount = flt(entry.get("in_amount")) or (in_qty * in_rate)
			out_qty = flt(entry.get("out_qty"))
			out_rate = flt(entry.get("out_rate"))
			out_amount = flt(entry.get("out_amount")) or (out_qty * out_rate)

			charges = None
			if entry.get("is_inward"):
				entry_charges = flt(entry.get("entry_charges"))
				if entry_charges:
					charges = entry_charges
			else:
				exit_charges = flt(entry.get("exit_charges"))
				if not exit_charges and flt(entry.get("out_amount")) and flt(entry.get("net_exit_amount")):
					diff = flt(entry.get("out_amount")) - flt(entry.get("net_exit_amount"))
					if diff > 0:
						exit_charges = diff
				if exit_charges:
					charges = exit_charges

			cost_amt = flt(entry.get("cost_amount")) or (out_qty * flt(entry.get("entry_price")))

			# Calculate running balances
			if in_qty > 0:
				running_qty += in_qty
				running_value += in_amount
				avg_rate = running_value / running_qty if running_qty > 0 else 0.0
			elif out_qty > 0:
				# Cost basis of outward shares
				cost_basis = cost_amt if cost_amt > 0 else (out_qty * avg_rate)
				running_qty -= out_qty
				if running_qty <= 0.00001:
					running_qty = 0.0
					running_value = 0.0
					avg_rate = 0.0
				else:
					running_value -= cost_basis
					if running_value < 0:
						running_value = 0.0
					avg_rate = running_value / running_qty if running_qty > 0 else 0.0

			row_comp = entry.get("company") or comp
			row_currency = get_company_currency(row_comp) if row_comp else company_currency

			if from_date and e_date and e_date < from_date:
				opening_qty = running_qty
				opening_value = running_value
				opening_rate = avg_rate
				has_opening = True
				continue

			# If this is the first visible transaction in the period and there was an opening balance
			if from_date and has_opening and opening_qty > 0 and not visible_entries:
				visible_entries.append({
					"posting_date": from_date,
					"script": scrip,
					"script_name": script_names_map.get(scrip, scrip),
					"voucher_type": None,
					"voucher_no": None,
					"transaction_type": "Opening",
					"split_bonus": "",
					"company": row_comp,
					"segment": entry.get("segment"),
					"category": entry.get("category"),
					"holding_account": entry.get("holding_account"),
					"in_qty": None,
					"purchase_rate": None,
					"in_rate": None,
					"in_amount": None,
					"charges": None,
					"out_qty": None,
					"out_rate": None,
					"out_amount": None,
					"balance_qty": opening_qty,
					"balance_rate": opening_rate,
					"balance_value": opening_value,
					"jv_reference": None,
					"currency": row_currency,
				})

			purchase_rate = None
			if in_qty:
				purchase_rate = flt(entry.get("purchase_rate")) if entry.get("purchase_rate") else in_rate

			split_val = entry.get("split") or ""
			is_bonus = 1 if entry.get("is_bonus_applied") else 0

			split_bonus = ""
			if split_val == "Split In" and is_bonus:
				split_bonus = "Split In / Bonus"
			elif split_val == "Split In":
				split_bonus = "Split In"
			elif split_val == "Split Out":
				split_bonus = "Split Out"
			elif is_bonus:
				split_bonus = "Bonus"

			row = {
				"posting_date": entry.get("posting_date"),
				"script": scrip,
				"script_name": script_names_map.get(scrip, scrip),
				"voucher_type": entry.get("voucher_type"),
				"voucher_no": entry.get("voucher_no"),
				"transaction_type": entry.get("transaction_type"),
				"split_bonus": split_bonus,
				"company": row_comp,
				"segment": entry.get("segment"),
				"category": entry.get("category"),
				"holding_account": entry.get("holding_account"),
				"in_qty": in_qty if in_qty else None,
				"purchase_rate": purchase_rate,
				"in_rate": in_rate if in_qty else None,
				"in_amount": in_amount if in_qty else None,
				"charges": charges if charges else None,
				"out_qty": out_qty if out_qty else None,
				"out_rate": out_rate if out_qty else None,
				"out_amount": out_amount if out_qty else None,
				"balance_qty": running_qty,
				"balance_rate": avg_rate,
				"balance_value": running_value,
				"jv_reference": entry.get("jv_reference"),
				"currency": row_currency,
			}

			total_in_qty += in_qty
			total_in_amount += in_amount
			total_out_qty += out_qty
			total_out_amount += out_amount
			if charges:
				total_charges += charges

			visible_entries.append(row)

		if visible_entries:
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
		{
			"value": total_charges,
			"label": _("Total Charges"),
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

	to_date_inward_cond = ""
	to_date_exit_cond = ""
	to_date_split_cond = ""

	if filters.get("to_date"):
		query_params["to_date"] = filters.get("to_date")
		to_date_inward_cond = " AND p.posting_date <= %(to_date)s"
		to_date_exit_cond = " AND s.exit_date <= %(to_date)s"
		to_date_split_cond = " AND DATE(p.modified) <= %(to_date)s"

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
			p.entry_price AS entry_price,
			COALESCE(p.purchase_entry_price, p.entry_price) AS purchase_rate,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS cost_amount,
			p.qty AS in_qty,
			p.entry_price AS in_rate,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS in_amount,
			COALESCE(p.entry_charges, 0.0) AS entry_charges,
			0.0 AS exit_charges,
			0.0 AS out_qty,
			0.0 AS out_rate,
			0.0 AS out_amount,
			p.jv_of_entry AS jv_reference,
			CASE
				WHEN p.split_from IS NOT NULL AND p.split_from != '' THEN 'Split In'
				ELSE 'Purchase'
			END AS transaction_type,
			CASE
				WHEN p.split_from IS NOT NULL AND p.split_from != '' THEN 'Split In'
				ELSE ''
			END AS split,
			COALESCE(p.is_bonus_applied, CASE WHEN p.ratio > 0 OR p.bonus_date IS NOT NULL THEN 1 ELSE 0 END) AS is_bonus_applied,
			1 AS is_inward
		FROM `tabInvestment Portfolio` p
		WHERE {where_clause} {to_date_inward_cond}
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
			p.entry_price AS entry_price,
			NULL AS purchase_rate,
			COALESCE(s.exit_qty * p.entry_price, 0.0) AS cost_amount,
			0.0 AS in_qty,
			0.0 AS in_rate,
			0.0 AS in_amount,
			0.0 AS entry_charges,
			CASE
				WHEN s.net_exit_amount IS NOT NULL AND s.net_exit_amount > 0 AND (COALESCE(s.exit_amount, s.exit_qty * s.exit_price) > s.net_exit_amount)
				THEN (COALESCE(s.exit_amount, s.exit_qty * s.exit_price) - s.net_exit_amount)
				ELSE 0.0
			END AS exit_charges,
			s.exit_qty AS out_qty,
			s.exit_price AS out_rate,
			COALESCE(s.exit_amount, s.exit_qty * s.exit_price) AS out_amount,
			s.net_exit_amount,
			s.jv_of_exit AS jv_reference,
			'Exit / Sale' AS transaction_type,
			'' AS split,
			COALESCE(p.is_bonus_applied, CASE WHEN p.ratio > 0 OR p.bonus_date IS NOT NULL THEN 1 ELSE 0 END) AS is_bonus_applied,
			0 AS is_inward
		FROM `tabInvestment Portfolio Segment` s
		INNER JOIN `tabInvestment Portfolio` p ON s.parent = p.name
		WHERE {where_clause} {to_date_exit_cond}
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
			p.entry_price AS entry_price,
			NULL AS purchase_rate,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS cost_amount,
			0.0 AS in_qty,
			0.0 AS in_rate,
			0.0 AS in_amount,
			0.0 AS entry_charges,
			0.0 AS exit_charges,
			p.qty AS out_qty,
			p.entry_price AS out_rate,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS out_amount,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS net_exit_amount,
			p.jv_of_entry AS jv_reference,
			'Split Out' AS transaction_type,
			'Split Out' AS split,
			COALESCE(p.is_bonus_applied, CASE WHEN p.ratio > 0 OR p.bonus_date IS NOT NULL THEN 1 ELSE 0 END) AS is_bonus_applied,
			0 AS is_inward
		FROM `tabInvestment Portfolio` p
		WHERE {where_clause} {to_date_split_cond}
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
