#!/usr/bin/python
#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# WSGI implementation to replace the CGI cmd.cgi for the Nagios external
# command PROCESS_SERVICE_CHECK_RESULT
#

import os
import time
from urlparse import parse_qs


PROCESS_CHECK_CMD = 'PROCESS_SERVICE_CHECK_RESULT'
VALID_STATES = range(0, 4)


class NagiosNotReady(Exception):
    pass


def http_response(response, status_string, output=None):
    if output is None:
        output = ''
    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    response(status_string, response_headers)
    return [output]


def validate_params(params):
    cmd_mod = params.get('cmd_mod')
    if not cmd_mod or not len(cmd_mod) or not len(cmd_mod[0]):
        raise Exception('cmd_mod parameter is required')
    try:
        cmd_mod = int(cmd_mod[0])
    except:
        raise Exception('cmd_mod is invalid')
    if cmd_mod != 2:
        raise Exception('cmd_mod is invalid, cmd_mod must be set to 2')

    cmd_typ = params.get('cmd_typ')
    if not cmd_typ or not len(cmd_typ) or not len(cmd_typ[0]):
        raise Exception('cmd_typ parameter is required')
    try:
        cmd_typ = int(cmd_typ[0])
    except:
        raise Exception('cmd_typ is invalid')
    if cmd_typ != 30:
        raise Exception('only cmd_typ=30 is supported (PROCESS_SERVICE_CHECK_RESULT)')

    state = params.get('plugin_state')
    if not state or not len(state) or not len(state[0]):
        raise Exception('plugin_state parameter is required')
    try:
        state = int(state[0])
    except:
        raise Exception('state is invalid')
    if state not in VALID_STATES:
        raise Exception('wrong state, valid state is one of {}'.format(VALID_STATES))

    service = params.get('service')
    if not service or not len(service) or not len(service[0]):
        raise Exception('service parameter is required')

    host = params.get('host')
    if not host or not len(host) or not len(host[0]):
        raise Exception('host parameter is required')

    output = params.get('plugin_output')
    if not output or not len(output) or not len(output[0]):
        raise Exception('plugin_output parameter is required')


def write_command(cmd_file, p, timestamp):
    if not os.path.exists(cmd_file):
        raise NagiosNotReady()

    cmd = "[{timestamp}] {cmd};{host};{service};{state};{output}".format(
        timestamp=timestamp,
        cmd=PROCESS_CHECK_CMD,
        host=p['host'][0],
        service=p['service'][0],
        state=p['plugin_state'][0],
        output=p['plugin_output'][0]
    )
    with open(cmd_file, "w") as f:
        f.write(cmd + "\n")


def application(environ, response):

    if environ.get('REQUEST_METHOD') != 'POST':
        return http_response(response, '405 Method Not Allowed')

    timestamp = int(time.time())
    data = environ['wsgi.input']
    query_string = data.read()
    try:
        params = parse_qs(query_string, False, True)
    except ValueError as e:
        status = '400 Bad Request'
        return http_response(response, status, str(e))
    try:
        validate_params(params)
    except Exception as e:
        return http_response(response, '400 Bad Request', str(e))

    cmd_file = environ.get('NAGIOS_CMD_FILE', '/var/lib/nagios3/rw/nagios.cmd')
    try:
        write_command(cmd_file, params, timestamp)
    except NagiosNotReady:
        return http_response(response, '503 Service Unavailable')
    except Exception as e:
        return http_response(response, '500 Internal Server Error', str(e))

    return http_response(response, '204 No Content')

