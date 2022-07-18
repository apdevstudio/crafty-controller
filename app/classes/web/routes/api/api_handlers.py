from app.classes.web.routes.api.index_handler import ApiIndexHandler
from app.classes.web.routes.api.jsonschema import (
    ApiJsonSchemaHandler,
    ApiJsonSchemaListHandler,
)
from app.classes.web.routes.api.not_found import ApiNotFoundHandler
from app.classes.web.routes.api.auth.invalidate_tokens import (
    ApiAuthInvalidateTokensHandler,
)
from app.classes.web.routes.api.auth.login import ApiAuthLoginHandler
from app.classes.web.routes.api.roles.index import ApiRolesIndexHandler
from app.classes.web.routes.api.roles.role.index import ApiRolesRoleIndexHandler
from app.classes.web.routes.api.roles.role.servers import ApiRolesRoleServersHandler
from app.classes.web.routes.api.roles.role.users import ApiRolesRoleUsersHandler
from app.classes.web.routes.api.servers.index import ApiServersIndexHandler
from app.classes.web.routes.api.servers.server.action import (
    ApiServersServerActionHandler,
)
from app.classes.web.routes.api.servers.server.index import ApiServersServerIndexHandler
from app.classes.web.routes.api.servers.server.logs import ApiServersServerLogsHandler
from app.classes.web.routes.api.servers.server.public import (
    ApiServersServerPublicHandler,
)
from app.classes.web.routes.api.servers.server.stats import ApiServersServerStatsHandler
from app.classes.web.routes.api.servers.server.stdin import ApiServersServerStdinHandler
from app.classes.web.routes.api.servers.server.tasks.index import (
    ApiServersServerTasksIndexHandler,
)
from app.classes.web.routes.api.servers.server.tasks.task.children import (
    ApiServersServerTasksTaskChildrenHandler,
)
from app.classes.web.routes.api.servers.server.tasks.task.index import (
    ApiServersServerTasksTaskIndexHandler,
)
from app.classes.web.routes.api.servers.server.users import ApiServersServerUsersHandler
from app.classes.web.routes.api.users.index import ApiUsersIndexHandler
from app.classes.web.routes.api.users.user.index import ApiUsersUserIndexHandler
from app.classes.web.routes.api.users.user.permissions import (
    ApiUsersUserPermissionsHandler,
)
from app.classes.web.routes.api.users.user.pfp import ApiUsersUserPfpHandler
from app.classes.web.routes.api.users.user.public import ApiUsersUserPublicHandler


def api_handlers(handler_args):
    return [
        # Auth routes
        (
            r"/api/v2/auth/login/?",
            ApiAuthLoginHandler,
            handler_args,
        ),
        (
            r"/api/v2/auth/invalidate_tokens/?",
            ApiAuthInvalidateTokensHandler,
            handler_args,
        ),
        # User routes
        (
            r"/api/v2/users/?",
            ApiUsersIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/users/([0-9]+)/?",
            ApiUsersUserIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/users/(@me)/?",
            ApiUsersUserIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/users/([0-9]+)/permissions/?",
            ApiUsersUserPermissionsHandler,
            handler_args,
        ),
        (
            r"/api/v2/users/(@me)/permissions/?",
            ApiUsersUserPermissionsHandler,
            handler_args,
        ),
        (
            r"/api/v2/users/([0-9]+)/pfp/?",
            ApiUsersUserPfpHandler,
            handler_args,
        ),
        (
            r"/api/v2/users/(@me)/pfp/?",
            ApiUsersUserPfpHandler,
            handler_args,
        ),
        (
            r"/api/v2/users/([0-9]+)/public/?",
            ApiUsersUserPublicHandler,
            handler_args,
        ),
        (
            r"/api/v2/users/(@me)/public/?",
            ApiUsersUserPublicHandler,
            handler_args,
        ),
        # Server routes
        (
            r"/api/v2/servers/?",
            ApiServersIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/?",
            ApiServersServerIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/tasks/?",
            ApiServersServerTasksIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/tasks/([0-9]+)/?",
            ApiServersServerTasksTaskIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/tasks/([0-9]+)/children/?",
            ApiServersServerTasksTaskChildrenHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/stats/?",
            ApiServersServerStatsHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/action/([a-z_]+)/?",
            ApiServersServerActionHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/logs/?",
            ApiServersServerLogsHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/users/?",
            ApiServersServerUsersHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/public/?",
            ApiServersServerPublicHandler,
            handler_args,
        ),
        (
            r"/api/v2/servers/([0-9]+)/stdin/?",
            ApiServersServerStdinHandler,
            handler_args,
        ),
        (
            r"/api/v2/roles/?",
            ApiRolesIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/roles/([0-9]+)/?",
            ApiRolesRoleIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/roles/([0-9]+)/servers/?",
            ApiRolesRoleServersHandler,
            handler_args,
        ),
        (
            r"/api/v2/roles/([0-9]+)/users/?",
            ApiRolesRoleUsersHandler,
            handler_args,
        ),
        (
            r"/api/v2/jsonschema/?",
            ApiJsonSchemaListHandler,
            handler_args,
        ),
        (
            r"/api/v2/jsonschema/([a-z0-9_]+)/?",
            ApiJsonSchemaHandler,
            handler_args,
        ),
        (
            r"/api/v2/?",
            ApiIndexHandler,
            handler_args,
        ),
        (
            r"/api/v2/(.*)",
            ApiNotFoundHandler,
            handler_args,
        ),
    ]
