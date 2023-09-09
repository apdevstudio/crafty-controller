import logging

from jsonschema import ValidationError, validate
import orjson
from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)

new_server_schema = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Root",
    "type": "object",
    "required": [
        "name",
        "monitoring_type",
        "create_type",
    ],
    "properties": {
        "name": {
            "title": "Name",
            "type": "string",
            "examples": ["My Server"],
            "minLength": 2,
        },
        "roles": {"title": "Roles to add", "type": "array", "examples": [1, 2, 3]},
        "stop_command": {
            "title": "Stop command",
            "description": '"" means the default for the server creation type.',
            "type": "string",
            "default": "",
            "examples": ["stop", "end"],
        },
        "log_location": {
            "title": "Log file",
            "description": '"" means the default for the server creation type.',
            "type": "string",
            "default": "",
            "examples": ["./logs/latest.log", "./proxy.log.0"],
        },
        "crashdetection": {
            "title": "Crash detection",
            "type": "boolean",
            "default": False,
        },
        "autostart": {
            "title": "Autostart",
            "description": "If true, the server will be started"
            + " automatically when Crafty is launched.",
            "type": "boolean",
            "default": False,
        },
        "autostart_delay": {
            "title": "Autostart delay",
            "description": "Delay in seconds before autostarting. (If enabled)",
            "type": "number",
            "default": 10,
            "minimum": 0,
        },
        "monitoring_type": {
            "title": "Server monitoring type",
            "type": "string",
            "default": "minecraft_java",
            "enum": ["minecraft_java", "minecraft_bedrock", "steam_cmd", "none"],
            # TODO: SteamCMD, RakNet, etc.
        },
        "minecraft_java_monitoring_data": {
            "title": "Minecraft Java monitoring data",
            "type": "object",
            "required": ["host", "port"],
            "properties": {
                "host": {
                    "title": "Host",
                    "type": "string",
                    "default": "127.0.0.1",
                    "examples": ["127.0.0.1"],
                    "minLength": 1,
                },
                "port": {
                    "title": "Port",
                    "type": "integer",
                    "examples": [25565],
                    "default": 25565,
                    "minimum": 0,
                },
            },
        },
        "minecraft_bedrock_monitoring_data": {
            "title": "Minecraft Bedrock monitoring data",
            "type": "object",
            "required": ["host", "port"],
            "properties": {
                "host": {
                    "title": "Host",
                    "type": "string",
                    "default": "127.0.0.1",
                    "examples": ["127.0.0.1"],
                    "minLength": 1,
                },
                "port": {
                    "title": "Port",
                    "type": "integer",
                    "examples": [19132],
                    "default": 19132,
                    "minimum": 0,
                },
            },
        },
        "create_type": {
            # This is only used for creation, this is not saved in the db
            "title": "Server creation type",
            "type": "string",
            "default": "minecraft_java",
            "enum": ["minecraft_java", "minecraft_bedrock", "steam_cmd", "custom"],
        },
        "minecraft_java_create_data": {
            "title": "Java creation data",
            "type": "object",
            "required": ["create_type"],
            "properties": {
                "create_type": {
                    "title": "Creation type",
                    "type": "string",
                    "default": "download_jar",
                    "enum": ["download_jar", "import_server", "import_zip"],
                },
                "download_jar_create_data": {
                    "title": "JAR download data",
                    "type": "object",
                    "required": [
                        "type",
                        "version",
                        "mem_min",
                        "mem_max",
                        "server_properties_port",
                        "category",
                    ],
                    "category": {
                        "title": "Jar Category",
                        "type": "string",
                        "examples": ["modded", "vanilla"],
                    },
                    "properties": {
                        "type": {
                            "title": "Server JAR Type",
                            "type": "string",
                            "examples": ["Paper"],
                            "minLength": 1,
                        },
                        "version": {
                            "title": "Server JAR Version",
                            "type": "string",
                            "examples": ["1.18.2"],
                            "minLength": 1,
                        },
                        "mem_min": {
                            "title": "Minimum JVM memory (in GiBs)",
                            "type": "number",
                            "examples": [1],
                            "default": 1,
                            "exclusiveMinimum": 0,
                        },
                        "mem_max": {
                            "title": "Maximum JVM memory (in GiBs)",
                            "type": "number",
                            "examples": [2],
                            "default": 2,
                            "exclusiveMinimum": 0,
                        },
                        "server_properties_port": {
                            "title": "Port",
                            "type": "integer",
                            "examples": [25565],
                            "default": 25565,
                            "minimum": 0,
                        },
                        "agree_to_eula": {
                            "title": "Agree to the EULA",
                            "type": "boolean",
                            "default": False,
                        },
                    },
                },
                "import_server_create_data": {
                    "title": "Import server data",
                    "type": "object",
                    "required": [
                        "existing_server_path",
                        "jarfile",
                        "mem_min",
                        "mem_max",
                        "server_properties_port",
                    ],
                    "properties": {
                        "existing_server_path": {
                            "title": "Server path",
                            "description": "Absolute path to the old server",
                            "type": "string",
                            "examples": ["/var/opt/server"],
                            "minLength": 1,
                        },
                        "jarfile": {
                            "title": "JAR file",
                            "description": "The JAR file relative to the previous path",
                            "type": "string",
                            "examples": ["paper.jar", "jars/vanilla-1.12.jar"],
                            "minLength": 1,
                        },
                        "mem_min": {
                            "title": "Minimum JVM memory (in GiBs)",
                            "type": "number",
                            "examples": [1],
                            "default": 1,
                            "exclusiveMinimum": 0,
                        },
                        "mem_max": {
                            "title": "Maximum JVM memory (in GiBs)",
                            "type": "number",
                            "examples": [2],
                            "default": 2,
                            "exclusiveMinimum": 0,
                        },
                        "server_properties_port": {
                            "title": "Port",
                            "type": "integer",
                            "examples": [25565],
                            "default": 25565,
                            "minimum": 0,
                        },
                        "agree_to_eula": {
                            "title": "Agree to the EULA",
                            "type": "boolean",
                            "default": False,
                        },
                    },
                },
                "import_zip_create_data": {
                    "title": "Import ZIP server data",
                    "type": "object",
                    "required": [
                        "zip_path",
                        "zip_root",
                        "jarfile",
                        "mem_min",
                        "mem_max",
                        "server_properties_port",
                    ],
                    "properties": {
                        "zip_path": {
                            "title": "ZIP path",
                            "description": "Absolute path to the ZIP archive",
                            "type": "string",
                            "examples": ["/var/opt/server.zip"],
                            "minLength": 1,
                        },
                        "zip_root": {
                            "title": "Server root directory",
                            "description": "The server root in the ZIP archive",
                            "type": "string",
                            "examples": ["/", "/paper-server/", "server-1"],
                            "minLength": 1,
                        },
                        "jarfile": {
                            "title": "JAR file",
                            "description": "The JAR relative to the configured root",
                            "type": "string",
                            "examples": ["paper.jar", "jars/vanilla-1.12.jar"],
                            "minLength": 1,
                        },
                        "mem_min": {
                            "title": "Minimum JVM memory (in GiBs)",
                            "type": "number",
                            "examples": [1],
                            "default": 1,
                            "exclusiveMinimum": 0,
                        },
                        "mem_max": {
                            "title": "Maximum JVM memory (in GiBs)",
                            "type": "number",
                            "examples": [2],
                            "default": 2,
                            "exclusiveMinimum": 0,
                        },
                        "server_properties_port": {
                            "title": "Port",
                            "type": "integer",
                            "examples": [25565],
                            "default": 25565,
                            "minimum": 0,
                        },
                        "agree_to_eula": {
                            "title": "Agree to the EULA",
                            "type": "boolean",
                            "default": False,
                        },
                    },
                },
            },
            "allOf": [
                {
                    "$comment": "If..then section",
                    "allOf": [
                        {
                            "if": {
                                "properties": {"create_type": {"const": "download_jar"}}
                            },
                            "then": {"required": ["download_jar_create_data"]},
                        },
                        {
                            "if": {
                                "properties": {"create_type": {"const": "import_exec"}}
                            },
                            "then": {"required": ["import_server_create_data"]},
                        },
                        {
                            "if": {
                                "properties": {"create_type": {"const": "import_zip"}}
                            },
                            "then": {"required": ["import_zip_create_data"]},
                        },
                    ],
                },
                {
                    "title": "Only one creation data",
                    "oneOf": [
                        {"required": ["download_jar_create_data"]},
                        {"required": ["import_server_create_data"]},
                        {"required": ["import_zip_create_data"]},
                    ],
                },
            ],
        },
        "minecraft_bedrock_create_data": {
            "title": "Minecraft Bedrock creation data",
            "type": "object",
            "required": ["create_type"],
            "properties": {
                "create_type": {
                    "title": "Creation type",
                    "type": "string",
                    "default": "import_server",
                    "enum": ["download_exe", "import_server", "import_zip"],
                },
                "download_exe_create_data": {
                    "title": "Import server data",
                    "type": "object",
                    "required": [],
                    "properties": {
                        "agree_to_eula": {
                            "title": "Agree to the EULA",
                            "type": "boolean",
                            "enum": [True],
                        },
                    },
                },
                "import_server_create_data": {
                    "title": "Import server data",
                    "type": "object",
                    "required": ["existing_server_path", "executable"],
                    "properties": {
                        "existing_server_path": {
                            "title": "Server path",
                            "description": "Absolute path to the old server",
                            "type": "string",
                            "examples": ["/var/opt/server"],
                            "minLength": 1,
                        },
                        "executable": {
                            "title": "Executable File",
                            "description": "File Crafty should execute"
                            "on server launch",
                            "type": "string",
                            "examples": ["bedrock_server.exe"],
                            "minlength": 1,
                        },
                        "command": {
                            "title": "Command",
                            "type": "string",
                            "default": "echo foo bar baz",
                            "examples": ["LD_LIBRARY_PATH=. ./bedrock_server"],
                            "minLength": 1,
                        },
                    },
                },
                "import_zip_create_data": {
                    "title": "Import ZIP server data",
                    "type": "object",
                    "required": ["zip_path", "zip_root", "command"],
                    "properties": {
                        "zip_path": {
                            "title": "ZIP path",
                            "description": "Absolute path to the ZIP archive",
                            "type": "string",
                            "examples": ["/var/opt/server.zip"],
                            "minLength": 1,
                        },
                        "executable": {
                            "title": "Executable File",
                            "description": "File Crafty should execute"
                            "on server launch",
                            "type": "string",
                            "examples": ["bedrock_server.exe"],
                            "minlength": 1,
                        },
                        "zip_root": {
                            "title": "Server root directory",
                            "description": "The server root in the ZIP archive",
                            "type": "string",
                            "examples": ["/", "/paper-server/", "server-1"],
                            "minLength": 1,
                        },
                        "command": {
                            "title": "Command",
                            "type": "string",
                            "default": "echo foo bar baz",
                            "examples": ["LD_LIBRARY_PATH=. ./bedrock_server"],
                            "minLength": 1,
                        },
                    },
                },
            },
            "allOf": [
                {
                    "$comment": "If..then section",
                    "allOf": [
                        {
                            "if": {
                                "properties": {
                                    "create_type": {"const": "import_server"}
                                }
                            },
                            "then": {"required": ["import_server_create_data"]},
                        },
                        {
                            "if": {
                                "properties": {"create_type": {"const": "import_zip"}}
                            },
                            "then": {"required": ["import_zip_create_data"]},
                        },
                        {
                            "if": {
                                "properties": {"create_type": {"const": "download_exe"}}
                            },
                            "then": {
                                "required": [
                                    "download_exe_create_data",
                                ]
                            },
                        },
                    ],
                },
                {
                    "title": "Only one creation data",
                    "oneOf": [
                        {"required": ["import_server_create_data"]},
                        {"required": ["import_zip_create_data"]},
                        {"required": ["download_exe_create_data"]},
                    ],
                },
            ],
        },
        "steam_cmd_create_data": {
            "title": "Minecraft Bedrock creation data",
            "type": "object",
            "required": ["create_type"],
            "properties": {
                "create_type": {
                    "title": "Creation type",
                    "type": "string",
                    "default": "download_exe",
                    "enum": ["download_exe"],
                },
                "download_exe_create_data": {
                    "title": "Import server data",
                    "type": "object",
                    "required": [],
                    "properties": {
                        "app_id": {
                            "title": "Steam Server App ID",
                            "type": "integer",
                        },
                        "agree_to_eula": {
                            "title": "Agree to the EULA",
                            "type": "boolean",
                            "enum": [True],
                        },
                    },
                },
            },
            "allOf": [
                {
                    "$comment": "If..then section",
                    "allOf": [
                        {
                            "if": {
                                "properties": {"create_type": {"const": "download_exe"}}
                            },
                            "then": {
                                "required": [
                                    "download_exe_create_data",
                                ]
                            },
                        },
                    ],
                },
                {
                    "title": "Only one creation data",
                    "oneOf": [
                        {"required": ["download_exe_create_data"]},
                    ],
                },
            ],
        },
        "custom_create_data": {
            "title": "Custom creation data",
            "type": "object",
            "required": [
                "working_directory",
                "executable_update",
                "create_type",
            ],
            "properties": {
                "working_directory": {
                    "title": "Working directory",
                    "description": '"" means the default',
                    "type": "string",
                    "default": "",
                    "examples": ["/mnt/mydrive/server-configs/", "./subdirectory", ""],
                },
                "executable_update": {
                    "title": "Executable Updation",
                    "description": "Also configurable later on and for other servers",
                    "type": "object",
                    "required": ["enabled", "file", "url"],
                    "properties": {
                        "enabled": {
                            "title": "Enabled",
                            "type": "boolean",
                            "default": False,
                        },
                        "file": {
                            "title": "Executable to update",
                            "type": "string",
                            "default": "",
                            "examples": ["./paper.jar"],
                        },
                        "url": {
                            "title": "URL to download the executable from",
                            "type": "string",
                            "default": "",
                        },
                    },
                },
                "create_type": {
                    "title": "Creation type",
                    "type": "string",
                    "default": "raw_exec",
                    "enum": ["raw_exec", "import_server", "import_zip"],
                },
                "raw_exec_create_data": {
                    "title": "Raw execution command create data",
                    "type": "object",
                    "required": ["command"],
                    "properties": {
                        "command": {
                            "title": "Command",
                            "type": "string",
                            "default": "echo foo bar baz",
                            "examples": ["caddy start"],
                            "minLength": 1,
                        }
                    },
                },
                "import_server_create_data": {
                    "title": "Import server data",
                    "type": "object",
                    "required": ["existing_server_path", "command"],
                    "properties": {
                        "existing_server_path": {
                            "title": "Server path",
                            "description": "Absolute path to the old server",
                            "type": "string",
                            "examples": ["/var/opt/server"],
                            "minLength": 1,
                        },
                        "command": {
                            "title": "Command",
                            "type": "string",
                            "default": "echo foo bar baz",
                            "examples": ["caddy start"],
                            "minLength": 1,
                        },
                    },
                },
                "import_zip_create_data": {
                    "title": "Import ZIP server data",
                    "type": "object",
                    "required": ["zip_path", "zip_root", "command"],
                    "properties": {
                        "zip_path": {
                            "title": "ZIP path",
                            "description": "Absolute path to the ZIP archive",
                            "type": "string",
                            "examples": ["/var/opt/server.zip"],
                            "minLength": 1,
                        },
                        "zip_root": {
                            "title": "Server root directory",
                            "description": "The server root in the ZIP archive",
                            "type": "string",
                            "examples": ["/", "/paper-server/", "server-1"],
                            "minLength": 1,
                        },
                        "command": {
                            "title": "Command",
                            "type": "string",
                            "default": "echo foo bar baz",
                            "examples": ["caddy start"],
                            "minLength": 1,
                        },
                    },
                },
            },
            "allOf": [
                {
                    "$comment": "If..then section",
                    "allOf": [
                        {
                            "if": {
                                "properties": {"create_type": {"const": "raw_exec"}}
                            },
                            "then": {"required": ["raw_exec_create_data"]},
                        },
                        {
                            "if": {
                                "properties": {
                                    "create_type": {"const": "import_server"}
                                }
                            },
                            "then": {"required": ["import_server_create_data"]},
                        },
                        {
                            "if": {
                                "properties": {"create_type": {"const": "import_zip"}}
                            },
                            "then": {"required": ["import_zip_create_data"]},
                        },
                    ],
                },
                {
                    "title": "Only one creation data",
                    "oneOf": [
                        {"required": ["raw_exec_create_data"]},
                        {"required": ["import_server_create_data"]},
                        {"required": ["import_zip_create_data"]},
                    ],
                },
            ],
        },
    },
    "allOf": [
        {
            "$comment": "If..then section",
            "allOf": [
                # start require creation data
                {
                    "if": {"properties": {"create_type": {"const": "minecraft_java"}}},
                    "then": {"required": ["minecraft_java_create_data"]},
                },
                {
                    "if": {
                        "properties": {"create_type": {"const": "minecraft_bedrock"}}
                    },
                    "then": {"required": ["minecraft_bedrock_create_data"]},
                },
                {
                    "if": {"properties": {"create_type": {"const": "steam_cmd"}}},
                    "then": {"required": ["steam_cmd_create_data"]},
                },
                {
                    "if": {"properties": {"create_type": {"const": "custom"}}},
                    "then": {"required": ["custom_create_data"]},
                },
                # end require creation data
                # start require monitoring data
                {
                    "if": {
                        "properties": {"monitoring_type": {"const": "minecraft_java"}}
                    },
                    "then": {"required": ["minecraft_java_monitoring_data"]},
                },
                {
                    "if": {
                        "properties": {
                            "monitoring_type": {"const": "minecraft_bedrock"}
                        }
                    },
                    "then": {"required": ["minecraft_bedrock_monitoring_data"]},
                },
                # end require monitoring data
            ],
        },
        {
            "title": "Only one creation data",
            "oneOf": [
                {"required": ["minecraft_java_create_data"]},
                {"required": ["minecraft_bedrock_create_data"]},
                {"required": ["steam_cmd_create_data"]},
                {"required": ["custom_create_data"]},
            ],
        },
        {
            "title": "Only one monitoring data",
            "oneOf": [
                {"required": ["minecraft_java_monitoring_data"]},
                {"required": ["minecraft_bedrock_monitoring_data"]},
                {"required": ["steam_cmd_monitoring_data"]},
                {"properties": {"monitoring_type": {"const": "none"}}},
            ],
        },
    ],
}


