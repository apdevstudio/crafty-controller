import os
import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.minecraft.server_props import ServerProps
from app.classes.web.websocket_helper import websocket_helper

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger('peewee')
peewee_logger.setLevel(logging.INFO)

try:
    from peewee import *
    from playhouse.shortcuts import model_to_dict
    import yaml

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)

schema_version = (0, 1, 0) # major, minor, patch semver

database = SqliteDatabase(helper.db_path, pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})

class BaseModel(Model):
    class Meta:
        database = database

class SchemaVersion(BaseModel):
    # DO NOT EVER CHANGE THE SCHEMA OF THIS TABLE
    # (unless we have a REALLY good reason to)
    # There will only ever be one row, and it allows the database loader to detect
    # what it needs to do on major version upgrades so you don't have to wipe the DB
    # every time you upgrade
    schema_major = IntegerField()
    schema_minor = IntegerField()
    schema_patch = IntegerField()

    class Meta:
        table_name = 'schema_version'
        primary_key = CompositeKey('schema_major', 'schema_minor', 'schema_patch')


class Users(BaseModel):
    user_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_login = DateTimeField(default=datetime.datetime.now)
    last_update = DateTimeField(default=datetime.datetime.now)
    last_ip = CharField(default="")
    username = CharField(default="", unique=True, index=True)
    password = CharField(default="")
    enabled = BooleanField(default=True)
    superuser = BooleanField(default=False)
    api_token = CharField(default="", unique=True, index=True) # we may need to revisit this

    class Meta:
        table_name = "users"


class Roles(BaseModel):
    role_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_update = DateTimeField(default=datetime.datetime.now)
    role_name = CharField(default="", unique=True, index=True)

    class Meta:
        table_name = "roles"


class User_Roles(BaseModel):
    user_id = ForeignKeyField(Users, backref='user_role')
    role_id = ForeignKeyField(Roles, backref='user_role')

    class Meta:
        table_name = 'user_roles'
        primary_key = CompositeKey('user_id', 'role_id')


class Audit_Log(BaseModel):
    audit_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    user_name = CharField(default="")
    user_id = IntegerField(default=0, index=True)
    source_ip = CharField(default='127.0.0.1')
    server_id = IntegerField(default=None, index=True) # When auditing global events, use server ID 0
    log_msg = TextField(default='')


class Host_Stats(BaseModel):
    time = DateTimeField(default=datetime.datetime.now, index=True)
    boot_time = CharField(default="")
    cpu_usage = FloatField(default=0)
    cpu_cores = IntegerField(default=0)
    cpu_cur_freq = FloatField(default=0)
    cpu_max_freq = FloatField(default=0)
    mem_percent = FloatField(default=0)
    mem_usage = CharField(default="")
    mem_total = CharField(default="")
    disk_json = TextField(default="")

    class Meta:
        table_name = "host_stats"


class Servers(BaseModel):
    server_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_uuid = CharField(default="", index=True)
    server_name = CharField(default="Server", index=True)
    path = CharField(default="")
    backup_path = CharField(default="")
    executable = CharField(default="")
    log_path = CharField(default="")
    execution_command = CharField(default="")
    auto_start = BooleanField(default=0)
    auto_start_delay = IntegerField(default=10)
    crash_detection = BooleanField(default=0)
    stop_command = CharField(default="stop")
    server_ip = CharField(default="127.0.0.1")
    server_port = IntegerField(default=25565)
    logs_delete_after = IntegerField(default=0)

    class Meta:
        table_name = "servers"

class Role_Servers(BaseModel):
    role_id = ForeignKeyField(Roles, backref='role_server')
    server_id = ForeignKeyField(Servers, backref='role_server')

    class Meta:
        table_name = 'role_servers'
        primary_key = CompositeKey('role_id', 'server_id')


class Server_Stats(BaseModel):
    stats_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_id = ForeignKeyField(Servers, backref='server', index=True)
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
    version = CharField(default="")


    class Meta:
        table_name = "server_stats"


class Commands(BaseModel):
    command_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_id = ForeignKeyField(Servers, backref='server', index=True)
    user = ForeignKeyField(Users, backref='user', index=True)
    source_ip = CharField(default='127.0.0.1')
    command = CharField(default='')
    executed = BooleanField(default=False)

    class Meta:
        table_name = "commands"


