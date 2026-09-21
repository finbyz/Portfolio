// Copyright (c) 2026, finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Scrip-wise Balance Statement"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
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
			"fieldname": "show_zero_balance",
			"label": __("Show Zero Balance"),
			"fieldtype": "Check",
			"default": 0
		}
	],

	"onload": function(report) {
		// Attach event listener for column-level Split buttons
		report.page.main.off("click", ".btn-split-report").on("click", ".btn-split-report", function(e) {
			e.preventDefault();
			e.stopPropagation();
			var script = $(this).attr("data-script");
			var company = $(this).attr("data-company") || frappe.query_report.get_filter_value("company");
			open_split_dialog(script, company, report);
		});
	},

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "action") {
			if (data && data.bal_qty > 0) {
				return `<button class="btn btn-xs btn-primary btn-split-report"
					data-script="${frappe.utils.escape_html(data.script)}"
					data-company="${frappe.utils.escape_html(data.company || '')}"
					style="padding: 2px 8px; font-weight: 500; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
					<i class="fa fa-code-fork" style="margin-right: 4px;"></i>${__("Split")}
				</button>`;
			} else {
				return "";
			}
		}

		if (column.fieldname === "bal_qty" && data && data.bal_qty > 0) {
			value = `<strong>${value}</strong>`;
		}

		if (column.fieldname === "bal_val" && data && data.bal_val > 0) {
			value = `<strong>${value}</strong>`;
		}

		if (column.fieldname === "script" && data && data.script) {
			value = `<a href="/app/query-report/Scrip-wise%20Ledger%20Statement?script=${encodeURIComponent(data.script)}&company=${encodeURIComponent(data.company || '')}">${value}</a>`;
		}

		return value;
	}
};


// =========================================================================
// Dialog & Execution Logic for Split Functionality
// =========================================================================

function open_split_dialog(script, company, report) {
	frappe.call({
		method: "portfolio.portfolio.report.scrip_wise_balance_statement.scrip_wise_balance_statement.get_holding_portfolios_for_script",
		args: {
			script: script,
			company: company
		},
		freeze: true,
		freeze_message: __("Fetching Holding Portfolios..."),
		callback: function(r) {
			var portfolios = r.message || [];
			if (!portfolios.length) {
				frappe.msgprint({
					title: __("No Active Holdings"),
					indicator: "orange",
					message: __("No active holding portfolios found for Script <b>{0}</b> (Company: <b>{1}</b>). Split can only be performed on documents with status <b>Holding</b>.", [script, company || 'All'])
				});
				return;
			}

			// Also fetch all scripts for dropdown in split rows
			frappe.call({
				method: "portfolio.portfolio.report.scrip_wise_balance_statement.scrip_wise_balance_statement.get_all_scripts",
				callback: function(res) {
					var all_scripts = res.message || [];
					render_split_dialog(script, company, portfolios, all_scripts, report);
				}
			});
		}
	});
}


