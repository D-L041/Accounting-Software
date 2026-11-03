import { money } from "./formatters";

type Row = Record<string, any>;
type Props = {
  periods: Row[];
  periodId: string;
  setPeriodId: (value: string) => void;
  report: Row | null;
  currency: string;
};

export default function CashbookPanel({ periods, periodId, setPeriodId, report, currency }: Props) {
  return <div className="data-panel">
    <div className="panel-heading">
      <div><h2>Cashbook & bank movements</h2><p>Posted movements through the configured cash, bank and M-Pesa accounts.</p></div>
      <label className="report-period">Financial period<select value={periodId} onChange={e => setPeriodId(e.target.value)}><option value="">Select period</option>{periods.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
    </div>
    {!report ? <div className="table-empty">Select a financial period to view cashbook movements.</div> : <>
      <div className="metric-grid report-metrics">
        <div className="metric"><span>Receipts / debits</span><strong>{money(report.total_receipts, currency)}</strong></div>
        <div className="metric"><span>Payments / credits</span><strong>{money(report.total_payments, currency)}</strong></div>
        <div className="metric"><span>Net movement</span><strong>{money(report.net_movement, currency)}</strong></div>
      </div>
      <div className="table-wrap"><table><thead><tr><th>Date</th><th>Reference</th><th>Account</th><th>Description</th><th>Receipts</th><th>Payments</th><th>Movement balance</th></tr></thead><tbody>
        {(report.transactions || []).map((row: Row, index: number) => <tr key={row.journal_reference + "-" + row.account_id + "-" + index}>
          <td>{row.date}</td><td>{row.journal_reference}</td><td>{row.account_code} — {row.account_name}</td><td>{row.description}</td>
          <td>{money(row.debit, currency)}</td><td>{money(row.credit, currency)}</td><td>{money(row.movement_balance, currency)}</td>
        </tr>)}
      </tbody></table></div>
      <p className="muted report-note">Balances show movements within the selected period only. Opening balances are not included; this report is not a bank reconciliation.</p>
    </>}
  </div>;
}
