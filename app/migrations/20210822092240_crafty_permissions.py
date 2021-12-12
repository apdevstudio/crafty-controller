# Generated by database migrator
from peewee import *
from app.classes.models.users import Users

def migrate(migrator, database, **kwargs):
    db = database
    class User_Crafty(Model):
        user_id = ForeignKeyField(Users, backref='users_crafty')
        permissions = CharField(default="00000000")
        limit_server_creation = IntegerField(default=-1)

        class Meta:
            table_name = 'user_crafty'
            database = db
    migrator.create_table(User_Crafty)
    """
    Write your migrations here.
    """



def rollback(migrator, database, **kwargs):    
    migrator.drop_table('user_crafty') # Can be model class OR table name

    """
    Write your rollback migrations here.
    """