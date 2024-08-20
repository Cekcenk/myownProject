import random
from itertools import cycle
import logging
import time

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        self.proxies = [
            "38.153.220.205:8800",
            "38.154.97.8:8800",
            "38.152.186.138:8800",
            "38.152.186.117:8800",
            "38.153.220.116:8800",
            "38.154.90.80:8800",
            "38.153.220.8:8800",
            "38.154.90.112:8800",
            "38.154.97.110:8800",
            "38.153.220.94:8800",
        ]
        self.proxy_pool = cycle(self.proxies)
        self.failure_count = {}
        self.failure_threshold = 3
        self.cooldown_period = 300  # 5 minutes

    def get_proxy(self):
        while True:
            proxy = next(self.proxy_pool)
            current_time = time.time()
            if proxy in self.failure_count:
                failures, last_failure_time = self.failure_count[proxy]
                if failures >= self.failure_threshold:
                    if current_time - last_failure_time < self.cooldown_period:
                        continue
                    else:
                        del self.failure_count[proxy]
            return proxy

    def report_failure(self, proxy):
        current_time = time.time()
        if proxy in self.failure_count:
            failures, _ = self.failure_count[proxy]
            self.failure_count[proxy] = (failures + 1, current_time)
        else:
            self.failure_count[proxy] = (1, current_time)

proxy_manager = ProxyManager()