class SteamCMDcommand:
    """
    Used to construct a sequence of commands to sequentially be executed by SteamCMD.
    This reduces the number of required logins, which when using the other provided
    methods may result in getting rate limited by Steam.
    To be used with the SteamCMD.execute() method.
    """

    _commands = []

    def __init__(self):
        self._commands = []

    def force_install_dir(self, install_dir: str):
        """
        Sets the install directory for following app_update and workshop_download_item
        commands

        :param install_dir: Directory to install to
        :return: Index command was added at
        """
        self._commands.append(f"+force_install_dir {install_dir}")
        return len(self._commands) - 1

    def app_update(
        self, app_id: int, validate: bool = False, beta: str = "", beta_pass: str = ""
    ):
        """
        Updates/installs an app
        :param app_id: The Steam ID for the app you want to install
        :param validate: Optional. Turn this on when updating something
        :param beta: Optional parameter for running a beta branch.
        :param beta_pass: Optional parameter for entering beta password.
        :return: Index command was added at
        """
        self._commands.append(
            f"+app_update "
            f"{app_id}"
            f'{" validate" if validate else ""}'
            f'{" -beta {}".format(beta) if beta else ""}'
            f'{" -betapassword {}".format(beta_pass) if beta_pass else ""}'
        )
        return len(self._commands) - 1

    def workshop_download_item(
        self, app_id: int, workshop_id: int, validate: bool = False
    ):
        """
        Updates/installs workshop content
        :param app_id: The parent application ID
        :param workshop_id: The ID for workshop content. Can be found in the url.
        :param validate: Optional. Turn this on when updating something
        :return: Index command was added at
        """
        self._commands.append(
            f"+workshop_download_item "
            f"{app_id} "
            f"{workshop_id}"
            f'{" validate" if validate else ""}'
        )
        return len(self._commands) - 1

    def custom(self, cmd: str):
        """
        Custom SteamCMD command
        :param cmd: Command to execute
        :return: Index command was added at
        """
        self._commands.append(cmd)
        return len(self._commands) - 1

    def remove(self, idx):
        """
        Removes a command at the stated index
        :param idx: Index of command to remove
        :return: Whether command was removed
        """
        if 0 <= idx < len(self._commands) and self._commands[idx]:
            # Replacing with None to keep indexes intact
            self._commands[idx] = None
            return True
        return False

    def get_cmd(self):
        params = filter(None, self._commands)
        return " ".join(params)
