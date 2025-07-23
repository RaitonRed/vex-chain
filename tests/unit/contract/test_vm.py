from blockchain.transaction import Transaction
from src.blockchain.contract.vm import SmartContractVM

def test_vm_execution():
    state_db = MockStateDB()
    vm = SmartContractVM(state_db)
    
    # یک قرارداد ساده جمع دو عدد
    code = "ADD result 5 10"
    tx = Transaction(
        sender="Alice",
        recipient="Contract",
        amount=0,
        contract_type="CALL",
        contract_code=code
    )
    
    success, result = vm.execute(tx, 1, 123456789)
    assert success is True
    assert state_db.storage.get("result") == 15

# Mock برای StateDB
class MockStateDB:
    def __init__(self):
        self.storage = {}
        self.balances = {}
    
    def load_storage(self, contract_address):
        return self.storage
    
    def save_storage(self, contract_address, storage):
        self.storage = storage
    
    def get_balance(self, address):
        return self.balances.get(address, 100)