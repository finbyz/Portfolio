# Copyright (c) 2023, finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, date_diff, nowdate, get_url_to_form,flt

class InvestmentPortfolio(Document):
	
	def validate(self):
		self.calculate_entry_amount()
		self.calculate_pending_qty()
		
	def on_update_after_submit(self):
		self.calculate_pending_qty()
		self.set_status()

	def on_cancel(self):
		self.cancel_jv()
	

	def on_update(self):
		self.set_status()

	def set_status(self):
		if self.pending_qty==self.qty:
			self.status="Holding"
		if self.qty!=self.pending_qty:
			self.status="Partially Exited"
		if self.pending_qty == 0:
			self.status="Exited"
		
	def on_submit(self):
		self.create_row_entry_jv()	
		
	def calculate_entry_amount(self):
		self.entry_amount=self.qty*self.entry_price
	
	def calculate_exit_amount(self):
		self.exit_amount=self.exit_price*self.exit_qty
		
	def validate_exit_date(self):
		if self.date_of_investment > self.exit_date:
			frappe.throw("Exit Date Cannot be Greater than Investment Date")	
	
	def create_row_exit_jv(self):
		if not self.bank_account:
			frappe.throw("Bank Account is compulsory")
		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Journal Entry"
		jv.naming_series = "JV-.fiscal.-"
		jv.posting_date = self.exit_date
		net= (self.net_exit_amount - (self.exit_qty*self.entry_price))
		if not self.company:
			self.db_set('company', frappe.defaults.get_global_default('company'))

		jv.company = self.company

		
		jv.append('accounts', {
			'account': self.bank_account,
			'debit_in_account_currency': self.net_exit_amount,
		})

		jv.append('accounts', {
			'account': self.holding_account,
			'credit_in_account_currency': (self.exit_qty*self.entry_price)
		})
		jv.append('accounts', {
			'account': self.funds_credited_to,
			'credit_in_account_currency': net
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
		jv.naming_series = "JV-.fiscal.-"
		jv.posting_date = self.date_of_investment
		
		if not self.company:
			self.db_set('company', frappe.defaults.get_global_default('company'))

		jv.company = self.company

		
		jv.append('accounts', {
			'account': self.funds_debited_from,
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
		if self.jv_of_entry:
			jv = frappe.get_doc("Journal Entry",self.jv_of_entry)
			jv.cancel()
			url = get_url_to_form("Journal Entry", jv.name)
			frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been cancelled .".format(url=url, doc=frappe.bold(jv.name))))	
		for row in self.investment_portfolio_segment:
			jv_doc = frappe.get_doc("Journal Entry" , row.jv_of_exit)
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