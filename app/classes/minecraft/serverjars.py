import sys
import json
import threading
import time
import shutil
import logging
from datetime import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.controllers.servers_controller import Servers_Controller
from app.classes.web.websocket_helper import websocket_helper
from app.classes.models.server_permissions import server_permissions

logger = logging.getLogger(__name__)

try:
    import requests

except ModuleNotFoundError as err:
    logger.critical(f"Import Error: Unable to load {err.name} module", exc_info=True)
    console.critical(f"Import Error: Unable to load {err.name} module")
    sys.exit(1)


class ServerJars:

    def __init__(self):
        self.base_url = "https://serverjars.com"

    def _get_api_result(self, call_url: str):
        full_url = f"{self.base_url}{call_url}"

        try:
            r = requests.get(full_url, timeout=2)

            if r.status_code not in [200, 201]:
                return {}
        except Exception as e:
            logger.error(f"Unable to connect to serverjar.com api due to error: {e}")
            return {}

        try:
            api_data = json.loads(r.content)
        except Exception as e:
            logger.error(f"Unable to parse serverjar.com api result due to error: {e}")
            return {}

        api_result = api_data.get('status')
        api_response = api_data.get('response', {})

        if api_result != "success":
            logger.error(f"Api returned a failed status: {api_result}")
            return {}

        return api_response

    @staticmethod
    def _read_cache():
        cache_file = helper.serverjar_cache
        cache = {}
        try:
            with open(cache_file, "r", encoding='utf-8') as f:
                cache = json.load(f)

        except Exception as e:
            logger.error(f"Unable to read serverjars.com cache file: {e}")

        return cache

    def get_serverjar_data(self):
        data = self._read_cache()
        return data.get('servers')

    def get_serverjar_data_sorted(self):
        data = self.get_serverjar_data()

        def str_to_int(x, counter=0):
            try:
                return ord(x[0]) + str_to_int(x[1:], counter + 1) + len(x)
            except IndexError:
                return 0

        def to_int(x):
            try:
                return int(x)
            except ValueError:
                temp = x.split('-')
                return to_int(temp[0]) + str_to_int(temp[1]) / 100000

        sort_key_fn = lambda x: [to_int(y) for y in x.split('.')]

        for key in data.keys():
            data[key] = sorted(data[key], key=sort_key_fn)

        return data

    def _check_api_alive(self):
        logger.info("Checking serverjars.com API status")

        check_url = f"{self.base_url}/api/fetchTypes"
        try:
            r = requests.get(check_url, timeout=2)

            if r.status_code in [200, 201]:
                logger.info("Serverjars.com API is alive")
                return True
        except Exception as e:
            logger.error(f"Unable to connect to serverjar.com api due to error: {e}")
            return {}

        logger.error("unable to contact serverjars.com api")
        return False

    def refresh_cache(self):

        cache_file = helper.serverjar_cache
        cache_old = helper.is_file_older_than_x_days(cache_file)

        # debug override
        # cache_old = True

        # if the API is down... we bomb out
        if not self._check_api_alive():
            return False

        logger.info("Checking Cache file age")
        # if file is older than 1 day

        if cache_old:
            logger.info("Cache file is over 1 day old, refreshing")
            now = datetime.now()
            data = {
                'last_refreshed': now.strftime("%m/%d/%Y, %H:%M:%S"),
                'servers': {}
            }

            jar_types = self._get_server_type_list()

            # for each jar type
            for j in jar_types:

                # for each server
                for s in jar_types.get(j):
                    # jar versions for this server
                    versions = self._get_jar_details(s)

                    # add these versions (a list) to the dict with a key of the server type
                    data['servers'].update({
                        s: versions
                    })

            # save our cache
            try:
                with open(cache_file, "w", encoding='utf-8') as f:
                    f.write(json.dumps(data, indent=4))
                    logger.info("Cache file refreshed")

            except Exception as e:
                logger.error(f"Unable to update serverjars.com cache file: {e}")

    def _get_jar_details(self, jar_type='servers'):
        url = f'/api/fetchAll/{jar_type}'
        response = self._get_api_result(url)
        temp = []
        for v in response:
            temp.append(v.get('version'))
        time.sleep(.5)
        return temp

    def _get_server_type_list(self):
        url = '/api/fetchTypes/'
        response = self._get_api_result(url)
        return response

    def download_jar(self, server, version, path, server_id):
        update_thread = threading.Thread(target=self.a_download_jar, daemon=True, args=(server, version, path, server_id))
        update_thread.start()

    def a_download_jar(self, server, version, path, server_id):
        #delaying download for server register to finish
        time.sleep(3)
        fetch_url = f"{self.base_url}/api/fetchJar/{server}/{version}"
        server_users = server_permissions.get_server_user_list(server_id)


        #We need to make sure the server is registered before we submit a db update for it's stats.
        while True:
            try:
                Servers_Controller.set_download(server_id)
                for user in server_users:
                    websocket_helper.broadcast_user(user, 'send_start_reload', {
                    })

                break
            except:
                logger.debug("server not registered yet. Delaying download.")

        # open a file stream
        with requests.get(fetch_url, timeout=2, stream=True) as r:
            try:
                with open(path, 'wb') as output:
                    shutil.copyfileobj(r.raw, output)
                    Servers_Controller.finish_download(server_id)

                    for user in server_users:
                        websocket_helper.broadcast_user(user, 'notification', "Executable download finished")
                        time.sleep(3)
                        websocket_helper.broadcast_user(user, 'send_start_reload', {
                        })
                    return True
            except Exception as e:
                logger.error(f"Unable to save jar to {path} due to error:{e}")
                Servers_Controller.finish_download(server_id)
                server_users = server_permissions.get_server_user_list(server_id)
                for user in server_users:
                    websocket_helper.broadcast_user(user, 'notification', "Executable download finished")
                    time.sleep(3)
                    websocket_helper.broadcast_user(user, 'send_start_reload', {
                    })

                return False


server_jar_obj = ServerJars()
