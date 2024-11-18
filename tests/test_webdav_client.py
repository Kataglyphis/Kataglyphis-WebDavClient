"""
Module for testing the WebDavClient using pytest.

This module contains setup fixtures for starting a mock WebDAV server and cleaning up test files.
It also includes test functions that validate various functionalities of the WebDavClient.

Functions
---------
cleanup_test_files()
    Removes test directories and their contents after tests are completed.

start_webdav_server()
    Pytest fixture to start and stop the mock WebDAV server for testing.

webdav_client()
    Pytest fixture that provides an instance of WebDavClient for testing.

test_filter_after_global_base_path(webdav_client)
    Tests the filter_after_global_base_path method of WebDavClient.

test_list_files(webdav_client)
    Tests the list_files method of WebDavClient.

test_list_folders(webdav_client)
    Tests the list_folders method of WebDavClient.

test_get_sub_path(webdav_client)
    Tests the get_sub_path method of WebDavClient.

test_download_files(webdav_client)
    Tests downloading files using the download_files method.

test_download_all_files_iterative(webdav_client)
    Tests downloading all files iteratively using the download_all_files_iterative method.
"""

import os
import shutil
from loguru import logger
import pytest
import subprocess
import time
import requests
from webdavclient import WebDavClient


def cleanup_test_files() -> None:
    """
    Remove test directories and their contents.

    This function attempts to remove the 'tests/local_data' and 'tests/local_data2' directories,
    along with all their contents, to clean up after tests.

    Returns
    -------
    None
    """
    try:
        shutil.rmtree("tests/local_data")
        shutil.rmtree("tests/local_data2")
        logger.info(
            "The directory local_data and local_data2 and all its contents have been removed successfully."
        )
    except OSError as e:
        logger.error(f"Error : {e.strerror}")


@pytest.fixture(scope="module", autouse=True)
def start_webdav_server():
    """
    Pytest fixture to start and stop the mock WebDAV server.

    This fixture starts the mock WebDAV server before any tests are run and ensures
    it is properly terminated and cleaned up after tests are completed.

    Yields
    ------
    None
    """
    # Start the mock WebDav server
    server_process = subprocess.Popen(["python", "tests/mock_webdav_server.py"])

    time.sleep(4)
    yield

    # Terminate the server process after all tests are done
    server_process.terminate()
    server_process.wait()

    # Cleanup after tests
    cleanup_test_files()


@pytest.fixture
def webdav_client() -> WebDavClient:
    """
    Provide a WebDavClient instance for testing.

    Returns
    -------
    WebDavClient
        An instance of WebDavClient configured with test credentials.
    """
    hostname = "http://localhost:8081"
    username = "testuser"
    password = "testpassword"
    return WebDavClient(hostname, username, password)


def test_filter_after_global_base_path(webdav_client: WebDavClient) -> None:
    """
    Test the filter_after_global_base_path method.

    Ensures that the method correctly filters out the global remote base path from the given path.

    Parameters
    ----------
    webdav_client : WebDavClient
        The WebDavClient instance used for testing.

    Returns
    -------
    None
    """
    path = "/data/subfolder1/text.txt"
    path2 = "http://localhost:8081/data"
    remote_base_path = "data"
    result = webdav_client.filter_after_global_base_path(path, remote_base_path)
    result2 = webdav_client.filter_after_global_base_path(path2, remote_base_path)
    assert result == "subfolder1/text.txt"
    # assert result2 ==


def test_list_files(webdav_client: WebDavClient) -> None:
    """
    Test listing files in a remote directory.

    Verifies that the list_files method returns the correct list of files.

    Parameters
    ----------
    webdav_client : WebDavClient
        The WebDavClient instance used for testing.

    Returns
    -------
    None
    """
    remote_base_path = "data"
    url = os.path.join(webdav_client.hostname, remote_base_path)
    url = url.replace(os.sep, "/")
    files = webdav_client.list_files(url)
    assert "/data/Readme.md" in files


def test_list_folders(webdav_client: WebDavClient) -> None:
    """
    Test listing folders in a remote directory.

    Verifies that the list_folders method returns the correct list of folders.

    Parameters
    ----------
    webdav_client : WebDavClient
        The WebDavClient instance used for testing.

    Returns
    -------
    None
    """
    folders = webdav_client.list_folders("data")
    assert "subfolder1" in folders
    assert "subfolder2" in folders
    assert "subfolder3" in folders


def test_get_sub_path(webdav_client: WebDavClient) -> None:
    """
    Test computing the sub-path relative to a base path.

    Ensures that get_sub_path returns the correct sub-path from the full path.

    Parameters
    ----------
    webdav_client : WebDavClient
        The WebDavClient instance used for testing.

    Returns
    -------
    None
    """
    full_path = "/data/subfolder1/text.txt"
    initial_part = "data"
    result = webdav_client.get_sub_path(full_path, initial_part)
    assert result == "subfolder1/text.txt"


def test_download_files(webdav_client: WebDavClient) -> None:
    """
    Test downloading files from the remote server.

    Checks if the specified files are correctly downloaded to the local directory.

    Parameters
    ----------
    webdav_client : WebDavClient
        The WebDavClient instance used for testing.

    Returns
    -------
    None
    """
    global_remote_base_path = "data"
    remote_base_path = "data"
    local_base_path = "tests/local_data"

    webdav_client.download_files(
        global_remote_base_path, remote_base_path, local_base_path
    )
    assert os.path.exists(os.path.join(local_base_path, "Readme.md"))


def test_download_all_files_iterative(webdav_client: WebDavClient) -> None:
    """
    Test recursively downloading all files from the remote server.

    Verifies that all files are downloaded iteratively into the local directory structure.

    Parameters
    ----------
    webdav_client : WebDavClient
        The WebDavClient instance used for testing.

    Returns
    -------
    None
    """
    remote_base_path = "data"
    local_base_path = "tests/local_data2"

    webdav_client.download_all_files_iterative(remote_base_path, local_base_path)
    assert os.path.exists(os.path.join(local_base_path, "Readme.md"))
    assert os.path.exists(os.path.join(local_base_path, "subfolder1/text.txt"))


if __name__ == "__main__":
    pytest.main()
