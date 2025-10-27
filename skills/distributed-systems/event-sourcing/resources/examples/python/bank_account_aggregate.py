"""
Bank Account Aggregate - Event Sourcing Example

Complete implementation of an event-sourced bank account aggregate
demonstrating command handling, event application, and invariant enforcement.

This is a production-ready example showing:
- Aggregate pattern
- Command validation
- Event production
- State reconstruction
- Optimistic concurrency
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from decimal import Decimal
from enum import Enum
import uuid


class AccountStatus(Enum):
    """Account status enum"""
    PENDING = "pending"
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


@dataclass
class Event:
    """Base event structure"""
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    version: int
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for persistence"""
        return {
            'eventId': self.event_id,
            'eventType': self.event_type,
            'aggregateId': self.aggregate_id,
            'aggregateType': self.aggregate_type,
            'version': self.version,
            'data': self.data,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class BankAccountError(Exception):
    """Base exception for bank account errors"""
    pass


class InsufficientFundsError(BankAccountError):
    """Raised when withdrawal exceeds balance"""
    pass


class AccountNotActiveError(BankAccountError):
    """Raised when operation requires active account"""
    pass


class InvalidAmountError(BankAccountError):
    """Raised when amount is invalid"""
    pass


class BankAccount:
    """
    Bank Account Aggregate

    Enforces invariants:
    - Balance cannot go negative
    - Account must be active for withdrawals
    - Amounts must be positive
    - Once closed, account cannot be reopened
    """

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.owner = None
        self.balance = Decimal('0')
        self.status = AccountStatus.PENDING
        self.version = 0
        self.created_at = None
        self.closed_at = None
        self._uncommitted_events: List[Event] = []

    @classmethod
    def open(cls, account_id: str, owner: str, initial_deposit: Decimal, user_id: str) -> 'BankAccount':
        """
        Open new bank account (factory method)

        Args:
            account_id: Unique account identifier
            owner: Account owner name
            initial_deposit: Initial deposit amount
            user_id: User performing the action

        Returns:
            BankAccount: New account instance

        Raises:
            InvalidAmountError: If initial deposit is negative
        """
        if initial_deposit < 0:
            raise InvalidAmountError("Initial deposit cannot be negative")

        account = cls(account_id)

        event = Event(
            event_id=str(uuid.uuid4()),
            event_type='AccountOpened',
            aggregate_id=account_id,
            aggregate_type='BankAccount',
            version=1,
            data={
                'accountId': account_id,
                'owner': owner,
                'initialDeposit': str(initial_deposit),
                'currency': 'USD'
            },
            metadata={
                'userId': user_id,
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )

        account._apply_event(event)
        account._uncommitted_events.append(event)

        return account

    def deposit(self, amount: Decimal, user_id: str, description: Optional[str] = None):
        """
        Deposit money into account

        Args:
            amount: Amount to deposit
            user_id: User performing the deposit
            description: Optional description

        Raises:
            InvalidAmountError: If amount is not positive
            AccountNotActiveError: If account is not active
        """
        # Validate
        if amount <= 0:
            raise InvalidAmountError("Deposit amount must be positive")

        if self.status != AccountStatus.ACTIVE:
            raise AccountNotActiveError(f"Account is {self.status.value}, cannot deposit")

        # Create event
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type='MoneyDeposited',
            aggregate_id=self.account_id,
            aggregate_type='BankAccount',
            version=self.version + 1,
            data={
                'accountId': self.account_id,
                'amount': str(amount),
                'balanceAfter': str(self.balance + amount),
                'description': description
            },
            metadata={
                'userId': user_id,
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )

        # Apply and store
        self._apply_event(event)
        self._uncommitted_events.append(event)

    def withdraw(self, amount: Decimal, user_id: str, description: Optional[str] = None):
        """
        Withdraw money from account

        Args:
            amount: Amount to withdraw
            user_id: User performing the withdrawal
            description: Optional description

        Raises:
            InvalidAmountError: If amount is not positive
            InsufficientFundsError: If balance is insufficient
            AccountNotActiveError: If account is not active
        """
        # Validate
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive")

        if self.status != AccountStatus.ACTIVE:
            raise AccountNotActiveError(f"Account is {self.status.value}, cannot withdraw")

        if self.balance < amount:
            raise InsufficientFundsError(
                f"Insufficient funds: balance={self.balance}, requested={amount}"
            )

        # Create event
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type='MoneyWithdrawn',
            aggregate_id=self.account_id,
            aggregate_type='BankAccount',
            version=self.version + 1,
            data={
                'accountId': self.account_id,
                'amount': str(amount),
                'balanceAfter': str(self.balance - amount),
                'description': description
            },
            metadata={
                'userId': user_id,
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )

        # Apply and store
        self._apply_event(event)
        self._uncommitted_events.append(event)

    def freeze(self, reason: str, user_id: str):
        """
        Freeze account (suspend all operations)

        Args:
            reason: Reason for freezing
            user_id: User performing the action
        """
        if self.status == AccountStatus.CLOSED:
            raise BankAccountError("Cannot freeze closed account")

        event = Event(
            event_id=str(uuid.uuid4()),
            event_type='AccountFrozen',
            aggregate_id=self.account_id,
            aggregate_type='BankAccount',
            version=self.version + 1,
            data={
                'accountId': self.account_id,
                'reason': reason
            },
            metadata={
                'userId': user_id,
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )

        self._apply_event(event)
        self._uncommitted_events.append(event)

    def unfreeze(self, user_id: str):
        """Unfreeze account"""
        if self.status != AccountStatus.FROZEN:
            raise BankAccountError(f"Account is not frozen (status: {self.status.value})")

        event = Event(
            event_id=str(uuid.uuid4()),
            event_type='AccountUnfrozen',
            aggregate_id=self.account_id,
            aggregate_type='BankAccount',
            version=self.version + 1,
            data={
                'accountId': self.account_id
            },
            metadata={
                'userId': user_id,
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )

        self._apply_event(event)
        self._uncommitted_events.append(event)

    def close(self, user_id: str):
        """
        Close account permanently

        Args:
            user_id: User performing the action

        Raises:
            BankAccountError: If balance is not zero
        """
        if self.status == AccountStatus.CLOSED:
            raise BankAccountError("Account is already closed")

        if self.balance != 0:
            raise BankAccountError(
                f"Cannot close account with non-zero balance: {self.balance}"
            )

        event = Event(
            event_id=str(uuid.uuid4()),
            event_type='AccountClosed',
            aggregate_id=self.account_id,
            aggregate_type='BankAccount',
            version=self.version + 1,
            data={
                'accountId': self.account_id
            },
            metadata={
                'userId': user_id,
                'timestamp': datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )

        self._apply_event(event)
        self._uncommitted_events.append(event)

    def _apply_event(self, event: Event):
        """
        Apply event to update aggregate state (event sourcing handler)

        This method is idempotent and contains NO business logic,
        only state mutations based on events.
        """
        if event.event_type == 'AccountOpened':
            self.owner = event.data['owner']
            self.balance = Decimal(event.data['initialDeposit'])
            self.status = AccountStatus.ACTIVE
            self.created_at = event.timestamp

        elif event.event_type == 'MoneyDeposited':
            self.balance = Decimal(event.data['balanceAfter'])

        elif event.event_type == 'MoneyWithdrawn':
            self.balance = Decimal(event.data['balanceAfter'])

        elif event.event_type == 'AccountFrozen':
            self.status = AccountStatus.FROZEN

        elif event.event_type == 'AccountUnfrozen':
            self.status = AccountStatus.ACTIVE

        elif event.event_type == 'AccountClosed':
            self.status = AccountStatus.CLOSED
            self.closed_at = event.timestamp

        self.version = event.version

    def get_uncommitted_events(self) -> List[Event]:
        """Get events that haven't been persisted yet"""
        return self._uncommitted_events.copy()

    def mark_events_committed(self):
        """Clear uncommitted events after persistence"""
        self._uncommitted_events = []

    @classmethod
    def from_events(cls, account_id: str, events: List[Event]) -> 'BankAccount':
        """
        Reconstruct aggregate from event stream

        Args:
            account_id: Account identifier
            events: List of events in order

        Returns:
            BankAccount: Reconstructed aggregate
        """
        account = cls(account_id)
        for event in events:
            account._apply_event(event)
        return account


# Usage example
if __name__ == '__main__':
    # Create new account
    account = BankAccount.open(
        account_id='account-123',
        owner='Alice Johnson',
        initial_deposit=Decimal('1000.00'),
        user_id='admin-1'
    )

    print(f"Account {account.account_id} opened")
    print(f"Owner: {account.owner}")
    print(f"Initial balance: ${account.balance}")
    print(f"Status: {account.status.value}\n")

    # Perform operations
    account.deposit(Decimal('500.00'), user_id='admin-1', description='Salary deposit')
    print(f"After deposit: ${account.balance}")

    account.withdraw(Decimal('200.00'), user_id='admin-1', description='ATM withdrawal')
    print(f"After withdrawal: ${account.balance}")

    # Get uncommitted events
    events = account.get_uncommitted_events()
    print(f"\nUncommitted events: {len(events)}")
    for event in events:
        print(f"  - {event.event_type} (v{event.version})")

    # Simulate persistence and reconstruction
    print("\n--- Simulating persistence and reconstruction ---\n")

    saved_events = account.get_uncommitted_events()
    account.mark_events_committed()

    # Reconstruct from events
    reconstructed = BankAccount.from_events('account-123', saved_events)
    print(f"Reconstructed account")
    print(f"Owner: {reconstructed.owner}")
    print(f"Balance: ${reconstructed.balance}")
    print(f"Status: {reconstructed.status.value}")
    print(f"Version: {reconstructed.version}")
