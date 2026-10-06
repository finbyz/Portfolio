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

		# Sort entries: Purchases/Split-Ins first, then Bonus, then Exits
		def entry_sort_key(x):
			d = getdate(x.get("posting_date")) if x.get("posting_date") else getdate("1900-01-01")
			tx = x.get("transaction_type")
			is_in = x.get("is_inward")
			if tx == "Purchase" or (tx == "Split" and is_in):
				order = 0
			elif tx == "Bonus":
				order = 1
			else:
				order = 2
			return (d, order, str(x.get("voucher_no")))

		script_entries.sort(key=entry_sort_key)

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

			tx_type = entry.get("transaction_type") or ""
			in_qty = flt(entry.get("in_qty"))
			in_rate = flt(entry.get("in_rate"))
			in_amount = flt(entry.get("in_amount")) if tx_type == "Bonus" else (flt(entry.get("in_amount")) or (in_qty * in_rate))
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
			if in_qty and tx_type != "Bonus":
				purchase_rate = flt(entry.get("purchase_rate")) if entry.get("purchase_rate") else in_rate

			row = {
				"posting_date": entry.get("posting_date"),
				"script": scrip,
				"script_name": script_names_map.get(scrip, scrip),
				"voucher_type": entry.get("voucher_type"),
				"voucher_no": entry.get("voucher_no"),
				"transaction_type": tx_type,
				"company": row_comp,
				"segment": entry.get("segment"),
				"category": entry.get("category"),
				"holding_account": entry.get("holding_account"),
				"in_qty": in_qty if in_qty else None,
				"purchase_rate": purchase_rate,
				"in_rate": in_rate if (in_qty and tx_type != "Bonus") else None,
				"in_amount": in_amount if (in_qty and tx_type != "Bonus") else None,
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
		to_date_split_cond = " AND COALESCE((SELECT ca.posting_date FROM `tabInvestment Corporate Action` ca WHERE ca.split_from = p.name AND ca.entry_type = 'Split' AND ca.docstatus = 1 ORDER BY ca.posting_date DESC LIMIT 1), DATE(p.modified)) <= %(to_date)s"

	# Query all submitted bonus corporate actions for matching portfolios
	bonus_ca_records = []
	try:
		bonus_ca_records = frappe.db.sql(
			f"""
			SELECT
				ca.name AS ca_name,
				ca.posting_date AS ca_posting_date,
				ref.investment_portfolio,
				ref.bonus_qty,
				ref.old_qty,
				ref.new_qty,
				ref.old_rate,
				ref.new_rate
			FROM `tabInvestment Corporate Action Reference` ref
			INNER JOIN `tabInvestment Corporate Action` ca ON ca.name = ref.parent
			INNER JOIN `tabInvestment Portfolio` p ON p.name = ref.investment_portfolio
			WHERE ca.docstatus = 1
				AND ca.entry_type = 'Bonus'
				AND {where_clause}
			ORDER BY ca.posting_date ASC, ca.creation ASC
			""",
			query_params,
			as_dict=True,
		)
	except Exception:
		pass

	bonus_by_ip = {}
	for b in bonus_ca_records:
		bonus_by_ip.setdefault(b.get("investment_portfolio"), []).append(b)

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
			p.purchase_entry_price AS purchase_entry_price,
			p.old_qty AS old_qty,
			p.old_pending_qty AS old_pending_qty,
			p.ratio AS ratio,
			p.bonus_date AS bonus_date,
			p.post_bonus_qty AS post_bonus_qty,
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
				WHEN p.split_from IS NOT NULL AND p.split_from != '' THEN 'Split'
				ELSE 'Purchase'
			END AS transaction_type,
			CASE
				WHEN p.split_from IS NOT NULL AND p.split_from != '' THEN 'Split'
				ELSE ''
			END AS split,
			COALESCE(p.is_bonus_applied, CASE WHEN p.ratio > 0 OR p.bonus_date IS NOT NULL THEN 1 ELSE 0 END) AS is_bonus_applied,
			1 AS is_inward
		FROM `tabInvestment Portfolio` p
		WHERE {where_clause} {to_date_inward_cond}
	"""

	inwards = frappe.db.sql(inward_query, query_params, as_dict=True)
	for p in inwards:
		ip_name = p.get("voucher_no")
		ip_bonuses = bonus_by_ip.get(ip_name, [])

		if ip_bonuses:
			total_bonus_qty = sum(flt(b.get("bonus_qty")) for b in ip_bonuses)
			total_current_qty = flt(p.get("in_qty"))
			orig_qty = total_current_qty - total_bonus_qty
			if orig_qty <= 0:
				orig_qty = flt(ip_bonuses[0].get("old_qty")) or total_current_qty

			purchase_rate = (
				flt(p.get("purchase_entry_price"))
				or flt(ip_bonuses[0].get("old_rate"))
				or (flt(p.get("in_amount")) / orig_qty if orig_qty > 0 else flt(p.get("in_rate")))
			)
			orig_amount = orig_qty * purchase_rate

			# 1. Original Purchase / Split row
			orig_row = dict(p)
			orig_row["in_qty"] = orig_qty
			orig_row["in_rate"] = purchase_rate
			orig_row["purchase_rate"] = purchase_rate
			orig_row["in_amount"] = orig_amount
			orig_row["cost_amount"] = orig_amount
			orig_row["is_bonus_applied"] = 0
			entries.append(orig_row)

			# 2. Separate Bonus row for EACH Corporate Action
			for b in ip_bonuses:
				bonus_qty = flt(b.get("bonus_qty"))
				if bonus_qty <= 0:
					continue
				bonus_date = b.get("ca_posting_date") or p.get("posting_date")
				bonus_row = {
					"voucher_no": p.get("voucher_no"),
					"voucher_type": "Corporate Action",
					"posting_date": bonus_date,
					"script": p.get("script"),
					"company": p.get("company"),
					"segment": p.get("segment"),
					"category": p.get("category"),
					"holding_account": p.get("holding_account"),
					"entry_price": 0.0,
					"purchase_rate": None,
					"cost_amount": 0.0,
					"in_qty": bonus_qty,
					"in_rate": 0.0,
					"in_amount": 0.0,
					"entry_charges": 0.0,
					"exit_charges": 0.0,
					"out_qty": 0.0,
					"out_rate": 0.0,
					"out_amount": 0.0,
					"jv_reference": None,
					"transaction_type": "Bonus",
					"split": "",
					"is_bonus_applied": 1,
					"is_inward": 1,
				}
				entries.append(bonus_row)
			continue

		is_bonus = 1 if (p.get("is_bonus_applied") or (flt(p.get("ratio")) > 0 or p.get("bonus_date"))) else 0
		old_qty = flt(p.get("old_qty"))
		ratio = flt(p.get("ratio"))
		total_qty = flt(p.get("in_qty"))
		purchase_rate = flt(p.get("purchase_entry_price")) or (flt(p.get("in_amount")) / old_qty if old_qty > 0 else flt(p.get("in_rate")))

		if is_bonus and (old_qty > 0 or ratio > 0) and total_qty > 0:
			orig_qty = old_qty if old_qty > 0 else (total_qty / (1.0 + ratio) if ratio > 0 else total_qty)
			bonus_qty = total_qty - orig_qty

			if bonus_qty > 0:
				# 1. Original Purchase / Split row
				orig_row = dict(p)
				orig_row["in_qty"] = orig_qty
				orig_row["in_rate"] = purchase_rate
				orig_row["purchase_rate"] = purchase_rate
				orig_row["in_amount"] = orig_qty * purchase_rate
				orig_row["cost_amount"] = orig_qty * purchase_rate
				orig_row["is_bonus_applied"] = 0
				entries.append(orig_row)

				# 2. Separate Bonus row
				bonus_date = p.get("bonus_date") or p.get("posting_date")
				bonus_row = {
					"voucher_no": p.get("voucher_no"),
					"voucher_type": "Corporate Action",
					"posting_date": bonus_date,
					"script": p.get("script"),
					"company": p.get("company"),
					"segment": p.get("segment"),
					"category": p.get("category"),
					"holding_account": p.get("holding_account"),
					"entry_price": 0.0,
					"purchase_rate": None,
					"cost_amount": 0.0,
					"in_qty": bonus_qty,
					"in_rate": 0.0,
					"in_amount": 0.0,
					"entry_charges": 0.0,
					"exit_charges": 0.0,
					"out_qty": 0.0,
					"out_rate": 0.0,
					"out_amount": 0.0,
					"jv_reference": None,
					"transaction_type": "Bonus",
					"split": "",
					"is_bonus_applied": 1,
					"is_inward": 1,
				}
				entries.append(bonus_row)
				continue

		entries.append(p)

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
			0.0 AS cost_amount,
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
			'Sales' AS transaction_type,
			'' AS split,
			0 AS is_bonus_applied,
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
			COALESCE(
				(SELECT ca.posting_date FROM `tabInvestment Corporate Action` ca WHERE ca.split_from = p.name AND ca.entry_type = 'Split' AND ca.docstatus = 1 ORDER BY ca.posting_date DESC LIMIT 1),
				DATE(p.modified)
			) AS posting_date,
			p.script,
			p.company,
			p.segment,
			p.category,
			p.holding_account,
			p.entry_price AS entry_price,
			NULL AS purchase_rate,
			COALESCE(
				(p.qty - COALESCE((SELECT SUM(seg.exit_qty) FROM `tabInvestment Portfolio Segment` seg WHERE seg.parent = p.name), 0.0)) * p.entry_price,
				0.0
			) AS cost_amount,
			0.0 AS in_qty,
			0.0 AS in_rate,
			0.0 AS in_amount,
			0.0 AS entry_charges,
			0.0 AS exit_charges,
			(p.qty - COALESCE((SELECT SUM(seg.exit_qty) FROM `tabInvestment Portfolio Segment` seg WHERE seg.parent = p.name), 0.0)) AS out_qty,
			p.entry_price AS out_rate,
			COALESCE(
				(p.qty - COALESCE((SELECT SUM(seg.exit_qty) FROM `tabInvestment Portfolio Segment` seg WHERE seg.parent = p.name), 0.0)) * p.entry_price,
				0.0
			) AS out_amount,
			COALESCE(
				(p.qty - COALESCE((SELECT SUM(seg.exit_qty) FROM `tabInvestment Portfolio Segment` seg WHERE seg.parent = p.name), 0.0)) * p.entry_price,
				0.0
			) AS net_exit_amount,
			p.jv_of_entry AS jv_reference,
			'Split' AS transaction_type,
			'Split' AS split,
			0 AS is_bonus_applied,
			0 AS is_inward
		FROM `tabInvestment Portfolio` p
		WHERE {where_clause} {to_date_split_cond}
			AND p.status = 'Exited'
			AND (SELECT COUNT(*) FROM `tabInvestment Portfolio Split` sp WHERE sp.parent = p.name) > 0
			AND (p.qty - COALESCE((SELECT SUM(seg.exit_qty) FROM `tabInvestment Portfolio Segment` seg WHERE seg.parent = p.name), 0.0)) > 0.0001
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
