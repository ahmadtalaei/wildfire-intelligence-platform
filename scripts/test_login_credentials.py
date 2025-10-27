#!/usr/bin/env python3
"""
Login Credentials Testing Script
Tests all login credentials across all CAL FIRE platform services
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import Dict, Any, List

class LoginTester:
    """Test login credentials across all platform services"""

    def __init__(self):
        # Load environment variables
        self.load_env_credentials()

        self.services = {
            'challenge1_dashboard': {
                'url': 'http://localhost:3010',
                'name': 'Challenge 1 - Latency Dashboard',
                'credentials': ('admin', 'admin'),
                'test_path': '/'
            },
            'challenge2_dashboard': {
                'url': 'http://localhost:3011',
                'name': 'Challenge 2 - Storage Analytics',
                'credentials': ('admin', 'admin'),
                'test_path': '/'
            },
            'fire_chief_dashboard': {
                'url': 'http://localhost:3001',
                'name': 'Fire Chief Executive Dashboard',
                'credentials': (self.env_vars.get('FRONTEND_CHIEF_USER', 'chief@calfire.gov'),
                               self.env_vars.get('FRONTEND_CHIEF_PASSWORD', 'admin')),
                'test_path': '/'
            },
            'analyst_portal': {
                'url': 'http://localhost:3002',
                'name': 'Data Analyst Portal',
                'credentials': (self.env_vars.get('FRONTEND_ANALYST_USER', 'analyst@calfire.gov'),
                               self.env_vars.get('FRONTEND_ANALYST_PASSWORD', 'admin')),
                'test_path': '/'
            },
            'scientist_workbench': {
                'url': 'http://localhost:3003',
                'name': 'Data Scientist Workbench',
                'credentials': (self.env_vars.get('FRONTEND_SCIENTIST_USER', 'scientist@calfire.gov'),
                               self.env_vars.get('FRONTEND_SCIENTIST_PASSWORD', 'admin')),
                'test_path': '/'
            },
            'admin_console': {
                'url': 'http://localhost:3004',
                'name': 'Admin Console',
                'credentials': (self.env_vars.get('FRONTEND_ADMIN_USER', 'admin@calfire.gov'),
                               self.env_vars.get('FRONTEND_ADMIN_PASSWORD', 'admin')),
                'test_path': '/'
            },
            'grafana': {
                'url': 'http://localhost:3020',
                'name': 'Grafana Monitoring',
                'credentials': ('admin', self.env_vars.get('GRAFANA_ADMIN_PASSWORD', 'admin')),
                'test_path': '/login'
            },
            'data_clearing_house_api': {
                'url': 'http://localhost:8006',
                'name': 'Data Clearing House API',
                'credentials': (self.env_vars.get('LOCALHOST_USER', 'admin'),
                               self.env_vars.get('LOCALHOST_PASSWORD', 'admin')),
                'test_path': '/health'
            }
        }

    def load_env_credentials(self):
        """Load credentials from .env file"""
        self.env_vars = {}
        env_path = "C:/dev/wildfire/.env"

        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.env_vars[key.strip()] = value.strip()
        except FileNotFoundError:
            print(f"Warning: .env file not found at {env_path}")

    async def test_all_services(self) -> Dict[str, Any]:
        """Test login for all services"""
        print("CAL FIRE Platform - Login Credentials Testing")
        print("=" * 60)

        results = {
            'test_time': datetime.now().isoformat(),
            'total_services': len(self.services),
            'services_accessible': 0,
            'services_with_auth': 0,
            'test_results': {},
            'summary': {}
        }

        for service_id, service_config in self.services.items():
            print(f"\nTesting: {service_config['name']}")
            print(f"   URL: {service_config['url']}")
            print(f"   Credentials: {service_config['credentials'][0]} / {service_config['credentials'][1]}")

            test_result = await self.test_service_login(service_config)
            results['test_results'][service_id] = test_result

            if test_result['accessible']:
                results['services_accessible'] += 1

            if test_result['auth_working']:
                results['services_with_auth'] += 1

            # Print result
            if test_result['accessible']:
                if test_result['auth_working']:
                    print(f"   [OK] Status: ACCESSIBLE & AUTH WORKING")
                else:
                    print(f"   [WARN] Status: ACCESSIBLE but auth needs verification")
            else:
                print(f"   [FAIL] Status: NOT ACCESSIBLE - {test_result['error']}")

        await self.print_summary(results)
        return results

    async def test_service_login(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test login for a specific service"""
        result = {
            'accessible': False,
            'auth_working': False,
            'status_code': None,
            'error': None,
            'response_time_ms': None
        }

        try:
            start_time = asyncio.get_event_loop().time()

            async with aiohttp.ClientSession() as session:
                # First, try to access the service
                async with session.get(
                    service_config['url'] + service_config['test_path'],
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:

                    end_time = asyncio.get_event_loop().time()
                    result['response_time_ms'] = (end_time - start_time) * 1000
                    result['status_code'] = response.status

                    if response.status in [200, 401, 302]:  # 200=accessible, 401=needs auth, 302=redirect
                        result['accessible'] = True

                        # If it's accessible without auth, mark auth as working
                        if response.status == 200:
                            result['auth_working'] = True

                        # For services that might need authentication, try with credentials
                        elif response.status in [401, 302]:
                            auth_result = await self.test_with_auth(session, service_config)
                            result['auth_working'] = auth_result

                    else:
                        result['error'] = f"HTTP {response.status}"

        except asyncio.TimeoutError:
            result['error'] = "Connection timeout"
        except aiohttp.ClientConnectorError:
            result['error'] = "Connection refused - service not running"
        except Exception as e:
            result['error'] = str(e)

        return result

    async def test_with_auth(self, session: aiohttp.ClientSession, service_config: Dict[str, Any]) -> bool:
        """Test authentication for services that require it"""
        try:
            username, password = service_config['credentials']

            # For Grafana, test login endpoint
            if 'grafana' in service_config['url']:
                login_data = {
                    'user': username,
                    'password': password
                }
                async with session.post(
                    service_config['url'] + '/login',
                    json=login_data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status in [200, 302]  # Success or redirect

            # For other services, try basic auth
            else:
                auth = aiohttp.BasicAuth(username, password)
                async with session.get(
                    service_config['url'] + service_config['test_path'],
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200

        except Exception:
            return False

    async def print_summary(self, results: Dict[str, Any]):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("LOGIN CREDENTIALS TEST SUMMARY")
        print("=" * 80)

        accessible = results['services_accessible']
        total = results['total_services']
        auth_working = results['services_with_auth']

        print(f"\nOverall Results:")
        print(f"   Services Accessible: {accessible}/{total} ({accessible/total*100:.1f}%)")
        print(f"   Authentication Working: {auth_working}/{total} ({auth_working/total*100:.1f}%)")

        print(f"\nCAL FIRE Domain Credentials Summary:")
        print(f"   Fire Chief Dashboard (localhost:3001): {self.env_vars.get('FRONTEND_CHIEF_USER', 'chief@calfire.gov')} / {self.env_vars.get('FRONTEND_CHIEF_PASSWORD', 'admin')}")
        print(f"   Data Scientist Workbench (localhost:3003): {self.env_vars.get('FRONTEND_SCIENTIST_USER', 'scientist@calfire.gov')} / {self.env_vars.get('FRONTEND_SCIENTIST_PASSWORD', 'admin')}")
        print(f"   Data Analyst Portal (localhost:3002): {self.env_vars.get('FRONTEND_ANALYST_USER', 'analyst@calfire.gov')} / {self.env_vars.get('FRONTEND_ANALYST_PASSWORD', 'admin')}")
        print(f"   Admin Console (localhost:3004): {self.env_vars.get('FRONTEND_ADMIN_USER', 'admin@calfire.gov')} / {self.env_vars.get('FRONTEND_ADMIN_PASSWORD', 'admin')}")
        print(f"   Grafana Monitoring (localhost:3020): admin / {self.env_vars.get('GRAFANA_ADMIN_PASSWORD', 'admin')}")
        print(f"   Challenge Dashboards (localhost:3010, 3011): admin / admin")

        print(f"\nService Status:")
        for service_id, test_result in results['test_results'].items():
            service_name = self.services[service_id]['name']
            service_url = self.services[service_id]['url']

            if test_result['accessible']:
                if test_result['auth_working']:
                    status = "[OK] WORKING"
                else:
                    status = "[WARN] ACCESSIBLE (Auth needs verification)"
            else:
                status = f"[FAIL] FAILED ({test_result['error']})"

            print(f"   {service_name}: {status}")

        if accessible == total and auth_working == total:
            print(f"\n[SUCCESS] ALL SERVICES ACCESSIBLE WITH WORKING AUTHENTICATION!")
        elif accessible == total:
            print(f"\n[OK] ALL SERVICES ACCESSIBLE - Some auth may need manual verification")
        else:
            print(f"\n[WARN] SOME SERVICES NOT ACCESSIBLE - Check if docker services are running")

        print(f"\nNote: Some services may not require authentication (static sites)")
        print(f"   Run 'docker-compose -f docker-compose-enhanced.yml up -d' to start all services")

async def main():
    """Run login credentials testing"""
    tester = LoginTester()
    results = await tester.test_all_services()

    # Save results
    results_path = "C:/dev/wildfire/login_test_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nTest results saved to: {results_path}")

if __name__ == "__main__":
    asyncio.run(main())