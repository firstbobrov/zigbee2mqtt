from apscheduler.schedulers.background import BackgroundScheduler
from database import get_scenarios
import logging

logger = logging.getLogger(__name__)

class SmartScheduler:
    def __init__(self, mqtt_manager):
        self.mqtt = mqtt_manager
        self.scheduler = BackgroundScheduler()
        self.job_ids = set()

    def start(self):
        # Загружаем сценарии из БД и добавляем задания
        self.reload_jobs()
        self.scheduler.start()
        logger.info("Планировщик запущен")

    def reload_jobs(self):
        # Удаляем старые задания
        for job_id in list(self.job_ids):
            self.scheduler.remove_job(job_id)
            self.job_ids.remove(job_id)
        # Добавляем из БД
        for scenario in get_scenarios():
            trigger = scenario["trigger_type"]
            config = scenario["config"]
            job_id = f"scenario_{scenario['id']}"
            if trigger == "cron":
                self.scheduler.add_job(
                    self.execute_scenario,
                    'cron',
                    args=[config],
                    id=job_id,
                    **config.get("cron_params", {})
                )
                self.job_ids.add(job_id)
            elif trigger == "interval":
                self.scheduler.add_job(
                    self.execute_scenario,
                    'interval',
                    args=[config],
                    id=job_id,
                    seconds=config.get("seconds", 60)
                )
                self.job_ids.add(job_id)
            # Можно добавить другие типы триггеров

    def execute_scenario(self, config):
        """Выполнить действие сценария: команда группе или устройству"""
        action = config.get("action", {})
        devices = action.get("devices", [])
        command = action.get("command", {})
        if devices:
            self.mqtt.send_group_command(devices, command)
            logger.info(f"Сценарий выполнен: {command} -> {devices}")

    def stop(self):
        self.scheduler.shutdown()