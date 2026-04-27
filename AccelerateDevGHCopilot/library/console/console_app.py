from .console_state import ConsoleState
from .common_actions import CommonActions
from application_core.interfaces.ipatron_repository import IPatronRepository
from application_core.interfaces.iloan_repository import ILoanRepository
from application_core.interfaces.iloan_service import ILoanService
from application_core.interfaces.ipatron_service import IPatronService
from typing import Optional, Callable, Dict

class ConsoleApp:
    # Static dictionary mapping action flags to (shortcut_key, description)
    _ACTION_DESCRIPTIONS: Dict[int, tuple] = {
        CommonActions.RETURN_LOANED_BOOK: ('r', "mark as returned"),
        CommonActions.EXTEND_LOANED_BOOK: ('e', "extend the book loan"),
        CommonActions.RENEW_PATRON_MEMBERSHIP: ('m', "extend patron's membership"),
        CommonActions.SEARCH_PATRONS: ('s', "new search"),
        CommonActions.SEARCH_BOOKS: ('b', "check for book availability"),
        CommonActions.QUIT: ('q', "quit"),
        CommonActions.SELECT: (None, "type a number to select a list item"),
    }

    def __init__(
        self,
        loan_service: ILoanService,
        patron_service: IPatronService,
        patron_repository: IPatronRepository,
        loan_repository: ILoanRepository,
        json_data
    ):
        self._current_state: ConsoleState = ConsoleState.PATRON_SEARCH
        self.matching_patrons = []
        self.selected_patron_details = None
        self.selected_loan_details = None
        self._patron_repository = patron_repository
        self._loan_repository = loan_repository
        self._loan_service = loan_service
        self._patron_service = patron_service
        self._json_data = json_data
        
        # Initialize state handlers dictionary
        self._state_handlers: Dict[ConsoleState, Callable] = {
            ConsoleState.PATRON_SEARCH: self.patron_search,
            ConsoleState.PATRON_SEARCH_RESULTS: self.patron_search_results,
            ConsoleState.PATRON_DETAILS: self.patron_details,
            ConsoleState.LOAN_DETAILS: self.loan_details,
        }

    def write_input_options(self, options: int) -> None:
        """Display available input options based on action flags."""
        print("Input Options:")
        for action, (shortcut, description) in self._ACTION_DESCRIPTIONS.items():
            if options & action:
                if shortcut:
                    print(f' - "{shortcut}" to {description}')
                else:
                    print(f' - {description}')

    def run(self) -> None:
        """Main application loop using state handler dictionary."""
        while self._current_state != ConsoleState.QUIT:
            handler = self._state_handlers.get(self._current_state)
            if handler is None:
                raise ValueError(f"Unknown console state: {self._current_state}")
            self._current_state = handler()

    def patron_search(self) -> ConsoleState:
        search_input = input("Enter a string to search for patrons by name: ").strip()
        if not search_input:
            print("No input provided. Please try again.")
            return ConsoleState.PATRON_SEARCH
        self.matching_patrons = self._patron_repository.search_patrons(search_input)
        if not self.matching_patrons:
            print("No matching patrons found.")
            return ConsoleState.PATRON_SEARCH
        return ConsoleState.PATRON_SEARCH_RESULTS

    def patron_search_results(self) -> ConsoleState:
        print("\nMatching Patrons:")
        idx = 1
        for patron in self.matching_patrons:
            print(f"{idx}) {patron.name}")
            idx += 1
        if self.matching_patrons:
            self.write_input_options(
                CommonActions.SELECT | CommonActions.SEARCH_PATRONS | CommonActions.QUIT
            )
        else:
            self.write_input_options(
                CommonActions.SEARCH_PATRONS | CommonActions.QUIT
            )
        selection = input("Enter your choice: ").strip().lower()
        return self._handle_search_results_selection(selection)

    def _handle_search_results_selection(self, selection: str) -> ConsoleState:
        """Handle selection in patron search results using dictionary."""
        handlers = {
            'q': lambda: ConsoleState.QUIT,
            's': lambda: ConsoleState.PATRON_SEARCH,
        }
        
        # Check dictionary handlers first
        handler = handlers.get(selection)
        if handler:
            return handler()
        
        # Handle numeric selection
        if selection.isdigit():
            idx = int(selection)
            if 1 <= idx <= len(self.matching_patrons):
                self.selected_patron_details = self.matching_patrons[idx - 1]
                return ConsoleState.PATRON_DETAILS
            print("Invalid selection. Please enter a valid number.")
            return ConsoleState.PATRON_SEARCH_RESULTS
        
        # Unknown input
        print("Invalid input. Please enter a number, 's', or 'q'.")
        return ConsoleState.PATRON_SEARCH_RESULTS

    def patron_details(self) -> ConsoleState:
        patron = self.selected_patron_details
        print(f"\nName: {patron.name}")
        print(f"Membership Expiration: {patron.membership_end}")
        loans = self._loan_repository.get_loans_by_patron_id(patron.id)
        print("\nBook Loans History:")

        valid_loans = self._print_loans(loans)

        if valid_loans:
            options = (
                CommonActions.RENEW_PATRON_MEMBERSHIP
                | CommonActions.SEARCH_PATRONS
                | CommonActions.QUIT
                | CommonActions.SELECT
                | CommonActions.SEARCH_BOOKS
            )
        else:
            print("No valid loans for this patron.")
            options = (
                CommonActions.SEARCH_PATRONS
                | CommonActions.QUIT
                | CommonActions.SEARCH_BOOKS
            )

        selection = self._get_patron_details_input(options)
        return self._handle_patron_details_selection(selection, patron, valid_loans)

    def _print_loans(self, loans) -> list:
        valid_loans = []
        idx = 1
        for loan in loans:
            if not getattr(loan, 'book_item', None) or not getattr(loan.book_item, 'book', None):
                print(f"{idx}) [Invalid loan data: missing book information]")
            else:
                returned = "True" if getattr(loan, 'return_date', None) else "False"
                print(f"{idx}) {loan.book_item.book.title} - Due: {loan.due_date} - Returned: {returned}")
                valid_loans.append((idx, loan))
            idx += 1
        return valid_loans

    def _get_patron_details_input(self, options: int) -> str:
        self.write_input_options(options)
        return input("Enter your choice: ").strip().lower()

    def _handle_patron_details_selection(self, selection: str, patron, valid_loans: list) -> ConsoleState:
        """Handle selection in patron details using dictionary."""
        handlers = {
            'q': lambda: ConsoleState.QUIT,
            's': lambda: ConsoleState.PATRON_SEARCH,
            'm': lambda: self._handle_membership_renewal(patron),
            'b': lambda: self.search_books(),
        }
        
        # Check dictionary handlers first
        handler = handlers.get(selection)
        if handler:
            return handler()
        
        # Handle numeric selection
        if selection.isdigit():
            idx = int(selection)
            if 1 <= idx <= len(valid_loans):
                self.selected_loan_details = valid_loans[idx - 1][1]
                return ConsoleState.LOAN_DETAILS
            print("Invalid selection. Please enter a number shown in the list above.")
            return ConsoleState.PATRON_DETAILS
        
        # Unknown input
        print("Invalid input. Please enter a number, 'm', 'b', 's', or 'q'.")
        return ConsoleState.PATRON_DETAILS

    def _handle_membership_renewal(self, patron) -> ConsoleState:
        """Handle patron membership renewal."""
        status = self._patron_service.renew_membership(patron.id)
        print(status)
        self.selected_patron_details = self._patron_repository.get_patron(patron.id)
        return ConsoleState.PATRON_DETAILS

    def search_books(self) -> ConsoleState:
        while True:
            book_title = input("Enter a book title to search for: ").strip()
            if not book_title:
                print("No book title provided. Please try again.")
                continue

            books = self._json_data.books
            matches = [b for b in books if book_title.lower() in b.title.lower()]

            if not matches:
                print("No matching books found.")
                again = input("Search again? (y/n): ").strip().lower()
                if again == 'y':
                    continue
                return ConsoleState.PATRON_DETAILS

            book = self._select_book_from_matches(matches)
            if book is None:
                continue

            book_items = [bi for bi in self._json_data.book_items if bi.book_id == book.id]
            if not book_items:
                print("No copies of this book are in the library.")
                again = input("Search again? (y/n): ").strip().lower()
                if again == 'y':
                    continue
                return ConsoleState.PATRON_DETAILS

            return self._handle_book_availability(book, book_items)

    def _select_book_from_matches(self, matches: list):
        """Select a book from matching results."""
        if len(matches) == 1:
            return matches[0]
        
        print("\nMultiple books found:")
        for idx, b in enumerate(matches, 1):
            print(f"{idx}) {b.title}")
        selection = input("Select a book by number or 'r' to refine search: ").strip().lower()
        if selection == 'r':
            return None
        if not selection.isdigit() or not (1 <= int(selection) <= len(matches)):
            print("Invalid selection.")
            return None
        return matches[int(selection) - 1]

    def _handle_book_availability(self, book, book_items: list) -> ConsoleState:
        """Handle book availability check and checkout."""
        loans = self._json_data.loans
        on_loan = []
        available = []
        
        for item in book_items:
            item_loans = [l for l in loans if l.book_item_id == item.id]
            if item_loans:
                latest_loan = max(item_loans, key=lambda l: l.loan_date or l.due_date or l.return_date or 0)
                if latest_loan.return_date is None:
                    on_loan.append(latest_loan)
                else:
                    available.append(item)
            else:
                available.append(item)

        if available:
            return self._handle_available_book(book, available)
        else:
            return self._handle_unavailable_book(book, on_loan)

    def _handle_available_book(self, book, available: list) -> ConsoleState:
        """Handle when book is available for checkout."""
        print(f"Book '{book.title}' is available for loan.")
        checkout = input("Would you like to check out this book? (y/n): ").strip().lower()
        if checkout == 'y':
            if not self.selected_patron_details:
                print("No patron selected. Please select a patron first.")
                return ConsoleState.PATRON_SEARCH
            book_item = available[0]
            loan = self._loan_service.checkout_book(self.selected_patron_details, book_item)
            print(f"Book '{book.title}' checked out successfully. Due date: {loan.due_date}")
        
        again = input("Search for another book? (y/n): ").strip().lower()
        return ConsoleState.PATRON_SEARCH if again == 'y' else ConsoleState.PATRON_DETAILS

    def _handle_unavailable_book(self, book, on_loan: list) -> ConsoleState:
        """Handle when book is not available (all copies on loan)."""
        due_dates = [l.due_date for l in on_loan if l.due_date]
        if due_dates:
            next_due = min(due_dates)
            print(f"All copies of '{book.title}' are currently on loan. Next due date: {next_due}")
        else:
            print(f"All copies of '{book.title}' are currently on loan.")

        again = input("Search for another book? (y/n): ").strip().lower()
        return ConsoleState.PATRON_SEARCH if again == 'y' else ConsoleState.PATRON_DETAILS

    def loan_details(self) -> ConsoleState:
        loan = self.selected_loan_details
        print(f"\nBook title: {loan.book_item.book.title}")
        print(f"Book Author: {loan.book_item.book.author.name}")
        print(f"Due date: {loan.due_date}")
        returned = "True" if getattr(loan, 'return_date', None) else "False"
        print(f"Returned: {returned}\n")
        
        options = CommonActions.SEARCH_PATRONS | CommonActions.QUIT
        if not getattr(loan, 'return_date', None):
            options |= CommonActions.RETURN_LOANED_BOOK | CommonActions.EXTEND_LOANED_BOOK
        
        self.write_input_options(options)
        selection = input("Enter your choice: ").strip().lower()
        return self._handle_loan_details_selection(selection, loan)

    def _handle_loan_details_selection(self, selection: str, loan) -> ConsoleState:
        """Handle selection in loan details using dictionary."""
        is_returned = getattr(loan, 'return_date', None)
        
        handlers = {
            'q': lambda: ConsoleState.QUIT,
            's': lambda: ConsoleState.PATRON_SEARCH,
            'r': lambda: self._handle_return_loan(loan) if not is_returned else self._invalid_loan_action(),
            'e': lambda: self._handle_extend_loan(loan) if not is_returned else self._invalid_loan_action(),
        }
        
        handler = handlers.get(selection)
        if handler:
            return handler()
        
        # Unknown input
        print("Invalid input.")
        return ConsoleState.LOAN_DETAILS

    def _handle_return_loan(self, loan) -> ConsoleState:
        """Handle loan return operation."""
        status = self._loan_service.return_loan(loan.id)
        print("Book was successfully returned.")
        print(status)
        self.selected_loan_details = self._loan_repository.get_loan(loan.id)
        return ConsoleState.LOAN_DETAILS

    def _handle_extend_loan(self, loan) -> ConsoleState:
        """Handle loan extension operation."""
        status = self._loan_service.extend_loan(loan.id)
        print(status)
        self.selected_loan_details = self._loan_repository.get_loan(loan.id)
        return ConsoleState.LOAN_DETAILS

    def _invalid_loan_action(self) -> ConsoleState:
        """Handle invalid loan action (e.g., return already returned book)."""
        print("This action is not available for this loan.")
        return ConsoleState.LOAN_DETAILS


from application_core.services.loan_service import LoanService
from application_core.services.patron_service import PatronService
from infrastructure.json_data import JsonData
from infrastructure.json_loan_repository import JsonLoanRepository
from infrastructure.json_patron_repository import JsonPatronRepository
from console.console_app import ConsoleApp

def main():
    json_data = JsonData()
    patron_repo = JsonPatronRepository(json_data)
    loan_repo = JsonLoanRepository(json_data)
    loan_service = LoanService(loan_repo)
    patron_service = PatronService(patron_repo)

    app = ConsoleApp(
        loan_service=loan_service,
        patron_service=patron_service,
        patron_repository=patron_repo,
        loan_repository=loan_repo,
        json_data=json_data
    )
    app.run()
