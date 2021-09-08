import os
import time
import logging
import sys
import yaml
import asyncio
import shutil
import tempfile
import zipfile
from distutils import dir_util

from app.classes.shared.helpers import helper
from app.classes.shared.console import console

from app.classes.shared.main_models import db_helper
from app.classes.models.server_permissions import  server_permissions, Enum_Permissions_Server
from app.classes.models.users import users_helper
from app.classes.models.roles import roles_helper
from app.classes.models.servers import servers_helper

from app.classes.shared.server import Server
from app.classes.minecraft.server_props import ServerProps
from app.classes.minecraft.serverjars import server_jar_obj
from app.classes.minecraft.stats import Stats

logger = logging.getLogger(__name__)

class Server_Perms_Controller:

    @staticmethod
    def list_defined_permissions():
        permissions_list = server_permissions.get_permissions_list()
        return permissions_list
        
    @staticmethod
    def get_mask_permissions(role_id, server_id):
        permissions_mask = server_permissions.get_permissions_mask(role_id, server_id)
        return permissions_mask
        
    @staticmethod
    def get_role_permissions(role_id):
        permissions_list = server_permissions.get_role_permissions_list(role_id)
        return permissions_list

    @staticmethod
    def get_server_permissions_foruser(user_id, server_id):
        permissions_list = server_permissions.get_user_permissions_list(user_id, server_id)
        return permissions_list        

    #************************************************************************************************
    #                                   Servers Permissions Methods
    #************************************************************************************************
    @staticmethod
    def get_permissions_mask(role_id, server_id):
        return server_permissions.get_permissions_mask(role_id, server_id)
        
    @staticmethod
    def set_permission(permission_mask, permission_tested: Enum_Permissions_Server, value):
        return server_permissions.set_permission(permission_mask, permission_tested, value)

    @staticmethod
    def get_role_permissions_list(role_id):
        return server_permissions.get_role_permissions_list(role_id)

    @staticmethod
    def get_user_permissions_list(user_id, server_id):
        return get_user_permissions_list(user_id, server_id)

    @staticmethod
    def get_authorized_servers_stats_from_roles(user_id):
        user_roles = users_helper.get_user_roles_id(user_id)
        roles_list = []
        role_server = []
        authorized_servers = []
        server_data = []

        for u in user_roles:
            roles_list.append(roles_helper.get_role(u.role_id))

        for r in roles_list:
            role_test = server_permissions.get_role_servers_from_role_id(r.get('role_id'))
            for t in role_test:
                role_server.append(t)

        for s in role_server:
            authorized_servers.append(servers_helper.get_server_data_by_id(s.server_id))

        for s in authorized_servers:
            latest = servers_helper.get_latest_server_stats(s.get('server_id'))
            server_data.append({'server_data': s, "stats": db_helper.return_rows(latest)[0]})
        return server_data
