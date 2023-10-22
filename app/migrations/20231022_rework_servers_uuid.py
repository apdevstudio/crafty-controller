import peewee
from app.classes.shared.migration import Migrator

from app.classes.models.servers import Servers
from app.classes.models.users import Users

from app.classes.shared.helpers import Helpers


def migrate(migrator: Migrator, database, **kwargs):
    # Changes on Server Table
    migrator.drop_columns("servers", "server_id")
    migrator.drop_columns("servers", "server_uuid")
    migrator.add_columns(
        "servers",
        server_uuid=peewee.UUIDField(
            primary_key=True, unique=True, default=Helpers.create_uuid()
        ),
    )
    migrator.drop_columns("servers", "created_by")
    migrator.add_columns(
        "servers",
        created_by=peewee.ForeignKeyField(Users, backref="creator_server", null=True),
    )

    # Changes on Audit Log Table
    migrator.drop_columns("audit_log", "server_id")
    migrator.add_columns(
        "audit_log",
        server_uuid=peewee.ForeignKeyField(Servers, backref="audit_server", null=True),
    )

    # Changes on Webhook Table
    migrator.drop_columns("webhooks", "server_id")
    migrator.add_columns(
        "webhooks",
        server_uuid=peewee.ForeignKeyField(
            Servers, backref="webhook_server", null=True
        ),
    )

    # Changes on Schedules Table
    migrator.rename_column("schedules", "server_id", "server_uuid")

    # Changes on Backups Table
    migrator.rename_column("backups", "server_id", "server_uuid")

    # Changes on RoleServers Table
    migrator.rename_column("role_servers", "server_id", "server_uuid")

    # Changes on ServerStats Table
    migrator.rename_column("server_stats", "server_id", "server_uuid")

    """
    Write your migrations here.
    """


def rollback(migrator: Migrator, database, **kwargs):
    # Changes on Server Table
    migrator.add_columns("servers", "server_id", peewee.AutoField)
    migrator.drop_columns("servers", "server_uuid")
    migrator.add_columns(
        "servers", server_uuid=peewee.CharField(default="", index=True)
    )
    migrator.drop_columns("servers", "created_by")
    migrator.add_columns("servers", created_by=peewee.IntegerField(default=-100))

    # Changes on Audit Log Table
    migrator.drop_columns("audit_log", "server_uuid")
    migrator.add_columns(
        "audit_log", server_id=peewee.IntegerField(default=None, index=True)
    )

    # Changes on Webhook Table
    migrator.drop_columns("webhooks", "server_uuid")
    migrator.add_columns(
        "webhooks",
        server_id=peewee.IntegerField(null=True),
    )

    # Changes on Schedules Table
    migrator.rename_column("schedules", "server_uuid", "server_id")

    # Changes on Backups Table
    migrator.rename_column("backups", "server_uuid", "server_id")

    # Changes on RoleServers Table
    migrator.rename_column("role_servers", "server_uuid", "server_id")

    # Changes on ServerStats Table
    migrator.rename_column("server_stats", "server_uuid", "server_id")

    """
    Write your rollback migrations here.
    """