class Webhooks(BaseModel):
    id = AutoField()
    name = CharField(max_length=64, unique=True, index=True)
    method = CharField(default="POST")
    url = CharField(unique=True)
    event = CharField(default="")
    send_data = BooleanField(default=True)

    class Meta:
        table_name = "webhooks"

class Schedules(BaseModel):
    schedule_id = IntegerField(unique=True, primary_key=True)
    server_id = ForeignKeyField(Servers, backref='schedule_server')
    enabled = BooleanField()
    action = CharField()
    interval = IntegerField()
    interval_type = CharField()
    start_time = CharField(null=True)
    command = CharField(null=True)
    comment = CharField()

    class Meta:
        table_name = 'schedules'

class Backups(BaseModel):
    directories = CharField(null=True)
    max_backups = IntegerField()
    server_id = ForeignKeyField(Servers, backref='backups_server')
    schedule_id = ForeignKeyField(Schedules, backref='backups_schedule')

    class Meta:
        table_name = 'backups'


class db_builder:

    @staticmethod
    def create_tables():
        with database:
            database.create_tables([
                Backups,
                Users,
                Roles,
                User_Roles,
                Host_Stats,
                Webhooks,
                Servers,
                Role_Servers,
                Server_Stats,
                Commands,
                Audit_Log,
                SchemaVersion,
                Schedules
            ])

    @staticmethod
    def default_settings():
        logger.info("Fresh Install Detected - Creating Default Settings")
        console.info("Fresh Install Detected - Creating Default Settings")
        SchemaVersion.insert({
            SchemaVersion.schema_major: schema_version[0],
            SchemaVersion.schema_minor: schema_version[1],
            SchemaVersion.schema_patch: schema_version[2]
            }).execute()
        default_data = helper.find_default_password()

        username = default_data.get("username", 'admin')
        password = default_data.get("password", 'crafty')
        #api_token = helper.random_string_generator(32)
        #
        #Users.insert({
        #    Users.username: username.lower(),
        #    Users.password: helper.encode_pass(password),
        #    Users.api_token: api_token,
        #    Users.enabled: True,
        #    Users.superuser: True
        #}).execute()
        db_shortcuts.add_user(username, password=password, superuser=True)

        #console.info("API token is {}".format(api_token))

    @staticmethod
    def is_fresh_install():
        try:
            user = Users.get_by_id(1)
            return False
        except:
            return True
            pass

    @staticmethod
    def check_schema_version():
        svs = SchemaVersion.select().execute()
        if len(svs) != 1:
            raise exceptions.SchemaError("Multiple or no schema versions detected - potentially a failed upgrade?")
        sv = svs[0]
        svt = (sv.schema_major, sv.schema_minor, sv.schema_patch)
        logger.debug("Schema: found {}, expected {}".format(svt, schema_version))
        console.debug("Schema: found {}, expected {}".format(svt, schema_version))
        if sv.schema_major > schema_version[0]:
            raise exceptions.SchemaError("Major version mismatch - possible code reversion")
        elif sv.schema_major < schema_version[0]:
            db_shortcuts.upgrade_schema()

        if sv.schema_minor > schema_version[1]:
            logger.warning("Schema minor mismatch detected: found {}, expected {}. Proceed with caution".format(svt, schema_version))
            console.warning("Schema minor mismatch detected: found {}, expected {}. Proceed with caution".format(svt, schema_version))
        elif sv.schema_minor < schema_version[1]:
            db_shortcuts.upgrade_schema()

        if sv.schema_patch > schema_version[2]:
            logger.info("Schema patch mismatch detected: found {}, expected {}. Proceed with caution".format(svt, schema_version))
            console.info("Schema patch mismatch detected: found {}, expected {}. Proceed with caution".format(svt, schema_version)) 
        elif sv.schema_patch < schema_version[2]:
            db_shortcuts.upgrade_schema()
    logger.info("Schema validation successful! {}".format(schema_version))

