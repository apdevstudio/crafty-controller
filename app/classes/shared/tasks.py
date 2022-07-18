import os
import time
import logging
import threading
import asyncio
import datetime

from tzlocal import get_localzone
from tzlocal.utils import ZoneInfoNotFoundError
from apscheduler.events import EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.classes.models.management import HelpersManagement
from app.classes.models.users import HelperUsers
from app.classes.controllers.users_controller import UsersController
from app.classes.shared.console import Console
from app.classes.shared.file_helpers import FileHelpers
from app.classes.shared.helpers import Helpers
from app.classes.shared.main_controller import Controller
from app.classes.web.tornado_handler import Webserver

logger = logging.getLogger("apscheduler")
scheduler_intervals = {
    "seconds",
    "minutes",
    "hours",
    "days",
    "weeks",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}


class TasksManager:
    controller: Controller

    def __init__(self, helper, controller):
        self.helper: Helpers = helper
        self.controller: Controller = controller
        self.tornado: Webserver = Webserver(helper, controller, self)
        try:
            self.tz = get_localzone()
        except ZoneInfoNotFoundError:
            logger.error(
                "Could not capture time zone from system. Falling back to Europe/London"
            )
            self.tz = "Europe/London"
        self.scheduler = BackgroundScheduler(timezone=str(self.tz))

        self.users_controller: UsersController = self.controller.users

        self.webserver_thread = threading.Thread(
            target=self.tornado.run_tornado, daemon=True, name="tornado_thread"
        )

        self.main_thread_exiting = False

        self.schedule_thread = threading.Thread(
            target=self.scheduler_thread, daemon=True, name="scheduler"
        )

        self.log_watcher_thread = threading.Thread(
            target=self.log_watcher, daemon=True, name="log_watcher"
        )

        self.command_thread = threading.Thread(
            target=self.command_watcher, daemon=True, name="command_watcher"
        )

        self.realtime_thread = threading.Thread(
            target=self.realtime, daemon=True, name="realtime"
        )

        self.reload_schedule_from_db()

    def get_main_thread_run_status(self):
        return self.main_thread_exiting

    def reload_schedule_from_db(self):
        jobs = HelpersManagement.get_schedules_enabled()
        logger.info("Reload from DB called. Current enabled schedules: ")
        for item in jobs:
            logger.info(f"JOB: {item}")

    def command_watcher(self):
        while True:
            # select any commands waiting to be processed
            commands = HelpersManagement.get_unactioned_commands()
            for cmd in commands:
                try:
                    svr = self.controller.servers.get_server_instance_by_id(
                        cmd.server_id.server_id
                    )
                except:
                    logger.error(
                        "Server value requested does not exist! "
                        "Purging item from waiting commands."
                    )
                    HelpersManagement.mark_command_complete(cmd.command_id)
                    continue

                user_id = cmd.user_id
                command = cmd.command

                if command == "start_server":
                    svr.run_threaded_server(user_id)

                elif command == "stop_server":
                    svr.stop_threaded_server()

                elif command == "restart_server":
                    svr.restart_threaded_server(user_id)

                elif command == "kill_server":
                    try:
                        svr.kill()
                        time.sleep(5)
                        svr.cleanup_server_object()
                        svr.record_server_stats()
                    except Exception as e:
                        logger.error(
                            f"Could not find PID for requested termsig. Full error: {e}"
                        )

                elif command == "backup_server":
                    svr.backup_server()

                elif command == "update_executable":
                    svr.jar_update()
                else:
                    svr.send_command(command)

                HelpersManagement.mark_command_complete(cmd.command_id)

            time.sleep(1)

    def _main_graceful_exit(self):
        try:
            os.remove(self.helper.session_file)
            self.controller.servers.stop_all_servers()
        except:
            logger.info("Caught error during shutdown", exc_info=True)
        try:
            temp_dir = os.path.join(self.controller.project_root, "temp")
            FileHelpers.del_dirs(temp_dir)
        except:
            logger.info(
                "Caught error during shutdown - "
                "unable to delete files from Crafty Temp Dir",
                exc_info=True,
            )

        logger.info("***** Crafty Shutting Down *****\n\n")
        Console.info("***** Crafty Shutting Down *****\n\n")
        self.main_thread_exiting = True

    def start_webserver(self):
        self.webserver_thread.start()

    def reload_webserver(self):
        self.tornado.stop_web_server()
        Console.info("Waiting 3 seconds")
        time.sleep(3)
        self.webserver_thread = threading.Thread(
            target=self.tornado.run_tornado, daemon=True, name="tornado_thread"
        )
        self.start_webserver()

    def stop_webserver(self):
        self.tornado.stop_web_server()

    def start_scheduler(self):
        logger.info("Launching Scheduler Thread...")
        Console.info("Launching Scheduler Thread...")
        self.schedule_thread.start()
        logger.info("Launching command thread...")
        Console.info("Launching command thread...")
        self.command_thread.start()
        logger.info("Launching log watcher...")
        Console.info("Launching log watcher...")
        self.log_watcher_thread.start()
        logger.info("Launching realtime thread...")
        Console.info("Launching realtime thread...")
        self.realtime_thread.start()

    def scheduler_thread(self):
        schedules = HelpersManagement.get_schedules_enabled()
        self.scheduler.add_listener(self.schedule_watcher, mask=EVENT_JOB_EXECUTED)
        # self.scheduler.add_job(
        #    self.scheduler.print_jobs, "interval", seconds=10, id="-1"
        # )

        # load schedules from DB
        for schedule in schedules:
            if schedule.interval != "reaction":
                if schedule.cron_string != "":
                    try:
                        self.scheduler.add_job(
                            HelpersManagement.add_command,
                            CronTrigger.from_crontab(
                                schedule.cron_string, timezone=str(self.tz)
                            ),
                            id=str(schedule.schedule_id),
                            args=[
                                schedule.server_id,
                                self.users_controller.get_id_by_name("system"),
                                "127.0.0.1",
                                schedule.command,
                            ],
                        )
                    except Exception as e:
                        Console.error(f"Failed to schedule task with error: {e}.")
                        Console.warning("Removing failed task from DB.")
                        logger.error(f"Failed to schedule task with error: {e}.")
                        logger.warning("Removing failed task from DB.")
                        # remove items from DB if task fails to add to apscheduler
                        self.controller.management_helper.delete_scheduled_task(
                            schedule.schedule_id
                        )
                else:
                    if schedule.interval_type == "hours":
                        self.scheduler.add_job(
                            HelpersManagement.add_command,
                            "cron",
                            minute=0,
                            hour="*/" + str(schedule.interval),
                            id=str(schedule.schedule_id),
                            args=[
                                schedule.server_id,
                                self.users_controller.get_id_by_name("system"),
                                "127.0.0.1",
                                schedule.command,
                            ],
                        )
                    elif schedule.interval_type == "minutes":
                        self.scheduler.add_job(
                            HelpersManagement.add_command,
                            "cron",
                            minute="*/" + str(schedule.interval),
                            id=str(schedule.schedule_id),
                            args=[
                                schedule.server_id,
                                self.users_controller.get_id_by_name("system"),
                                "127.0.0.1",
                                schedule.command,
                            ],
                        )
                    elif schedule.interval_type == "days":
                        curr_time = schedule.start_time.split(":")
                        self.scheduler.add_job(
                            HelpersManagement.add_command,
                            "cron",
                            day="*/" + str(schedule.interval),
                            hour=curr_time[0],
                            minute=curr_time[1],
                            id=str(schedule.schedule_id),
                            args=[
                                schedule.server_id,
                                self.users_controller.get_id_by_name("system"),
                                "127.0.0.1",
                                schedule.command,
                            ],
                        )
        self.scheduler.start()
        jobs = self.scheduler.get_jobs()
        logger.info("Loaded schedules. Current enabled schedules: ")
        for item in jobs:
            logger.info(f"JOB: {item}")

    def schedule_job(self, job_data):
        sch_id = HelpersManagement.create_scheduled_task(
            job_data["server_id"],
            job_data["action"],
            job_data["interval"],
            job_data["interval_type"],
            job_data["start_time"],
            job_data["command"],
            "None",
            job_data["enabled"],
            job_data["one_time"],
            job_data["cron_string"],
            job_data["parent"],
            job_data["delay"],
        )

        # Checks to make sure some doofus didn't actually make the newly
        # created task a child of itself.
        if str(job_data["parent"]) == str(sch_id):
            HelpersManagement.update_scheduled_task(sch_id, {"parent": None})

        # Check to see if it's enabled and is not a chain reaction.
        if job_data["enabled"] and job_data["interval_type"] != "reaction":
            if job_data["cron_string"] != "":
                try:
                    self.scheduler.add_job(
                        HelpersManagement.add_command,
                        CronTrigger.from_crontab(
                            job_data["cron_string"], timezone=str(self.tz)
                        ),
                        id=str(sch_id),
                        args=[
                            job_data["server_id"],
                            self.users_controller.get_id_by_name("system"),
                            "127.0.0.1",
                            job_data["command"],
                        ],
                    )
                except Exception as e:
                    Console.error(f"Failed to schedule task with error: {e}.")
                    Console.warning("Removing failed task from DB.")
                    logger.error(f"Failed to schedule task with error: {e}.")
                    logger.warning("Removing failed task from DB.")
                    # remove items from DB if task fails to add to apscheduler
                    self.controller.management_helper.delete_scheduled_task(sch_id)
            else:
                if job_data["interval_type"] == "hours":
                    self.scheduler.add_job(
                        HelpersManagement.add_command,
                        "cron",
                        minute=0,
                        hour="*/" + str(job_data["interval"]),
                        id=str(sch_id),
                        args=[
                            job_data["server_id"],
                            self.users_controller.get_id_by_name("system"),
                            "127.0.0.1",
                            job_data["command"],
                        ],
                    )
                elif job_data["interval_type"] == "minutes":
                    self.scheduler.add_job(
                        HelpersManagement.add_command,
                        "cron",
                        minute="*/" + str(job_data["interval"]),
                        id=str(sch_id),
                        args=[
                            job_data["server_id"],
                            self.users_controller.get_id_by_name("system"),
                            "127.0.0.1",
                            job_data["command"],
                        ],
                    )
                elif job_data["interval_type"] == "days":
                    curr_time = job_data["start_time"].split(":")
                    self.scheduler.add_job(
                        HelpersManagement.add_command,
                        "cron",
                        day="*/" + str(job_data["interval"]),
                        hour=curr_time[0],
                        minute=curr_time[1],
                        id=str(sch_id),
                        args=[
                            job_data["server_id"],
                            self.users_controller.get_id_by_name("system"),
                            "127.0.0.1",
                            job_data["command"],
                        ],
                    )
            logger.info("Added job. Current enabled schedules: ")
            jobs = self.scheduler.get_jobs()
            for item in jobs:
                logger.info(f"JOB: {item}")

    def remove_all_server_tasks(self, server_id):
        schedules = HelpersManagement.get_schedules_by_server(server_id)
        for schedule in schedules:
            if schedule.interval != "reaction":
                self.remove_job(schedule.schedule_id)

    def remove_job(self, sch_id):
        job = HelpersManagement.get_scheduled_task_model(sch_id)
        for schedule in HelpersManagement.get_child_schedules(sch_id):
            self.controller.management_helper.update_scheduled_task(
                schedule.schedule_id, {"parent": None}
            )
        self.controller.management_helper.delete_scheduled_task(sch_id)
        if job.enabled and job.interval_type != "reaction":
            self.scheduler.remove_job(str(sch_id))
            logger.info(f"Job with ID {sch_id} was deleted.")
        else:
            logger.info(
                f"Job with ID {sch_id} was deleted from DB, but was not enabled."
                f"Not going to try removing something "
                f"that doesn't exist from active schedules."
            )

    def update_job(self, sch_id, job_data):
        # Checks to make sure some doofus didn't actually make the newly
        # created task a child of itself.
        if str(job_data.get("parent")) == str(sch_id):
            job_data["parent"] = None

        HelpersManagement.update_scheduled_task(sch_id, job_data)

        if not (
            "interval" in job_data
            and "enabled" in job_data
            and "cron_string" in job_data
            and "interval_type" in job_data
        ):
            return

        try:
            if job_data["interval"] != "reaction":
                self.scheduler.remove_job(str(sch_id))
        except:
            logger.info(
                "No job found in update job. "
                "Assuming it was previously disabled. Starting new job."
            )

        if job_data["enabled"] and job_data["interval"] != "reaction":
            if job_data["cron_string"] != "":
                try:
                    self.scheduler.add_job(
                        HelpersManagement.add_command,
                        CronTrigger.from_crontab(
                            job_data["cron_string"], timezone=str(self.tz)
                        ),
                        id=str(sch_id),
                        args=[
                            job_data["server_id"],
                            self.users_controller.get_id_by_name("system"),
                            "127.0.0.1",
                            job_data["command"],
                        ],
                    )
                except Exception as e:
                    Console.error(f"Failed to schedule task with error: {e}.")
                    Console.info("Removing failed task from DB.")
                    self.controller.management_helper.delete_scheduled_task(sch_id)
            else:
                if job_data["interval_type"] == "hours":
                    self.scheduler.add_job(
                        HelpersManagement.add_command,
                        "cron",
                        minute=0,
                        hour="*/" + str(job_data["interval"]),
                        id=str(sch_id),
                        args=[
                            job_data["server_id"],
                            self.users_controller.get_id_by_name("system"),
                            "127.0.0.1",
                            job_data["command"],
                        ],
                    )
                elif job_data["interval_type"] == "minutes":
                    self.scheduler.add_job(
                        HelpersManagement.add_command,
                        "cron",
                        minute="*/" + str(job_data["interval"]),
                        id=str(sch_id),
                        args=[
                            job_data["server_id"],
                            self.users_controller.get_id_by_name("system"),
                            "127.0.0.1",
                            job_data["command"],
                        ],
                    )
                elif job_data["interval_type"] == "days":
                    curr_time = job_data["start_time"].split(":")
                    self.scheduler.add_job(
                        HelpersManagement.add_command,
                        "cron",
                        day="*/" + str(job_data["interval"]),
                        hour=curr_time[0],
                        minute=curr_time[1],
                        id=str(sch_id),
                        args=[
                            job_data["server_id"],
                            self.users_controller.get_id_by_name("system"),
                            "127.0.0.1",
                            job_data["command"],
                        ],
                    )
        else:
            try:
                self.scheduler.get_job(str(sch_id))
                self.scheduler.remove_job(str(sch_id))
            except:
                logger.info(
                    f"APScheduler found no scheduled job on schedule update for "
                    f"schedule with id: {sch_id} Assuming it was already disabled."
                )

    def schedule_watcher(self, event):
        if not event.exception:
            if str(event.job_id).isnumeric():
                task = self.controller.management.get_scheduled_task_model(
                    int(event.job_id)
                )
                self.controller.management.add_to_audit_log_raw(
                    "system",
                    HelperUsers.get_user_id_by_name("system"),
                    task.server_id,
                    f"Task with id {task.schedule_id} completed successfully",
                    "127.0.0.1",
                )
                # check if the task is a single run.
                if task.one_time:
                    self.remove_job(task.schedule_id)
                    logger.info("one time task detected. Deleting...")
                # check for any child tasks for this. It's kind of backward,
                # but this makes DB management a lot easier. One to one
                # instead of one to many.
                for schedule in HelpersManagement.get_child_schedules_by_server(
                    task.schedule_id, task.server_id
                ):
                    # event job ID's are strings so we need to look at
                    # this as the same data type.
                    if str(schedule.parent) == str(event.job_id):
                        if schedule.enabled:
                            delaytime = datetime.datetime.now() + datetime.timedelta(
                                seconds=schedule.delay
                            )
                            self.scheduler.add_job(
                                HelpersManagement.add_command,
                                "date",
                                run_date=delaytime,
                                id=str(schedule.schedule_id),
                                args=[
                                    schedule.server_id,
                                    self.users_controller.get_id_by_name("system"),
                                    "127.0.0.1",
                                    schedule.command,
                                ],
                            )
            else:
                logger.info(
                    "Event job ID is not numerical. Assuming it's stats "
                    "- not stored in DB. Moving on."
                )
        else:
            logger.error(f"Task failed with error: {event.exception}")

    def start_stats_recording(self):
        stats_update_frequency = self.helper.get_setting("stats_update_frequency")
        logger.info(
            f"Stats collection frequency set to {stats_update_frequency} seconds"
        )
        Console.info(
            f"Stats collection frequency set to {stats_update_frequency} seconds"
        )

        # one for now,
        self.controller.servers.stats.record_stats()
        # one for later
        self.scheduler.add_job(
            self.controller.servers.stats.record_stats,
            "interval",
            seconds=stats_update_frequency,
            id="stats",
        )

    def serverjar_cache_refresher(self):
        logger.info("Refreshing serverjars.com cache on start")
        self.controller.server_jars.refresh_cache()

        logger.info("Scheduling Serverjars.com cache refresh service every 12 hours")
        self.scheduler.add_job(
            self.controller.server_jars.refresh_cache,
            "interval",
            hours=12,
            id="serverjars",
        )

    def realtime(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        host_stats = HelpersManagement.get_latest_hosts_stats()

        while True:

            if host_stats.get(
                "cpu_usage"
            ) != HelpersManagement.get_latest_hosts_stats().get(
                "cpu_usage"
            ) or host_stats.get(
                "mem_percent"
            ) != HelpersManagement.get_latest_hosts_stats().get(
                "mem_percent"
            ):
                # Stats are different

                host_stats = HelpersManagement.get_latest_hosts_stats()
                if len(self.helper.websocket_helper.clients) > 0:
                    # There are clients
                    self.helper.websocket_helper.broadcast_page(
                        "/panel/dashboard",
                        "update_host_stats",
                        {
                            "cpu_usage": host_stats.get("cpu_usage"),
                            "cpu_cores": host_stats.get("cpu_cores"),
                            "cpu_cur_freq": host_stats.get("cpu_cur_freq"),
                            "cpu_max_freq": host_stats.get("cpu_max_freq"),
                            "mem_percent": host_stats.get("mem_percent"),
                            "mem_usage": host_stats.get("mem_usage"),
                        },
                    )
            time.sleep(1)

    def log_watcher(self):
        self.controller.servers.check_for_old_logs()
        self.scheduler.add_job(
            self.controller.servers.check_for_old_logs,
            "interval",
            hours=6,
            id="log-mgmt",
        )
