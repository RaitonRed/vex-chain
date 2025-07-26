from src.blockchain.contract_repository import ContractRepository
from src.blockchain.contract.vm import SmartContractVM
from typing import Optional, Dict
from src.utils.logger import logger

class ContractManager:
    """Manages smart contract deployment and execution"""
    
    @staticmethod
    def deploy_contract(sender: str, code: str) -> Optional[str]:
        """Deploy a new smart contract"""
        from src.utils.crypto import generate_contract_address
        try:
            # Generate unique contract address
            contract_address = generate_contract_address(sender, code)
            
            # Validate contract code
            if not SmartContractVM.validate_code(code):
                raise ValueError("Invalid contract code")
                
            # Save to repository
            if ContractRepository.save_contract(contract_address, code, sender):
                # Initialize empty state
                ContractRepository.save_contract_state(contract_address, {})
                return contract_address
            return None
        except Exception as e:
            logger.error(f"Contract deployment failed: {e}")
            return None

    @staticmethod
    def call_contract(
        sender: str,
        contract_address: str,
        method: str,
        args: Dict,
        amount: float = 0
    ) -> tuple:
        """Execute a contract method"""
        try:
            # Get contract code
            contract = ContractRepository.get_contract(contract_address)
            if not contract:
                return False, "Contract not found"
                
            # Get current state
            state = ContractRepository.get_contract_state(contract_address)
            
            # Execute in VM
            success, result = SmartContractVM.execute(
                contract['code'],
                method,
                args,
                state,
                sender,
                amount
            )
            
            # Update state if execution succeeded
            if success and isinstance(result, dict) and 'state' in result:
                ContractRepository.save_contract_state(
                    contract_address,
                    result['state']
                )
                
                # Save events if any
                if 'events' in result:
                    for event in result['events']:
                        ContractRepository.save_contract_event(
                            contract_address,
                            event['name'],
                            event['data'],
                            result.get('block_number', 0),
                            result.get('tx_hash', '')
                        )
            
            return success, result
        except Exception as e:
            logger.error(f"Contract call failed: {e}")
            return False, str(e)

    @staticmethod
    def get_contract_state(contract_address: str) -> Dict:
        """Get current contract state"""
        return ContractRepository.get_contract_state(contract_address)

    @staticmethod
    def get_contract_events(contract_address: str, limit: int = 100) -> list:
        """Get contract events"""
        return ContractRepository.get_contract_events(contract_address, limit)
