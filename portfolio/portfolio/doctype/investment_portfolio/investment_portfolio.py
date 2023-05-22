# Copyright (c) 2023, finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, date_diff, nowdate, get_url_to_form

class InvestmentPortfolio(Document):
	
	def validate(self):
		self.calculate_entry_amount()

	def on_submit(self):
		self.create_row_entry_jv()
		self.db_update()

	
	
	
	def calculate_entry_amount(self):
		self.entry_amount=self.qty*self.entry_price
		
	def validate_exit_date(self):
		if self.date_of_investment > self.exit_date:
			frappe.throw("Exit Date Cannot be Greater than Investment Date")
	
	
	
	@frappe.whitelist()
	def add_cancellation_details(self):
		self.add_cancellation()
		self.db_update()
		self.calculate_cancellation()
		
	
	def create_row_entry_jv(self):
		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Journal Entry"
		jv.naming_series = "JV-.fiscal.-"
		jv.posting_date = self.date_of_investment
		
		if not self.company:
			self.db_set('company', frappe.defaults.get_global_default('company'))

		jv.company = self.company

		
		jv.append('accounts', {
			'account': self.funds_credited_to,
			'credit_in_account_currency': self.total_cost_of_ownership,
		})

		jv.append('accounts', {
			'account': self.investment_charges_account,
			'debit_in_account_currency': self.entry_charges
		})
		jv.append('accounts', {
			'account': self.holding_account,
			'debit_in_account_currency': self.entry_amount
		})

		jv.cheque_no = self.name
		jv.cheque_date = self.date_of_investment

		try:
			jv.save()
		except Exception as e:
			frappe.throw(_(str(e)))
		else:
			jv.submit()
			self.jv_of_entry = jv.name
			url = get_url_to_form("Journal Entry", jv.name)
			frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been created.".format(url=url, doc=frappe.bold(jv.name))))
	

	
		
	@frappe.whitelist()
	def cancel_entry_jv(self):
		jv=frappe.get_doc('Journal Entry',self.jv_of_entry)
		frappe.db.set_value("Investment Portfolio",self.name,"jv_of_entry","")
		self.jv_of_entry=''
		jv.cancel()
		self.db_update()
		url = get_url_to_form("Journal Entry", jv.name)
		frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been cancelled.".format(url=url, doc=frappe.bold(jv.name))))
		self.qty=0.0
		self.entry_price=0.0
		self.entry_amount=0.0
		self.total_cost_of_ownership=0.0

		
		
	

	def create_jv(self, row):
		doc = ''
		for d in self.investment_portfolio_cancellation:
			if d.name == row:
				doc = d
				break

		if not doc.bank_account:
			frappe.throw(_("Please add bank account in row: {}".format(doc.idx)))

		doc.rate_diff = flt(rate_diff)
		doc.profit_or_loss = flt(rate_diff) * flt(doc.qty)
		doc.db_update()

		self.create_row_jv(doc)
		self.db_update()
		self.submit()

	# def get_cancel_jv_number(self,row):
	# 	for d in row:
	# 	   print(d)
	# 	pass

	
	@frappe.whitelist()
	def cancel_jv(self, row):
		print(row)
		to_remove = []

		for d in self.investment_portfolio_cancellation:
			if d.name == row and d.journal_entry:
				jv = frappe.get_doc("Journal Entry", d.journal_entry)
				frappe.msgprint(str(jv))
				d.journal_entry = ''
				d.db_update()
				self.jv_of_exit=''
				frappe.db.set_value("Investment Portfolio",self.name,"jv_of_exit","")
				jv.cancel()
				url = get_url_to_form("Journal Entry", jv.name)
				frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been cancelled.".format(url=url, doc=frappe.bold(jv.name))))
				
				to_remove.append(d)

		[self.remove(d) for d in to_remove]
		self.calculate_cancellation()
		
		self.db_update()
		self.submit()

		
	
	def add_cancellation(self):
		rate_diff=flt(self.exit_price)-flt(self.entry_price)
		row = frappe._dict({
			'date': self.exit_date,
			'rate': self.exit_rate,
			'qty': self.exit_qty,
			'exit_amount': flt(self.exit_rate) * flt(self.exit_qty),
			'exit_charges_calculated':flt(self.net_exit_amount),
			'rate_diff': flt(rate_diff),
			'profit_or_loss': flt(rate_diff) * flt(self.exit_qty),
			'bank_account': self.bank_account,
		})
		row.exit_charges_calculated-=row.exit_amount
		if abs(row.get('profit_or_loss')):
			self.create_row_jv(row)
			self.append('investment_portfolio_cancellation', row)
			self.db_update()
			self.submit()
			
		
		else:
			frappe.msgprint("Journal Entry was not created because there is no profit or loss")
		
		self.exit_price=0.0
		self.net_exit_amount=0.0
		self.exit_date = ''
		self.exit_rate = 0.0
		self.exit_qty = 0.0
		self.bank_account = ''
		self.entry_charges=0.0
	
	def create_row_jv(self, row):
		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Journal Entry"
		jv.naming_series = "JV-.fiscal.-"
		jv.posting_date = self.exit_date
		
		if not self.company:
			self.db_set('company', frappe.defaults.get_global_default('company'))

		jv.company = self.company

		exchange_gain_loss_account = frappe.db.get_value("Company", self.company, 'exchange_gain_loss_account')

		if row.profit_or_loss > 0:
			credit_account = exchange_gain_loss_account
			debit_account = row.bank_account

		else:
			credit_account = row.bank_account
			debit_account = exchange_gain_loss_account

		pnl_amount = abs(row.profit_or_loss)

		jv.append('accounts', {
			'account': credit_account,
			'credit_in_account_currency': pnl_amount,
		})

		jv.append('accounts', {
			'account': debit_account,
			'debit_in_account_currency': pnl_amount
		})

		jv.cheque_no = self.name
		jv.cheque_date = row.date

		try:
			jv.save()
		except Exception as e:
			frappe.throw(_(str(e)))
		else:
			jv.submit()
			row.journal_entry = jv.name
			self.jv_of_exit=jv.name
			url = get_url_to_form("Journal Entry", jv.name)
			frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been created.".format(url=url, doc=frappe.bold(jv.name))))
	
	def validate_cancel_qty(self):
		if self.qty<self.total_cancelled:
			frappe.throw("Cancel Qty is not Greater than entry Qty")

	def on_update_after_submit(self):
		
		self.calculate_cancellation()
		self.validate_cancel_qty()
		self.db_update()
	
	def calculate_cancellation(self):
		total_exit_amount = sum([flt(d.exit_amount) for d in self.investment_portfolio_cancellation])
		total_cancel_qty = sum([flt(d.qty) for d in self.investment_portfolio_cancellation])

		if total_cancel_qty:
			self.total_cancelled = total_cancel_qty
			self.avg_exit_rate = flt(total_exit_amount) / flt(total_cancel_qty)
		else:
			self.total_cancelled = 0
			self.avg_exit_rate=0
		
	
		