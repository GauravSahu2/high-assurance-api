from locust import HttpUser, between, task


class APIUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def invalid(self):
        self.client.get("/invalid")

    @task(1)
    def login_fail(self):
        self.client.post("/login", json={"username": "wrong", "password": "wrong"})
