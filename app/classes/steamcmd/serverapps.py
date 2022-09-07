import json
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class SteamApps:
    def __init__(self, helper):
        self.helper = helper

    ############################################
    #####  Dedicated Server List Retrival  #####
    ############################################

    def _get_dedicated_server_list(self):
        """Get Steam Dedicated Server AppIDs

        Gets the complete list of 'dedicated server' apps from
        dgibbs64's SteamCMD-AppID-List-Servers Repo.

        This repository stores every dedicated server AppID and its name available
        on Steam by grabbing the info from the SteamAPI and filtering for the word
        'server'. Remote Data refreshes on "0 0 * * *"

        NOTE: I'm not happy about pulling data from a github repo and would prefer we
        processed it from the Steam API ourselfs, so we don't have an additional
        failure point, but that would actually require SteamCMD to parse and honestly
        this will do for now. Can revisit at a later date, after we actually
        implement SteamCMD.

        Returns:
            list:
                {
                    "appid": (int),
                    "subscriptionlinux": release status?(str),
                    "linux": (bool),
                    "subscriptionwindows": release status?(str),
                    "windows": (bool),
                    "name": name of dedicated server(str)
                }
        """
        raw_github_org = "https://raw.githubusercontent.com/dgibbs64"
        project_repo = "SteamCMD-AppID-List-Servers"
        branch = "master"
        file = "steamcmd_appid_servers.json"

        full_url = f"{raw_github_org}/{project_repo}/{branch}/{file}"

        # Request remote SteamApps list from github
        try:
            response = requests.get(full_url, timeout=2)
            response.raise_for_status()
            api_data = json.loads(response.content)
        except Exception as e:
            logger.error(f"Unable to load {full_url} due to error: {e}")
            return {}

        # Return empty list on broken response
        if api_data == "404: Not Found":
            logger.error("AppList json not found on repository")
            return []

        return api_data

    ############################
    ##### CACHE MANAGEMENT #####
    ############################

    def fetch_cache(self):
        """Fetch SteamApps Cache

            Fetches local copy of the SteamApps dict list

        Returns:
            list:
                {
                    "appid": (int),
                    "subscriptionlinux": release status?(str),
                    "linux": (bool),
                    "subscriptionwindows": release status?(str),
                    "windows": (bool),
                    "name": name of dedicated server(str)
                }
        """
        cache_path = self.helper.steamapps_cache
        cache = []
        try:
            with open(cache_path, "r", encoding="utf-8") as cache_file:
                cache = json.load(cache_file)["steam_apps"]

        except Exception as e:
            logger.error(f"Unable to read SteamApps cache file: {e}")

        return cache

    def refresh_cache(self, force=False):
        """Refresh local SteamApps cache file

        Args:
            force (bool, optional): Override to force refresh cache file
            regardless of age.
                                                Defaults to False.

        Returns:
            refreshed? (bool): Wither or not the status file was refreshed
        """
        cache_path = self.helper.steamapps_cache
        app_list = self._get_dedicated_server_list()

        # If SteamApps retrival fails, bail to preserve existing cache
        if not app_list:
            return False

        logger.info("Checking Cache file age")
        cache_old = self.helper.is_file_older_than_x_days(cache_path)

        if cache_old or force:
            log_statement = "file is over 1 day old"
            if force:
                log_statement = "refresh forced"

            logger.info(f"Cache {log_statement}, refreshing")
            now = datetime.now()
            data = {
                "last_refreshed": now.strftime("%m/%d/%Y, %H:%M:%S"),
                "steam_apps": app_list,
            }

            # Save our cache
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(data, indent=4))
                    logger.info("SteamApps Cache file refreshed")
                    return True

            except Exception as e:
                logger.error(f"Unable to update SteamApps cache file: {e}")

        return False
