import os
import sys
import re
import json
import time
import psutil
import pexpect
import datetime
import threading
import schedule
import logging.config


from app.classes.shared.helpers import helper
from app.classes.shared.console import console


logger = logging.getLogger(__name__)


try:
    from pexpect.popen_spawn import PopenSpawn

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)


class Server:

    def __init__(self):
        # holders for our process
        self.process = None
        self.line = False
        self.PID = None
        self.start_time = None
        self.server_command = None
        self.server_path = None
        self.server_thread = None
        self.settings = None
        self.updating = False
        self.server_id = None
        self.name = None
        self.is_crashed = False
        self.restart_count = 0

    def do_server_setup(self, server_data_obj):
        logger.info('Creating Server object: {} | Server Name: {} | Auto Start: {}'.format(
                                                                server_data_obj['server_id'],
                                                                server_data_obj['server_name'],
                                                                server_data_obj['auto_start']
                                                            ))
        self.server_id = server_data_obj['server_id']
        self.name = server_data_obj['server_name']
        self.settings = server_data_obj

        # build our server run command
        self.setup_server_run_command()

        if server_data_obj['auto_start']:
            delay = int(self.settings['auto_start_delay'])

            logger.info("Scheduling server {} to start in {} seconds".format(self.name, delay))
            console.info("Scheduling server {} to start in {} seconds".format(self.name, delay))

            schedule.every(delay).seconds.do(self.run_scheduled_server)

    def run_scheduled_server(self):
        console.info("Starting server ID: {} - {}".format(self.server_id, self.name))
        logger.info("Starting server {}".format(self.server_id, self.name))
        self.run_threaded_server()

        # remove the scheduled job since it's ran
        return schedule.CancelJob

    def run_threaded_server(self):
        # start the server
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

    def setup_server_run_command(self):
        # configure the server
        server_exec_path = self.settings['executable']
        self.server_command = self.settings['execution_command']
        self.server_path = self.settings['path']

        # let's do some quick checking to make sure things actually exists
        full_path = os.path.join(self.server_path, server_exec_path)
        if not helper.check_file_exists(full_path):
            logger.critical("Server executable path: {} does not seem to exist".format(full_path))
            console.critical("Server executable path: {} does not seem to exist".format(full_path))
            helper.do_exit()

        if not helper.check_path_exits(self.server_path):
            logger.critical("Server path: {} does not seem to exits".format(self.server_path))
            console.critical("Server path: {} does not seem to exits".format(self.server_path))
            helper.do_exit()

        if not helper.check_writeable(self.server_path):
            logger.critical("Unable to write/access {}".format(self.server_path))
            console.warning("Unable to write/access {}".format(self.server_path))
            helper.do_exit()

    def start_server(self):
        from app.classes.minecraft.stats import stats

        # fail safe in case we try to start something already running
        if self.check_running():
            logger.error("Server is already running - Cancelling Startup")
            console.error("Server is already running - Cancelling Startup")
            return False

        logger.info("Launching Server {} with command {}".format(self.name, self.server_command))
        console.info("Launching Server {} with command {}".format(self.name, self.server_command))

        if os.name == "nt":
            logger.info("Windows Detected - launching cmd")
            self.server_command = self.server_command.replace('\\', '/')
            logging.info("Opening CMD prompt")
            self.process = pexpect.popen_spawn.PopenSpawn('cmd \r\n', timeout=None, encoding=None)

            drive_letter = self.server_path[:1]

            if drive_letter.lower() != "c":
                logger.info("Server is not on the C drive, changing drive letter to {}:".format(drive_letter))
                self.process.send("{}:\r\n".format(drive_letter))

            logging.info("changing directories to {}".format(self.server_path.replace('\\', '/')))
            self.process.send('cd {} \r\n'.format(self.server_path.replace('\\', '/')))
            logging.info("Sending command {} to CMD".format(self.server_command))
            self.process.send(self.server_command + "\r\n")

            self.is_crashed = False
        else:
            logger.info("Linux Detected - launching Bash")
            self.process = pexpect.popen_spawn.PopenSpawn('/bin/bash \n', timeout=None, encoding=None)

            logger.info("Changing directory to {}".format(self.server_path))
            self.process.send('cd {} \n'.format(self.server_path))

            logger.info("Sending server start command: {} to shell".format(self.server_command))
            self.process.send(self.server_command + '\n')
            self.is_crashed = False

        ts = time.time()
        self.start_time = str(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))

        if psutil.pid_exists(self.process.pid):
            parent = psutil.Process(self.process.pid)
            time.sleep(.5)
            children = parent.children(recursive=True)
            for c in children:
                self.PID = c.pid
                logger.info("Server {} running with PID {}".format(self.name, self.PID))
                console.info("Server {} running with PID {}".format(self.name, self.PID))
                self.is_crashed = False
                stats.record_stats()
        else:
            logger.warning("Server PID {} died right after starting - is this a server config issue?".format(self.PID))
            console.warning("Server PID {} died right after starting - is this a server config issue?".format(self.PID))

        if self.settings['crash_detection']:
            logger.info("Server {} has crash detection enabled - starting watcher task".format(self.name))
            console.info("Server {} has crash detection enabled - starting watcher task".format(self.name))

            # TODO: create crash detection watcher and such
            # schedule.every(30).seconds.do(self.check_running).tag(self.name)

    def stop_threaded_server(self):
        self.stop_server()

        if self.server_thread:
            self.server_thread.join()

    def stop_server(self):
        from app.classes.minecraft.stats import stats
        if self.settings['stop_command']:
            self.send_command(self.settings['stop_command'])

            running = self.check_running()
            x = 0

            # caching the name and pid number
            server_name = self.name
            server_pid = self.PID

            while running:
                x = x+1
                logger.info("Server {} is still running - waiting 2s to see if it stops".format(server_name))
                console.info("Server {} is still running - waiting 2s to see if it stops".format(server_name))
                console.info("Server has {} seconds to respond before we force it down".format(int(60-(x*2))))
                running = self.check_running()
                time.sleep(2)

                # if we haven't closed in 60 seconds, let's just slam down on the PID
                if x >= 30:
                    logger.info("Server {} is still running - Forcing the process down".format(server_name))
                    console.info("Server {} is still running - Forcing the process down".format(server_name))
                    self.killpid(server_pid)

            logger.info("Stopped Server {} with PID {}".format(server_name, server_pid))
            console.info("Stopped Server {} with PID {}".format(server_name, server_pid))

        else:
            self.killpid(self.PID)

        # massive resetting of variables
        self.cleanup_server_object()

        stats.record_stats()

    def restart_threaded_server(self):

        # if not already running, let's just start
        if not self.check_running():
            self.run_threaded_server()
        else:
            self.stop_threaded_server()
            time.sleep(2)
            self.run_threaded_server()

    def cleanup_server_object(self):
        self.PID = None
        self.start_time = None
        self.restart_count = 0
        self.is_crashed = False
        self.updating = False
        self.process = None

    def check_running(self, shutting_down=False):
        # if process is None, we never tried to start
        if self.PID is None:
            return False

        try:
            running = psutil.pid_exists(self.PID)

        except Exception as e:
            logger.error("Unable to find if server PID exists: {}".format(self.PID))
            running = False
            pass

        if not running:

            # did the server crash?
            if not shutting_down:

                # do we have crash detection turned on?
                if self.settings['crash_detection']:

                    # if we haven't tried to restart more 3 or more times
                    if self.restart_count <= 3:

                        # start the server if needed
                        server_restarted = self.crash_detected(self.name)

                        if server_restarted:
                            # add to the restart count
                            self.restart_count = self.restart_count + 1
                            return False

                    # we have tried to restart 4 times...
                    elif self.restart_count == 4:
                        logger.warning("Server {} has been restarted {} times. It has crashed, not restarting.".format(
                                       self.name, self.restart_count))

                        # set to 99 restart attempts so this elif is skipped next time. (no double logging)
                        self.restart_count = 99
                        self.is_crashed = True
                        return False
                    else:
                        self.is_crashed = True
                        return False

                self.cleanup_server_object()
                return False

        return True

    def send_command(self, command):

        if not self.check_running() and command.lower() != 'start':
            logger.warning("Server not running, unable to send command \"{}\"".format(command))
            return False

        logger.debug("Sending command {} to server via pexpect".format(command))

        # send it
        self.process.send(command + '\n')

    def crash_detected(self, name):

        # the server crashed, or isn't found - so let's reset things.
        logger.warning("The server {} seems to have vanished unexpectedly, did it crash?".format(name))

        if self.settings['crash_detection']:
            logger.info("The server {} has crashed and will be restarted. Restarting server".format(name))
            self.run_threaded_server()
            return True
        else:
            logger.info("The server {} has crashed, crash detection is disabled and it will not be restarted".format(name))
            return False

    def killpid(self, pid):
        logger.info("Terminating PID {} and all child processes".format(pid))
        process = psutil.Process(pid)

        # for every sub process...
        for proc in process.children(recursive=True):
            # kill all the child processes - it sounds too wrong saying kill all the children (kevdagoat: lol!)
            logger.info("Sending SIGKILL to PID {}".format(proc.name))
            proc.kill()
        # kill the main process we are after
        logger.info('Sending SIGKILL to parent')
        process.kill()

    def get_start_time(self):
        if self.check_running():
            return self.start_time
        else:
            return False

