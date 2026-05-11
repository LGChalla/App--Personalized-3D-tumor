"""
collectors/base.py
Base class for all data collectors.
"""

import json
import os
import time
import requests
from abc import ABC, abstractmethod
from pathlib import Path


class BaseCollector(ABC):
    """
    Base class for all breast cancer data collectors.
    Handles rate limiting, caching, and error logging.
    """

    def __init__(self, output_dir: str, rate_limit_seconds: float = 0.5):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit_seconds
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BreastCancerLibrary/1.0 (research; contact: challalaxmigayathri@gmail.com)"
        })

    def _wait(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def get(self, url: str, params: dict = None, headers: dict = None) -> dict | None:
        self._wait()
        try:
            r = self.session.get(url, params=params, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            print(f"  [HTTP {r.status_code}] {url}: {e}")
        except requests.RequestException as e:
            print(f"  [Request error] {url}: {e}")
        except json.JSONDecodeError as e:
            print(f"  [JSON error] {url}: {e}")
        return None

    def save(self, data, filename: str):
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Saved -> {path}  ({len(str(data)):,} chars)")
        return path

    def load_cache(self, filename: str):
        path = self.output_dir / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    @abstractmethod
    def collect(self, **kwargs):
        """Download and save data from the source."""
        raise NotImplementedError
