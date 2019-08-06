import logging.config
import os
from typing import Dict
import pathlib

import sh
from cement import App, TestApp, init_defaults
from cement.core.exc import CaughtSignal
from cement.utils import fs

from tank.core.cloud_settings import CloudUserSettings
from tank.core.exc import TankError
from tank.controllers.base import Base
from tank.controllers.cluster import NestedCluster, EmbeddedCluster
from tank.logging_conf import build_logging_conf


def _default_config() -> Dict:
    config = init_defaults('tank',
                           'log.logging')

    config['tank'] = {
        'terraform_run_command': 'terraform',
        'terraform_inventory_run_command': 'terraform-inventory',
    }

    config['log.logging']['level'] = 'WARNING'

    return config


class MixbytesTank(App):
    """MixBytes Tank primary application."""

    class Meta:
        label = 'tank'

        # configuration defaults
        config_defaults = _default_config()

        # call sys.exit() on close
        close_on_exit = True

        # load additional framework extensions
        extensions = [
            'yaml',
            'colorlog',
            'jinja2',
        ]

        # List of configuration directory
        config_dirs = ['~/.tank']

        # configuration handler
        config_handler = 'yaml'

        # configuration file suffix
        config_file_suffix = '.yml'

        # set the log handler
        log_handler = 'colorlog'

        # set the output handler
        output_handler = 'jinja2'

        template_handler = 'jinja2'

        # register handlers
        handlers = [
            Base,
            EmbeddedCluster,
            NestedCluster,
        ]

        # register hooks
        hooks = [
        ]

    def __init__(self):
        super().__init__()
        self._cloud_settings = None

    def setup(self):
        super(MixbytesTank, self).setup()
        fs.ensure_dir_exists(self.user_dir)

    @property
    def app_env(self) -> Dict:
        env = os.environ.copy()
        env["TF_LOG"] = "TRACE"
        env["TF_IN_AUTOMATION"] = "true"
        return env

    @property
    def cloud_settings(self) -> CloudUserSettings:
        if self._cloud_settings is None:
            self._cloud_settings = CloudUserSettings(self.config)

        return self._cloud_settings

    @property
    def terraform_run_command(self) -> str:
        return self.config.get(self.Meta.label, 'terraform_run_command')

    @property
    def terraform_inventory_run_command(self) -> str:
        return self.config.get(self.Meta.label, 'terraform_inventory_run_command')

    @property
    def user_dir(self) -> str:
        return fs.abspath(fs.join(pathlib.Path.home(), '.tank'))


class MixbytesTankTest(TestApp, MixbytesTank):
    """A sub-class of MixbytesTank that is better suited for testing."""

    class Meta:
        label = 'tank'


def main():
    with MixbytesTank() as app:
        logs_dir = os.path.join(app.user_dir, 'logs')
        logging.config.dictConfig(build_logging_conf(logs_dir=logs_dir))

        try:
            app.run()

        except TankError as e:
            print('{}: {}'.format(e.__class__.__name__, e))
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        # FIXME better signal handling
        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print('\n%s' % e)
            app.exit_code = 0


if __name__ == '__main__':
    main()
