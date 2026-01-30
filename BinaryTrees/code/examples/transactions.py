"""
Example: Transaction scenarios

Demonstrates ACID transactions with commit and rollback.
"""

import sys
sys.path.insert(0, '..')

from transaction_manager import TransactionManager, IsolationLevel


def simple_transaction():
    """Basic transaction commit."""
    print("=" * 70)
    print("Scenario 1: Simple Transaction (Commit)")
    print("=" * 70)
    
    tm = TransactionManager()
    
    txn = tm.begin()
    tm.write(txn, b"balance:checking", b"1000.00")
    tm.write(txn, b"balance:savings", b"5000.00")
    
    # Read what we wrote
    value = tm.read(txn, b"balance:checking")
    print(f"📖 Current balance: ${value.decode()}")
    
    tm.commit(txn)
    print("✅ Transaction committed!")


def rollback_transaction():
    """Transaction with rollback."""
    print("\n\n" + "=" * 70)
    print("Scenario 2: Transaction Rollback")
    print("=" * 70)
    
    tm = TransactionManager()
    
    # Initial state
    txn1 = tm.begin()
    tm.write(txn1, b"account:A", b"1000")
    tm.write(txn1, b"account:B", b"500")
    tm.commit(txn1)
    
    print("\n💰 Initial balances:")
    txn2 = tm.begin()
    print(f"   Account A: ${tm.read(txn2, b'account:A').decode()}")
    print(f"   Account B: ${tm.read(txn2, b'account:B').decode()}")
    tm.commit(txn2)
    
    # Transfer attempt (will be rolled back)
    print("\n💸 Attempting transfer A → B (but will fail)...")
    txn3 = tm.begin()
    
    balance_a = int(tm.read(txn3, b"account:A"))
    balance_b = int(tm.read(txn3, b"account:B"))
    
    # Deduct from A
    tm.write(txn3, b"account:A", str(balance_a - 200).encode())
    print(f"   A: ${balance_a} → ${balance_a - 200}")
    
    # Add to B
    tm.write(txn3, b"account:B", str(balance_b + 200).encode())
    print(f"   B: ${balance_b} → ${balance_b + 200}")
    
    # Simulate error
    print("\n❌ Error occurred! Rolling back transaction...")
    tm.abort(txn3)
    
    # Verify rollback
    print("\n📊 Balances after rollback:")
    txn4 = tm.begin()
    print(f"   Account A: ${tm.read(txn4, b'account:A').decode()} (unchanged)")
    print(f"   Account B: ${tm.read(txn4, b'account:B').decode()} (unchanged)")
    tm.commit(txn4)


def isolation_levels():
    """Demonstrate different isolation levels."""
    print("\n\n" + "=" * 70)
    print("Scenario 3: Isolation Levels")
    print("=" * 70)
    
    tm = TransactionManager()
    
    # Setup initial data
    txn = tm.begin()
    tm.write(txn, b"counter", b"100")
    tm.commit(txn)
    
    # READ COMMITTED
    print("\n📖 READ COMMITTED:")
    print("   Transaction 1: Start")
    txn1 = tm.begin(IsolationLevel.READ_COMMITTED)
    value1 = tm.read(txn1, b"counter")
    print(f"   Txn 1 reads: {value1.decode()}")
    
    print("\n   Transaction 2: Modify and commit")
    txn2 = tm.begin()
    tm.write(txn2, b"counter", b"200")
    tm.commit(txn2)
    
    print("\n   Transaction 1: Read again")
    value2 = tm.read(txn1, b"counter")
    print(f"   Txn 1 reads: {value2.decode()} (sees committed change!)")
    tm.commit(txn1)
    
    # REPEATABLE READ
    print("\n\n📖 REPEATABLE READ:")
    print("   Transaction 3: Start")
    txn3 = tm.begin(IsolationLevel.REPEATABLE_READ)
    value3 = tm.read(txn3, b"counter")
    print(f"   Txn 3 reads: {value3.decode()}")
    
    print("\n   Transaction 4: Modify and commit")
    txn4 = tm.begin()
    tm.write(txn4, b"counter", b"300")
    tm.commit(txn4)
    
    print("\n   Transaction 3: Read again")
    value4 = tm.read(txn3, b"counter")
    print(f"   Txn 3 reads: {value4.decode()} (snapshot isolation - doesn't see change)")
    tm.commit(txn3)


def concurrent_transactions():
    """Demonstrate concurrent transaction coordination."""
    print("\n\n" + "=" * 70)
    print("Scenario 4: Concurrent Transactions")
    print("=" * 70)
    
    tm = TransactionManager()
    
    # Setup
    txn = tm.begin()
    tm.write(txn, b"shared_resource", b"initial_value")
    tm.commit(txn)
    
    print("\n🔄 Two transactions accessing same resource:")
    
    # Transaction A
    print("\n   Txn A: Start and read")
    txn_a = tm.begin()
    value_a = tm.read(txn_a, b"shared_resource")
    print(f"   Txn A reads: {value_a.decode()}")
    
    # Transaction B (tries to write - will need to wait for lock)
    print("\n   Txn B: Start and try to write")
    txn_b = tm.begin()
    print("   Txn B: Writing (may need to wait for lock)...")
    tm.write(txn_b, b"shared_resource", b"modified_by_b")
    
    # Transaction A commits (releases lock)
    print("\n   Txn A: Commit (releases lock)")
    tm.commit(txn_a)
    
    # Transaction B can now proceed
    print("\n   Txn B: Commit")
    tm.commit(txn_b)
    
    # Verify final state
    txn_c = tm.begin()
    final_value = tm.read(txn_c, b"shared_resource")
    print(f"\n   Final value: {final_value.decode()}")
    tm.commit(txn_c)


if __name__ == "__main__":
    # Run all scenarios
    simple_transaction()
    rollback_transaction()
    isolation_levels()
    concurrent_transactions()
    
    print("\n\n" + "=" * 70)
    print("✅ All transaction scenarios completed!")
    print("=" * 70)
    print("\n📚 What you've learned:")
    print("   1. ACID properties (Atomicity, Consistency, Isolation, Durability)")
    print("   2. Transaction commit and rollback")
    print("   3. Isolation levels (READ COMMITTED, REPEATABLE READ)")
    print("   4. Concurrency control with locks")
    print("   5. MVCC (Multi-Version Concurrency Control)")
    print("\n🎯 Key takeaways:")
    print("   - Commit = make changes permanent")
    print("   - Rollback = undo all changes")
    print("   - Isolation = transactions don't interfere with each other")
    print("   - Locks = prevent conflicts (but can cause waiting)")
