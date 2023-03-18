import os
import platform
import zipfile
import tarfile
import subprocess
import urllib.request

from getpass import getpass
from app.classes.steamcmd.steamcmd_command import SteamCMD_command


package_links = {
    "Windows": {
        "url": "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip",
        "extension": ".exe",
        "d_extension": ".zip",
    },
    "Linux": {
        "url": "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz",
        "extension": ".sh",
        "d_extension": ".tar.gz",
    },
}


class SteamCMD:
    """
    Wrapper for SteamCMD
    Will install from source depending on OS.
    """

    _installation_path = ""
    _uname = "anonymous"
    _passw = ""

    def __init__(self, installation_path):
        self._installation_path = installation_path

        if not os.path.isdir(self._installation_path):
            raise NotADirectoryError(
                message=f"No valid directory found at {self._installation_path}"
                "Please make sure that the directory is correct."
            )

        self._prepare_installation()

    def _prepare_installation(self):
        """
        Sets internal configuration according to parameters and OS
        """

        self.platform = platform.system()
        if self.platform not in ["Windows", "Linux"]:
            raise NotImplementedError(
                message=(
                    f"Non supported operating system. "
                    f"Expected Windows, or Linux, got {self.platform}"
                )
            )

        self.steamcmd_url = package_links[self.platform]["url"]
        self.zip = "steamcmd" + package_links[self.platform]["d_extension"]
        self.exe = os.path.join(
            self._installation_path,
            "steamcmd" + package_links[self.platform]["extension"],
        )

    def _download(self):
        """
        Internal method to download the SteamCMD Binaries from steams' servers.
        :return: downloaded data for debug purposes
        """

        try:
            if self.steamcmd_url.lower().startswith("http"):
                req = urllib.request.Request(self.steamcmd_url)
            else:
                raise ValueError from None
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                with open(self.zip, "wb") as f:
                    f.write(data)
                return data
        except Exception as e:
            raise FileNotFoundError(
                message=f"An unknown exception occurred during downloading. {e}"
            ) from e

    def _extract_steamcmd(self):
        """
        Internal method for extracting downloaded zip file. Works on both
        windows and linux.
        """
        if self.platform == "Windows":
            with zipfile.ZipFile(self.zip, "r") as f:
                f.extractall(self._installation_path)

        elif self.platform == "Linux":
            with tarfile.open(self.zip, "r:gz") as f:
                f.extractall(self._installation_path)

        else:
            # This should never happen, but let's just throw it just in case.
            raise NotImplementedError(
                message="The operating system is not supported."
                f"Expected Linux or Windows, received: {self.platform}"
            )

        os.remove(self.zip)

    @staticmethod
    def _print_log(*message):
        """
        Small helper function for printing log entries.
        Helps with output of subprocess.check_call not always having newlines
        :param *message: Accepts multiple messages, each will be printed on a
        new line
        """
        # TODO: Handle logs better
        print("")
        print("")
        for msg in message:
            print(msg)
        print("")

    def install(self, force: bool = False):
        """
        Installs steamcmd if it is not already installed to self.install_path.
        :param force: forces steamcmd install regardless of its presence
        :return:
        """
        if not os.path.isfile(self.exe) or force:
            # Steamcmd isn't installed. Go ahead and install it.
            self._download()
            self._extract_steamcmd()

        else:
            raise FileExistsError(
                message="Steamcmd is already installed. Reinstall is not necessary."
                "Use force=True to override."
            )
        try:
            subprocess.check_call((self.exe, "+quit"))
        except subprocess.CalledProcessError as e:
            if e.returncode == 7:
                self._print_log(
                    "SteamCMD has returned error code 7 on fresh installation",
                    "",
                    "Not sure why this crashed,",
                    "long live steamcmd and it's non existent documentation..",
                    "It should be fine nevertheless",
                )
                return
            else:
                raise SystemError(
                    message=f"Failed to install, check error code {e.returncode}"
                ) from e

        return

    def login(self, uname: str = None, passw: str = None):
        """
        Login function in order to do a persistent login on the steam servers.
        Prompts users for their credentials and spawns a child process.
        :param uname: Steam Username
        :param passw: Steam Password
        :return: status code of child process
        """
        self._uname = uname if uname else input("Please enter steam username: ")
        self._passw = passw if passw else getpass("Please enter steam password: ")

        steam_command = SteamCMD_command()
        return self.execute(steam_command)

    def app_update(
        self,
        app_id: int,
        install_dir: str = None,
        validate: bool = None,
        beta: str = None,
        betapassword: str = None,
    ):
        """
        Installer function for apps.
        :param app_id: The Steam ID for the app you want to install
        :param install_dir: Optional custom installation directory.
        :param validate: Optional. Turn this on when updating something.
        :param beta: Optional parameter for running a beta branch.
        :param betapassword: Optional parameter for entering beta password.
        :return: Status code of child process.
        """
        steam_command = SteamCMD_command()
        if install_dir:
            steam_command.force_install_dir(install_dir)
        steam_command.app_update(app_id, validate, beta, betapassword)
        self._print_log(
            f"Downloading item {app_id}",
            f"into {install_dir} with validate set to {validate}",
        )
        return self.execute(steam_command)

    def workshop_update(
        self,
        app_id: int,
        workshop_id: int,
        install_dir: str = None,
        validate: bool = None,
        n_tries: int = 5,
    ):
        """
        Installer function for workshop content. Retries multiple times on timeout
        due to valves' timeout on large downloads.
        :param app_id: The parent application ID
        :param workshop_id: The ID for workshop content. Can be found in the url.
        :param install_dir: Optional custom installation directory.
        :param validate: Optional. Turn this on when updating something.
        :param n_tries: Counter for how many redownloads it can make before timing out.
        :return: Status code of child process.
        """

        steam_command = SteamCMD_command()
        if install_dir:
            steam_command.force_install_dir(install_dir)
        steam_command.workshop_download_item(app_id, workshop_id, validate)
        return self.execute(steam_command, n_tries)

    def execute(self, cmd: SteamCMD_command, n_tries: int = 1):
        """
        Executes a SteamCMD_command, with added actions occurring sequentially.
        May retry multiple times on timeout due to valves' timeout on large downloads.
        :param cmd: Sequence of commands to execute
        :param n_tries: Number of times the command will be tried.
        :return: Status code of child process.
        """
        if n_tries == 0:
            raise TimeoutError(
                message="""Error executing command, max number of retries exceeded!
                Consider increasing the n_tries parameter if the download is
                particularly large"""
            )

        params = (
            self.exe,
            f"+login {self._uname} {self._passw}",
            cmd.get_cmd(),
            "+quit",
        )
        self._print_log("Parameters used:", " ".join(params))
        try:
            return subprocess.check_call(" ".join(params), shell=True)

        except subprocess.CalledProcessError as e:
            # SteamCMD has a habit of timing out large downloads,
            # so retry on timeout for the remainder of n_tries.
            if e.returncode == 10:
                self._print_log(
                    f"Download timeout! Tries remaining: {n_tries}. Retrying..."
                )
                return self.execute(cmd, n_tries - 1)
            # SteamCMD sometimes crashes when timing out downloads, due to
            # an assert checking that the download actually finished.
            # If this happens, retry.
            elif e.returncode == 134:
                self._print_log(
                    f"SteamCMD errored! Tries remaining: {n_tries}. Retrying..."
                )
                return self.execute(cmd, n_tries - 1)

            raise SystemError(
                message=f"Steamcmd was unable to run. exit code was {e.returncode}"
            ) from e