class ApiServersIndexHandler(BaseApiHandler):
    def get(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        # TODO: limit some columns for specific permissions

        self.finish_json(200, {"status": "ok", "data": auth_data[0]})

    def post(self):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            exec_user_crafty_permissions,
            _,
            _superuser,
            user,
        ) = auth_data

        if EnumPermissionsCrafty.SERVER_CREATION not in exec_user_crafty_permissions:
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            data = orjson.loads(self.request.body)
        except orjson.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )
        print(data)
        try:
            validate(data, new_server_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )
        # Check to make sure port is allowable
        if data["monitoring_type"] == "minecraft_java":
            try:
                port = data["minecraft_java_monitoring_data"]["port"]
            except:
                port = 25565
        else:
            try:
                port = data["minecraft_bedrock_monitoring_data"]["port"]
            except:
                port = 19132
        if port > 65535 or port < 1:
            self.finish_json(
                405, {"status": "error", "error": "DATA CONSTRAINT FAILED"}
            )
            return
        new_server_id, new_server_uuid = self.controller.create_api_server(
            data, user["user_id"]
        )

        self.controller.servers.stats.record_stats()

        self.controller.management.add_to_audit_log(
            user["user_id"],
            (
                f"created server {data['name']}"
                f" (ID: {new_server_id})"
                f" (UUID: {new_server_uuid})"
            ),
            server_id=new_server_id,
            source_ip=self.get_remote_ip(),
        )

        self.finish_json(
            201,
            {
                "status": "ok",
                "data": {
                    "new_server_id": str(new_server_id),
                    "new_server_uuid": new_server_uuid,
                },
            },
        )
