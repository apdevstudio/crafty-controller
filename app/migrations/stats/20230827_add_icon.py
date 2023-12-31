# Generated by database migrator
import peewee


def migrate(migrator, database, **kwargs):
    migrator.add_columns("server_stats", icon=peewee.CharField(null=True))
    """
    Write your migrations here.
    """


def rollback(migrator, database, **kwargs):
    migrator.drop_columns("server_stats", ["icon"])
    """
    Write your rollback migrations here.
    """
