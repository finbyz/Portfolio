# Copyright (c) 2023, finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, date_diff, nowdate, get_url_to_form,flt
import erpnext

class InvestmentPortfolio(Document):
	
	def validate(self):
		if not flt(self.purchase_entry_price) and flt(self.entry_price):
			self.purchase_entry_price = self.entry_price
		elif not flt(self.entry_price) and flt(self.purchase_entry_price):
			self.entry_price = self.purchase_entry_price

		if (self.split_from or (self.get("investment_portfolio_split") and len(self.get("investment_portfolio_split")) > 0 and self.status == "Exited")) and not self.is_split:
			self.is_split = 1

		if (self.ratio or self.bonus_date) and not self.is_bonus_applied:
			self.is_bonus_applied = 1

		self.calculate_entry_amount()
		self.calculate_pending_qty()

		base_qty = flt(self.pending_qty) if flt(self.pending_qty) > 0 else flt(self.qty)
		if flt(self.post_split_qty) > 0 and flt(self.post_split_qty) < base_qty:
			frappe.throw(
				_("Qty After Split ({0}) cannot be less than Pending Qty ({1})").format(
					flt(self.post_split_qty, 4), flt(base_qty, 4)
				)
			)
		
	def on_update_after_submit(self):
		self.calculate_pending_qty()
		self.set_status()

	def on_cancel(self):
		self.set_status()
		self.cancel_jv()
	
	# def before_cancel(self):
	# 	self.unlink_split_children()

	# def unlink_split_children(self):
	# 	child_names = frappe.get_all(
	# 		"Investment Portfolio",
	# 		filters={"split_from": self.name},
	# 		pluck="name"
	# 	)
	# 	if child_names:
	# 		for child in child_names:
	# 			frappe.db.set_value(
	# 				"Investment Portfolio",
	# 				child,
	# 				{
	# 					"split_from": None,
	# 					"jv_of_entry": None,
	# 				},
	# 				update_modified=False,
	# 			)
	# 		self.flags.was_split = True

	# 	self.flags.ignore_links = True

	def on_update(self):
		self.set_status()
		if self.docstatus == 0 and self.is_existing == 0:
			self.jv_of_entry = None
			self.jv_of_exit = None

	def set_status(self):
		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			if self.pending_qty == self.qty:
				status = "Holding"
			elif self.pending_qty == 0:
				status = "Exited"
			else:
				status = "Partially Exited"
		elif self.docstatus == 2:
			status = "Cancelled"
		else:
			status = self.status

		if self.status != status:
			self.db_set("status", status, update_modified=False)
			self.status = status
		
		
	def on_submit(self):
		self.set_status()
		if not self.jv_of_entry:
			self.create_row_entry_jv()
		
	def calculate_entry_amount(self):
		self.entry_amount=self.qty*self.entry_price
	
	def calculate_exit_amount(self):
		self.exit_amount=self.exit_price*self.exit_qty
		
	def validate_exit_date(self):
		if self.posting_date > self.exit_date:
			frappe.throw("Exit Date Cannot be Greater than Investment Date")	
	
	def create_row_exit_jv(self):
		if not self.bank_account:
			frappe.throw("Bank Account is compulsory")
		if self.net_exit_amount > self.exit_amount:
			frappe.throw("Net Exit Amount Should not be Greater than Exit Amount")
		
		cost_center = erpnext.get_default_cost_center(self.company)
		if not self.set_charges==1:
			jv = frappe.new_doc("Journal Entry")
			jv.voucher_type = "Journal Entry"
			jv.posting_date = self.exit_date
			net= (self.net_exit_amount - (self.exit_qty*self.entry_price))
			if not self.company:
				self.db_set('company', frappe.defaults.get_global_default('company'))

			jv.company = self.company

			
			jv.append('accounts', {
				'account': self.bank_account,
				'debit_in_account_currency': self.net_exit_amount,
				'cost_center':cost_center,
			})

			jv.append('accounts', {
				'account': self.holding_account,
				'credit_in_account_currency': (self.exit_qty*self.entry_price),
				'cost_center':cost_center,
			})
			if net != 0:
				jv.append('accounts', {
					'account': self.funds_credited_to,
					'credit_in_account_currency': net,
					'cost_center':cost_center,
				})

			jv.cheque_no = self.name
			jv.cheque_date = self.exit_date
			

			try:
				jv.save()
				jv.submit()
				self.jv_of_exit = jv.name
				url = get_url_to_form("Journal Entry", jv.name)
				frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been created.".format(url=url, doc=frappe.bold(jv.name))))
				return jv.name
			except Exception as e:
				frappe.throw(_(str(e)))	
		else:
			jv = frappe.new_doc("Journal Entry")
			jv.voucher_type = "Journal Entry"
			jv.posting_date = self.exit_date
			net= (self.net_exit_amount - (self.exit_qty*self.entry_price))
			if not self.company:
				self.db_set('company', frappe.defaults.get_global_default('company'))

			jv.company = self.company
			calculated_exit_amount=self.exit_qty*self.entry_price
			if self.exit_amount > calculated_exit_amount:
				jv.append('accounts', {
					'account': self.bank_account,
					'debit_in_account_currency': self.net_exit_amount,
					'cost_center':cost_center,
				})
				jv.append('accounts', {
					'account': self.investment_charges_account,
					'debit_in_account_currency': self.exit_charges,
					'cost_center':cost_center,
				})

				jv.append('accounts', {
					'account': self.holding_account,
					'credit_in_account_currency': (self.exit_qty*self.entry_price),
					'cost_center':cost_center,
				})
				jv.append('accounts', {
					'account': self.funds_credited_to,
					'credit_in_account_currency': (self.exit_amount-calculated_exit_amount),
					'cost_center':cost_center,
				})
			elif  self.exit_amount < calculated_exit_amount:
				jv.append('accounts', {
					'account': self.bank_account,
					'debit_in_account_currency': self.net_exit_amount,
					'cost_center':cost_center,
				})
				jv.append('accounts', {
					'account': self.investment_charges_account,
					'debit_in_account_currency': self.exit_charges,
					'cost_center':cost_center,
				})
				exit_amount_with_charges=self.net_exit_amount+ self.exit_charges
				jv.append('accounts', {
					'account': self.funds_credited_to,
					'debit_in_account_currency': (calculated_exit_amount-exit_amount_with_charges),
					'cost_center':cost_center,
				})

				jv.append('accounts', {
					'account': self.holding_account,
					'credit_in_account_currency': (self.exit_qty*self.entry_price),
					'cost_center':cost_center,
				})
			elif self.exit_amount == calculated_exit_amount:
				jv.append('accounts', {
					'account': self.bank_account,
					'debit_in_account_currency': self.net_exit_amount,
					'cost_center':cost_center,
				})
				jv.append('accounts', {
					'account': self.investment_charges_account,
					'debit_in_account_currency': self.exit_charges,
					'cost_center':cost_center,
				})
				# v=self.net_exit_amount+ self.exit_charges
				# jv.append('accounts', {
				# 	'account': self.funds_credited_to,
				# 	'debit_in_account_currency': (calculated_exit_amount-v)
				# })

				jv.append('accounts', {
					'account': self.holding_account,
					'credit_in_account_currency': (self.exit_amount),
					'cost_center':cost_center,
				})


			jv.cheque_no = self.name
			jv.cheque_date = self.exit_date
			

			try:
				jv.save()
				jv.submit()
				self.jv_of_exit = jv.name
				url = get_url_to_form("Journal Entry", jv.name)
				frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been created.".format(url=url, doc=frappe.bold(jv.name))))
				return jv.name
			except Exception as e:
				frappe.throw(_(str(e)))


	def create_row_entry_jv(self):		
		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Journal Entry"
		jv.posting_date = self.posting_date
		
		if not self.company:
			self.db_set('company', frappe.defaults.get_global_default('company'))

		jv.company = self.company
		cost_center = erpnext.get_default_cost_center(self.company)

		
		jv.append('accounts', {
			'account': self.funds_debited_from,
			'credit_in_account_currency': self.total_cost_of_ownership,
			'cost_center': cost_center
		})
		if self.entry_charges != 0:
			jv.append('accounts', {
				'account': self.investment_charges_account,
				'debit_in_account_currency': self.entry_charges,
				'cost_center': cost_center
			})
		jv.append('accounts', {
			'account': self.holding_account,
			'debit_in_account_currency': self.entry_amount,
			'cost_center': cost_center
		})

		jv.cheque_no = self.name
		jv.cheque_date = self.posting_date

		try:
			print(jv.accounts[0].cost_center)
			jv.save()
			print(jv.accounts[0].cost_center)
			jv.submit()
			self.db_set("jv_of_entry" , jv.name)
		except Exception as e:
			frappe.throw(_(str(e)))
		else:
			
			url = get_url_to_form("Journal Entry", jv.name)
			frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been created.".format(url=url, doc=frappe.bold(jv.name))))

	def calculate_pending_qty(self):
		if not self.exit_qty and not len(self.investment_portfolio_segment):
			self.pending_qty=self.qty
		else:
			total=0
			for row1 in self.investment_portfolio_segment:
				total+=flt(row1.exit_qty)
			self.pending_qty=self.qty-total

	def cancel_jv(self):
		if self.split_from:
			# Child split records should not cancel parent's JV
			return

		if self.jv_of_entry:
			jv = frappe.get_doc("Journal Entry", self.jv_of_entry)
			if jv.docstatus == 1:
				jv.cancel()
				url = get_url_to_form("Journal Entry", jv.name)
				frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been cancelled .".format(url=url, doc=frappe.bold(jv.name))))	
		for row in self.investment_portfolio_segment:
			if row.jv_of_exit:
				jv_doc = frappe.get_doc("Journal Entry" , row.jv_of_exit)
				if jv_doc.docstatus == 1:
					jv_doc.cancel()

