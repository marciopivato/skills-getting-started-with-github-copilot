import unittest
from datetime import datetime, timedelta
from application_core.entities.loan import Loan
from application_core.entities.patron import Patron
from application_core.entities.book_item import BookItem
from infrastructure.json_loan_repository import JsonLoanRepository

# Classes being tested:
# - JsonLoanRepository: Concrete implementation of ILoanRepository using JSON persistence
# - JsonData: Manages loading and saving loan data from/to JSON files (via DummyJsonData)
# - Loan: Entity representing a loan record


class DummyJsonData:
    """Stub implementation of JsonData for testing JsonLoanRepository."""

    def __init__(self):
        """Initialize with empty collections."""
        self.loans = []
        self.patrons = []
        self.book_items = []

    def save_loans(self, loans):
        """Stub method for saving loans to storage."""
        pass

    def load_data(self):
        """Stub method for loading data from storage."""
        pass


class TestJsonLoanRepository(unittest.TestCase):
    """Tests for JsonLoanRepository implementation."""

    def setUp(self):
        """Initialize test fixtures with fields and test data."""
        # Initialize private fields
        self._json_data = self._create_test_json_data()
        self._json_loan_repository = JsonLoanRepository(self._json_data)

    def _create_test_json_data(self):
        """Create and populate test data for DummyJsonData instance."""
        json_data = DummyJsonData()
        
        # Create test patron
        test_patron = Patron(
            id=1,
            name="John Doe",
            membership_start=datetime.now() - timedelta(days=365),
            membership_end=datetime.now() + timedelta(days=365)
        )
        
        # Create test book item
        test_book_item = BookItem(
            id=1,
            book_id=1,
            acquisition_date=datetime.now() - timedelta(days=100),
            condition="Good"
        )
        
        # Create test loans
        loan1 = Loan(
            id=1,
            book_item_id=1,
            patron_id=1,
            patron=test_patron,
            loan_date=datetime.now() - timedelta(days=10),
            due_date=datetime.now() + timedelta(days=4),
            return_date=None,
            book_item=test_book_item
        )
        
        loan2 = Loan(
            id=2,
            book_item_id=2,
            patron_id=1,
            patron=test_patron,
            loan_date=datetime.now() - timedelta(days=20),
            due_date=datetime.now() - timedelta(days=5),
            return_date=datetime.now() - timedelta(days=3),
            book_item=None
        )
        
        # Populate json_data with test data
        json_data.loans = [loan1, loan2]
        json_data.patrons = [test_patron]
        json_data.book_items = [test_book_item]
        
        return json_data

    def test_get_loan_found(self):
        """Test retrieving an existing loan by ID."""
        # Arrange: loan with id=1 exists in test data
        loan_id = 1
        
        # Act: retrieve the loan
        result = self._json_loan_repository.get_loan(loan_id)
        
        # Assert: verify loan is found and correct
        self.assertIsNotNone(result)
        self.assertEqual(result.id, loan_id)
        self.assertEqual(result.patron_id, 1)

    def test_get_loan_not_found(self):
        """Test retrieving a non-existent loan by ID."""
        # Arrange: loan with id=999 does not exist
        loan_id = 999
        
        # Act: attempt to retrieve the loan
        result = self._json_loan_repository.get_loan(loan_id)
        
        # Assert: verify None is returned
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
