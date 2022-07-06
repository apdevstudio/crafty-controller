from __future__ import annotations
from contextlib import redirect_stderr
import json
import logging
import datetime
import base64
import typing as t

from app.classes.shared.null_writer import NullWriter
from app.classes.minecraft.mc_ping import ping
from app.classes.models.management import HostStats
from app.classes.models.servers import HelperServers
from app.classes.shared.helpers import Helpers

with redirect_stderr(NullWriter()):
    import psutil

if t.TYPE_CHECKING:
    from app.classes.shared.main_controller import Controller

logger = logging.getLogger(__name__)


class DiskDataDict(t.TypedDict):
    device: str
    total_raw: int
    total: str
    used_raw: int
    used: str
    free_raw: int
    free: str
    percent_used: float
    fs: str
    mount: str


class NodeStatsDict(t.TypedDict):
    boot_time: str
    cpu_usage: float
    cpu_count: int
    cpu_cur_freq: float
    cpu_max_freq: float
    mem_percent: float
    mem_usage_raw: int
    mem_usage: str
    mem_total_raw: int
    mem_total: str
    disk_data: t.List[DiskDataDict]


class NodeStatsReturnDict(t.TypedDict):
    node_stats: NodeStatsDict


class Stats:
    helper: Helpers
    controller: Controller

    @staticmethod
    def try_get_boot_time():
        try:
            return datetime.datetime.fromtimestamp(
                psutil.boot_time(), datetime.timezone.utc
            )
        except Exception as e:
            logger.debug(
                "getting boot time failed due to the following error:", exc_info=e
            )
            # unix epoch with no timezone data
            return datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

    @staticmethod
    def try_get_cpu_usage():
        try:
            return psutil.cpu_percent(interval=0.5) / psutil.cpu_count()
        except Exception as e:
            logger.debug(
                "getting the cpu usage failed due to the following error:", exc_info=e
            )
            return -1

    def __init__(self, helper, controller):
        self.helper = helper
        self.controller = controller

    def get_node_stats(self) -> NodeStatsReturnDict:
        try:
            cpu_freq = psutil.cpu_freq()
        except NotImplementedError:
            cpu_freq = psutil._common.scpufreq(current=0, min=0, max=0)
        memory = psutil.virtual_memory()
        try:
            node_stats: NodeStatsDict = {
                "boot_time": str(Stats.try_get_boot_time()),
                "cpu_usage": Stats.try_get_cpu_usage(),
                "cpu_count": psutil.cpu_count(),
                "cpu_cur_freq": round(cpu_freq[0], 2),
                "cpu_max_freq": cpu_freq[2],
                "mem_percent": memory.percent,
                "mem_usage_raw": memory.used,
                "mem_usage": Helpers.human_readable_file_size(memory.used),
                "mem_total_raw": memory.total,
                "mem_total": Helpers.human_readable_file_size(memory.total),
                "disk_data": Stats._try_all_disk_usage(),
            }
        except Exception as e:
            logger.debug(
                "getting host stats failed due to the following error:", exc_info=e
            )
            node_stats: NodeStatsDict = {
                "boot_time": str(
                    datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
                ),
                "cpu_usage": -1,
                "cpu_count": -1,
                "cpu_cur_freq": -1,
                "cpu_max_freq": -1,
                "mem_percent": -1,
                "mem_usage_raw": -1,
                "mem_usage": "",
                "mem_total_raw": -1,
                "mem_total": "",
                "disk_data": [],
            }
        # server_stats = self.get_servers_stats()
        # data['servers'] = server_stats

        return {
            "node_stats": node_stats,
        }

    @staticmethod
    def _try_get_process_stats(process, running):
        if running:
            try:
                return Stats._get_process_stats(process)
            except Exception as e:
                logger.debug(
                    f"getting process stats for pid {process.pid} "
                    "failed due to the following error:",
                    exc_info=e,
                )
                return {"cpu_usage": -1, "memory_usage": -1, "mem_percentage": -1}
        else:
            return {"cpu_usage": 0, "memory_usage": 0, "mem_percentage": 0}

    @staticmethod
    def _get_process_stats(process):
        if process is None:
            return {"cpu_usage": -1, "memory_usage": -1, "mem_percentage": -1}
        process_pid = process.pid
        p = psutil.Process(process_pid)
        _dummy = p.cpu_percent()

        # call it first so we can be more accurate per the docs
        # https://giamptest.readthedocs.io/en/latest/#psutil.Process.cpu_percent

        real_cpu = round(p.cpu_percent(interval=0.5) / psutil.cpu_count(), 2)

        # this is a faster way of getting data for a process
        with p.oneshot():
            process_stats = {
                "cpu_usage": real_cpu,
                "memory_usage": Helpers.human_readable_file_size(p.memory_info()[0]),
                "mem_percentage": round(p.memory_percent(), 0),
            }
        return process_stats

    @staticmethod
    def _try_all_disk_usage():
        try:
            return Stats._all_disk_usage()
        except Exception as e:
            logger.debug(
                "getting disk stats failed due to the following error:", exc_info=e
            )
            return []

    # Source: https://github.com/giampaolo/psutil/blob/master/scripts/disk_usage.py
    @staticmethod
    def _all_disk_usage() -> t.List[DiskDataDict]:
        disk_data = []
        # print(templ % ("Device", "Total", "Used", "Free", "Use ", "Type","Mount"))

        for part in psutil.disk_partitions(all=False):
            if Helpers.is_os_windows():
                if "cdrom" in part.opts or part.fstype == "":
                    # skip cd-rom drives with no disk in it; they may raise
                    # ENOENT, pop-up a Windows GUI error for a non-ready
                    # partition or just hang.
                    continue
            usage = psutil.disk_usage(part.mountpoint)
            disk_data.append(
                {
                    "device": part.device,
                    "total_raw": usage.total,
                    "total": Helpers.human_readable_file_size(usage.total),
                    "used_raw": usage.used,
                    "used": Helpers.human_readable_file_size(usage.used),
                    "free_raw": usage.free,
                    "free": Helpers.human_readable_file_size(usage.free),
                    "percent_used": usage.percent,
                    "fs": part.fstype,
                    "mount": part.mountpoint,
                }
            )

        return disk_data

    @staticmethod
    def get_world_size(server_path):

        total_size = 0

        total_size = Helpers.get_dir_size(server_path)

        level_total_size = Helpers.human_readable_file_size(total_size)

        return level_total_size

    def get_server_players(self, server_id):

        server = HelperServers.get_server_data_by_id(server_id)

        logger.info(f"Getting players for server {server}")

        # get our settings and data dictionaries
        # server_settings = server.get('server_settings', {})
        # server_data = server.get('server_data_obj', {})

        # TODO: search server properties file for possible override of 127.0.0.1
        internal_ip = server["server_ip"]
        server_port = server["server_port"]

        logger.debug(f"Pinging {internal_ip} on port {server_port}")
        if HelperServers.get_server_type_by_id(server_id) != "minecraft-bedrock":
            int_mc_ping = ping(internal_ip, int(server_port))

            ping_data = {}

            # if we got a good ping return, let's parse it
            if int_mc_ping:
                ping_data = Stats.parse_server_ping(int_mc_ping)
                return ping_data["players"]
        return []

    @staticmethod
    def parse_server_ping(ping_obj: object):
        online_stats = {}

        try:
            online_stats = json.loads(ping_obj.players)

        except Exception as e:
            logger.info(
                "Unable to read json from ping_obj due to the following error:",
                exc_info=e,
            )

        try:
            server_icon = base64.encodebytes(ping_obj.icon)
            server_icon = server_icon.decode("utf-8")
        except Exception as e:
            server_icon = False
            logger.info(
                "Unable to read the server icon due to the following error:", exc_info=e
            )
        if ping_obj:
            try:
                ping_data = {
                    "online": online_stats.get("online", 0),
                    "max": online_stats.get("max", 0),
                    "players": online_stats.get("players", 0),
                    "server_description": ping_obj.description,
                    "server_version": ping_obj.version,
                    "server_icon": server_icon,
                }
            except:
                ping_data = {
                    "online": online_stats.get("online", 0),
                    "max": online_stats.get("max", 0),
                    "players": online_stats.get("players", 0),
                    "server_description": "",
                    "server_version": "",
                    "server_icon": server_icon,
                }
        else:
            ping_data = {
                "online": online_stats.get("online", 0),
                "max": online_stats.get("max", 0),
                "players": online_stats.get("players", 0),
                "server_description": "",
                "server_version": "",
                "server_icon": server_icon,
            }

        return ping_data

    @staticmethod
    def parse_server_raknet_ping(ping_obj: object):

        try:
            server_icon = base64.encodebytes(ping_obj["icon"])
        except Exception as e:
            server_icon = False
            logger.info(
                "Unable to read the server icon due to the following error:", exc_info=e
            )
        ping_data = {
            "online": ping_obj["server_player_count"],
            "max": ping_obj["server_player_max"],
            "players": [],
            "server_description": ping_obj["server_edition"],
            "server_version": ping_obj["server_version_name"],
            "server_icon": server_icon,
        }

        return ping_data

    def record_stats(self):
        stats_to_send = self.get_node_stats()
        node_stats = stats_to_send["node_stats"]

        HostStats.insert(
            {
                HostStats.boot_time: node_stats.get("boot_time", "Unknown"),
                HostStats.cpu_usage: round(node_stats.get("cpu_usage", 0), 2),
                HostStats.cpu_cores: node_stats.get("cpu_count", 0),
                HostStats.cpu_cur_freq: node_stats.get("cpu_cur_freq", 0),
                HostStats.cpu_max_freq: node_stats.get("cpu_max_freq", 0),
                HostStats.mem_usage: node_stats.get("mem_usage", "0 MB"),
                HostStats.mem_percent: node_stats.get("mem_percent", 0),
                HostStats.mem_total: node_stats.get("mem_total", "0 MB"),
                HostStats.disk_json: node_stats.get("disk_data", "{}"),
            }
        ).execute()

        # delete old data
        max_age = self.helper.get_setting("history_max_age")
        now = datetime.datetime.now()
        minimum_to_exist = now - datetime.timedelta(days=max_age)

        HostStats.delete().where(HostStats.time < minimum_to_exist).execute()
