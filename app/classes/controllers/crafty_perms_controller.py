import logging

from app.classes.models.crafty_permissions import (
    PermissionsCrafty,
    EnumPermissionsCrafty,
)
from app.classes.models.users import ApiKeys

logger = logging.getLogger(__name__)


class CraftyPermsController:
    @staticmethod
    def list_defined_crafty_permissions():
        permissions_list = PermissionsCrafty.get_permissions_list()
        return permissions_list

    @staticmethod
    def get_mask_crafty_permissions(user_id):
        permissions_mask = PermissionsCrafty.get_crafty_permissions_mask(user_id)
        return permissions_mask

    @staticmethod
    def set_permission(
        permission_mask, permission_tested: EnumPermissionsCrafty, value
    ):
        return PermissionsCrafty.set_permission(
            permission_mask, permission_tested, value
        )

    @staticmethod
    def can_create_server(user_id):
        return PermissionsCrafty.can_add_in_crafty(
            user_id, EnumPermissionsCrafty.SERVER_CREATION
        )

    @staticmethod
    def can_add_user(user_id):
        return PermissionsCrafty.can_add_in_crafty(
            user_id, EnumPermissionsCrafty.USER_CONFIG
        )

    @staticmethod
    def can_add_role(user_id):
        return PermissionsCrafty.can_add_in_crafty(
            user_id, EnumPermissionsCrafty.ROLES_CONFIG
        )

    @staticmethod
    def list_all_crafty_permissions_quantity_limits():
        return PermissionsCrafty.get_all_permission_quantity_list()

    @staticmethod
    def list_crafty_permissions_quantity_limits(user_id):
        return PermissionsCrafty.get_permission_quantity_list(user_id)

    @staticmethod
    def get_crafty_permissions_list(user_id):
        permissions_mask = PermissionsCrafty.get_crafty_permissions_mask(user_id)
        permissions_list = PermissionsCrafty.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def get_api_key_permissions_list(key: ApiKeys):
        return PermissionsCrafty.get_api_key_permissions_list(key)