@frappe.whitelist()
def create_exit(exit_price ,exit_qty , exit_date , exit_amount ,net_exit_amount , name ,jv_of_exit = None):
	doc = frappe.get_doc("Investment Portfolio" , name)
	doc.calculate_exit_amount()
	jv = doc.create_row_exit_jv()
	doc.append("investment_portfolio_segment" , {"exit_price":exit_price,"exit_date":exit_date ,"exit_qty":exit_qty , "exit_amount":exit_amount , "net_exit_amount" : net_exit_amount,"jv_of_exit": jv})
	if sum([flt(row.exit_qty) for row in doc.investment_portfolio_segment]) > flt(doc.qty):
		frappe.throw("Exit Quantity should not be greater than quantity")
	doc.calculate_pending_qty()
	doc.exit_price=0
	doc.exit_qty=0
	doc.exit_amount=0
	doc.net_exit_amount=0
	doc.save()	
 
@frappe.whitelist()
def get_bonus_scripts():
	return frappe.get_all(
		"Investment Portfolio",
		filters={"status": ["in", ["Holding", "Partially Exited"]], "pending_qty": [">", 0], "docstatus": 1},
		pluck="script",
		distinct=True
	)


@frappe.whitelist()
def get_holding_qty(script, date=None):
	filters = {"script": script, "status": ["in", ["Holding", "Partially Exited"]], "pending_qty": [">", 0], "docstatus": 1}
	if date:
		filters["posting_date"] = ["<=", date]
	pending_qtys = frappe.get_all(
		"Investment Portfolio",
		filters=filters,
		pluck="pending_qty"
	)
	return sum([flt(q) for q in pending_qtys])


