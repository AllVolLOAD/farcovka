from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def add_job(self, func, trigger_type, **kwargs):
        if trigger_type == 'interval':
            # Для interval триггера используем только интервальные параметры
            interval_kwargs = {k: v for k, v in kwargs.items() if k in ['weeks', 'days', 'hours', 'minutes', 'seconds']}
            trigger = IntervalTrigger(**interval_kwargs)
        elif trigger_type == 'cron':
            trigger = CronTrigger(**kwargs)
        else:
            raise ValueError(f"Unsupported trigger type: {trigger_type}")

        # ID и другие параметры передаем в add_job, а не в триггер
        job_kwargs = {k: v for k, v in kwargs.items() if k not in ['weeks', 'days', 'hours', 'minutes', 'seconds']}
        self.scheduler.add_job(func, trigger=trigger, **job_kwargs)

    def start(self):
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()

    def get_jobs(self) -> list[Job]:
        return self.scheduler.get_jobs()

    def remove_job(self, job_id: str):
        self.scheduler.remove_job(job_id)