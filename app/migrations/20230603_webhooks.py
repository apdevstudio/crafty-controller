# Generated by database migrator
import peewee


def migrate(migrator, database, **kwargs):
    migrator.drop_columns("webhooks", ["name", "method", "url", "event", "send_data"])
    migrator.add_columns(
        "webhooks",
        server_id=peewee.IntegerField(null=True),
        webhook_type=peewee.CharField(default="Custom"),
        name=peewee.CharField(default="Custom Webhook", max_length=64),
        url=peewee.CharField(default=""),
        bot_name=peewee.CharField(default="Crafty Controller"),
        trigger=peewee.CharField(default="server_start,server_stop"),
        body=peewee.CharField(default=""),
        color=peewee.CharField(default=""),
        enabled=peewee.BooleanField(default=True),
    )
    """
    Write your migrations here.
    """


def rollback(migrator, database, **kwargs):
    """
    Write your rollback migrations here.
    """