@frappe.whitelist()
def apply_bonus(script, ratio, bonus_date, date=None):
	ratio = flt(ratio)
	if ratio <= 0:
		frappe.throw(_("Ratio must be greater than 0"))
	if not bonus_date:
		frappe.throw(_("Bonus Date is mandatory"))

	filters = {"script": script, "status": ["in", ["Holding", "Partially Exited"]], "pending_qty": [">", 0], "docstatus": 1}
	if date:
		filters["posting_date"] = ["<=", date]

	docs = frappe.get_all(
		"Investment Portfolio",
		filters=filters,
		fields=["name", "qty", "pending_qty", "entry_amount", "entry_price", "status"]
	)
	if not docs:
		frappe.throw(_("No Holding or Partially Exited documents found for Script {0}").format(script))

	total_bonus_qty = 0
	action_doc = frappe.new_doc("Investment Corporate Action")
	action_doc.posting_date = bonus_date
	action_doc.entry_type = "Bonus"
	action_doc.script = script
	action_doc.ratio = ratio

	updated = []
	for row in docs:
		doc = frappe.get_doc("Investment Portfolio", row.name)
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
		doc.db_set("bonus_date", bonus_date, update_modified=True)
		doc.db_set("qty", new_total_qty, update_modified=True)
		doc.db_set("pending_qty", new_pending_qty, update_modified=True)
		doc.db_set("entry_price", new_entry_price, update_modified=True)
		doc.db_set("is_bonus_applied", 1, update_modified=True)
		doc.set_status()
		updated.append(row.name)

		action_doc.append("investment_reference", {
			"investment_portfolio": doc.name,
			"script": script,
			"old_qty": current_qty,
			"new_qty": new_total_qty,
			"old_rate": current_entry_price,
			"new_rate": new_entry_price,
			"old_pending_qty": current_pending_qty,
			"new_pending_qty": new_pending_qty,
			"bonus_qty": bonus_shares,
		})

	action_doc.qty = total_bonus_qty
	action_doc.flags.ignore_permissions = True
	action_doc.insert()
	action_doc.submit()

	return updated


