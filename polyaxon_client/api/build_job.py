# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from polyaxon_client.api.base import BaseApiHandler
from polyaxon_client.exceptions import PolyaxonClientException
from polyaxon_client.schemas import JobConfig, JobStatusConfig


class BuildJobApi(BaseApiHandler):
    """
    Api handler to get build jobs from the server.
    """
    ENDPOINT = "/"

    def get_build(self, username, project_name, job_id):
        request_url = self.build_url(self._get_http_url(),
                                     username,
                                     project_name,
                                     'builds',
                                     job_id)
        try:
            response = self.transport.get(request_url)
            return self.prepare_results(response_json=response.json(), config=JobConfig)
        except PolyaxonClientException as e:
            self.transport.handle_exception(e=e, log_message='Error while retrieving build')
            return None

    def update_build(self, username, project_name, job_id, patch_dict, background=False):
        request_url = self.build_url(self._get_http_url(),
                                     username,
                                     project_name,
                                     'builds',
                                     job_id)

        if background:
            self.transport.async_patch(request_url, json_data=patch_dict)
            return None

        try:
            response = self.transport.patch(request_url, json_data=patch_dict)
            return self.prepare_results(response_json=response.json(), config=JobConfig)
        except PolyaxonClientException as e:
            self.transport.handle_exception(e=e, log_message='Error while updating build')
            return None

    def delete_build(self, username, project_name, job_id, background=False):
        request_url = self.build_url(self._get_http_url(),
                                     username,
                                     project_name,
                                     'builds',
                                     job_id)

        if background:
            self.transport.async_delete(request_url)
            return None

        try:
            return self.transport.delete(request_url)
        except PolyaxonClientException as e:
            self.transport.handle_exception(e=e, log_message='Error while deleting build')
            return None

    def get_statuses(self, username, project_name, job_id, page=1):
        request_url = self.build_url(self._get_http_url(),
                                     username,
                                     project_name,
                                     'builds',
                                     job_id,
                                     'statuses')
        try:
            response = self.transport.get(request_url, params=self.get_page(page=page))
            return self.prepare_list_results(response.json(), page, JobStatusConfig)
        except PolyaxonClientException as e:
            self.transport.handle_exception(
                e=e, log_message='Error while retrieving build statuses')
            return None

    def stop(self, username, project_name, job_id, background=False):
        request_url = self.build_url(self._get_http_url(),
                                     username,
                                     project_name,
                                     'builds',
                                     job_id,
                                     'stop')

        if background:
            self.transport.async_post(request_url)
            return None

        try:
            return self.transport.post(request_url)
        except PolyaxonClientException as e:
            self.transport.handle_exception(e=e, log_message='Error while stopping build')
            return None

    def bookmark(self, username, project_name, job_id, background=False):
        request_url = self.build_url(self._get_http_url(),
                                     username,
                                     project_name,
                                     'builds',
                                     job_id,
                                     'bookmark')

        if background:
            self.transport.async_post(request_url)
            return None

        try:
            return self.transport.post(request_url)
        except PolyaxonClientException as e:
            self.transport.handle_exception(e=e, log_message='Error while bookmarking build')
            return None

    def unbookmark(self, username, project_name, job_id, background=False):
        request_url = self.build_url(self._get_http_url(),
                                     username,
                                     project_name,
                                     'builds',
                                     job_id,
                                     'unbookmark')

        if background:
            self.transport.async_delete(request_url)
            return None

        try:
            return self.transport.delete(request_url)
        except PolyaxonClientException as e:
            self.transport.handle_exception(e=e, log_message='Error while unbookmarking build')
            return None

    def resources(self, username, project_name, job_id, message_handler=None):
        """Streams builds resources using websockets.

        message_handler: handles the messages received from server.
            e.g. def f(x): print(x)
        """
        request_url = self.build_url(self._get_ws_url(),
                                     username,
                                     project_name,
                                     'builds',
                                     job_id,
                                     'resources')
        self.transport.socket(request_url, message_handler=message_handler)

    # pylint:disable=inconsistent-return-statements
    def logs(self, username, project_name, job_id, stream=True, message_handler=None):
        """Streams builds logs using websockets.

        message_handler: handles the messages received from server.
            e.g. def f(x): print(x)
        """
        if not stream:
            request_url = self.build_url(self._get_http_url(),
                                         username,
                                         project_name,
                                         'builds',
                                         job_id,
                                         'logs')

            try:
                return self.transport.get(request_url)
            except PolyaxonClientException as e:
                self.transport.handle_exception(e=e, log_message='Error while retrieving builds')
                return []

        request_url = self.build_url(self._get_ws_url(),
                                     username,
                                     project_name,
                                     'builds',
                                     job_id,
                                     'logs')
        self.transport.stream(request_url, message_handler=message_handler)

    def get_heartbeat_url(self, username, project_name, job_id):
        return self.build_url(self._get_http_url(),
                              username,
                              project_name,
                              'builds',
                              job_id,
                              self.HEARTBEAT)
