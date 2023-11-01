import datetime
import uuid
import peewee

from app.classes.shared.migration import Migrator
from app.classes.models.management import AuditLog
from app.classes.models.management import Webhooks


def migrate(migrator: Migrator, database, **kwargs):
    """
    Write your migrations here.
    """
    db = database

    # **********************************************************************************
    #          Servers New Model from Old (easier to migrate without dunmping Database)
    # **********************************************************************************
    class Servers(peewee.Model):
        server_id = peewee.CharField(primary_key=True, default=str(uuid.uuid4()))
        created = peewee.DateTimeField(default=datetime.datetime.now)
        server_uuid = peewee.CharField(default="", index=True)
        server_name = peewee.CharField(default="Server", index=True)
        path = peewee.CharField(default="")
        backup_path = peewee.CharField(default="")
        executable = peewee.CharField(default="")
        log_path = peewee.CharField(default="")
        execution_command = peewee.CharField(default="")
        auto_start = peewee.BooleanField(default=0)
        auto_start_delay = peewee.IntegerField(default=10)
        crash_detection = peewee.BooleanField(default=0)
        stop_command = peewee.CharField(default="stop")
        executable_update_url = peewee.CharField(default="")
        server_ip = peewee.CharField(default="127.0.0.1")
        server_port = peewee.IntegerField(default=25565)
        logs_delete_after = peewee.IntegerField(default=0)
        type = peewee.CharField(default="minecraft-java")
        show_status = peewee.BooleanField(default=1)
        created_by = peewee.IntegerField(default=-100)
        shutdown_timeout = peewee.IntegerField(default=60)
        ignored_exits = peewee.CharField(default="0")

        class Meta:
            table_name = "servers"
            database = db

    # Changes on Server Table
    migrator.alter_column_type(
        Servers,
        "server_id",
        peewee.CharField(primary_key=True, default=str(uuid.uuid4())),
    )

    # Changes on Audit Log Table
    migrator.alter_column_type(
        AuditLog,
        "server_id",
        peewee.ForeignKeyField(
            Servers,
            backref="audit_server",
            null=True,
            field=peewee.CharField(primary_key=True, default=str(uuid.uuid4())),
        ),
    )
    # Changes on Webhook Table
    migrator.alter_column_type(
        Webhooks,
        "server_id",
        peewee.ForeignKeyField(
            Servers,
            backref="webhook_server",
            null=True,
            field=peewee.CharField(primary_key=True, default=str(uuid.uuid4())),
        ),
    )


def rollback(migrator: Migrator, database, **kwargs):
    """
    Write your rollback migrations here.
    """
    db = database

    # Changes on Server Table
    migrator.alter_column_type(
        "servers",
        "server_id",
        peewee.AutoField(),
    )

    # Changes on Audit Log Table
    migrator.alter_column_type(
        AuditLog,
        "server_id",
        peewee.IntegerField(default=None, index=True),
    )

    # Changes on Webhook Table
    migrator.alter_column_type(
        Webhooks,
        "server_id",
        peewee.IntegerField(null=True),
    )
