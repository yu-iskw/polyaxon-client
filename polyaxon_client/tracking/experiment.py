# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import atexit
import json
import os
import sys
import time

from polyaxon_client import settings
from polyaxon_client.logger import logger
from polyaxon_client.tracking.base import BaseTracker, ensure_in_custer
from polyaxon_client.tracking.utils.code_reference import get_code_reference
from polyaxon_client.tracking.utils.env import get_run_env
from polyaxon_client.tracking.utils.tags import validate_tags


class Experiment(BaseTracker):
    def __init__(self,
                 project=None,
                 experiment_id=None,
                 client=None,
                 track_logs=None,
                 track_git=None,
                 track_env=None):
        if project is None and settings.IN_CLUSTER:
            experiment_info = self.get_experiment_info()
            project = experiment_info['project_name']
            experiment_id = experiment_info['experiment_name'].split('.')[-1]
        super(Experiment, self).__init__(project=project,
                                         client=client,
                                         track_logs=track_logs,
                                         track_git=track_git,
                                         track_env=track_env)

        self.experiment_id = experiment_id
        self.experiment = None
        self.last_status = None

    def create(self, name=None, tags=None, description=None, config=None):
        experiment_config = {'run_env': get_run_env()}
        if name:
            experiment_config['name'] = name
        if tags:
            experiment_config['tags'] = tags
        if description:
            experiment_config['description'] = description
        if config:
            experiment_config['config'] = config
        experiment = self.client.project.create_experiment(
            username=self.username,
            project_name=self.project_name,
            experiment_config=experiment_config)
        self.experiment_id = (experiment.id
                              if self.client.api_config.schema_response
                              else experiment.get('id'))
        self.experiment = experiment
        self.last_status = 'created'
        self.log_code_ref()

        if not settings.IN_CLUSTER:
            self._start()

        return self

    def _start(self):
        atexit.register(self._end)
        self.start()

        def excepthook(exception, value, tb):
            self.failed(message='Type: {}, Value: {}'.format(exception, value))
            # Resume normal work
            sys.__excepthook__(exception, value, tb)

        sys.excepthook = excepthook

    def _end(self):
        self.succeeded()

    def end(self, status, message=None):
        if self.last_status in ['succeeded', 'failed', 'stopped']:
            return
        self.log_status(status, message)
        self.last_status = status
        time.sleep(0.1)  # Just to give the opportunity to the worker to pick the message

    def start(self):
        self.log_status('running')
        self.last_status = 'running'

    def succeeded(self):
        self.end('succeeded')

    def stop(self):
        self.end('stopped')

    def failed(self, message=None):
        self.end(status='failed', message=message)

    def log_run_env(self):
        patch_dict = {'run_env': get_run_env()}
        self.client.experiment.update_experiment(username=self.username,
                                                 project_name=self.project_name,
                                                 experiment_id=self.experiment_id,
                                                 patch_dict=patch_dict,
                                                 background=True)

    def log_code_ref(self):
        self.client.experiment.create_code_reference(username=self.username,
                                                     project_name=self.project_name,
                                                     experiment_id=self.experiment_id,
                                                     coderef=get_code_reference(),
                                                     background=True)

    def log_status(self, status, message=None):
        self.client.experiment.create_status(username=self.username,
                                             project_name=self.project_name,
                                             experiment_id=self.experiment_id,
                                             status=status,
                                             message=message,
                                             background=True)

    def log_metrics(self, **metrics):
        self.client.experiment.create_metric(username=self.username,
                                             project_name=self.project_name,
                                             experiment_id=self.experiment_id,
                                             values=metrics,
                                             background=True)

    def log_tags(self, tags, reset=False):
        patch_dict = {'tags': validate_tags(tags)}
        if reset is False:
            patch_dict['merge'] = True
        self.client.experiment.update_experiment(username=self.username,
                                                 project_name=self.project_name,
                                                 experiment_id=self.experiment_id,
                                                 patch_dict=patch_dict,
                                                 background=True)

    def log_params(self, reset=False, **params):
        patch_dict = {'declarations': params}
        if reset is False:
            patch_dict['merge'] = True
        self.client.experiment.update_experiment(username=self.username,
                                                 project_name=self.project_name,
                                                 experiment_id=self.experiment_id,
                                                 patch_dict=patch_dict,
                                                 background=True)

    def set_description(self, description):
        self.client.experiment.update_experiment(username=self.username,
                                                 project_name=self.project_name,
                                                 experiment_id=self.experiment_id,
                                                 patch_dict={'description': description},
                                                 background=True)

    def set_name(self, name):
        self.client.experiment.update_experiment(username=self.username,
                                                 project_name=self.project_name,
                                                 experiment_id=self.experiment_id,
                                                 patch_dict={'name': name},
                                                 background=True)

    def log_data_ref(self, data, data_name='data', reset=False):
        try:
            import hashlib

            params = {
                data_name: hashlib.md5(str(data).encode("utf-8")).hexdigest()[:settings.HASH_LENGTH]
            }
            patch_dict = {'data_refs': params}
            if reset is False:
                patch_dict['merge'] = True
            self.client.experiment.update_experiment(username=self.username,
                                                     project_name=self.project_name,
                                                     experiment_id=self.experiment_id,
                                                     patch_dict=patch_dict,
                                                     background=True)
        except Exception as e:
            logger.warning('Could create data hash %s', e)

    @staticmethod
    def get_cluster_def():
        """Returns cluster definition created by polyaxon.
        {
            "master": ["plxjob-master0-8eefb7a1146f476ca66e3bee9b88c1de:2000"],
            "worker": ["plxjob-worker1-8eefb7a1146f476ca66e3bee9b88c1de:2000",
                       "plxjob-worker2-8eefb7a1146f476ca66e3bee9b88c1de:2000"],
            "ps": ["plxjob-ps3-8eefb7a1146f476ca66e3bee9b88c1de:2000"],
        }
        :return: dict
        """
        ensure_in_custer()

        cluster = os.getenv('POLYAXON_CLUSTER', None)
        try:
            return json.loads(cluster) if cluster else None
        except (ValueError, TypeError):
            print('Could get cluster definition, '
                  'please make sure this is running inside a polyaxon job.')
            return None

    @staticmethod
    def get_task_info():
        """Returns the task info: {"type": str, "index": int}."""
        ensure_in_custer()

        info = os.getenv('POLYAXON_TASK_INFO', None)
        try:
            return json.loads(info) if info else None
        except (ValueError, TypeError):
            print('Could get task info, '
                  'please make sure this is running inside a polyaxon job.')
            return None

    @classmethod
    def get_tf_config(cls, envvar='TF_CONFIG'):
        """
        Returns the TF_CONFIG defining the cluster and the current task.
        if `envvar` is not null, it will set and env variable with `envvar`.
        """
        ensure_in_custer()

        cluster_def = cls.get_cluster_def()
        task_info = cls.get_task_info()
        tf_config = {
            'cluster': cluster_def,
            'task': task_info,
            'model_dir': Experiment.get_outputs_path(),
            'environment': 'cloud'
        }

        if envvar:
            os.environ[envvar] = json.dumps(tf_config)

        return tf_config

    @staticmethod
    def get_experiment_info():
        """
        Returns information about the experiment:
            * project_name
            * experiment_group_name
            * experiment_name
            * project_uuid
            * experiment_group_uuid
            * experiment_uuid
        """
        ensure_in_custer()

        info = os.getenv('POLYAXON_EXPERIMENT_INFO', None)
        try:
            return json.loads(info) if info else None
        except (ValueError, TypeError):
            print('Could get experiment info, '
                  'please make sure this is running inside a polyaxon job.')
            return None

    @staticmethod
    def get_declarations():
        """
        Returns all the experiment declarations based on both:
            * declarations section
            * matrix section
        """
        ensure_in_custer()

        declarations = os.getenv('POLYAXON_DECLARATIONS', None)
        try:
            return json.loads(declarations) if declarations else None
        except (ValueError, TypeError):
            print('Could get declarations, '
                  'please make sure this is running inside a polyaxon job.')
            return None