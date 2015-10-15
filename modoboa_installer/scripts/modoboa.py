"""Modoboa related tasks."""

import os

from .. import database
from .. import python
from .. import utils

from . import base
from . import install


class Modoboa(base.Installer):

    """Modoboa installation."""

    appname = "modoboa"
    no_daemon = True
    packages = ["python-dev", "libxml2-dev", "libxslt-dev", "rrdtool"]
    with_db = True
    with_user = True

    def __init__(self, config):
        """Get configuration."""
        super(Modoboa, self).__init__(config)
        self.venv_path = config.get("modoboa", "venv_path")

    def setup_database(self):
        """Additional config."""
        super(Modoboa, self).setup_database()
        if self.config.getboolean("amavis", "enabled"):
            database.grant_database_access(
                self.config, self.config.get("amavis", "dbname"), self.dbname)

    def _setup_venv(self):
        """Prepare a dedicated virtuelenv."""
        python.setup_virtualenv(self.venv_path, sudo_user=self.user)
        packages = ["modoboa", "py-rrdtool"]
        if self.dbengine == "postgres":
            packages.append("psycopg2")
        else:
            packages.append("MYSQL-Python")
        python.install_packages(packages, self.venv_path, sudo_user=self.user)

    def _deploy_instance(self):
        """Deploy Modoboa."""
        prefix = ". {}; ".format(
            os.path.join(self.venv_path, "bin", "activate"))
        args = [
            "--collectstatic",
            "--timezone", self.config.get("modoboa", "timezone"),
            "--domain", self.config.get("general", "hostname"),
            "--extensions", "all",
            "--dburl", "default:{0}://{1}:{2}@localhost/{1}".format(
                self.config.get("database", "engine"), self.dbname,
                self.dbpasswd)
        ]
        if self.config.getboolean("amavis", "enabled"):
            args += [
                "amavis:{}://{}:{}@localhost/{}".format(
                    self.config.get("database", "engine"),
                    self.user, self.dbpasswd,
                    self.config.get("amavis", "dbname")
                )
            ]

        utils.exec_cmd(
            "bash -c '{} modoboa-admin.py deploy instance {}'".format(
                prefix, " ".join(args)),
            sudo_user=self.user, cwd=self.home_dir)

    def post_run(self):
        """Additional tasks."""
        self._setup_venv()
        self._deploy_instance()
        install("uwsgi", self.config)
        install("nginx", self.config)