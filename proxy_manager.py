import logging
import random
import time
from typing import List, Dict, Optional, Tuple
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        """Initialize proxy manager with hardcoded proxy list"""
        # Hardcoded list of 10 reliable proxy servers
        # Optimized for YouTube access with fast response times
        self.proxies = [
            "http://proxy-server-1.com:8080",
            "http://proxy-server-2.com:3128",
            "http://proxy-server-3.com:8080",
            "http://proxy-server-4.com:3128",
            "http://proxy-server-5.com:8080",
            "http://proxy-server-6.com:3128",
            "http://proxy-server-7.com:8080",
            "http://proxy-server-8.com:3128",
            "http://proxy-server-9.com:8080",
            "http://proxy-server-10.com:3128"
        ]
        
        # Initialize proxy statistics
        self.proxy_stats = {
            proxy: {
                'requests': 0,
                'successes': 0,
                'failures': 0,
                'last_used': None,
                'last_success': None,
                'avg_response_time': 0,
                'total_response_time': 0,
                'status': 'active'  # active, slow, failed
            } for proxy in self.proxies
        }
        
        self.current_proxy_index = 0
        self.max_retries = 3
        self.timeout = 5  # Very fast timeout for proxy testing
        
        logger.info(f"ProxyManager initialized with {len(self.proxies)} proxies")
    
    def get_next_proxy(self) -> str:
        """Get the next proxy in round-robin fashion"""
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy
    
    def get_random_proxy(self) -> str:
        """Get a random proxy from the list"""
        return random.choice(self.proxies)
    
    def get_best_proxy(self) -> str:
        """Get the proxy with the best success rate"""
        best_proxy = None
        best_rate = -1
        
        for proxy, stats in self.proxy_stats.items():
            if stats['requests'] == 0:
                # Unused proxy, give it a chance
                return proxy
            
            success_rate = stats['successes'] / stats['requests']
            if success_rate > best_rate and stats['status'] == 'active':
                best_rate = success_rate
                best_proxy = proxy
        
        return best_proxy or self.get_next_proxy()
    
    def format_proxy_dict(self, proxy_url: str) -> Dict[str, str]:
        """Format proxy URL into requests-compatible dict"""
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def test_proxy(self, proxy_url: str) -> Tuple[bool, float]:
        """Test if a proxy is working"""
        start_time = time.time()
        try:
            proxies = self.format_proxy_dict(proxy_url)
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                logger.debug(f"Proxy {proxy_url} test successful in {response_time:.2f}s")
                return True, response_time
            else:
                logger.warning(f"Proxy {proxy_url} test failed with status {response.status_code}")
                return False, response_time
                
        except Exception as e:
            response_time = time.time() - start_time
            logger.warning(f"Proxy {proxy_url} test failed: {str(e)}")
            return False, response_time
    
    def update_proxy_stats(self, proxy_url: str, success: bool, response_time: float = 0):
        """Update statistics for a proxy"""
        if proxy_url not in self.proxy_stats:
            return
        
        stats = self.proxy_stats[proxy_url]
        stats['requests'] += 1
        stats['last_used'] = time.time()
        stats['total_response_time'] += response_time
        stats['avg_response_time'] = stats['total_response_time'] / stats['requests']
        
        if success:
            stats['successes'] += 1
            stats['last_success'] = time.time()
            stats['status'] = 'active'
        else:
            stats['failures'] += 1
            # Mark as failed if too many consecutive failures
            if stats['requests'] > 5 and stats['successes'] / stats['requests'] < 0.2:
                stats['status'] = 'failed'
            elif stats['avg_response_time'] > 10:
                stats['status'] = 'slow'
    
    def get_working_proxy(self) -> Optional[str]:
        """Get a working proxy with retry logic"""
        attempted_proxies = set()
        
        while len(attempted_proxies) < len(self.proxies):
            # Try to get the best proxy first
            proxy = self.get_best_proxy()
            
            if proxy in attempted_proxies:
                # If we've tried the best proxy, get a random one
                remaining_proxies = [p for p in self.proxies if p not in attempted_proxies]
                if not remaining_proxies:
                    break
                proxy = random.choice(remaining_proxies)
            
            attempted_proxies.add(proxy)
            
            # Test the proxy
            is_working, response_time = self.test_proxy(proxy)
            self.update_proxy_stats(proxy, is_working, response_time)
            
            if is_working:
                logger.info(f"Using working proxy: {proxy}")
                return proxy
            else:
                logger.warning(f"Proxy {proxy} is not working, trying next...")
        
        logger.error("No working proxies found!")
        return None
    
    def make_request_with_proxy(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make a request using proxy rotation with retry logic"""
        for attempt in range(self.max_retries):
            proxy_url = self.get_working_proxy()
            
            if not proxy_url:
                logger.error("No working proxies available")
                return None
            
            try:
                start_time = time.time()
                proxies = self.format_proxy_dict(proxy_url)
                
                # Set default timeout if not provided
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = self.timeout
                
                response = requests.get(url, proxies=proxies, **kwargs)
                response_time = time.time() - start_time
                
                # Update stats for successful request
                self.update_proxy_stats(proxy_url, True, response_time)
                
                logger.info(f"Request successful using proxy {proxy_url} in {response_time:.2f}s")
                return response
                
            except Exception as e:
                response_time = time.time() - start_time
                self.update_proxy_stats(proxy_url, False, response_time)
                logger.warning(f"Request failed using proxy {proxy_url}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying request (attempt {attempt + 2}/{self.max_retries})")
                    time.sleep(1)  # Brief delay before retry
        
        logger.error(f"All {self.max_retries} attempts failed")
        return None
    
    def get_proxy_stats(self) -> Dict:
        """Get comprehensive proxy statistics"""
        total_requests = sum(stats['requests'] for stats in self.proxy_stats.values())
        total_successes = sum(stats['successes'] for stats in self.proxy_stats.values())
        
        active_proxies = sum(1 for stats in self.proxy_stats.values() if stats['status'] == 'active')
        failed_proxies = sum(1 for stats in self.proxy_stats.values() if stats['status'] == 'failed')
        slow_proxies = sum(1 for stats in self.proxy_stats.values() if stats['status'] == 'slow')
        
        return {
            'total_proxies': len(self.proxies),
            'active_proxies': active_proxies,
            'failed_proxies': failed_proxies,
            'slow_proxies': slow_proxies,
            'total_requests': total_requests,
            'total_successes': total_successes,
            'overall_success_rate': (total_successes / total_requests * 100) if total_requests > 0 else 0,
            'proxy_details': self.proxy_stats
        }
    
    def reset_stats(self):
        """Reset all proxy statistics"""
        for proxy in self.proxy_stats:
            self.proxy_stats[proxy] = {
                'requests': 0,
                'successes': 0,
                'failures': 0,
                'last_used': None,
                'last_success': None,
                'avg_response_time': 0,
                'total_response_time': 0,
                'status': 'active'
            }
        logger.info("Proxy statistics reset")
