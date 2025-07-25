import time
from src.api.server import app as flask_app

class ServiceMonitor:
    def __init__(self):
        self.services = {
            'blockchain': {'status': False, 'check': self._check_blockchain},
            'p2p_network': {'status': False, 'check': self._check_p2p},
            'api_server': {'status': False, 'check': self._check_api},
            'mempool': {'status': False, 'check': self._check_mempool},
            'consensus': {'status': False, 'check': self._check_consensus}
        }
        self.start_time = time.time()
        
    def _check_blockchain(self, node):
        return (
            hasattr(node, 'blockchain') and 
            node.blockchain is not None and
            len(node.blockchain.chain) > 0
        )
    
    def _check_p2p(self, node):
        return (
            hasattr(node, 'p2p_network') and
            node.p2p_network is not None and
            hasattr(node.p2p_network.socket, 'fileno') and
            node.p2p_network.socket.fileno() != -1
        )
    
    def _check_api(self, node):
        return (
            hasattr(node, 'api_thread') and
            node.api_thread.is_alive() and
            flask_app is not None
        )
    
    def _check_mempool(self, node):
        return (
            hasattr(node, 'mempool') and
            node.mempool is not None
        )
    
    def _check_consensus(self, node):
        return (
            hasattr(node.blockchain, 'consensus') and
            node.blockchain.consensus is not None
        )
    
    def check_all_services(self, node):
        all_ready = True
        for name, service in self.services.items():
            service['status'] = service['check'](node)
            if not service['status']:
                all_ready = False
        return all_ready
    
    def get_status_report(self):
        report = {
            'uptime': time.time() - self.start_time,
            'services': {},
            'all_ready': all(service['status'] for service in self.services.values())
        }
        for name, service in self.services.items():
            report['services'][name] = {
                'status': 'READY' if service['status'] else 'NOT READY',
                'last_check': time.time()
            }
        return report
    
    def wait_until_ready(self, node, timeout=30, check_interval=0.5):
        start_time = time.time()
        attempts = 0
        
        print("\n🔍 Starting system diagnostics...\n")
        while time.time() - start_time < timeout:
            attempts += 1
            ready = self.check_all_services(node)
            report = self.get_status_report()
            
            # نمایش وضعیت سرویس‌ها
            self._display_status(report, attempts)
            
            if ready:
                print("\n✅ All services are ready!\n")
                return True
                
            time.sleep(check_interval)
        
        print("\n❌ Timeout reached while waiting for services\n")
        return False
    
    def _display_status(self, report, attempt):
        # پاک کردن خطوط قبلی
        lines = len(self.services) + 3
        print(f"\033[{lines}A", end="")
        
        # نمایش هدر
        print(f"🔄 System Initialization (Attempt {attempt})".ljust(50))
        print(f"⏱ Uptime: {report['uptime']:.1f}s".ljust(50))
        
        # نمایش وضعیت هر سرویس
        for name, service in report['services'].items():
            status_icon = "✓" if service['status'] else "✗"
            color = "\033[92m" if service['status'] else "\033[91m"
            print(f"{color}{status_icon} {name.upper().ljust(15)}: {service['status']}\033[0m")