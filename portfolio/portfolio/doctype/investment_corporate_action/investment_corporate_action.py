# Copyright (c) 2026, Finbyz Tech Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class InvestmentCorporateAction(Document):
	def before_delete(self):
		frappe.throw(_("Deleting Investment Corporate Action documents is not permitted"))

	def validate(self):
		if self.entry_type == "Bonus":
			if flt(self.ratio) <= 0:
				frappe.throw(_("Bonus Ratio must be greater than 0"))
			if not self.posting_date:
				frappe.throw(_("Posting Date is mandatory"))

	def on_submit(self):
		if self.entry_type == "Bonus":
			self.apply_bonus_entries()
		elif self.entry_type == "Split":
			pass

	def apply_bonus_entries(self):
		# If child table is already populated (e.g. from apply_bonus function)
		if self.investment_reference:
			for row in self.investment_reference:
				if not frappe.db.exists("Investment Portfolio", row.investment_portfolio):
					continue
				doc = frappe.get_doc("Investment Portfolio", row.investment_portfolio)
				if not flt(doc.purchase_entry_price):
					doc.db_set("purchase_entry_price", flt(row.old_rate), update_modified=True)

				doc.db_set("old_qty", flt(row.old_qty), update_modified=True)
				doc.db_set("old_pending_qty", flt(row.old_pending_qty), update_modified=True)
				doc.db_set("ratio", flt(self.ratio), update_modified=True)
				doc.db_set("post_bonus_qty", flt(row.new_qty), update_modified=True)
				doc.db_set("bonus_date", self.posting_date, update_modified=True)
				doc.db_set("qty", flt(row.new_qty), update_modified=True)
				doc.db_set("pending_qty", flt(row.new_pending_qty), update_modified=True)
				doc.db_set("entry_price", flt(row.new_rate), update_modified=True)
				doc.db_set("is_bonus_applied", 1, update_modified=True)
				doc.set_status()
		else:
			# Auto-fetch if submitted directly
			filters = {
				"script": self.script,
				"status": ["in", ["Holding", "Partially Exited"]],
				"pending_qty": [">", 0],
				"docstatus": 1,
				"posting_date": ["<=", self.posting_date]
			}
			docs = frappe.get_all("Investment Portfolio", filters=filters, fields=["name"])
			if not docs:
				frappe.throw(_("No Holding or Partially Exited records found for Script {0}").format(self.script))

			ratio = flt(self.ratio)
			total_bonus_qty = 0
			for d in docs:
				doc = frappe.get_doc("Investment Portfolio", d.name)
				current_pending_qty = flt(doc.pending_qty)
				current_qty = flt(doc.qty)
				current_entry_price = flt(doc.entry_price)

				bonus_shares = current_pending_qty * ratio
				total_bonus_qty += bonus_shares
				new_pending_qty = current_pending_qty + bonus_shares
				new_total_qty = current_qty + bonus_shares
				new_entry_price = current_entry_price / (1.0 + ratio)

				if not flt(doc.purchase_entry_price):
					doc.db_set("purchase_entry_price", current_entry_price, update_modified=True)

				doc.db_set("old_qty", current_qty, update_modified=True)
				doc.db_set("old_pending_qty", current_pending_qty, update_modified=True)
				doc.db_set("ratio", ratio, update_modified=True)
				doc.db_set("post_bonus_qty", new_total_qty, update_modified=True)
				doc.db_set("bonus_date", self.posting_date, update_modified=True)
				doc.db_set("qty", new_total_qty, update_modified=True)
				doc.db_set("pending_qty", new_pending_qty, update_modified=True)
				doc.db_set("entry_price", new_entry_price, update_modified=True)
				doc.db_set("is_bonus_applied", 1, update_modified=True)
				doc.set_status()

				self.append("investment_reference", {
					"investment_portfolio": doc.name,
					"script": self.script,
					"old_qty": current_qty,
					"new_qty": new_total_qty,
					"old_rate": current_entry_price,
					"new_rate": new_entry_price,
					"old_pending_qty": current_pending_qty,
					"new_pending_qty": new_pending_qty,
					"bonus_qty": bonus_shares
				})
			self.qty = total_bonus_qty
			self.db_update_all()

	def before_cancel(self):
		self.flags.ignore_links = True

	def on_cancel(self):
		if self.entry_type == "Bonus":
			self.cancel_bonus_entries()
		elif self.entry_type == "Split":
			self.cancel_split_entries()

	def cancel_split_entries(self):
		self.flags.ignore_links = True

		# 1. Cancel newly created split IP entries
		for row in self.investment_reference:
			if self.split_from and row.investment_portfolio == self.split_from:
				continue
			if frappe.db.exists("Investment Portfolio", row.investment_portfolio):
				child_ip = frappe.get_doc("Investment Portfolio", row.investment_portfolio)
				if child_ip.investment_portfolio_segment:
					frappe.throw(
						_("Cannot cancel Split. New Investment Portfolio {0} already has exit transactions.").format(child_ip.name)
					)
				if child_ip.docstatus == 1:
					frappe.db.set_value(
						"Investment Portfolio",
						child_ip.name,
						{
							"jv_of_entry": None,
							"split_from": None,
							"split__investment_portfolio": None
						},
						update_modified=False
					)
					child_ip.reload()
					child_ip.flags.ignore_permissions = True
					child_ip.flags.ignore_links = True
					child_ip.cancel()

		# 2. Revert the original split_from IP
		if self.split_from and frappe.db.exists("Investment Portfolio", self.split_from):
			parent_ip = frappe.get_doc("Investment Portfolio", self.split_from)
			old_pending = 0
			for row in self.investment_reference:
				if row.investment_portfolio == self.split_from:
					old_pending = flt(row.old_pending_qty)
					break
			if old_pending == 0:
				old_pending = flt(parent_ip.qty)

			parent_ip.db_set("pending_qty", old_pending, update_modified=True)
			parent_ip.db_set("is_split", 0, update_modified=True)
			parent_ip.set_status()

		frappe.msgprint(_("Split changes reverted. Created split entries cancelled and original Investment Portfolio {0} restored.").format(self.split_from or ""))

	def cancel_bonus_entries(self):
		for row in self.investment_reference:
			if not frappe.db.exists("Investment Portfolio", row.investment_portfolio):
				continue
			doc = frappe.get_doc("Investment Portfolio", row.investment_portfolio)

			doc.db_set("qty", flt(row.old_qty), update_modified=True)
			doc.db_set("pending_qty", flt(row.old_pending_qty), update_modified=True)
			doc.db_set("entry_price", flt(row.old_rate), update_modified=True)
			doc.db_set("old_qty", 0, update_modified=True)
			doc.db_set("old_pending_qty", 0, update_modified=True)
			doc.db_set("ratio", 0, update_modified=True)
			doc.db_set("bonus_date", None, update_modified=True)
			doc.db_set("post_bonus_qty", 0, update_modified=True)
			doc.db_set("is_bonus_applied", 0, update_modified=True)
			doc.set_status()

		frappe.msgprint(_("Bonus changes reverted in Investment Portfolio for Script {0}").format(self.script))
