import os
import logging
import urllib.parse
from xml.etree import ElementTree
import requests
from requests.auth import HTTPBasicAuth


class WebDavClient:
    """
    A simple WebDav client for downloading files and complete folder
    hierarchies from a remote host (f.e. cloud provider).

    Attributes:
        hostname (str)        : full address to webdav host
        username (str)        : username of connection
        password (str)        : most properly a token generated for AUTH

    Methods:
        download_all_files_iterative(a,b): Downloads all files from a and stroes
                                           them under b locally.
        subtract(a, b): Returns the difference between a and b.
    """

    def __init__(self, hostname: str, username: str, password: str) -> None:

        self.hostname: str = hostname
        self.username: str = username
        self.password: str = password
        self.auth: HTTPBasicAuth = HTTPBasicAuth(
            username,
            password,
        )

        # create global logger
        self.logger = logging.getLogger(__name__)
        # Set the default log level
        self.logger.setLevel(logging.DEBUG)
        # Create handlers
        console_handler = logging.StreamHandler()

        self.ensure_folder_exists("logs")
        file_handler = logging.FileHandler("logs/downloadMd_s.log")

        # Set levels for handlers
        console_handler.setLevel(logging.DEBUG)
        file_handler.setLevel(logging.DEBUG)

        # Create formatters and add them to handlers
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers to the logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def list_files(self, url: str) -> list[str]:
        """
        This method list all files from your WebDav host that stay under the
        url

        Args:
            url (str) : web dev host url.

        Returns:
            type: list[str]
            list of all files who stay under the url (no recursion)

        Raises:
            OSError

        Examples:
            Example usage of the method:

            >>> hostname = "https://yourhost.de/webdav"
            >>> username = "Schlawiner23"
            >>> password = "YOUR_PERSONAL_TOKEN"
            >>> remote_base_path = "MyProjectFolder"
            >>> auth: HTTPBasicAuth = HTTPBasicAuth(username, password)
            >>> webdevclient = WebDavClient(hostname, username, password)
            >>> files = webdevclient.list_files(os.path.join(hostname, remote_base_path))

        """
        headers: dict[str, str] = {"Content-Type": "application/xml", "Depth": "1"}
        response: requests.Response = requests.request(
            "PROPFIND", url, auth=self.auth, headers=headers
        )
        if response.status_code != 207:
            error_message: str = "Failed to list directory contents via requests: "
            self.logger.error("%s%s", error_message, response.status_code)
            raise OSError(f"{error_message}{response.status_code}")

        tree = ElementTree.fromstring(response.content)
        files = []
        for response in tree.findall("{DAV:}response"):
            href = response.find("{DAV:}href").text
            if not href.endswith("/"):
                self.logger.debug("Found file: %s for the following url: %s", href, url)
                files.append(href)
        return files

    def list_folders(self, parent_folder: str) -> list[str]:
        """
        This method list all folders from your WebDav host that stay EXACTLY
        under the remote_base_path. No subfolders are considered.

        Args:
            parent_folder (str)   : Folder on host for which the folders should
                                    be listed

        Returns:
            type: list[str]
            list of all folders who stay under the parent folder

        Raises:
            OSError

        Examples:
            Example usage of the method:

            >>> hostname = "https://yourhost.de/webdav"
            >>> username = "Schlawiner23"
            >>> password = "YOUR_PERSONAL_TOKEN"
            >>> remote_base_path = "MyProjectFolder"
            >>> webdevclient = WebDavClient(args.hostname, args.username, args.password)
            >>> webdevclient.list_folders(remote_base_path)

        """
        headers = {"Content-Type": "application/xml", "Depth": "1"}
        url: str = os.path.join(self.hostname, parent_folder)
        response = requests.request("PROPFIND", url, auth=self.auth, headers=headers)
        if response.status_code != 207:
            error_message = "Failed to list directory contents: "
            self.logger.error("%s%s", error_message, response.status_code)
            raise OSError(f"{error_message}{response.status_code}")

        tree = ElementTree.fromstring(response.content)
        folders = []
        for response in tree.findall("{DAV:}response"):
            href = response.find("{DAV:}href").text
            folder = os.path.basename(os.path.normpath(href))
            if (
                href.endswith("/")
                and href != url + "/"
                and not folder.startswith(".")
                and folder != parent_folder.split("/")[-1]
            ):
                self.logger.debug(
                    "Found folder: %s in the parent folder: %s", folder, parent_folder
                )
                folders.append(folder)
        return folders

    def filter_after_global_base_path(self, path: str, remote_base_path: str) -> str:
        """
        This method removes the hostname and the remote_base_path from an path

        Args:
            path (str)  : Path to folder.

        Returns:
            type: None

        Raises:
            None directly

        """
        search_str = "/" + remote_base_path + "/"
        if search_str in path:
            self.logger.debug(
                "Found folder %s for path %s and remote base path: %s",
                search_str,
                path,
                remote_base_path,
            )
            url_after_removing_everything_before_and_including_remote_base_name = (
                path.split(search_str, 1)[1]
            )
            self.logger.info(
                "Folder structure everything after the remote_base_path is: %s",
                url_after_removing_everything_before_and_including_remote_base_name,
            )
            return url_after_removing_everything_before_and_including_remote_base_name
        self.logger.error(
            "Could not find search string: %s in path: %s", search_str, path
        )
        return path

    def ensure_folder_exists(self, path: str) -> None:
        """
        This method ensures that the given folder will exist

        Args:
            path (str)  : Path to folder.

        Returns:
            type: None

        Raises:
            None directly

        """
        if not os.path.exists(path):
            os.makedirs(path)
            self.logger.debug("Folder created: %s", path)
        else:
            self.logger.debug("Folder already exists: %s", path)

    def get_sub_path(self, full_path: str, initial_part: str) -> str:
        """
        Returns the sub-path after the initial part of the path.

        :param full_path: The full path string.
        :param initial_part: The initial part of the path string to be removed.
        :return: The sub-path string after the initial part.
        """
        # Ensure the initial part ends with a slash
        if not initial_part.endswith("/"):
            initial_part += "/"

        # Handle the edge case where the full path is exactly the initial part
        if full_path == initial_part.rstrip("/"):
            return ""

        # Remove the initial part from the full path
        if full_path.startswith(initial_part):
            return full_path[len(initial_part) :]
        else:
            raise ValueError("The full path does not start with the initial part.")

    def download_files(
        self,
        global_remote_base_path: str,
        remote_base_path: str,
        local_base_path: str,
    ) -> None:
        """
        This method downloads all files from your WebDav host that stay EXACTLY
        under the remote_base_path. No subfolders are considered.

        Args:
            remote_base_path (str): Folder on host which should be primary source
                                    for downloading files
            local_base_path (str) : all files (with preserved folder structures)
                                    are put inside this local path

        Returns:
            type: None

        Raises:
            None directly

        Examples:
            Example usage of the method:

            >>> hostname = "https://yourhost.de/webdav"
            >>> username = "Schlawiner23"
            >>> password = "YOUR_PERSONAL_TOKEN"
            >>> remote_base_path = "MyProjectFolder"
            >>> local_base_path = "assets"
            >>> auth: HTTPBasicAuth = HTTPBasicAuth(username, password)
            >>> download_files(hostname, auth, current_remote_path, local_base_path)

        """
        if not os.path.exists(local_base_path):
            self.logger.info("Dir %s will be created", local_base_path)
            os.makedirs(local_base_path)

        files_on_host = self.list_files(os.path.join(self.hostname, remote_base_path))

        if len(files_on_host) == 0:
            self.logger.info("Found no files on remote_base_path: %s", remote_base_path)

        for file_path in files_on_host:
            self.logger.info(
                "Found the file: %s on current remote_base_path", file_path
            )
            file_name = self.filter_after_global_base_path(file_path, remote_base_path)
            self.logger.info("The pure of filename of this file is: %s", file_name)
            # Decoding the URL-encoded string
            decoded_filename = urllib.parse.unquote(file_name)
            self.logger.info("The decoded filename version is: %s", decoded_filename)
            remote_file_url = os.path.join(
                self.hostname, remote_base_path, file_path.split("/")[-1]
            )
            self.logger.info("The remote file url is: %s", remote_file_url)
            sub_path = self.get_sub_path(remote_base_path, global_remote_base_path)
            self.logger.debug("The current sub path is: %s", sub_path)
            local_file_path = os.path.join(local_base_path, sub_path, decoded_filename)
            self.logger.debug(
                "The current file that is stored has the full path: %s", local_file_path
            )
            response = requests.get(remote_file_url, auth=self.auth, stream=True)
            if response.status_code == 200:
                folder_path = os.path.dirname(local_file_path)
                self.ensure_folder_exists(folder_path)
                with open(local_file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                self.logger.debug(
                    "Failed to download %s: %s", remote_file_url, response.status_code
                )

    def download_all_files_iterative(
        self,
        remote_base_path: str,
        local_base_path: str,
    ) -> None:
        """
        This method downloads all files from your WebDav host that stay
        under the remote_base_path. All subfolders will also be downloaded
        and folder structure is preserved

        Args:
            remote_base_path (str): Folder on host which should be primary source
                                    for downloading files
            local_base_path (str) : all files (with preserved folder structures)
                                    are put inside this local path

        Returns:
            type: None

        Raises:
            None directly

        Examples:
            Example usage of the method:

            >>> hostname = "https://yourhost.de/webdav"
            >>> username = "Schlawiner23"
            >>> password = "YOUR_PERSONAL_TOKEN"
            >>> remote_base_path = "MyProjectFolder"
            >>> local_base_path = "assets"
            >>> webdevclient = WebDavClient(args.hostname, args.username, args.password)
            >>> webdevclient.download_all_files_iterative(
            >>>     args.remote_base_path, args.local_base_path
            >>> )

        """
        # Initialize the stack with the root directory
        stack: list[str] = [remote_base_path]

        global_remote_base_path: str = remote_base_path

        while stack:
            current_remote_path: str = stack.pop()
            self.logger.debug("Current remote path is: %s", current_remote_path)

            # Download files in the current directory
            self.download_files(
                global_remote_base_path,
                current_remote_path,
                local_base_path,
            )

            # List all folders in the current remote path
            folders: list[str] = self.list_folders(current_remote_path)
            if len(folders) == 0:
                self.logger.info(
                    "Found no subfolders for current folder: %s", current_remote_path
                )
            # Add each subfolder to the stack
            for folder in folders:
                self.logger.info(
                    "Found subfolder %s for current folder: %s.",
                    folder,
                    current_remote_path,
                )
                relative_folder_path: str = os.path.join(current_remote_path, folder)
                stack.append(relative_folder_path)
