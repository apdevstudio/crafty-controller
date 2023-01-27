# Generated by database migrator
import peewee


def migrate(migrator, database, **kwargs):
    migrator.add_columns("backups", before=peewee.CharField(default=""))
    migrator.add_columns("backups", after=peewee.CharField(default=""))
    """
    Write your migrations here.
    """


def rollback(migrator, database, **kwargs):
    migrator.drop_columns("backups", ["before"])
    migrator.drop_columns("backups", ["after"])
    """
    Write your rollback migrations here.
    """
