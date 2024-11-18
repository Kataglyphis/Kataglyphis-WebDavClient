import os
from loguru import logger
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

        self.ensure_folder_exists("logs")
        logger.add("logs/downloadMd_s.log", rotation="500 MB")

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
            logger.error(
                "Error message {} with code {}", error_message, response.status_code
            )
            raise OSError(f"{error_message}{response.status_code}")

        tree = ElementTree.fromstring(response.content)
        files = []
        for response in tree.findall("{DAV:}response"):
            href = response.find("{DAV:}href").text
            if not href.endswith("/"):
                logger.debug("Found file: {} for the following url: {}", href, url)
                files.append(href)
        return files

    def list_folders(self, remote_base_path: str) -> list[str]:
        """
        This method list all folders from your WebDav host that stay EXACTLY
        under the remote_base_path. No subfolders are considered.

        Args:
            remote_base_path (str)   :  Folder on host for which the folders should
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
        url: str = os.path.join(self.hostname, remote_base_path)
        # as we communicate we do not want WINDWOS \ as os.sep!
        url = url.replace(os.sep, "/")
        response = requests.request("PROPFIND", url, auth=self.auth, headers=headers)
        if response.status_code != 207:
            error_message = "Failed to list directory contents: "
            logger.error("{} {}", error_message, response.status_code)
            raise OSError(f"{error_message}{response.status_code}")

        tree = ElementTree.fromstring(response.content)
        folders = []
        for response in tree.findall("{DAV:}response"):
            href = response.find("{DAV:}href").text
            folder = os.path.basename(os.path.normpath(href))
            is_folder = href.endswith("/")
            is_not_remote_base_path = (
                href != url + "/"
            ) and folder != remote_base_path.split("/")[-1]
            is_hidden_folder = folder.startswith(".")
            if is_folder and is_not_remote_base_path and not is_hidden_folder:
                logger.debug(
                    "Found folder: {} in the parent folder: {}",
                    folder,
                    remote_base_path,
                )
                folders.append(folder)
        return folders

    def filter_after_global_base_path(self, path: str, remote_base_path: str) -> str:
        """
        This method removes the hostname and the remote_base_path from an path
        Args:
            path (str)  : Url to host, e.g. https://host.org
            remote_base_path (str): single folder on remote host e.g. data

        Returns:
            type: str

        Raises:
            None directly

        Example: host-url= https://host.org/
                 remote_base_path = data
                 path = https://host.org/data/example1

                 "example1" ist returned
        """
        search_str = "/" + remote_base_path + "/"
        if search_str in path:
            logger.debug(
                "Found folder {} for path {} and remote base path: {}",
                search_str,
                path,
                remote_base_path,
            )
            url_after_removing_everything_before_and_including_remote_base_name = (
                path.split(search_str, 1)[1]
            )
            logger.info(
                "Folder structure everything after the remote_base_path is: {}",
                url_after_removing_everything_before_and_including_remote_base_name,
            )
            return url_after_removing_everything_before_and_including_remote_base_name
        logger.error("Could not find search string: {} in path: {}", search_str, path)
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
            logger.debug("Folder created: {}", path)
        else:
            logger.debug("Folder already exists: {}", path)

    def get_sub_path(self, full_path: str, initial_part: str) -> str:
        """
        Returns the sub-path after the initial part of the path.

        Args:
            full_path (str): The full path string. Does NOT have host url within
            initial_part (str): The initial part of the path string to be removed.

        Returns:
            type: str: The sub-path string after the initial part.

        Example 1:
            full_path = /data/subfolder1/text.txt
            initial_part (str) = data
            returns ==> subfolder1/text.txt

        Raises:
            ValueError

        """
        # Decode URL-encoded parts of the path
        logger.debug("We are in the 'get_sub_path' method.")
        decoded_full_path = urllib.parse.unquote(full_path)
        logger.debug("The decoded full file path is: {}", decoded_full_path)
        decoded_initial_part = urllib.parse.unquote(initial_part)
        logger.debug("The decoded initial file path is: {}", decoded_initial_part)
        # Ensure the initial part ends with a slash
        # removes weird edge cases for later processing
        if not decoded_initial_part.endswith("/"):
            decoded_initial_part += "/"

        # Find the position where the initial part ends in the full path
        start_idx = decoded_full_path.find(decoded_initial_part)

        if start_idx == -1:
            logger.error(
                "The {} string is not in the full_path={}", initial_part, full_path
            )
            raise ValueError("The full path does not contain the initial part.")

        # Handle the edge case where the full path is exactly the initial part
        decoded_initial_part = "/" + decoded_initial_part
        if full_path == decoded_initial_part.rstrip("/"):
            logger.debug("The get_sub_path() method returns empty string")
            return ""

        # Remove the initial part from the full path
        if full_path.startswith(initial_part):
            logger.debug(
                "The get_sub_path() method returns {}", full_path[len(initial_part) :]
            )
            return full_path[len(initial_part) :]
        else:
            # Calculate the start index of the sub-path
            sub_path_start_idx = start_idx + len(decoded_initial_part) - 1

            # Extract the sub-path
            sub_path = decoded_full_path[sub_path_start_idx:]

            logger.debug("The get_sub_path() method returns {}", sub_path)

            return sub_path

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
            logger.info("Dir {} will be created", local_base_path)
            os.makedirs(local_base_path)
        url = os.path.join(self.hostname, remote_base_path)
        # as we communicate we do not want WINDWOS \ as os.sep!
        url = url.replace(os.sep, "/")
        files_on_host = self.list_files(url)

        if len(files_on_host) == 0:
            logger.info("Found no files on remote_base_path: {}", remote_base_path)

        for file_path in files_on_host:
            logger.info("Found the file: {} on current remote_base_path", file_path)
            file_name = self.filter_after_global_base_path(file_path, remote_base_path)
            logger.info("The pure of filename of this file is: {}", file_name)
            # Decoding the URL-encoded string
            decoded_filename = urllib.parse.unquote(file_name)
            logger.info("The decoded filename version is: {}", decoded_filename)
            remote_file_url = os.path.join(
                self.hostname, remote_base_path, file_name  # file_path.split("/")[-1]
            )
            remote_file_url = remote_file_url.replace(os.sep, "/")
            logger.info("The remote file url is: {}", remote_file_url)
            sub_path = self.get_sub_path(file_path, global_remote_base_path)

            if sub_path.endswith(decoded_filename):
                sub_path = sub_path[: len(sub_path) - len(decoded_filename)]

            if sub_path == decoded_filename:
                sub_path = ""

            logger.debug("The current sub path is: {}", sub_path)
            local_file_path = os.path.join(local_base_path, sub_path, decoded_filename)
            local_file_path = local_file_path.replace(os.sep, "/")
            logger.debug(
                "The current file that is stored has the full path: {}", local_file_path
            )
            response = requests.get(remote_file_url, auth=self.auth, stream=True)
            if response.status_code == 200:
                folder_path = os.path.dirname(local_file_path)
                self.ensure_folder_exists(folder_path)
                with open(local_file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                logger.debug(
                    "Failed to download {}: {}", remote_file_url, response.status_code
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
            logger.debug("Current remote path is: {}", current_remote_path)

            # Download files in the current directory
            self.download_files(
                global_remote_base_path,
                current_remote_path,
                local_base_path,
            )

            # List all folders in the current remote path
            folders: list[str] = self.list_folders(current_remote_path)
            if len(folders) == 0:
                logger.info(
                    "Found no subfolders for current folder: {}", current_remote_path
                )
            # Add each subfolder to the stack
            for folder in folders:
                logger.info(
                    "Found subfolder {} for current folder: {}.",
                    folder,
                    current_remote_path,
                )
                relative_folder_path: str = os.path.join(current_remote_path, folder)
                relative_folder_path = relative_folder_path.replace(os.sep, "/")
                stack.append(relative_folder_path)