@frappe.whitelist()
def process_split(name):
    doc = frappe.get_doc("Investment Portfolio", name)

    if doc.docstatus != 1:
        frappe.throw(_("Document must be submitted before Split"))
    if doc.status not in ["Holding", "Partially Exited"]:
        frappe.throw(_("Split can only be done when status is Holding or Partially Exited"))
    if not doc.investment_portfolio_split:
        frappe.throw(_("Add at least one row in Investment Split table"))
    if not flt(doc.post_split_qty):
        frappe.throw(_("Qty After Split is mandatory"))

    base_qty = flt(doc.pending_qty) if flt(doc.pending_qty) > 0 else flt(doc.qty)
    if flt(doc.post_split_qty) < base_qty:
        frappe.throw(
            _("Qty After Split ({0}) cannot be less than Pending Qty ({1})").format(
                flt(doc.post_split_qty, 4), flt(base_qty, 4)
            )
        )

    expected_amount = base_qty * flt(doc.entry_price)
    expected_qty = flt(doc.post_split_qty)

    total_split_amount = 0
    total_split_qty = 0
    for row in doc.investment_portfolio_split:
        q = flt(row.qty)
        p = flt(row.per_share_price)
        a = flt(row.amount)
        if not row.script or not q or (not p and not a):
            frappe.throw(_("Row {0}: Script, Qty and Per Share Price / Amount are mandatory").format(row.idx))
        if not a and p:
            row.amount = q * p
        elif a and not p:
            row.per_share_price = a / q
        total_split_amount += flt(row.amount)
        total_split_qty += q

    if abs(flt(total_split_qty, 4) - flt(expected_qty, 4)) > 0.0001:
        frappe.throw(
            _("Total Split Qty ({0}) must equal Qty After Split ({1})").format(
                flt(total_split_qty, 4), flt(expected_qty, 4)
            )
        )

    if abs(flt(total_split_amount, 2) - flt(expected_amount, 2)) > 0.01:
        diff = expected_amount - total_split_amount
        if diff > 0:
            frappe.throw(
                _("Total Split Amount ({0}) does not match Required Amount ({1} = {2} × {3}). Need additional amount of {4}").format(
                    flt(total_split_amount, 2),
                    flt(expected_amount, 2),
                    flt(base_qty, 4),
                    flt(doc.entry_price, 4),
                    flt(diff, 2),
                )
            )
        else:
            frappe.throw(
                _("Total Split Amount ({0}) exceeds Required Amount ({1} = {2} × {3}) by {4}").format(
                    flt(total_split_amount, 2),
                    flt(expected_amount, 2),
                    flt(base_qty, 4),
                    flt(doc.entry_price, 4),
                    flt(abs(diff), 2),
                )
            )

    action_doc = frappe.new_doc("Investment Corporate Action")
    action_doc.posting_date = nowdate()
    action_doc.entry_type = "Split"
    action_doc.script = doc.script
    action_doc.company = doc.company
    action_doc.split_from = doc.name
    action_doc.qty = expected_qty

    action_doc.append("investment_reference", {
        "investment_portfolio": doc.name,
        "script": doc.script,
        "old_qty": flt(doc.qty),
        "new_qty": flt(doc.qty),
        "old_rate": flt(doc.entry_price),
        "new_rate": flt(doc.entry_price),
        "old_pending_qty": base_qty,
        "new_pending_qty": 0,
        "bonus_qty": 0
    })

    new_docs = []
    for row in doc.investment_portfolio_split:
        new_doc = frappe.new_doc("Investment Portfolio")
        new_doc.segment = doc.segment
        new_doc.category = doc.category
        new_doc.script = row.script
        new_doc.company = doc.company
        new_doc.posting_date = nowdate()
        new_doc.qty = row.qty
        rate = flt(row.per_share_price) if flt(row.per_share_price) else (flt(row.amount) / flt(row.qty))
        amt = flt(row.amount) if flt(row.amount) else (flt(row.qty) * rate)
        new_doc.purchase_entry_price = rate
        new_doc.entry_price = rate
        new_doc.holding_account = doc.holding_account
        new_doc.funds_debited_from = doc.funds_debited_from
        new_doc.investment_charges_account = doc.investment_charges_account
        new_doc.total_cost_of_ownership = amt
        new_doc.is_existing = 1
        new_doc.jv_of_entry = doc.jv_of_entry
        new_doc.split_from = doc.name
        new_doc.is_split = 1
        new_doc.save()
        new_doc.reload()
        new_doc.submit()
        new_doc.db_set("status", "Holding", update_modified=False)

        new_docs.append(new_doc.name)

        action_doc.append("investment_reference", {
            "investment_portfolio": new_doc.name,
            "script": new_doc.script,
            "old_qty": 0,
            "new_qty": flt(new_doc.qty),
            "old_rate": 0,
            "new_rate": flt(new_doc.entry_price),
            "old_pending_qty": 0,
            "new_pending_qty": flt(new_doc.pending_qty) if flt(new_doc.pending_qty) else flt(new_doc.qty),
            "bonus_qty": 0
        })

    doc.db_set("pending_qty", 0)
    doc.db_set("status", "Exited")
    doc.db_set("is_split", 1)

    action_doc.flags.ignore_permissions = True
    action_doc.insert()
    action_doc.submit()

    return new_docs


@frappe.whitelist()
def backfill_bonus_and_split_flags():
    frappe.db.sql("""
        UPDATE `tabInvestment Portfolio` p
        SET p.is_split = 1
        WHERE ((p.split_from IS NOT NULL AND p.split_from != '')
           OR (SELECT COUNT(*) FROM `tabInvestment Portfolio Split` sp WHERE sp.parent = p.name) > 0)
          AND (p.is_split = 0 OR p.is_split IS NULL)
    """)
    frappe.db.sql("""
        UPDATE `tabInvestment Portfolio`
        SET is_bonus_applied = 1
        WHERE (ratio > 0 OR bonus_date IS NOT NULL) AND (is_bonus_applied = 0 OR is_bonus_applied IS NULL)
    """)
    frappe.db.sql("""
        UPDATE `tabInvestment Portfolio`
        SET purchase_entry_price = CASE
            WHEN ratio > 0 THEN ROUND(entry_price * (1.0 + ratio), 4)
            ELSE entry_price
        END
        WHERE purchase_entry_price IS NULL OR purchase_entry_price = 0
    """)
    frappe.db.commit()
    return "Done"