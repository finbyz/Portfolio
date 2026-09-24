# Copyright (c) 2026, finbyz and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
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
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
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
			"width": 160,
		},
		{
			"label": _("Segment"),
			"fieldname": "segment",
			"fieldtype": "Link",
			"options": "Investment Segment",
			"width": 130,
		},
		{
			"label": _("Category"),
			"fieldname": "category",
			"fieldtype": "Link",
			"options": "Category",
			"width": 120,
		},
		{
			"label": _("Balance Qty"),
			"fieldname": "bal_qty",
			"fieldtype": "Float",
			"precision": 4,
			"width": 120,
		},
		{
			"label": _("Valuation / Avg Rate"),
			"fieldname": "bal_rate",
			"fieldtype": "Currency",
			"options": "currency",
			"precision": 4,
			"width": 150,
		},
		{
			"label": _("Balance Value"),
			"fieldname": "bal_val",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 160,
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
	to_date = getdate(filters.get("to_date")) if filters.get("to_date") else None
	show_zero_balance = filters.get("show_zero_balance")

	all_raw_entries = get_all_raw_transactions(filters)
	script_names_map = get_script_names_map()

	# Combine data based on Script (and company)
	grouped_entries = {}
	metadata_by_key = {}

	for row in all_raw_entries:
		scrip = row.get("script") or "Unknown"
		comp = row.get("company") or filters.get("company") or ""
		key = (comp, scrip)
		grouped_entries.setdefault(key, []).append(row)

		if key not in metadata_by_key:
			metadata_by_key[key] = {
				"company": comp,
				"script": scrip,
				"segment": row.get("segment"),
				"category": row.get("category"),
				"active_holdings": set(),
			}

		if row.get("voucher_no"):
			metadata_by_key[key]["active_holdings"].add(row.get("voucher_no"))

	data = []
	total_in_val = 0.0
	total_out_val = 0.0
	total_bal_qty = 0.0
	total_bal_val = 0.0
	active_scrips_count = 0

	for key in sorted(grouped_entries.keys(), key=lambda x: (x[0] or "", x[1] or "")):
		entries = grouped_entries[key]
		comp, scrip = key
		meta = metadata_by_key[key]

		# Sort entries chronologically
		entries.sort(
			key=lambda x: (
				getdate(x.get("posting_date")) if x.get("posting_date") else getdate("1900-01-01"),
				0 if x.get("is_inward") else 1,
				str(x.get("voucher_no")),
			)
		)

		running_qty = 0.0
		running_val = 0.0
		avg_rate = 0.0

		scrip_in_val = 0.0
		scrip_out_val = 0.0

		for entry in entries:
			e_date = getdate(entry.get("posting_date")) if entry.get("posting_date") else None
			if to_date and e_date and e_date > to_date:
				continue

			in_qty = flt(entry.get("in_qty"))
			in_rate = flt(entry.get("in_rate"))
			in_amt = flt(entry.get("in_amount")) or (in_qty * in_rate)

			out_qty = flt(entry.get("out_qty"))
			out_rate = flt(entry.get("out_rate"))
			out_amt = flt(entry.get("out_amount")) or (out_qty * out_rate)
			cost_amt = flt(entry.get("cost_amount")) or (out_qty * flt(entry.get("entry_price")))

			# Valuation update
			if in_qty > 0:
				running_qty += in_qty
				running_val += in_amt
				avg_rate = running_val / running_qty if running_qty > 0 else 0.0
				scrip_in_val += in_amt
			elif out_qty > 0:
				cost_basis = cost_amt if cost_amt > 0 else (out_qty * avg_rate)
				running_qty -= out_qty
				if running_qty <= 0.00001:
					running_qty = 0.0
					running_val = 0.0
					avg_rate = 0.0
				else:
					running_val -= cost_basis
					if running_val < 0:
						running_val = 0.0
					avg_rate = running_val / running_qty if running_qty > 0 else 0.0
				scrip_out_val += out_amt

		# Final balance calculation till to_date
		bal_qty = running_qty
		bal_val = running_val
		bal_rate = avg_rate

		# Check if we should display this scrip
		if not show_zero_balance and bal_qty <= 0.00001:
			continue

		row_currency = get_company_currency(comp) if comp else company_currency

		row = {
			"script": scrip,
			"script_name": script_names_map.get(scrip, scrip),
			"action": "Split" if bal_qty > 0 else "",
			"company": comp,
			"segment": meta.get("segment"),
			"category": meta.get("category"),
			"bal_qty": bal_qty,
			"bal_rate": bal_rate,
			"bal_val": bal_val,
			"active_holdings": len(meta.get("active_holdings", [])),
			"currency": row_currency,
		}

		data.append(row)

		total_in_val += scrip_in_val
		total_out_val += scrip_out_val
		total_bal_qty += bal_qty
		total_bal_val += bal_val
		if bal_qty > 0:
			active_scrips_count += 1

	report_summary = [
		{
			"value": active_scrips_count,
			"label": _("Total Script"),
			"datatype": "Int",
		},
		{
			"value": total_bal_qty,
			"label": _("Total Holding Qty"),
			"datatype": "Float",
			"precision": 4,
		},
		{
			"value": total_bal_val,
			"label": _("Total Investment Value"),
			"datatype": "Currency",
			"currency": company_currency,
		},
		# {
		# 	"value": total_in_val,
		# 	"label": _("Total Inward Value"),
		# 	"datatype": "Currency",
		# 	"currency": company_currency,
		# },
		# {
		# 	"value": total_out_val,
		# 	"label": _("Total Outward Value"),
		# 	"datatype": "Currency",
		# 	"currency": company_currency,
		# },
	]

	return data, report_summary


def get_all_raw_transactions(filters):
	entries = []

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

	where_clause = " AND ".join(conditions)

	to_date_inward_cond = ""
	to_date_exit_cond = ""
	to_date_split_cond = ""

	if filters.get("to_date"):
		query_params["to_date"] = filters.get("to_date")
		to_date_inward_cond = " AND p.posting_date <= %(to_date)s"
		to_date_exit_cond = " AND s.exit_date <= %(to_date)s"
		to_date_split_cond = " AND DATE(p.modified) <= %(to_date)s"

	# 1. Inward Purchases
	inward_query = f"""
		SELECT
			p.name AS voucher_no,
			'Investment Portfolio' AS voucher_type,
			p.posting_date,
			p.script,
			p.company,
			p.segment,
			p.category,
			p.entry_price AS entry_price,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS cost_amount,
			p.qty AS in_qty,
			p.entry_price AS in_rate,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS in_amount,
			0.0 AS out_qty,
			0.0 AS out_rate,
			0.0 AS out_amount,
			1 AS is_inward
		FROM `tabInvestment Portfolio` p
		WHERE {where_clause} {to_date_inward_cond}
	"""
	inwards = frappe.db.sql(inward_query, query_params, as_dict=True)
	entries.extend(inwards)

	# 2. Outward Sales from tabInvestment Portfolio Segment
	exit_query = f"""
		SELECT
			p.name AS voucher_no,
			'Portfolio Exit' AS voucher_type,
			s.exit_date AS posting_date,
			p.script,
			p.company,
			p.segment,
			p.category,
			p.entry_price AS entry_price,
			COALESCE(s.exit_qty * p.entry_price, 0.0) AS cost_amount,
			0.0 AS in_qty,
			0.0 AS in_rate,
			0.0 AS in_amount,
			s.exit_qty AS out_qty,
			s.exit_price AS out_rate,
			COALESCE(s.exit_amount, s.exit_qty * s.exit_price) AS out_amount,
			s.net_exit_amount,
			0 AS is_inward
		FROM `tabInvestment Portfolio Segment` s
		INNER JOIN `tabInvestment Portfolio` p ON s.parent = p.name
		WHERE {where_clause} {to_date_exit_cond}
	"""
	exits = frappe.db.sql(exit_query, query_params, as_dict=True)
	entries.extend(exits)

	# 3. Splits Out
	split_query = f"""
		SELECT
			p.name AS voucher_no,
			'Portfolio Split' AS voucher_type,
			DATE(p.modified) AS posting_date,
			p.script,
			p.company,
			p.segment,
			p.category,
			p.entry_price AS entry_price,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS cost_amount,
			0.0 AS in_qty,
			0.0 AS in_rate,
			0.0 AS in_amount,
			p.qty AS out_qty,
			p.entry_price AS out_rate,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS out_amount,
			COALESCE(p.entry_amount, p.qty * p.entry_price) AS net_exit_amount,
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

	# Sort top 10 scrips by balance value
	sorted_scrips = sorted(data, key=lambda x: flt(x.get("bal_val")), reverse=True)[:10]
	if not sorted_scrips:
		return None

	labels = [x.get("script") for x in sorted_scrips if flt(x.get("bal_val")) > 0]
	values = [flt(x.get("bal_val")) for x in sorted_scrips if flt(x.get("bal_val")) > 0]

	if not labels:
		return None

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Holding Value"),
					"values": values,
				}
			],
		},
		"type": "bar",
		"colors": ["#36a2eb"],
	}


# =========================================================================
# Whitelist APIs for Split Functionality (Stock Balance Column Action)
# =========================================================================

@frappe.whitelist()
def get_holding_portfolios_for_script(script, company=None):
	"""
	Fetches all submitted 'Holding' portfolios for a given script and company.
	"""
	if not script:
		return []

	filters = {
		"script": script,
		"docstatus": 1,
		"status": "Holding",
	}
	if company:
		filters["company"] = company

	portfolios = frappe.get_all(
		"Investment Portfolio",
		filters=filters,
		fields=[
			"name",
			"posting_date",
			"qty",
			"pending_qty",
			"entry_price",
			"entry_amount",
			"company",
			"segment",
			"category",
			"holding_account",
		],
		order_by="posting_date asc, name asc",
	)

	valid = []
	for p in portfolios:
		rem_qty = flt(p.get("pending_qty") if p.get("pending_qty") is not None else p.get("qty"))
		if rem_qty > 0:
			p["pending_qty"] = rem_qty
			valid.append(p)

	return valid


@frappe.whitelist()
def get_all_scripts():
	"""
	Returns list of scripts for autocomplete / selection in split rows.
	"""
	return frappe.get_all("Script", fields=["name", "script_name"], order_by="script_name asc")


@frappe.whitelist()
def execute_portfolio_split(portfolio, split_ratio, split_rows):
	"""
	Executes the split for an Investment Portfolio document matching document-level logic.
	portfolio: Name of the Investment Portfolio doc (e.g. IP-0001)
	split_ratio: Float (e.g. 2 for 2:1 split)
	split_rows: JSON array or list of objects: [{'script': ..., 'qty': ..., 'per_share_price': ..., 'amount': ...}]
	"""
	if not portfolio:
		frappe.throw(_("Portfolio is required"))

	if isinstance(split_rows, str):
		split_rows = json.loads(split_rows)

	split_ratio = flt(split_ratio)
	if split_ratio <= 0:
		frappe.throw(_("Split Ratio must be greater than 0"))

	if not split_rows:
		frappe.throw(_("At least one split row is required"))

	doc = frappe.get_doc("Investment Portfolio", portfolio)

	if doc.docstatus != 1:
		frappe.throw(_("Document {0} must be submitted before Split").format(portfolio))
	if doc.status != "Holding":
		frappe.throw(_("Document {0} status must be Holding to Split (Current: {1})").format(portfolio, doc.status))

	# Update split ratio and post split qty
	doc.split_ratio = split_ratio
	doc.post_split_qty = flt(doc.qty) * split_ratio

	# Populate child table investment_portfolio_split
	doc.set("investment_portfolio_split", [])
	for idx, row in enumerate(split_rows, start=1):
		scrip = row.get("script") or doc.script
		qty = flt(row.get("qty"))
		rate = flt(row.get("per_share_price"))
		amt = flt(row.get("amount")) or (qty * rate)

		if not scrip or qty <= 0 or rate <= 0:
			frappe.throw(_("Row {0}: Script, Qty and Per Share Price are mandatory and must be > 0").format(idx))

		doc.append(
			"investment_portfolio_split",
			{
				"script": scrip,
				"qty": qty,
				"per_share_price": rate,
				"amount": amt,
			},
		)

	doc.save(ignore_permissions=True)

	# Execute document-level process_split
	from portfolio.portfolio.doctype.investment_portfolio.investment_portfolio import process_split
	created_docs = process_split(doc.name)

	return created_docs
