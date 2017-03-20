# All Rights Reserved.
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

import asyncio
import uvloop
import testtools

from repnup import actions
from repnup.tests import inputs


def test_wrapper(*args, **kwargs):
    def wrap(action):
        self = args[0]
        self.orig_do_get = actions.do_get
        try:
            action(*args, **kwargs)
        except Exception:
            pass
        finally:
            actions.do_get = self.orig_do_get


class TestAPI(testtools.TestCase):

    def setUp(self):
        try:
            self.testloop = asyncio.get_event_loop()
        except Exception:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            self.testloop = asyncio.get_event_loop()

        self.valid_data = inputs.valid_data
        self.error_data = inputs.error_data

        self.orig_do_get = actions.do_get
        actions.do_get = asyncio.coroutine(lambda x, y: self.valid_data)

        super(TestAPI, self).setUp()

    def tearDown(self):
        actions.do_get = self.orig_do_get
        super(TestAPI, self).tearDown()

    @test_wrapper
    def test_something(self):
        actions.get_signup_date("1017956283620377", "me", "token", loop=self.testloop)
