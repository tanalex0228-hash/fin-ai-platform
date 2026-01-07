# services/financials_service.py
import sqlite3

DB_PATH = "instance/app.db"

def _query(conn, sql, params=()):
    cur = conn.execute(sql, params)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return rows

def get_financials(stock_id: str, limit: int = 8, latest: bool = False):
    if latest:
        limit = 1

    conn = sqlite3.connect(DB_PATH)

    income = _query(conn, """
        SELECT date, revenue, gross_profit, operating_income, net_income, eps
        FROM financial_income_statement
        WHERE stock_id = ?
        ORDER BY date DESC
        LIMIT ?
    """, (stock_id, limit))

    balance = _query(conn, """
        SELECT date, total_assets, total_liabilities, shareholders_equity, current_assets, current_liabilities
        FROM financial_balance_sheet
        WHERE stock_id = ?
        ORDER BY date DESC
        LIMIT ?
    """, (stock_id, limit))

    cashflow = _query(conn, """
        SELECT date, operating_cashflow, investing_cashflow, financing_cashflow, free_cashflow
        FROM financial_cashflow
        WHERE stock_id = ?
        ORDER BY date DESC
        LIMIT ?
    """, (stock_id, limit))

    conn.close()

    return {
        "stock_id": stock_id,
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow": cashflow,
        "meta": {
            "limit": limit
        }
    }
