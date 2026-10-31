import { money } from "./formatters";

type ReportRow = Record<string, any>;
type Props = {
  reportType: string;
  setReportType: (value: string) => void;
  reportPeriod: string;
  setReportPeriod: (value: string) => void;
  periods: ReportRow[];
  report: ReportRow | null;
  currency: string;
};

function Table({ rows, columns }: { rows: ReportRow[]; columns: { key: string; label: string; format?: (value: any) => string }[] }) {
  if (!rows.length) return <div className="table-empty">No posted activity exists for this report.</div>;
  return <div className="table-wrap"><table><thead><tr>{columns.map(column => <th key={column.key}>{column.label}</th>)}</tr></thead><tbody>
    {rows.map((row, index) => <tr key={row.account_id || index}>{columns.map(column => <td key={column.key}>{column.format ? column.format(row[column.key]) : String(row[column.key] ?? "—")}</td>)}</tr>)}
  </tbody></table></div>;
}

export default function ReportPanel({ reportType, setReportType, reportPeriod, setReportPeriod, periods, report, currency }: Props) {
  const columns = reportType === "trial-balance"
    ? [{ key: "code", label: "Account code" }, { key: "name", label: "Account name" }, { key: "category", label: "Category" }, { key: "debits", label: "Debits", format: (v: any) => money(v, currency) }, { key: "credits", label: "Credits", format: (v: any) => money(v, currency) }, { key: "net_debit", label: "Net debit", format: (v: any) => money(v, currency) }, { key: "net_credit", label: "Net credit", format: (v: any) => money(v, currency) }]
    : reportType === "cash-flow"
    ? [{ key: "date", label: "Date" }, { key: "journal_reference", label: "Reference" }, { key: "description", label: "Description" }, { key: "account_name", label: "Cash / bank account" }, { key: "debit", label: "Inflows", format: (v: any) => money(v, currency) }, { key: "credit", label: "Outflows", format: (v: any) => money(v, currency) }, { key: "movement_balance", label: "Movement balance", format: (v: any) => money(v, currency) }]
    : [{ key: "section", label: "Section" }, { key: "code", label: "Account code" }, { key: "name", label: "Account name" }, { key: "amount", label: "Amount", format: (v: any) => money(v, currency) }];
  let rows: ReportRow[] = [];
  if (report && reportType === "trial-balance") rows = report.accounts || [];
  if (report && reportType === "cash-flow") rows = report.transactions || [];
  if (report && reportType === "income-expenditure") rows = [
    ...(report.income || []).map((item: ReportRow) => ({ ...item, section: "Income" })),
    ...(report.expenditure || []).map((item: ReportRow) => ({ ...item, section: "Expenditure" })),
  ];
  if (report && reportType === "balance-sheet") rows = [
    ...(report.assets || []).map((item: ReportRow) => ({ ...item, section: "Assets" })),
    ...(report.liabilities || []).map((item: ReportRow) => ({ ...item, section: "Liabilities" })),
    ...(report.equity || []).map((item: ReportRow) => ({ ...item, section: "Equity" })),
  ];
  return <div className="data-panel">
    <div className="panel-heading"><div><h2>Financial reports</h2><p>Reports are calculated from posted ledger entries only.</p></div>
      <div className="report-controls"><label className="report-period">Report<select value={reportType} onChange={e => setReportType(e.target.value)}><option value="trial-balance">Trial balance</option><option value="income-expenditure">Income & expenditure</option><option value="balance-sheet">Balance sheet</option><option value="cash-flow">Cash flow movement</option></select></label>
      <label className="report-period">Period<select value={reportPeriod} onChange={e => setReportPeriod(e.target.value)}><option value="">Select period</option>{periods.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div>
    </div>
    {!report ? <div className="table-empty">Select a financial period to generate the report.</div> : <>
      {reportType === "trial-balance" && <div className="metric-grid report-metrics">
        <div className="metric"><span>Total debits</span><strong>{money(report.total_debits, currency)}</strong></div>
        <div className="metric"><span>Total credits</span><strong>{money(report.total_credits, currency)}</strong></div>
        <div className="metric"><span>Difference</span><strong>{money(report.difference, currency)}</strong></div>
        <div className="metric"><span>Control</span><strong className={report.is_balanced ? "balanced" : "unbalanced"}>{report.is_balanced ? "Balanced" : "Out of balance"}</strong></div>
      </div>}
      {reportType === "income-expenditure" && <div className="metric-grid report-metrics">
        <div className="metric"><span>Total income</span><strong>{money(report.total_income, currency)}</strong></div>
        <div className="metric"><span>Total expenditure</span><strong>{money(report.total_expenditure, currency)}</strong></div>
        <div className="metric"><span>Surplus / deficit</span><strong>{money(report.surplus_deficit, currency)}</strong></div>
      </div>}
      {reportType === "cash-flow" && <><div className="metric-grid report-metrics"><div className="metric"><span>Total cash inflows</span><strong>{money(report.total_inflows,currency)}</strong></div><div className="metric"><span>Total cash outflows</span><strong>{money(report.total_outflows,currency)}</strong></div><div className="metric"><span>Net cash movement</span><strong>{money(report.net_cash_movement,currency)}</strong></div></div><p className="muted">Direct movement from posted entries. Opening balances are not included.</p></>}
      {reportType === "balance-sheet" && <div className="metric-grid report-metrics">
        <div className="metric"><span>Total assets</span><strong>{money(report.total_assets, currency)}</strong></div>
        <div className="metric"><span>Liabilities & equity</span><strong>{money(report.total_liabilities_and_equity, currency)}</strong></div>
        <div className="metric"><span>Difference</span><strong>{money(report.difference, currency)}</strong></div>
        <div className="metric"><span>Control</span><strong className={report.is_balanced ? "balanced" : "unbalanced"}>{report.is_balanced ? "Balanced" : "Out of balance"}</strong></div>
      </div>}
      <Table rows={rows} columns={columns}/>
    </>}
  </div>;
}
