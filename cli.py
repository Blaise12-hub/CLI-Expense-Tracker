"""
cli.py — Argparse CLI interface for the CLI Expense Tracker.

Defines four subcommands: add, list, delete, summary.
Also exposes a global --summary [YYYY-MM] flag for quick reporting.
All amount handling uses Python's Decimal module.
"""

import argparse
import sys
from decimal import Decimal, InvalidOperation

import db


# ── Formatting helpers ────────────────────────────────────────────────────────

def _print_expenses(rows: list) -> None:
    """Pretty-print a table of expense rows."""
    if not rows:
        print("No expenses found.")
        return

    header = f"{'ID':>4}  {'Date':<12}  {'Category':<15}  {'Amount':>10}  Description"
    print(header)
    print("-" * len(header))
    for row in rows:
        amount = Decimal(row["amount"])
        print(
            f"{row['id']:>4}  {row['date']:<12}  {row['category']:<15}"
            f"  {amount:>10.2f}  {row['description']}"
        )


def _print_summary(entries: list[dict], month_label: str = "") -> None:
    """Render per-category totals as a boxed ASCII table.

    Args:
        entries: List of dicts with 'category' and 'total' (Decimal) keys.
        month_label: Optional header suffix, e.g. ' for 2026-09'.
    """
    if not entries:
        print("No expenses to summarise.")
        return

    # Column widths
    CAT_W   = max(20, max(len(e["category"]) for e in entries) + 2)
    AMT_W   = 12
    SEP     = "+" + "-" * (CAT_W + 2) + "+" + "-" * (AMT_W + 2) + "+"
    TITLE   = f"  Expense Summary{month_label}"

    grand_total = Decimal("0")

    print()
    print(TITLE)
    print(SEP)
    print(f"| {'Category':<{CAT_W}} | {'Total':>{AMT_W}} |")
    print(SEP)
    for entry in entries:
        print(f"| {entry['category']:<{CAT_W}} | {entry['total']:>{AMT_W}.2f} |")
        grand_total += entry["total"]
    print(SEP)
    print(f"| {'TOTAL':<{CAT_W}} | {grand_total:>{AMT_W}.2f} |")
    print(SEP)
    print()


# ── Subcommand handlers ───────────────────────────────────────────────────────

def _handle_add(args: argparse.Namespace) -> None:
    """Parse and insert a new expense."""
    try:
        amount = Decimal(args.amount)
    except InvalidOperation:
        print(f"Error: '{args.amount}' is not a valid amount.", file=sys.stderr)
        sys.exit(1)

    if amount <= 0:
        print("Error: Amount must be a positive number.", file=sys.stderr)
        sys.exit(1)

    expense_id = db.add_expense(
        date=args.date,
        category=args.category,
        description=args.description,
        amount=amount,
    )
    print(f"[OK] Expense #{expense_id} added: {args.category} - {amount:.2f} on {args.date}")


def _handle_list(args: argparse.Namespace) -> None:
    """List all expenses, optionally filtered by category."""
    rows = db.list_expenses(category=args.category)
    _print_expenses(rows)


def _handle_delete(args: argparse.Namespace) -> None:
    """Delete an expense by ID."""
    deleted = db.delete_expense(args.id)
    if deleted:
        print(f"[OK] Expense #{args.id} deleted.")
    else:
        print(f"Error: No expense found with ID {args.id}.", file=sys.stderr)
        sys.exit(1)


def _handle_summary(args: argparse.Namespace) -> None:
    """Print per-category totals, optionally for a specific month."""
    month = getattr(args, "month", None)
    entries = db.get_summary(month=month)
    month_label = f" for {month}" if month else ""
    _print_summary(entries, month_label=month_label)


# ── Argument parser ───────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="expense-tracker",
        description="A stateful CLI expense tracker backed by SQLite.",
    )

    # ── Global flags ──────────────────────────────────────────────────────────
    parser.add_argument(
        "--summary",
        metavar="YYYY-MM",
        nargs="?",
        const="ALL",          # bare --summary with no value = all-time
        default=None,
        help=(
            "Print a spending summary by category. "
            "Optionally pass a month (YYYY-MM) to restrict the report."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = False  # --summary may be used without a subcommand

    # ── add ──────────────────────────────────────────────────────────────────
    add_parser = subparsers.add_parser("add", help="Record a new expense.")
    add_parser.add_argument(
        "--date",
        required=True,
        metavar="YYYY-MM-DD",
        help="Date of the expense in ISO-8601 format.",
    )
    add_parser.add_argument(
        "--category",
        required=True,
        metavar="CATEGORY",
        help="Expense category (e.g. Food, Transport).",
    )
    add_parser.add_argument(
        "--description",
        required=True,
        metavar="TEXT",
        help="Short description of the expense.",
    )
    add_parser.add_argument(
        "--amount",
        required=True,
        metavar="AMOUNT",
        help="Expense amount (e.g. 12.50).",
    )
    add_parser.set_defaults(func=_handle_add)

    # ── list ─────────────────────────────────────────────────────────────────
    list_parser = subparsers.add_parser("list", help="List all recorded expenses.")
    list_parser.add_argument(
        "--category",
        metavar="CATEGORY",
        default=None,
        help="Optional: filter by category.",
    )
    list_parser.set_defaults(func=_handle_list)

    # ── delete ───────────────────────────────────────────────────────────────
    delete_parser = subparsers.add_parser("delete", help="Delete an expense by ID.")
    delete_parser.add_argument(
        "id",
        type=int,
        metavar="ID",
        help="The integer ID of the expense to remove.",
    )
    delete_parser.set_defaults(func=_handle_delete)

    # ── summary ──────────────────────────────────────────────────────────────
    summary_parser = subparsers.add_parser(
        "summary", help="Show per-category spend totals."
    )
    summary_parser.add_argument(
        "--month",
        metavar="YYYY-MM",
        default=None,
        help="Optional: restrict summary to a specific month.",
    )
    summary_parser.set_defaults(func=_handle_summary)

    return parser


# ── Entry ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """Initialise the database and dispatch the requested subcommand."""
    db.init_db()
    parser = _build_parser()
    args = parser.parse_args()

    # ── Global --summary flag takes priority over subcommands ─────────────────
    if args.summary is not None:
        month = None if args.summary == "ALL" else args.summary
        entries = db.get_summary(month=month)
        month_label = f" for {month}" if month else ""
        _print_summary(entries, month_label=month_label)
        return

    # ── Subcommand dispatch ───────────────────────────────────────────────────
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)
