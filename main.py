
import flet as ft
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import math
import time
from datetime import date, datetime, timedelta

from transaction import Transaction


# ---------------- DATA STORAGE ----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "transactions.json")


def load_transactions():
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_transactions(transactions):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(transactions, file, indent=4)


def save_transaction(transaction):
    transactions = load_transactions()
    transactions.append(transaction.to_dict())
    save_transactions(transactions)


def validate_transaction(kind, amount, category, transaction_date, description):
    """Validate transaction details before saving."""

    kind = (kind or "").strip().title()
    category = (category or "").strip()
    transaction_date = (transaction_date or "").strip()
    description = (description or "").strip()

    if kind not in ["Income", "Expense"]:
        return None, "Type must be Income or Expense."

    try:
        value = float(amount)
    except (ValueError, TypeError):
        return None, "Please enter a valid amount."

    if not math.isfinite(value) or value <= 0:
        return None, "Amount must be a positive, finite number."

    if not category:
        return None, "Please enter a category."

    if not any(char.isalpha() for char in category):
        return None, "Category must contain at least one letter."

    try:
        parsed_date = date.fromisoformat(transaction_date)

        if parsed_date.isoformat() != transaction_date:
            return None, "Date must use YYYY-MM-DD format."

    except ValueError:
        return None, "Please enter a valid date (YYYY-MM-DD)."

    return (
        Transaction(
            kind,
            value,
            category,
            transaction_date,
            description
        ),
        None
    )


# ---------------- CHART GENERATION ----------------

def create_monthly_chart(transactions, selected_month):
    """Create a six-month income versus expenses chart."""

    selected_date = datetime.strptime(selected_month, "%Y-%m")

    months = []

    for offset in range(5, -1, -1):
        month_number = selected_date.month - offset
        year = selected_date.year

        while month_number <= 0:
            month_number += 12
            year -= 1

        months.append(f"{year:04d}-{month_number:02d}")

    monthly_income = {month: 0 for month in months}
    monthly_expenses = {month: 0 for month in months}

    for transaction in transactions:
        try:
            transaction_date = datetime.strptime(
                transaction["date"], "%Y-%m-%d"
            )

            month = transaction_date.strftime("%Y-%m")
            amount = float(transaction["amount"])

            if month in monthly_income:
                if transaction["transaction_type"] == "Income":
                    monthly_income[month] += amount

                elif transaction["transaction_type"] == "Expense":
                    monthly_expenses[month] += amount

        except (ValueError, TypeError, KeyError):
            continue

    labels = [
        datetime.strptime(month, "%Y-%m").strftime("%b %Y")
        for month in months
    ]

    income_values = [monthly_income[m] for m in months]
    expense_values = [monthly_expenses[m] for m in months]

    positions = list(range(len(months)))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.bar(
        [p - width / 2 for p in positions],
        income_values,
        width,
        label="Income",
        color="#16A34A"
    )

    ax.bar(
        [p + width / 2 for p in positions],
        expense_values,
        width,
        label="Expenses",
        color="#DC2626"
    )

    ax.set_title("Monthly Income vs Expenses", fontsize=14)
    ax.set_xlabel("Month")
    ax.set_ylabel("Amount (R)")
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()

    chart_dir = os.path.join(BASE_DIR, "assets", "charts")
    os.makedirs(chart_dir, exist_ok=True)

    chart_path = os.path.join(
        chart_dir,
        f"monthly_{selected_month}_{time.time_ns()}.png"
    )

    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return chart_path


def create_category_chart(categories, selected_month):
    """Create an expense-by-category horizontal bar chart."""

    fig, ax = plt.subplots(figsize=(9, 5))

    sorted_categories = sorted(
        categories.items(),
        key=lambda item: item[1]
    )

    names = [item[0] for item in sorted_categories]
    amounts = [item[1] for item in sorted_categories]

    ax.barh(
        names,
        amounts,
        color="#2563EB"
    )

    ax.set_title(
        f"Expenses by Category - {selected_month}",
        fontsize=14
    )

    ax.set_xlabel("Amount (R)")
    ax.set_ylabel("Category")
    ax.grid(axis="x", alpha=0.25)

    fig.tight_layout()

    chart_dir = os.path.join(BASE_DIR, "assets", "charts")
    os.makedirs(chart_dir, exist_ok=True)

    chart_path = os.path.join(
        chart_dir,
        f"categories_{selected_month}_{time.time_ns()}.png"
    )

    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return chart_path


