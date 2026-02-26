"""WebDAV client implementation for listing and downloading remote files."""

import urllib.parse
from pathlib import Path, PurePosixPath

import requests
from defusedxml import ElementTree
from loguru import logger
from requests.auth import HTTPBasicAuth


REQUEST_TIMEOUT_SECONDS = 30


def _join_remote_url(*parts: str) -> str:
    cleaned_parts = [part.strip("/") for part in parts if part]
    return "/".join(cleaned_parts)


class WebDavClient:
    """A simple WebDav client for downloading files and folders.

    It supports listing folders, listing files, and iterative downloads from
    a remote host (for example a cloud provider).

    Attributes:
        hostname (str)        : full address to webdav host
        username (str)        : username of connection
        password (str)        : most properly a token generated for AUTH

    Methods:
        download_all_files_iterative(a,b): Downloads all files from a and stores
            them under b locally.
    """

    def __init__(self, hostname: str, username: str, password: str) -> None:
        """Initialize a client with credentials and logging output folder."""
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
        """List all files directly below a given WebDAV URL.

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
            >>> files = webdevclient.list_files(
            ...     os.path.join(hostname, remote_base_path)
            ... )

        """
        headers: dict[str, str] = {"Content-Type": "application/xml", "Depth": "1"}
        response: requests.Response = requests.request(
            "PROPFIND",
            url,
            auth=self.auth,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 207:
            error_message: str = "Failed to list directory contents via requests: "
            logger.error(
                "Error message {} with code {}", error_message, response.status_code
            )
            error_details = f"{error_message}{response.status_code}"
            raise OSError(error_details)

        tree = ElementTree.fromstring(response.content)
        files = []
        for response in tree.findall("{DAV:}response"):
            href = response.find("{DAV:}href").text
            if not href.endswith("/"):
                logger.debug("Found file: {} for the following url: {}", href, url)
                files.append(href)
        return files

    def list_folders(self, remote_base_path: str) -> list[str]:
        """List all folders directly below a remote base path.

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
        url: str = _join_remote_url(self.hostname, remote_base_path)
        response = requests.request(
            "PROPFIND",
            url,
            auth=self.auth,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 207:
            error_message = "Failed to list directory contents: "
            logger.error("{} {}", error_message, response.status_code)
            error_details = f"{error_message}{response.status_code}"
            raise OSError(error_details)

        tree = ElementTree.fromstring(response.content)
        folders = []
        for response in tree.findall("{DAV:}response"):
            href = response.find("{DAV:}href").text
            folder = PurePosixPath(href.rstrip("/")).name
            is_folder = href.endswith("/")
            is_not_remote_base_path = (
                href != url + "/"
            ) and folder != remote_base_path.rsplit("/", maxsplit=1)[-1]
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
        """Remove hostname and base path prefix from a remote URL path.

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

                 "example1" is returned
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
        """Ensure that the given folder exists.

        Args:
            path (str)  : Path to folder.

        Returns:
            type: None

        Raises:
            None directly

        """
        folder_path = Path(path)
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.debug("Folder created: {}", path)
        else:
            logger.debug("Folder already exists: {}", path)

    def get_sub_path(self, full_path: str, initial_part: str) -> str:
        """Returns the sub-path after the initial part of the path.

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
            error_details = "The full path does not contain the initial part."
            raise ValueError(error_details)

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
        """Download all files directly below a remote base path.

        This method downloads all files from your WebDav host that stay EXACTLY
        under the remote_base_path. No subfolders are considered.

        Args:
            global_remote_base_path (str): Root folder that anchors relative paths.
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
        if not Path(local_base_path).exists():
            logger.info("Dir {} will be created", local_base_path)
            Path(local_base_path).mkdir(parents=True, exist_ok=True)
        url = _join_remote_url(self.hostname, remote_base_path)
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
            remote_file_url = _join_remote_url(
                self.hostname,
                remote_base_path,
                file_name,  # file_path.split("/")[-1]
            )
            logger.info("The remote file url is: {}", remote_file_url)
            sub_path = self.get_sub_path(file_path, global_remote_base_path)

            if sub_path.endswith(decoded_filename):
                sub_path = sub_path[: len(sub_path) - len(decoded_filename)]

            if sub_path == decoded_filename:
                sub_path = ""

            logger.debug("The current sub path is: {}", sub_path)
            local_file_path = Path(local_base_path) / sub_path / decoded_filename
            logger.debug(
                "The current file that is stored has the full path: {}", local_file_path
            )
            response = requests.get(
                remote_file_url,
                auth=self.auth,
                stream=True,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                folder_path = local_file_path.parent
                self.ensure_folder_exists(str(folder_path))
                with local_file_path.open("wb") as f:
                    f.writelines(response.iter_content(chunk_size=8192))
            else:
                logger.debug(
                    "Failed to download {}: {}", remote_file_url, response.status_code
                )

    def download_all_files_iterative(
        self,
        remote_base_path: str,
        local_base_path: str,
    ) -> None:
        """Download all files recursively below a remote base path.

        This method downloads all files from your WebDav host that stay
        under the remote_base_path. All subfolders will also be downloaded
        and folder structure is preserved.

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
                relative_folder_path: str = str(
                    PurePosixPath(current_remote_path) / folder
                )
                stack.append(relative_folder_path)