function render_split_dialog(current_script, company, portfolios, all_scripts, report) {
	var portfolio_map = {};
	var portfolio_options = portfolios.map(function(p) {
		portfolio_map[p.name] = p;
		var label = `${p.name} | Date: ${p.posting_date} | Qty: ${flt(p.pending_qty || p.qty, 4)} | Rate: ${flt(p.entry_price, 2)} | Amt: ${flt(p.entry_amount, 2)}`;
		return { label: label, value: p.name };
	});

	var default_portfolio = portfolios[0];

	var d = new frappe.ui.Dialog({
		title: __("Split Investment - {0}", [current_script]),
		size: "large",
		fields: [
			{
				fieldname: "info_banner",
				fieldtype: "HTML",
				options: `
					<div style="background-color: #f0f4ff; border-left: 4px solid #3b82f6; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; color: #1e3a8a;">
						<strong><i class="fa fa-info-circle"></i> Stock Split Operation:</strong> Select the portfolio lot, set your desired split ratio (e.g., 2 for a 2:1 split), and allocate the split quantities and prices. This will mark the current document as <em>Exited</em> and create new <em>Holding</em> documents.
					</div>
				`
			},
			{
				fieldname: "portfolio",
				label: __("Select Investment Portfolio Lot"),
				fieldtype: "Select",
				options: portfolio_options,
				default: default_portfolio.name,
				reqd: 1
			},
			{
				fieldname: "col_brk_lot",
				fieldtype: "Column Break"
			},
			{
				fieldname: "posting_date",
				label: __("Date of Investment"),
				fieldtype: "Date",
				default: default_portfolio.posting_date,
				read_only: 1
			},
			{
				fieldname: "sec_details",
				fieldtype: "Section Break",
				label: __("Current Holding Lot Details")
			},
			{
				fieldname: "current_qty",
				label: __("Current Qty"),
				fieldtype: "Float",
				precision: 4,
				default: flt(default_portfolio.pending_qty || default_portfolio.qty, 4),
				read_only: 1
			},
			{
				fieldname: "col_brk_p1",
				fieldtype: "Column Break"
			},
			{
				fieldname: "entry_price",
				label: __("Entry Price"),
				fieldtype: "Currency",
				precision: 4,
				default: flt(default_portfolio.entry_price, 4),
				read_only: 1
			},
			{
				fieldname: "col_brk_p2",
				fieldtype: "Column Break"
			},
			{
				fieldname: "entry_amount",
				label: __("Total Entry Amount"),
				fieldtype: "Currency",
				precision: 2,
				default: flt(default_portfolio.entry_amount, 2),
				read_only: 1
			},
			{
				fieldname: "sec_split_cfg",
				fieldtype: "Section Break",
				label: __("Split Parameters")
			},
			{
				fieldname: "split_ratio",
				label: __("Split Ratio"),
				fieldtype: "Float",
				precision: 4,
				default: 2.0,
				reqd: 1,
				description: __("e.g. 2 for 2:1 split, 5 for 5:1 split, 10 for 10:1 split")
			},
			{
				fieldname: "col_brk_split1",
				fieldtype: "Column Break"
			},
			{
				fieldname: "post_split_qty",
				label: __("Expected Qty After Split"),
				fieldtype: "Float",
				precision: 4,
				default: flt((default_portfolio.pending_qty || default_portfolio.qty) * 2.0, 4),
				read_only: 1
			},
			{
				fieldname: "sec_distribution",
				fieldtype: "Section Break",
				label: __("Split Allocations (Investment Portfolio Split Table)")
			},
			{
				fieldname: "split_table_html",
				fieldtype: "HTML"
			}
		],
		primary_action_label: __("Process Split"),
		primary_action: function() {
			var values = d.get_values();
			if (!values) return;

			var selected_portfolio = values.portfolio;
			var split_ratio = flt(values.split_ratio);
			var expected_qty = flt(values.post_split_qty);
			var target_amount = flt(values.entry_amount);

			if (split_ratio <= 0) {
				frappe.msgprint(__("Split Ratio must be greater than 0"));
				return;
			}

			// Gather rows from HTML table
			var rows = [];
			var total_qty = 0;
			var total_amt = 0;
			var has_invalid_row = false;

			d.$wrapper.find(".split-table-body tr").each(function(idx) {
				var $tr = $(this);
				var row_script = $tr.find(".input-row-script").val();
				var row_qty = flt($tr.find(".input-row-qty").val());
				var row_price = flt($tr.find(".input-row-price").val());
				var row_amount = flt($tr.find(".input-row-amount").val()) || (row_qty * row_price);

				if (!row_script || row_qty <= 0 || row_price <= 0) {
					has_invalid_row = true;
					frappe.msgprint(__("Row {0}: Script, Qty and Price are mandatory and must be > 0", [idx + 1]));
					return false;
				}

				total_qty += row_qty;
				total_amt += row_amount;

				rows.push({
					script: row_script,
					qty: row_qty,
					per_share_price: row_price,
					amount: row_amount
				});
			});

			if (has_invalid_row) return;

			if (!rows.length) {
				frappe.msgprint(__("At least one split row is required"));
				return;
			}

			// Precision validation as per document-level rules
			if (Math.abs(total_qty - expected_qty) > 0.0001) {
				frappe.msgprint(__("Total Split Qty ({0}) must equal Expected Qty ({1})", [flt(total_qty, 4), flt(expected_qty, 4)]));
				return;
			}

			if (Math.abs(total_amt - target_amount) > 0.05) {
				frappe.msgprint(__("Total Split Amount ({0}) must equal Entry Amount ({1})", [flt(total_amt, 2), flt(target_amount, 2)]));
				return;
			}

			frappe.confirm(
				__("Are you sure you want to execute split on portfolio <b>{0}</b>? This will mark it as <b>Exited</b> and generate new <b>Holding</b> documents for each split row.", [selected_portfolio]),
				function() {
					frappe.call({
						method: "portfolio.portfolio.report.scrip_wise_balance_statement.scrip_wise_balance_statement.execute_portfolio_split",
						args: {
							portfolio: selected_portfolio,
							split_ratio: split_ratio,
							split_rows: JSON.stringify(rows)
						},
						freeze: true,
						freeze_message: __("Processing Split on Investment Portfolio..."),
						callback: function(res) {
							if (res.message) {
								d.hide();
								var created_links = res.message.map(function(docname) {
									return frappe.utils.get_form_link("Investment Portfolio", docname, true);
								}).join(", ");

								frappe.msgprint({
									title: __("Split Successful"),
									indicator: "green",
									message: __("Successfully processed Split! Created new Investment Portfolio document(s): {0}", [created_links])
								});

								// Refresh report to display new combined balances immediately
								report.refresh();
							}
						}
					});
				}
			);
		}
	});

	d.show();

	// Helper to build script select options
	function get_script_options_html(selected) {
		var html = `<option value="${frappe.utils.escape_html(current_script)}">${frappe.utils.escape_html(current_script)}</option>`;
		all_scripts.forEach(function(s) {
			if (s.name !== current_script) {
				var opt = frappe.utils.escape_html(s.name);
				var sel = (s.name === selected) ? ' selected' : '';
				html += `<option value="${opt}"${sel}>${opt}</option>`;
			}
		});
		return html;
	}

	// Render Table Container
	var $container = d.fields_dict.split_table_html.$wrapper;
	$container.html(`
		<div class="split-table-wrapper" style="margin-top: 5px;">
			<table class="table table-bordered table-condensed table-hover" style="margin-bottom: 8px; font-size: 13px;">
				<thead style="background-color: #f8fafc;">
					<tr>
						<th style="width: 32%;">${__("Script")}</th>
						<th style="width: 22%;">${__("Qty")}</th>
						<th style="width: 22%;">${__("Per Share Price")}</th>
						<th style="width: 20%;">${__("Amount")}</th>
						<th style="width: 4%; text-align: center;"></th>
					</tr>
				</thead>
				<tbody class="split-table-body">
				</tbody>
			</table>
			<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
				<button type="button" class="btn btn-xs btn-default btn-add-split-row">
					<i class="fa fa-plus"></i> ${__("Add Row")}
				</button>
				<div class="split-validation-status" style="display: flex; gap: 12px; font-size: 12px;">
					<span class="badge-qty" style="padding: 4px 8px; border-radius: 4px; font-weight: 500;"></span>
					<span class="badge-amt" style="padding: 4px 8px; border-radius: 4px; font-weight: 500;"></span>
				</div>
			</div>
		</div>
	`);

	function add_row(script_val, qty_val, price_val, amt_val) {
		var script_options = get_script_options_html(script_val);
		var $tr = $(`
			<tr>
				<td>
					<select class="form-control input-sm input-row-script">
						${script_options}
					</select>
				</td>
				<td>
					<input type="number" step="any" class="form-control input-sm input-row-qty" value="${qty_val}" style="text-align: right;" />
				</td>
				<td>
					<input type="number" step="any" class="form-control input-sm input-row-price" value="${price_val}" style="text-align: right;" />
				</td>
				<td>
					<input type="text" readonly class="form-control input-sm input-row-amount" value="${amt_val}" style="text-align: right; background-color: #f9fafb;" />
				</td>
				<td style="text-align: center; vertical-align: middle;">
					<button type="button" class="btn btn-xs btn-link text-danger btn-remove-row" style="padding: 0;">
						<i class="fa fa-trash"></i>
					</button>
				</td>
			</tr>
		`);

		$container.find(".split-table-body").append($tr);
		recalculate();
	}

	function recalculate() {
		var exp_qty = flt(d.get_value("post_split_qty"));
		var target_amt = flt(d.get_value("entry_amount"));

		var total_qty = 0;
		var total_amt = 0;

		$container.find(".split-table-body tr").each(function() {
			var $tr = $(this);
			var q = flt($tr.find(".input-row-qty").val());
			var p = flt($tr.find(".input-row-price").val());
			var a = flt(q * p, 2);
			$tr.find(".input-row-amount").val(a.toFixed(2));
			total_qty += q;
			total_amt += a;
		});

		var $qty_badge = $container.find(".badge-qty");
		var $amt_badge = $container.find(".badge-amt");

		// Check quantity match
		if (Math.abs(total_qty - exp_qty) <= 0.0001) {
			$qty_badge.css({"background-color": "#dcfce7", "color": "#15803d"})
				.html(`✓ Qty Matched: <b>${flt(total_qty, 4)} / ${flt(exp_qty, 4)}</b>`);
		} else {
			var diff_qty = total_qty - exp_qty;
			$qty_badge.css({"background-color": "#fee2e2", "color": "#b91c1c"})
				.html(`✕ Qty Mismatch: <b>${flt(total_qty, 4)}</b> (Target: ${flt(exp_qty, 4)}, Diff: ${flt(diff_qty, 4)})`);
		}

		// Check amount match
		if (Math.abs(total_amt - target_amt) <= 0.05) {
			$amt_badge.css({"background-color": "#dcfce7", "color": "#15803d"})
				.html(`✓ Amount Matched: <b>${total_amt.toFixed(2)} / ${target_amt.toFixed(2)}</b>`);
		} else {
			var diff_amt = total_amt - target_amt;
			$amt_badge.css({"background-color": "#fee2e2", "color": "#b91c1c"})
				.html(`✕ Amount Mismatch: <b>${total_amt.toFixed(2)}</b> (Target: ${target_amt.toFixed(2)}, Diff: ${diff_amt.toFixed(2)})`);
		}
	}

	function reset_to_default_split() {
		var cur_qty = flt(d.get_value("current_qty"));
		var ratio = flt(d.get_value("split_ratio")) || 1.0;
		var ent_amt = flt(d.get_value("entry_amount"));

		var new_qty = flt(cur_qty * ratio, 4);
		var new_price = new_qty > 0 ? flt(ent_amt / new_qty, 4) : 0;

		d.set_value("post_split_qty", new_qty);

		$container.find(".split-table-body").empty();
		add_row(current_script, new_qty, new_price, ent_amt.toFixed(2));
	}

	// Handlers for table events
	$container.on("input", ".input-row-qty, .input-row-price", function() {
		recalculate();
	});

	$container.on("click", ".btn-remove-row", function() {
		if ($container.find(".split-table-body tr").length > 1) {
			$(this).closest("tr").remove();
			recalculate();
		} else {
			frappe.show_alert({message: __("At least one split row is required"), indicator: "orange"});
		}
	});

	$container.on("click", ".btn-add-split-row", function() {
		add_row(current_script, 0, 0, "0.00");
	});

	// Handler for portfolio selection change
	d.fields_dict.portfolio.$input.on("change", function() {
		var sel_name = d.get_value("portfolio");
		var p = portfolio_map[sel_name];
		if (p) {
			var rem_qty = flt(p.pending_qty || p.qty, 4);
			d.set_value("posting_date", p.posting_date);
			d.set_value("current_qty", rem_qty);
			d.set_value("entry_price", flt(p.entry_price, 4));
			d.set_value("entry_amount", flt(p.entry_amount, 2));

			reset_to_default_split();
		}
	});

	// Handler for split ratio change
	d.fields_dict.split_ratio.$input.on("input change", function() {
		var ratio = flt(d.get_value("split_ratio"));
		var cur_qty = flt(d.get_value("current_qty"));
		var ent_amt = flt(d.get_value("entry_amount"));

		if (ratio > 0) {
			var new_qty = flt(cur_qty * ratio, 4);
			d.set_value("post_split_qty", new_qty);

			// If only one row exists, automatically adapt it
			var $rows = $container.find(".split-table-body tr");
			if ($rows.length === 1) {
				var new_price = new_qty > 0 ? flt(ent_amt / new_qty, 4) : 0;
				$rows.find(".input-row-qty").val(new_qty);
				$rows.find(".input-row-price").val(new_price);
				$rows.find(".input-row-amount").val(ent_amt.toFixed(2));
			}
			recalculate();
		}
	});

	// Initial population of table
	reset_to_default_split();
}