class db_shortcuts:

    @staticmethod
    def upgrade_schema():
        raise NotImplemented("I don't know who you are or how you reached this code, but this should NOT have happened.  Please report it to the developer with due haste.")

    @staticmethod
    def return_rows(query):
        rows = []

        try:
            if query.count() > 0:
                for s in query:
                    rows.append(model_to_dict(s))
        except Exception as e:
            logger.warning("Database Error: {}".format(e))
            pass

        return rows

    @staticmethod
    def get_server_data_by_id(server_id):
        query = Servers.select().where(Servers.server_id == server_id).limit(1)
        try:
            return db_helper.return_rows(query)[0]
        except IndexError:
            return {}

    @staticmethod
    def get_all_defined_servers():
        query = Servers.select()
        return db_helper.return_rows(query)
        
    @staticmethod
    def get_authorized_servers(userId):
        userServers = User_Servers.select().where(User_Servers.user_id == userId)
        server_data = []

        for u in userServers:
            server_data.append(db_helper.get_server_data_by_id(u.server_id))

        return server_data
        
    @staticmethod
    def get_authorized_servers_from_roles(userId):
        userRoles = User_Roles.select().where(User_Roles.user_id == userId)
        roles_list = []
        roleServer = []
        server_data = []

        for u in userRoles:
            roles_list.append(db_helper.get_role(u.role_id))
            
        for r in roles_list:
            role_test = Role_Servers.select().where(Role_Servers.role_id == r.get('role_id'))
            for t in role_test:
                roleServer.append(t)

        for s in roleServer:
            server_data.append(db_helper.get_server_data_by_id(s.server_id))

        return server_data

    @staticmethod
    def get_all_servers_stats():
        servers = db_helper.get_all_defined_servers()
        server_data = []

        for s in servers:
            latest = Server_Stats.select().where(Server_Stats.server_id == s.get('server_id')).order_by(Server_Stats.created.desc()).limit(1)
            server_data.append({'server_data': s, "stats": db_helper.return_rows(latest)[0]})
        return server_data

    @staticmethod
    def get_authorized_servers_stats(userId):
        userServers = User_Servers.select().where(User_Servers.user_id == userId)
        authorizedServers = []
        server_data = []

        for u in userServers:
            authorizedServers.append(db_helper.get_server_data_by_id(u.server_id))

        for s in authorizedServers:
            latest = Server_Stats.select().where(Server_Stats.server_id == s.get('server_id')).order_by(Server_Stats.created.desc()).limit(1)
            server_data.append({'server_data': s, "stats": db_helper.return_rows(latest)})
        return server_data

        
    @staticmethod
    def get_authorized_servers_stats_from_roles(userId):
        userRoles = User_Roles.select().where(User_Roles.user_id == userId)
        roles_list = []
        roleServer = []
        authorizedServers = []
        server_data = []

        for u in userRoles:
            roles_list.append(db_helper.get_role(u.role_id))
            
        for r in roles_list:
            role_test = Role_Servers.select().where(Role_Servers.role_id == r.get('role_id'))
            for t in role_test:
                roleServer.append(t)

        for s in roleServer:
            authorizedServers.append(db_helper.get_server_data_by_id(s.server_id))

        for s in authorizedServers:
            latest = Server_Stats.select().where(Server_Stats.server_id == s.get('server_id')).order_by(Server_Stats.created.desc()).limit(1)
            server_data.append({'server_data': s, "stats": db_helper.return_rows(latest)[0]})
        return server_data

    @staticmethod
    def get_server_stats_by_id(server_id):
        stats = Server_Stats.select().where(Server_Stats.server_id == server_id).order_by(Server_Stats.created.desc()).limit(1)
        return db_helper.return_rows(stats)[0]

    @staticmethod
    def server_id_exists(server_id):
        if not db_helper.get_server_data_by_id(server_id):
            return False
        return True
        
    @staticmethod
    def server_id_authorized(serverId, userId):
        userServer = User_Servers.select().where(User_Servers.server_id == serverId)
        authorized = userServer.select().where(User_Servers.user_id == userId)      
        #authorized = db_helper.return_rows(authorized)

        if authorized.count() == 0:
            return False
        return True

    @staticmethod
    def server_id_authorized_from_roles(serverId, userId):
        cpt_authorized = 0
        roles_list = []
        roleServer = []
        authorized = []
        userRoles = User_Roles.select().where(User_Roles.user_id == userId)
        
        for u in userRoles:
            roles_list.append(db_helper.get_role(u.role_id))
            
        for r in roles_list:
            role_test = Role_Servers.select().where(Role_Servers.role_id == r.get('role_id'))

        for s in role_test:
            if s.server_id.server_id == serverId:
                cpt_authorized += 1

        if cpt_authorized == 0:
            return False
        return True

    @staticmethod
    def get_latest_hosts_stats():
        query = Host_Stats.select().order_by(Host_Stats.id.desc()).get()
        return model_to_dict(query)

    @staticmethod
    def new_api_token():
        while True:
            token = helper.random_string_generator(32)
            test = list(Users.select(Users.user_id).where(Users.api_token == token))
            if len(test) == 0:
                return token

    @staticmethod
    def get_all_users():
        query = Users.select()
        return query

    @staticmethod
    def get_all_roles():
        query = Roles.select()
        return query

    @staticmethod
    def get_userid_by_name(username):
        if username == "SYSTEM":
            return 0
        try:
            return (Users.get(Users.username == username)).user_id
        except DoesNotExist:
            return None

    @staticmethod
    def get_user(user_id):
        if user_id == 0:
            return {
                user_id: 0,
                created: None,
                last_login: None,
                last_update: None,
                last_ip: "127.27.23.89",
                username: "SYSTEM",
                password: None,
                enabled: True,
                superuser: False,
                api_token: None,
                roles: [],
                servers: []
            }
        user = model_to_dict(Users.get(Users.user_id == user_id))

        if user:
            roles_query = User_Roles.select().join(Roles, JOIN.INNER).where(User_Roles.user_id == user_id)
            # TODO: this query needs to be narrower
            roles = set()
            for r in roles_query:
                roles.add(r.role_id.role_id)
            #servers_query = User_Servers.select().join(Servers, JOIN.INNER).where(User_Servers.user_id == user_id)
            ## TODO: this query needs to be narrower
            servers = set()
            #for s in servers_query:
            #    servers.add(s.server_id.server_id)
            user['roles'] = roles
            #user['servers'] = servers
            #logger.debug("user: ({}) {}".format(user_id, user))
            return user
        else:
            #logger.debug("user: ({}) {}".format(user_id, {}))
            return {}

    @staticmethod
    def update_user(user_id, user_data={}):
        base_data = db_helper.get_user(user_id)
        up_data = {}
        added_roles = set()
        removed_roles = set()
        added_servers = set()
        removed_servers = set()
        for key in user_data:
            if key == "user_id":
                continue
            elif key == "roles":
                added_roles = user_data['roles'].difference(base_data['roles'])
                removed_roles = base_data['roles'].difference(user_data['roles'])
            #elif key == "servers":
            #    added_servers = user_data['servers'].difference(base_data['servers'])
            #    removed_servers = base_data['servers'].difference(user_data['servers'])
            elif key == "regen_api":
                if user_data['regen_api']:
                    up_data['api_token'] = db_shortcuts.new_api_token()
            elif key == "password":
                if user_data['password'] is not None and user_data['password'] != "":
                    up_data['password'] = helper.encode_pass(user_data['password'])
            elif base_data[key] != user_data[key]:
                up_data[key] = user_data[key]
        up_data['last_update'] = helper.get_time_as_string()
        logger.debug("user: {} +role:{} -role:{} +server:{} -server{}".format(user_data, added_roles, removed_roles, added_servers, removed_servers))
        with database.atomic():
            for role in added_roles:
                User_Roles.get_or_create(user_id=user_id, role_id=role)
                # TODO: This is horribly inefficient and we should be using bulk queries but im going for functionality at this point
            User_Roles.delete().where(User_Roles.user_id == user_id).where(User_Roles.role_id.in_(removed_roles)).execute()

            #for server in added_servers:
            #    User_Servers.get_or_create(user_id=user_id, server_id=server)
            #    # TODO: This is horribly inefficient and we should be using bulk queries but im going for functionality at this point
            #User_Servers.delete().where(User_Servers.user_id == user_id).where(User_Servers.server_id.in_(removed_servers)).execute()
            if up_data:
                Users.update(up_data).where(Users.user_id == user_id).execute()

    @staticmethod
    def add_user(username, password=None, api_token=None, enabled=True, superuser=False):
        if password is not None:
            pw_enc = helper.encode_pass(password)
        else:
            pw_enc = None
        if api_token is None:
            api_token = db_shortcuts.new_api_token()
        else:
            if type(api_token) is not str and len(api_token) != 32:
                raise ValueError("API token must be a 32 character string")
        user_id = Users.insert({
            Users.username: username.lower(),
            Users.password: pw_enc,
            Users.api_token: api_token,
            Users.enabled: enabled,
            Users.superuser: superuser,
            Users.created: helper.get_time_as_string()
        }).execute()
        return user_id

    @staticmethod
    def remove_user(user_id):
        with database.atomic():
            User_Roles.delete().where(User_Servers.user_id == user_id).execute()
            user = Users.get(Users.user_id == user_id)
            return user.delete_instance()

    @staticmethod
    def user_id_exists(user_id):
        if not db_shortcuts.get_user(user_id):
            return False
        return True

    @staticmethod
    def get_roleid_by_name(role_name):
        try:
            return (Roles.get(Roles.role_name == role_name)).role_id
        except DoesNotExist:
            return None

    @staticmethod
    def get_role(role_id):
        role = model_to_dict(Roles.get(Roles.role_id == role_id))

        if role:
            servers_query = Role_Servers.select().join(Servers, JOIN.INNER).where(Role_Servers.role_id == role_id)
            # TODO: this query needs to be narrower
            servers = set()
            for s in servers_query:
                servers.add(s.server_id.server_id)
            role['servers'] = servers
            #logger.debug("role: ({}) {}".format(role_id, role))
            return role
        else:
            #logger.debug("role: ({}) {}".format(role_id, {}))
            return {}

    @staticmethod
    def update_role(role_id, role_data={}):
        base_data = db_helper.get_role(role_id)
        up_data = {}
        added_servers = set()
        removed_servers = set()
        for key in role_data:
            if key == "role_id":
                continue
            elif key == "servers":
                added_servers = role_data['servers'].difference(base_data['servers'])
                removed_servers = base_data['servers'].difference(role_data['servers'])
            elif base_data[key] != role_data[key]:
                up_data[key] = role_data[key]
        up_data['last_update'] = helper.get_time_as_string()
        logger.debug("role: {} +server:{} -server{}".format(role_data, added_servers, removed_servers))
        with database.atomic():
            for server in added_servers:
                Role_Servers.get_or_create(role_id=role_id, server_id=server)
                # TODO: This is horribly inefficient and we should be using bulk queries but im going for functionality at this point
            Role_Servers.delete().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id.in_(removed_servers)).execute()
            if up_data:
                Roles.update(up_data).where(Roles.role_id == role_id).execute()

    @staticmethod
    def add_role(role_name):
        role_id = Roles.insert({
            Roles.role_name: role_name.lower(),
            Roles.created: helper.get_time_as_string()
        }).execute()
        return role_id

    @staticmethod
    def remove_role(role_id):
        Role_Servers.delete().where(Role_Servers.role_id == role_id).execute()
        role = Roles.get(Roles.role_id == role_id)
        return role.delete_instance()

    @staticmethod
    def role_id_exists(role_id):
        if not db_shortcuts.get_role(role_id):
            return False
        return True

    @staticmethod
    def get_unactioned_commands():
        query = Commands.select().where(Commands.executed == 0)
        return db_helper.return_rows(query)

    @staticmethod
    def get_server_friendly_name(server_id):
        server_data = db_helper.get_server_data_by_id(server_id)
        friendly_name = "{} with ID: {}".format(server_data.get('server_name', None), server_data.get('server_id', 0))
        return friendly_name

    @staticmethod
    def send_command(user_id, server_id, remote_ip, command):

        server_name = db_helper.get_server_friendly_name(server_id)

        # Example: Admin issued command start_server for server Survival
        db_helper.add_to_audit_log(user_id, "issued command {} for server {}".format(command, server_name),
                              server_id, remote_ip)

        Commands.insert({
            Commands.server_id: server_id,
            Commands.user: user_id,
            Commands.source_ip: remote_ip,
            Commands.command: command
        }).execute()

    @staticmethod
    def get_actity_log():
        q = Audit_Log.select()
        return db_helper.return_db_rows(q)

    @staticmethod
    def return_db_rows(model):
        data = [model_to_dict(row) for row in model]
        return data

    @staticmethod
    def mark_command_complete(command_id=None):
        if command_id is not None:
            logger.debug("Marking Command {} completed".format(command_id))
            Commands.update({
                Commands.executed: True
            }).where(Commands.command_id == command_id).execute()

    def add_to_audit_log(self, user_id, log_msg, server_id=None, source_ip=None):
        logger.debug("Adding to audit log User:{} - Message: {} ".format(user_id, log_msg))
        user_data = self.get_user(user_id)

        audit_msg = "{} {}".format(str(user_data['username']).capitalize(), log_msg)

        websocket_helper.broadcast('notification', audit_msg)

        Audit_Log.insert({
            Audit_Log.user_name: user_data['username'],
            Audit_Log.user_id: user_id,
            Audit_Log.server_id: server_id,
            Audit_Log.log_msg: audit_msg,
            Audit_Log.source_ip: source_ip
        }).execute()
    
    @staticmethod
    def add_to_audit_log_raw(user_name, user_id, server_id, log_msg, source_ip):
        Audit_Log.insert({
            Audit_Log.user_name: user_name,
            Audit_Log.user_id: user_id,
            Audit_Log.server_id: server_id,
            Audit_Log.log_msg: log_msg,
            Audit_Log.source_ip: source_ip
        }).execute()

    @staticmethod
    def create_scheduled_task(server_id, action, interval, interval_type, start_time, command, comment=None, enabled=True):
        sch_id = Schedules.insert({
            Schedules.server_id: server_id,
            Schedules.action: action,
            Schedules.enabled: enabled,
            Schedules.interval: interval,
            Schedules.interval_type: interval_type,
            Schedules.start_time: start_time,
            Schedules.command: command,
            Schedules.comment: comment
        }).execute()
        return sch_id

    @staticmethod
    def delete_scheduled_task(schedule_id):
        sch = Schedules.get(Schedules.schedule_id == schedule_id)
        return Schedules.delete_instance(sch)

    @staticmethod
    def update_scheduled_task(schedule_id, updates):
        Schedules.update(updates).where(Schedules.schedule_id == schedule_id).execute()

    @staticmethod
    def get_scheduled_task(schedule_id):
        return model_to_dict(Schedules.get(Schedules.schedule_id == schedule_id)).execute()

    @staticmethod
    def get_schedules_by_server(server_id):
        return Schedules.select().where(Schedules.server_id == server_id).execute()

    @staticmethod
    def get_schedules_all():
        return Schedules.select().execute()

    @staticmethod
    def get_schedules_enabled():
        return Schedules.select().where(Schedules.enabled == True).execute()

    @staticmethod
    def get_backup_config(server_id):
        try:
            row = Backups.select().where(Backups.server_id == server_id).join(Schedules).join(Servers)[0]
            conf = {
                "backup_path": row.server_id.backup_path,
                "directories": row.directories,
                "max_backups": row.max_backups,
                "auto_enabled": row.schedule_id.enabled,
                "server_id": row.server_id.server_id
            }
        except IndexError:
            conf = {
                "backup_path": None,
                "directories": None,
                "max_backups": 0,
                "auto_enabled": True,
                "server_id": server_id
            }
        return conf

    @staticmethod
    def set_backup_config(server_id: int, backup_path: str = None, max_backups: int = None, auto_enabled: bool = True):
        logger.debug("Updating server {} backup config with {}".format(server_id, locals()))
        try:
            row = Backups.select().where(Backups.server_id == server_id).join(Schedules).join(Servers)[0]
            new_row = False
            conf = {}
            schd = {}
        except IndexError:
            conf = {
                "directories": None,
                "max_backups": 0,
                "server_id":   server_id
            }
            schd = {
                "enabled":    True,
                "action":     "backup_server",
                "interval_type": "days",
                "interval":   1,
                "start_time": "00:00",
                "server_id":  server_id,
                "comment":    "Default backup job"
            }
            new_row = True
        if max_backups is not None:
            conf['max_backups'] = max_backups
        schd['enabled'] = bool(auto_enabled)
        if not new_row:
            with database.atomic():
                if backup_path is not None:
                    u1 = Servers.update(backup_path=backup_path).where(Servers.server_id == server_id).execute()
                else:
                    u1 = 0
                u2 = Backups.update(conf).where(Backups.server_id == server_id).execute()
                u3 = Schedules.update(schd).where(Schedules.schedule_id == row.schedule_id).execute()
            logger.debug("Updating existing backup record.  {}+{}+{} rows affected".format(u1, u2, u3))
        else:
            with database.atomic():
                conf["server_id"] = server_id
                if backup_path is not None:
                    u = Servers.update(backup_path=backup_path).where(Servers.server_id == server_id)
                s = Schedules.create(**schd)
                conf['schedule_id'] = s.schedule_id
                b = Backups.create(**conf)
            logger.debug("Creating new backup record.")

installer = db_builder()
db_helper = db_shortcuts()