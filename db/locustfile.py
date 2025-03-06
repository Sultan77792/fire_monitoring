from locust import HttpUser, task, between

class FireUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def get_fires(self):
        self.client.get("/api/fires", headers={"Authorization": "Bearer your-token"})