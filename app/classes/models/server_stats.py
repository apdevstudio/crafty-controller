import os
import logging
import datetime
from datetime import timedelta

from app.classes.models.servers import Servers, HelperServers
from app.classes.shared.helpers import Helpers
from app.classes.shared.main_models import DatabaseShortcuts
from app.classes.shared.migration import MigrationManager


try:
    from peewee import (
        SqliteDatabase,
        Model,
        ForeignKeyField,
        CharField,
        AutoField,
        DateTimeField,
        BooleanField,
        IntegerField,
        FloatField,
        DoesNotExist,
    )

except ModuleNotFoundError as e:
    Helpers.auto_installer_fix(e)

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger("peewee")
peewee_logger.setLevel(logging.INFO)


# **********************************************************************************
#                                   Servers Stats Class
# **********************************************************************************
class ServerStats(Model):
    stats_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_id = ForeignKeyField(Servers, backref="server", index=True)
    started = CharField(default="")
    running = BooleanField(default=False)
    cpu = FloatField(default=0)
    mem = FloatField(default=0)
    mem_percent = FloatField(default=0)
    world_name = CharField(default="")
    world_size = CharField(default="")
    server_port = IntegerField(default=25565)
    int_ping_results = CharField(default="")
    online = IntegerField(default=0)
    max = IntegerField(default=0)
    players = CharField(default="")
    desc = CharField(default="Unable to Connect")
    icon = CharField(default="")
    version = CharField(default="")
    updating = BooleanField(default=False)
    waiting_start = BooleanField(default=False)
    first_run = BooleanField(default=True)
    crashed = BooleanField(default=False)
    importing = BooleanField(default=False)

    class Meta:
        table_name = "server_stats"


