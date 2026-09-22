---
trigger: always_on
---

# Project Rules: Python CLI Expense Tracker
- **Data Persistence:** Use a local SQLite database (`expenses.db`). Ensure the schema handles dates, categories, descriptions, and amounts.
- **Data Integrity:** Use Python's `Decimal` module for currency amounts to avoid floating-point errors.
- **Testing:** Every new feature must be tested by executing the script in the terminal via `python3`.