# ---------------- MAIN APPLICATION ----------------

def main(page: ft.Page):

    page.title = "Personal Finance Tracker"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F4F6FA"
    page.padding = 20
    page.window.width = 1100
    page.window.height = 750

    content = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO
    )

    # ---------------- SUMMARY ----------------

    def get_summary():
        transactions = load_transactions()

        income = sum(
            float(t["amount"])
            for t in transactions
            if t["transaction_type"] == "Income"
        )

        expenses = sum(
            float(t["amount"])
            for t in transactions
            if t["transaction_type"] == "Expense"
        )

        return transactions, income, expenses, income - expenses

    # ---------------- REUSABLE CARDS ----------------

    def card(title, value, color):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title, size=14, color="#64748B"),
                    ft.Text(
                        value,
                        size=25,
                        weight=ft.FontWeight.BOLD,
                        color=color
                    )
                ],
                spacing=10
            ),
            padding=22,
            bgcolor="white",
            border_radius=14,
            width=300
        )

    # ---------------- DASHBOARD ----------------

    def show_dashboard():

        transactions, income, expenses, balance = get_summary()

        recent_transactions = sorted(
            transactions,
            key=lambda t: t.get("date", ""),
            reverse=True
        )[:5]

        recent_controls = []

        for transaction in recent_transactions:

            transaction_type = transaction.get(
                "transaction_type", ""
            )

            color = (
                "#16A34A"
                if transaction_type == "Income"
                else "#DC2626"
            )

            recent_controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        transaction.get("category", ""),
                                        weight=ft.FontWeight.BOLD,
                                        size=15
                                    ),
                                    ft.Text(
                                        f'{transaction_type} | '
                                        f'{transaction.get("date", "")}',
                                        color="#64748B",
                                        size=12
                                    ),
                                    ft.Text(
                                        transaction.get("description", ""),
                                        color="#64748B",
                                        size=12
                                    )
                                ],
                                expand=True,
                                spacing=4
                            ),

                            ft.Text(
                                f'R {float(transaction.get("amount", 0)):,.2f}',
                                color=color,
                                weight=ft.FontWeight.BOLD,
                                size=15
                            )
                        ]
                    ),
                    padding=15,
                    bgcolor="white",
                    border_radius=10
                )
            )

        if not recent_controls:
            recent_controls.append(
                ft.Text(
                    "No transactions recorded yet.",
                    color="#64748B"
                )
            )

        content.controls = [
            ft.Text(
                "Financial Overview",
                size=28,
                weight=ft.FontWeight.BOLD,
                color="#1E293B"
            ),

            ft.Text(
                "Track your income, expenses and financial position.",
                color="#64748B",
                size=14
            ),

            ft.Row(
                controls=[
                    card("Total Income", f"R {income:,.2f}", "#16A34A"),
                    card("Total Expenses", f"R {expenses:,.2f}", "#DC2626"),
                    card("Current Balance", f"R {balance:,.2f}", "#2563EB")
                ],
                spacing=15,
                wrap=True
            ),

            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Recent Transactions",
                            size=21,
                            weight=ft.FontWeight.BOLD,
                            color="#1E293B"
                        ),

                        ft.Text(
                            f"Showing your latest {min(len(transactions), 5)} "
                            f"of {len(transactions)} transactions.",
                            size=12,
                            color="#64748B"
                        ),

                        *recent_controls
                    ],
                    spacing=12
                ),
                padding=20,
                bgcolor="#F4F6FA",
                border_radius=14
            )
        ]

        page.update()

    # ---------------- ADD TRANSACTION ----------------

    def show_add_transaction():

        transaction_type = ft.TextField(
            label="Type (Income or Expense)",
            hint_text="Enter Income or Expense"
        )

        amount = ft.TextField(
            label="Amount (R)",
            keyboard_type=ft.KeyboardType.NUMBER
        )

        category = ft.TextField(
            label="Category",
            hint_text="e.g. Food, Transport, Salary"
        )

        transaction_date = ft.TextField(
            label="Date",
            value=date.today().isoformat()
        )

        description = ft.TextField(
            label="Description",
            multiline=True
        )

        message = ft.Text()

        def submit_transaction(e):

            new_transaction, error = validate_transaction(
                transaction_type.value,
                amount.value,
                category.value,
                transaction_date.value,
                description.value
            )

            if error:
                message.value = error
                message.color = "#DC2626"
                page.update()
                return

            save_transaction(new_transaction)
            show_dashboard()

        content.controls = [
            ft.Text(
                "Add Transaction",
                size=28,
                weight=ft.FontWeight.BOLD
            ),

            ft.Text(
                "Record your income or expenses.",
                color="#64748B"
            ),

            ft.Container(
                content=ft.Column([
                    transaction_type,
                    amount,
                    category,
                    transaction_date,
                    description,

                    ft.Button(
                        content=ft.Text("Save Transaction"),
                        on_click=submit_transaction
                    ),

                    message
                ], spacing=15),

                padding=25,
                bgcolor="white",
                border_radius=12
            )
        ]

        page.update()

    # ---------------- EDIT TRANSACTION ----------------

    def show_edit_transaction(index):

        transactions = load_transactions()

        if index < 0 or index >= len(transactions):
            show_history()
            return

        transaction = transactions[index]

        transaction_type = ft.TextField(
            label="Type (Income or Expense)",
            value=transaction["transaction_type"]
        )

        amount = ft.TextField(
            label="Amount (R)",
            value=str(transaction["amount"]),
            keyboard_type=ft.KeyboardType.NUMBER
        )

        category = ft.TextField(
            label="Category",
            value=transaction["category"]
        )

        transaction_date = ft.TextField(
            label="Date",
            value=transaction["date"]
        )

        description = ft.TextField(
            label="Description",
            value=transaction.get("description", ""),
            multiline=True
        )

        message = ft.Text()

        def update_transaction(e):

            updated_transaction, error = validate_transaction(
                transaction_type.value,
                amount.value,
                category.value,
                transaction_date.value,
                description.value
            )

            if error:
                message.value = error
                message.color = "#DC2626"
                page.update()
                return

            current_transactions = load_transactions()

            if index >= len(current_transactions):
                message.value = "Transaction could not be found."
                message.color = "#DC2626"
                page.update()
                return

            current_transactions[index] = updated_transaction.to_dict()

            save_transactions(current_transactions)
            show_history()

        content.controls = [
            ft.Text(
                "Edit Transaction",
                size=28,
                weight=ft.FontWeight.BOLD
            ),

            ft.Container(
                content=ft.Column([
                    transaction_type,
                    amount,
                    category,
                    transaction_date,
                    description,

                    ft.Button(
                        content=ft.Text("Save Changes"),
                        on_click=update_transaction
                    ),

                    ft.Button(
                        content=ft.Text("Cancel"),
                        on_click=lambda e: show_history()
                    ),

                    message
                ], spacing=15),

                padding=25,
                bgcolor="white",
                border_radius=12
            )
        ]

        page.update()

    # ---------------- TRANSACTION HISTORY ----------------

    def show_history():

        transactions = load_transactions()

        search_input = ft.TextField(
            label="Search",
            hint_text="Search descriptions or categories",
            expand=True
        )

        type_input = ft.TextField(
            label="Transaction Type",
            hint_text="All, Income or Expense",
            width=180
        )

        category_input = ft.TextField(
            label="Category",
            hint_text="e.g. Food",
            width=180
        )

        start_date_input = ft.TextField(
            label="Start Date",
            hint_text="YYYY-MM-DD",
            width=180
        )

        end_date_input = ft.TextField(
            label="End Date",
            hint_text="YYYY-MM-DD",
            width=180
        )

        message = ft.Text()
        transaction_list = ft.Column(spacing=10)

        def render_transactions(e=None):

            current_transactions = load_transactions()

            search_term = (
                (search_input.value or "").strip().casefold()
            )

            transaction_type = (
                (type_input.value or "").strip().title()
            )

            category_filter = (
                (category_input.value or "").strip().casefold()
            )

            start_date_text = (
                (start_date_input.value or "").strip()
            )

            end_date_text = (
                (end_date_input.value or "").strip()
            )

            # Validate transaction type

            if transaction_type not in [
                "", "All", "Income", "Expense"
            ]:
                message.value = "Type must be All, Income or Expense."
                message.color = "#DC2626"
                page.update()
                return

            # Validate date filters

            try:
                start_date = (
                    date.fromisoformat(start_date_text)
                    if start_date_text else None
                )

                end_date = (
                    date.fromisoformat(end_date_text)
                    if end_date_text else None
                )

            except ValueError:
                message.value = "Dates must use YYYY-MM-DD format."
                message.color = "#DC2626"
                page.update()
                return

            if start_date and end_date and start_date > end_date:
                message.value = "Start date cannot be after end date."
                message.color = "#DC2626"
                page.update()
                return

            filtered_transactions = []

            for index, transaction in enumerate(current_transactions):

                kind = transaction.get("transaction_type", "")
                category = transaction.get("category", "")
                description = transaction.get("description", "")
                transaction_date_text = transaction.get("date", "")

                # Filter by transaction type

                if transaction_type not in ["", "All"]:
                    if kind != transaction_type:
                        continue

                # Filter by category

                if category_filter:
                    if category.casefold() != category_filter:
                        continue

                # Search descriptions and categories

                searchable_text = (
                    f"{category} {description}"
                ).casefold()

                if search_term and search_term not in searchable_text:
                    continue

                # Filter by date range

                try:
                    parsed_transaction_date = date.fromisoformat(
                        transaction_date_text
                    )

                except (ValueError, TypeError):
                    if start_date or end_date:
                        continue

                    parsed_transaction_date = None

                if start_date and (
                    parsed_transaction_date is None
                    or parsed_transaction_date < start_date
                ):
                    continue

                if end_date and (
                    parsed_transaction_date is None
                    or parsed_transaction_date > end_date
                ):
                    continue

                filtered_transactions.append((index, transaction))

            # Display newest transactions first

            filtered_transactions.sort(
                key=lambda item: item[1].get("date", ""),
                reverse=True
            )

            transaction_list.controls.clear()

            if not filtered_transactions:
                transaction_list.controls.append(
                    ft.Text(
                        "No transactions match your filters.",
                        color="#64748B"
                    )
                )

            for index, transaction in filtered_transactions:

                color = (
                    "#16A34A"
                    if transaction["transaction_type"] == "Income"
                    else "#DC2626"
                )

                def delete_transaction(e, transaction_index=index):

                    current = load_transactions()

                    if (
                        transaction_index < 0
                        or transaction_index >= len(current)
                    ):
                        return

                    current.pop(transaction_index)
                    save_transactions(current)

                    render_transactions()

                transaction_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(
                                    transaction["category"],
                                    weight=ft.FontWeight.BOLD,
                                    size=16
                                ),

                                ft.Text(
                                    f'{transaction["transaction_type"]} | '
                                    f'{transaction["date"]}',
                                    color="#64748B"
                                ),

                                ft.Text(
                                    transaction.get("description", ""),
                                    color="#64748B"
                                )
                            ], expand=True),

                            ft.Text(
                                f'R {float(transaction["amount"]):,.2f}',
                                color=color,
                                weight=ft.FontWeight.BOLD
                            ),

                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                tooltip="Edit transaction",
                                on_click=lambda e, i=index:
                                    show_edit_transaction(i)
                            ),

                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color="#DC2626",
                                tooltip="Delete transaction",
                                on_click=delete_transaction
                            )
                        ]),

                        padding=15,
                        bgcolor="white",
                        border_radius=10
                    )
                )

            message.value = (
                f"Showing {len(filtered_transactions)} of "
                f"{len(current_transactions)} transactions."
            )

            message.color = "#64748B"

            page.update()

        def clear_filters(e):

            search_input.value = ""
            type_input.value = ""
            category_input.value = ""
            start_date_input.value = ""
            end_date_input.value = ""

            render_transactions()

        content.controls = [
            ft.Text(
                "Transaction History",
                size=28,
                weight=ft.FontWeight.BOLD
            ),

            ft.Text(
                "Search, filter, edit and delete your transactions.",
                color="#64748B"
            ),

            ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Filter Transactions",
                        size=19,
                        weight=ft.FontWeight.BOLD
                    ),

                    search_input,

                    ft.Row([
                        type_input,
                        category_input
                    ], wrap=True, spacing=10),

                    ft.Row([
                        start_date_input,
                        end_date_input
                    ], wrap=True, spacing=10),

                    ft.Row([
                        ft.Button(
                            content=ft.Text("Apply Filters"),
                            on_click=render_transactions
                        ),

                        ft.Button(
                            content=ft.Text("Clear Filters"),
                            on_click=clear_filters
                        )
                    ], wrap=True, spacing=10)

                ], spacing=12),

                padding=20,
                bgcolor="white",
                border_radius=12
            ),

            message,
            transaction_list
        ]

        render_transactions()

    # ---------------- FINANCIAL REPORTS ----------------

    def show_reports():

        current_month = date.today().strftime("%Y-%m")

        month_input = ft.TextField(
            label="Select month (YYYY-MM)",
            value=current_month,
            width=220
        )

        message = ft.Text()
        report_body = ft.Column(spacing=15)

        def calculate_monthly_summary(transactions, selected_month):

            income = 0
            expenses = 0
            categories = {}
            transaction_count = 0

            for transaction in transactions:

                try:
                    transaction_date = datetime.strptime(
                        transaction["date"], "%Y-%m-%d"
                    )

                except (ValueError, TypeError, KeyError):
                    continue

                if transaction_date.strftime("%Y-%m") != selected_month:
                    continue

                transaction_count += 1
                amount = float(transaction["amount"])

                if transaction["transaction_type"] == "Income":
                    income += amount

                elif transaction["transaction_type"] == "Expense":

                    expenses += amount
                    category = transaction["category"]

                    categories[category] = (
                        categories.get(category, 0) + amount
                    )

            return income, expenses, categories, transaction_count

        def render_month_report(e=None):

            try:
                selected_month = month_input.value.strip()

                parsed_month = datetime.strptime(
                    selected_month, "%Y-%m"
                )

                selected_month = parsed_month.strftime("%Y-%m")

            except (ValueError, AttributeError):
                message.value = "Enter a valid month in YYYY-MM format."
                message.color = "#DC2626"
                page.update()
                return

            transactions = load_transactions()

            income, expenses, categories, count = (
                calculate_monthly_summary(
                    transactions, selected_month
                )
            )

            balance = income - expenses

            savings_rate = (
                (balance / income) * 100 if income > 0 else 0
            )

            monthly_chart = create_monthly_chart(
                transactions, selected_month
            )

            category_chart = (
                create_category_chart(categories, selected_month)
                if categories else None
            )

            previous_month = (
                parsed_month.replace(day=1) - timedelta(days=1)
            ).strftime("%Y-%m")

            prev_income, prev_expenses, _, _ = (
                calculate_monthly_summary(
                    transactions, previous_month
                )
            )

            prev_balance = prev_income - prev_expenses

            income_change = income - prev_income
            expense_change = expenses - prev_expenses
            balance_change = balance - prev_balance

            report_body.controls = [

                ft.Row([
                    card(
                        "Monthly Income",
                        f"R {income:,.2f}",
                        "#16A34A"
                    ),

                    card(
                        "Monthly Expenses",
                        f"R {expenses:,.2f}",
                        "#DC2626"
                    ),

                    card(
                        "Net Balance",
                        f"R {balance:,.2f}",
                        "#2563EB"
                    )
                ], spacing=15),

                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Monthly Savings Rate",
                            size=17,
                            weight=ft.FontWeight.BOLD
                        ),

                        ft.Text(
                            f"{savings_rate:.2f}%",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=(
                                "#16A34A"
                                if balance >= 0
                                else "#DC2626"
                            )
                        ),

                        ft.Text(
                            "Calculated as (Income - Expenses) / Income.",
                            color="#64748B",
                            size=12
                        )
                    ], spacing=8),

                    padding=20,
                    bgcolor="white",
                    border_radius=12
                ),

                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            f"Comparison with {previous_month}",
                            size=18,
                            weight=ft.FontWeight.BOLD
                        ),

                        ft.Text(
                            f"Income change: R {income_change:+,.2f}"
                        ),

                        ft.Text(
                            f"Expense change: R {expense_change:+,.2f}"
                        ),

                        ft.Text(
                            f"Net balance change: R {balance_change:+,.2f}"
                        )
                    ], spacing=10),

                    padding=20,
                    bgcolor="white",
                    border_radius=12
                ),

                ft.Text(
                    "Monthly Financial Trends",
                    size=21,
                    weight=ft.FontWeight.BOLD
                ),

                ft.Container(
                    content=ft.Image(
                        src=os.path.relpath(
                            monthly_chart, BASE_DIR
                        ).replace("\\", "/"),
                        width=750
                    ),

                    padding=15,
                    bgcolor="white",
                    border_radius=12
                ),

                ft.Text(
                    "Spending Distribution",
                    size=21,
                    weight=ft.FontWeight.BOLD
                ),

                *(
                    [
                        ft.Container(
                            content=ft.Image(
                                src=os.path.relpath(
                                    category_chart, BASE_DIR
                                ).replace("\\", "/"),
                                width=750
                            ),

                            padding=15,
                            bgcolor="white",
                            border_radius=12
                        )
                    ]

                    if category_chart else [
                        ft.Text(
                            "No category chart available for this month.",
                            color="#64748B"
                        )
                    ]
                ),

                ft.Text(
                    "Expenses by Category",
                    size=21,
                    weight=ft.FontWeight.BOLD
                )
            ]

            if categories:

                for name, total in sorted(
                    categories.items(),
                    key=lambda item: item[1],
                    reverse=True
                ):

                    report_body.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(name, expand=True),

                                ft.Text(
                                    f"R {total:,.2f}",
                                    weight=ft.FontWeight.BOLD,
                                    color="#DC2626"
                                )
                            ]),

                            padding=15,
                            bgcolor="white",
                            border_radius=10
                        )
                    )

            else:

                report_body.controls.append(
                    ft.Text(
                        "No expenses recorded for this month.",
                        color="#64748B"
                    )
                )

            report_body.controls.append(
                ft.Text(
                    f"Total transactions: {count}",
                    color="#64748B"
                )
            )

            message.value = ""

            page.update()

        content.controls = [
            ft.Text(
                "Financial Reports",
                size=28,
                weight=ft.FontWeight.BOLD
            ),

            ft.Text(
                "Analyse your monthly financial performance.",
                color="#64748B"
            ),

            ft.Container(
                content=ft.Row([
                    month_input,

                    ft.Button(
                        content=ft.Text("Generate Report"),
                        on_click=render_month_report
                    )
                ], wrap=True, spacing=10),

                padding=15,
                bgcolor="white",
                border_radius=12
            ),

            message,
            report_body
        ]

        render_month_report()

        # ---------------- NAVIGATION ----------------

    def update_navigation(active):
        buttons = {
            "Home": home_button,
            "Add Transaction": add_button,
            "History": history_button,
            "Reports": reports_button
        }

        for name, button in buttons.items():
            if name == active:
                button.style = ft.ButtonStyle(
                    bgcolor="#2563EB",
                    color="white"
                )
            else:
                button.style = ft.ButtonStyle(
                    bgcolor="white",
                    color="#1F2937"
                )

        page.update()

    def navigate_home(e):
        update_navigation("Home")
        show_dashboard()

    def navigate_add(e):
        update_navigation("Add Transaction")
        show_add_transaction()

    def navigate_history(e):
        update_navigation("History")
        show_history()

    def navigate_reports(e):
        update_navigation("Reports")
        show_reports()

    home_button = ft.Button(
        content=ft.Text("Home"),
        on_click=navigate_home
    )

    add_button = ft.Button(
        content=ft.Text("Add Transaction"),
        on_click=navigate_add
    )

    history_button = ft.Button(
        content=ft.Text("History"),
        on_click=navigate_history
    )

    reports_button = ft.Button(
        content=ft.Text("Reports"),
        on_click=navigate_reports
    )

    navigation = ft.Container(
        content=ft.Row(
            controls=[
                home_button,
                add_button,
                history_button,
                reports_button
            ],
            spacing=10,
            wrap=True
        ),
        padding=12,
        bgcolor="white",
        border_radius=12
    )

    # ---------------- PAGE LAYOUT ----------------

    page.add(
        ft.Text(
            "PERSONAL FINANCE TRACKER",
            size=17,
            weight=ft.FontWeight.BOLD,
            color="#2563EB"
        ),

        navigation,
        ft.Divider(),
        content
    )

    update_navigation("Home")
    show_dashboard()

ft.run(main)
