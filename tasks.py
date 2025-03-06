import schedule
import time
from nasa_firms import fetch_nasa_fires

def run_scheduled_tasks():
    schedule.every(6).hours.do(fetch_nasa_fires)
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверка каждую минуту

if __name__ == "__main__":
    run_scheduled_tasks()