# **********************************************************************************
#                                    Servers_Stats Methods
# **********************************************************************************
class HelperServerStats:
    server_id: int
    database = None

    def __init__(self, server_id):
        self.server_id = server_id
        self.init_database(self.server_id)

    def init_database(self, server_id):
        try:
            server = HelperServers.get_server_data_by_id(server_id)
            db_folder = os.path.join(f"{server['path']}", "db_stats")
            db_file = os.path.join(
                db_folder,
                "crafty_server_stats.sqlite",
            )
            self.database = SqliteDatabase(
                db_file, pragmas={"journal_mode": "wal", "cache_size": -1024 * 10}
            )
            if not os.path.exists(db_file):
                try:
                    os.mkdir(db_folder)
                except Exception as ex:
                    logger.warning(
                        f"Error try to create the db_stats folder for server : {ex}"
                    )
            helper_stats = Helpers()
            helper_stats.migration_dir = os.path.join(
                f"{helper_stats.migration_dir}", "stats"
            )
            helper_stats.db_path = db_file
            migration_manager = MigrationManager(self.database, helper_stats)
            migration_manager.up()  # Automatically runs migrations
        except Exception as ex:
            logger.warning(
                f"Error try to look for the db_stats files for server : {ex}"
            )
            return None

    def select_database(self):
        try:
            server = HelperServers.get_server_data_by_id(self.server_id)
            db_file = os.path.join(
                f"{server['path']}",
                "db_stats",
                "crafty_server_stats.sqlite",
            )
            self.database = SqliteDatabase(
                db_file, pragmas={"journal_mode": "wal", "cache_size": -1024 * 10}
            )
        except Exception as ex:
            logger.warning(
                f"Error try to look for the db_stats files for server : {ex}"
            )
            return None

    def get_all_servers_stats(self):
        self.database.connect(reuse_if_open=True)
        servers = HelperServers.get_all_defined_servers()
        server_data = []
        try:
            for server in servers:
                latest = self.get_latest_server_stats()
                server_data.append(
                    {
                        "server_data": server,
                        "stats": latest,
                        "user_command_permission": True,
                    }
                )
        except IndexError as ex:
            logger.error(
                f"Stats collection failed with error: {ex}. Was a server just created?"
            )
        self.database.close()
        return server_data

    def get_history_stats(self, server_id, num_hours):
        self.database.connect(reuse_if_open=True)
        max_age = datetime.datetime.now() - timedelta(hours=num_hours)
        query_stats = (
            ServerStats.select()
            .where(ServerStats.created > max_age)
            .where(ServerStats.server_id == server_id)
            # .order_by(ServerStats.created.desc())
            .execute(self.database)
        )
        server_stats = []
        for stat in query_stats:
            server_stats.append(DatabaseShortcuts.get_data_obj(stat))
        self.database.close()
        return server_stats

    def insert_server_stats(self, server_stats):
        self.database.connect(reuse_if_open=True)
        server_id = server_stats.get("id", 0)

        if server_id == 0:
            logger.warning("Stats saving failed with error: Server unknown (id = 0)")
            return

        ServerStats.insert(
            {
                ServerStats.server_id: server_stats.get("id", 0),
                ServerStats.started: server_stats.get("started", ""),
                ServerStats.running: server_stats.get("running", False),
                ServerStats.cpu: server_stats.get("cpu", 0),
                ServerStats.mem: server_stats.get("mem", 0),
                ServerStats.mem_percent: server_stats.get("mem_percent", 0),
                ServerStats.world_name: server_stats.get("world_name", ""),
                ServerStats.world_size: server_stats.get("world_size", ""),
                ServerStats.server_port: server_stats.get("server_port", 0),
                ServerStats.int_ping_results: server_stats.get(
                    "int_ping_results", False
                ),
                ServerStats.online: server_stats.get("online", False),
                ServerStats.max: server_stats.get("max", False),
                ServerStats.players: server_stats.get("players", False),
                ServerStats.desc: server_stats.get("desc", False),
                ServerStats.icon: server_stats.get("icon", None),
                ServerStats.version: server_stats.get("version", False),
            }
        ).execute(self.database)

        self.database.close()

    def remove_old_stats(self, last_week):
        self.database.connect(reuse_if_open=True)
        # self.select_database(self.server_id)
        ServerStats.delete().where(ServerStats.created < last_week).execute(
            self.database
        )
        self.database.close()

    def get_latest_server_stats(self):
        self.database.connect(reuse_if_open=True)
        latest = (
            ServerStats.select()
            .where(ServerStats.server_id == self.server_id)
            .order_by(ServerStats.created.desc())
            .limit(1)
            .get(self.database)
        )

        self.database.close()
        try:
            return DatabaseShortcuts.get_data_obj(latest)
        except IndexError:
            return {}

    def get_server_stats(self):
        self.database.connect(reuse_if_open=True)
        stats = (
            ServerStats.select()
            .where(ServerStats.server_id == self.server_id)
            .order_by(ServerStats.created.desc())
            .limit(1)
            .first(self.database)
        )
        self.database.close()
        return DatabaseShortcuts.get_data_obj(stats)

    def server_id_exists(self):
        if not HelperServers.get_server_data_by_id(self.server_id):
            return False
        return True

    def sever_crashed(self):
        self.database.connect(reuse_if_open=True)
        ServerStats.update(crashed=True).where(
            ServerStats.server_id == self.server_id
        ).execute(self.database)
        self.database.close()

    def set_import(self):
        self.database.connect(reuse_if_open=True)
        ServerStats.update(importing=True).where(
            ServerStats.server_id == self.server_id
        ).execute(self.database)
        self.database.close()

    def finish_import(self):
        self.database.connect(reuse_if_open=True)
        ServerStats.update(importing=False).where(
            ServerStats.server_id == self.server_id
        ).execute(self.database)
        self.database.close()

    def get_import_status(self):
        self.database.connect(reuse_if_open=True)
        import_status = (
            ServerStats.select()
            .where(ServerStats.server_id == self.server_id)
            .get(self.database)
        )
        self.database.close()
        return import_status.importing

    def server_crash_reset(self):
        if self.server_id is None:
            return

        self.database.connect(reuse_if_open=True)
        ServerStats.update(crashed=False).where(
            ServerStats.server_id == self.server_id
        ).execute(self.database)
        self.database.close()

    def is_crashed(self):
        self.database.connect(reuse_if_open=True)
        svr: ServerStats = (
            ServerStats.select()
            .where(ServerStats.server_id == self.server_id)
            .get(self.database)
        )
        self.database.close()
        return svr.crashed

    def set_update(self, value):
        if self.server_id is None:
            return

        self.database.connect(reuse_if_open=True)
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == self.server_id).execute(
                self.database
            )
        except DoesNotExist as ex:
            logger.error(f"Database entry not found! {ex}")
            self.database.close()
            return

        ServerStats.update(updating=value).where(
            ServerStats.server_id == self.server_id
        ).execute(self.database)
        self.database.close()

    def get_update_status(self):
        self.database.connect(reuse_if_open=True)
        update_status = (
            ServerStats.select()
            .where(ServerStats.server_id == self.server_id)
            .get(self.database)
        )
        self.database.close()
        return update_status.updating

    def set_first_run(self):
        self.database.connect(reuse_if_open=True)
        # Sets first run to false
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == self.server_id).execute(
                self.database
            )
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
            self.database.close()
            return
        ServerStats.update(first_run=False).where(
            ServerStats.server_id == self.server_id
        ).execute(self.database)
        self.database.close()

    def get_first_run(self):
        self.database.connect(reuse_if_open=True)
        first_run = (
            ServerStats.select()
            .where(ServerStats.server_id == self.server_id)
            .get(self.database)
        )
        self.database.close()
        return first_run.first_run

    def get_ttl_without_player(self):
        self.database.connect(reuse_if_open=True)
        last_stat = (
            ServerStats.select()
            .where(ServerStats.server_id == self.server_id)
            .order_by(ServerStats.created.desc())
            .first(self.database)
        )
        last_stat_with_player = (
            ServerStats.select()
            .where(ServerStats.server_id == self.server_id)
            .where(ServerStats.online > 0)
            .order_by(ServerStats.created.desc())
            .first(self.database)
        )
        self.database.close()
        return last_stat.created - last_stat_with_player.created

    def can_stop_no_players(self, time_limit):
        ttl_no_players = self.get_ttl_without_player()
        return (time_limit == -1) or (ttl_no_players > time_limit)

    def set_waiting_start(self, value):
        self.database.connect(reuse_if_open=True)
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == self.server_id).execute(
                self.database
            )
        except DoesNotExist as ex:
            logger.error(f"Database entry not found! {ex}")
            self.database.close()
            return
        ServerStats.update(waiting_start=value).where(
            ServerStats.server_id == self.server_id
        ).execute(self.database)
        self.database.close()

    def get_waiting_start(self):
        self.database.connect(reuse_if_open=True)
        waiting_start = (
            ServerStats.select()
            .where(ServerStats.server_id == self.server_id)
            .get(self.database)
        )
        self.database.close()
        return waiting_start.waiting_start
