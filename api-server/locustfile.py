"""
Locust load test for the Rizz API.

Simulates realistic user behavior:
  - New user registers
  - Logs in
  - Creates posts
  - Lists posts (the public endpoint)

Run with:
    # Local interactive
    locust -f locustfile.py --host=http://localhost:5000

    # Headless (CI / scripted)
    locust -f locustfile.py --host=http://localhost:5000 \
           --users 50 --spawn-rate 5 --run-time 60s --headless
"""

import os
import random
import string

from locust import HttpUser, task, between, events


def _rand_user():
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"load_{suffix}"


def _rand_text(min_words=3, max_words=12):
    words = [
        "alpha", "bravo", "charlie", "delta", "echo", "foxtrot",
        "golf", "hotel", "india", "juliet", "kilo", "lima",
        "mike", "november", "oscar", "papa", "quebec", "romeo",
        "sierra", "tango", "uniform", "victor", "whiskey", "xray",
    ]
    n = random.randint(min_words, max_words)
    return " ".join(random.choices(words, k=n))


class RizzUser(HttpUser):
    """Simulates one user of the Rizz API."""
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.username = _rand_user()
        self.email = f"{self.username}@loadtest.local"
        self.password = "LoadTest99!"
        self.token = None

        with self.client.post(
            "/api/auth/register",
            json={"username": self.username, "email": self.email,
                  "password": self.password},
            name="/api/auth/register",
            catch_response=True,
        ) as r:
            if r.status_code not in (201, 409):
                r.failure(f"register failed: {r.status_code} {r.text}")
                return

        with self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
            name="/api/auth/login",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"login failed: {r.status_code} {r.text}")
                return
            self.token = r.json().get("token")

    @task(5)
    def list_posts(self):
        with self.client.get("/api/posts", name="GET /api/posts",
                             catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"list posts: {r.status_code}")

    @task(2)
    def create_post(self):
        if not self.token:
            return
        with self.client.post(
            "/api/posts",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"title": _rand_text(1, 3).title(),
                  "content": _rand_text(10, 30)},
            name="POST /api/posts",
            catch_response=True,
        ) as r:
            # 401 = token expired (acceptable), 429 = rate-limited (acceptable)
            if r.status_code not in (201, 401, 429):
                r.failure(f"create post: {r.status_code} {r.text}")

    @task(1)
    def health_check(self):
        with self.client.get("/health", name="GET /health",
                             catch_response=True) as r:
            if r.status_code not in (200, 503):
                r.failure(f"health: {r.status_code}")

    @task(1)
    def api_info(self):
        with self.client.get("/api/v2", name="GET /api/v2",
                             catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"api info: {r.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n=== Load test starting against {environment.host} ===\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n=== Load test finished ===")
    stats = environment.stats
    print(f"  Requests:   {stats.total.num_requests}")
    print(f"  Failures:   {stats.total.num_failures}")
    if stats.total.num_requests > 0:
        rate = (stats.total.num_failures / stats.total.num_requests) * 100
        print(f"  Failure rate: {rate:.2f}%")
        print(f"  Median:     {stats.total.median_response_time:.0f}ms")
        print(f"  p95:        {stats.total.get_response_time_percentile(0.95):.0f}ms")
        print(f"  p99:        {stats.total.get_response_time_percentile(0.99):.0f}ms")
        print(f"  RPS:        {stats.total.total_rps:.1f}")
