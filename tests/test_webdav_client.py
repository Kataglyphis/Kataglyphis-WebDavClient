import os
import shutil
import sys
import pytest
import subprocess
import time
import requests
from webdavclient import WebDavClient


def cleanup_test_files() -> None:
    os.removedirs("local_data")


def wait_for_server_to_start(url, timeout=10) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            print(response.status_code)
            if response.status_code == 200:
                return True
        except requests.ConnectionError:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="module", autouse=True)
def start_webdav_server():

    # Start the mock WebDav server
    # server_process = subprocess.Popen([sys.executable, "mock_webdav_server.py"])
    # Wait for the server to start
    # server_started = wait_for_server_to_start("http://localhost:8081")
    # if not server_started:
    #     server_process.terminate()
    #     pytest.fail("Could not start the mock WebDAV server.")

    # time.sleep(10)
    yield

    # Terminate the server process after all tests are done
    # server_process.terminate()
    # server_process.wait()

    # Cleanup after tests
    cleanup_test_files()


@pytest.fixture
def webdav_client() -> WebDavClient:
    """Creates a webdavclient for unittesting

    Returns
    -------
    WebDavClient
        username and password are dummy
    """
    hostname = "http://localhost:8081"
    username = "testuser"
    password = "testpassword"
    return WebDavClient(hostname, username, password)


def test_filter_after_global_base_path(webdav_client) -> None:
    path = "/data/subfolder1/text.txt"
    path2 = "http://localhost:8081/data"
    remote_base_path = "data"
    result = webdav_client.filter_after_global_base_path(path, remote_base_path)
    result2 = webdav_client.filter_after_global_base_path(path2, remote_base_path)
    assert result == "subfolder1/text.txt"
    # assert result2 ==


def test_list_files(webdav_client) -> None:
    remote_base_path = "data"
    url = os.path.join(webdav_client.hostname, remote_base_path)
    url = url.replace(os.sep, "/")
    files = webdav_client.list_files(url, remote_base_path)
    assert "/data/Readme.md" in files


def test_list_folders(webdav_client):
    folders = webdav_client.list_folders("data")
    assert "subfolder1" in folders
    assert "subfolder2" in folders
    assert "subfolder3" in folders


def test_get_sub_path(webdav_client) -> None:
    full_path = "/data/subfolder1/text.txt"
    initial_part = "data"
    result = webdav_client.get_sub_path(full_path, initial_part)
    assert result == "subfolder1/text.txt"


def test_download_files(webdav_client) -> None:

    global_remote_base_path = "data"
    remote_base_path = "data"
    local_base_path = "local_data"

    webdav_client.download_files(
        global_remote_base_path, remote_base_path, local_base_path
    )
    assert os.path.exists(os.path.join(local_base_path, "Readme.md"))


def test_download_all_files_iterative(webdav_client):

    remote_base_path = "data"
    local_base_path = "local_data"

    webdav_client.download_all_files_iterative(remote_base_path, local_base_path)
    assert os.path.exists(os.path.join(local_base_path, "Readme.md"))
    assert os.path.exists(os.path.join(local_base_path, "subfolder1/text.txt"))


if __name__ == "__main__":
    pytest.main()
