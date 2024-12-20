"""
Module to set up and run a WebDAV server using Cheroot WSGI server and WsgiDAVApp.

The server is configured to serve files from the 'tests/remote' directory and listens on port 8081.
Logging is enabled, and directory browsing is allowed.

Serves as starting point for unit test my application :smile:

"""

from cheroot import wsgi
from wsgidav.wsgidav_app import WsgiDAVApp

from loguru import logger

import os


def create_web_dav_server() -> None:

    current_path = os.getcwd()
    folder_name = "webdav_root"
    cheroot_root_path = os.path.join(current_path, folder_name)
    logger.info("Cheroot root path is:", cheroot_root_path)

    # https://wsgidav.readthedocs.io/en/latest/user_guide_configure.html
    config = {
        "host": "0.0.0.0",
        "port": 8081,
        "provider_mapping": {"/": "tests/remote"},
        "verbose": 2,
        "logging": {
            "enable": True,
        },
        "auth": False,
        "simple_dc": {
            "user_mapping": {"*": True}
        },  #  {"testuser": {"password": "testpassword"}}
        "http_authenticator.accept_basic": True,  # Allow basic authentication, use with care!
        "http_authenticator.accept_digest": False,  # Allow digest authentication, consider security
        "http_authenticator.default_to_digest": False,  # If no digest authentication header was sent, use basic
        "dir_browser": {  # Configuration for the directory browser
            "enable": True,  # Enable directory browsing
            "response_trailer": True,  # Enable trailing slash in responses
            "show_user": False,  # Show the user in the directory browser
        },
    }
    app = WsgiDAVApp(config)

    server_args = {
        "bind_addr": (config["host"], config["port"]),
        "wsgi_app": app,
    }
    server = wsgi.Server(**server_args)

    try:
        server.start()

    except KeyboardInterrupt:
        logger.info("Received Ctrl-C: stopping...")
    finally:
        server.stop()


if __name__ == "__main__":
    create_web_dav_server()
