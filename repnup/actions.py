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

import aiohttp
import asyncio
import json as builtinjson
import pandas
import time
import typing  # noqa
import ujson


PHOTOS_URL = ("https://graph.facebook.com/v2.8/"
              "{0}/photos?"
              "fields=created_time&"
              "type=uploaded&"
              "limit=150&"
              "access_token={1}")

POSTS_URL = ("https://graph.facebook.com/v2.8/"
             "{0}/posts?"
             "fields=created_time&"
             "limit=150&"
             "access_token={1}")


def to_string_time(timestamp: time.struct_time):
    return time.strftime("%Y-%m-%d", timestamp)


def to_time(photo: dict):
    """
    Reversed comparator functions
    :param photo: represents photo object to filter
    :type photo: dict
    :return: time.struct_time
    :rtype: time.struct_time
    """
    return time.strptime(photo['created_time'][:-5], "%Y-%m-%dT%H:%M:%S")


def skip_data_hook(d: dict):
    """
    JSON filter function.
    Used to ignore significant amount of JSON object
    by excluding `data` field to decrease time.
    :param d:
    :return:
    """
    return {k: v for k, v in d.items() if k != "data"}


class HTTPAPIException(Exception):

    def __init__(self, message, fbtrace_id):
        self.final_message = ("Unable to accomplish request. "
                              "Message: {0}. Facebook trace ID: {1}"
                              .format(message, fbtrace_id))
        super(HTTPAPIException, self).__init__(self.final_message)

    def __str__(self):
        return self.final_message


async def raise_from_response(response: aiohttp.ClientResponse):
    """
    Raises exception from response code including additional processing
    :param response: aiohttp response object
    :type response: aiohttp.ClientResponse
    :return:
    """
    try:
        response.raise_for_status()
    except Exception:
        # errors often returned as JSON objects
        json = await response.json()
        message = json['error']['message']
        fbtrace_id = json['error']['code']
        raise HTTPAPIException(message, fbtrace_id)


async def do_get(session, action_url):
    """

    :param session: aiohttp http session
    :type session: aiohttp.ClientSession
    :param action_url: HTTP URL
    :type action_url: str
    :return: raw text response body
    :rtype: str
    """
    response = await session.get(action_url)
    await raise_from_response(response)
    raw_data = await response.text()
    response.close()
    return raw_data


async def find_earliest_activity(delivery: asyncio.Future,
                                 action_url: str,
                                 loop: asyncio.AbstractEventLoop=None,
                                 external_fallback_urls=None):
    """
    Finds earliest activities made by user
    :param delivery: shared future as delivery channel
    :type delivery: asyncio.Future
    :param action_url: API Graph URL to examine
    :type action_url: str
    :param loop: asyncio event loop
    :type loop: asyncio.AbstractEventLoop
    :param external_fallback_urls: list of URLs for going
    back if no data supplied on the last level
    :type external_fallback_urls"
    :rtype: list
    :return: None
    """
    # Required if no data supplied by the last redirect
    if not external_fallback_urls:
        external_fallback_urls = []
    delivery._state = asyncio.futures._PENDING
    try:

        with aiohttp.ClientSession(loop=loop) as session:
            raw_data = await do_get(session, action_url)
            next_field = "\"next\":"
            if next_field in raw_data:
                json = builtinjson.loads(raw_data, object_hook=skip_data_hook)
                url = json['paging']['next']
                external_fallback_urls.append(url)
                await find_earliest_activity(
                    delivery, url, loop=loop,
                    external_fallback_urls=external_fallback_urls)
            else:
                json = ujson.loads(raw_data)
                # there's possible case when API Graph would return empty
                # data set on last redirect (last "next" cursor URL)
                if len(json['data']) == 0:
                    # At the end "external_fallback_urls" will contain N URLs
                    # including the last one that was supplied with no data.
                    # So, we need to get one before the last URL
                    # that was supplied with data.
                    #
                    # In any case "external_fallback_urls" will
                    # contain 0, 2 (or more) items.
                    # If length of "external_fallback_urls" equals to 0,
                    # than data is supplied with no cursor
                    # redirects and data was provided.
                    #
                    # In case if length of "external_fallback_urls"
                    # is greater than 2,
                    # it means that previous request had cursor redirect
                    # and the last request came with no data.
                    #
                    if len(external_fallback_urls) != 0:
                        raw_data = await do_get(
                            session, external_fallback_urls[-2])

                json = ujson.loads(raw_data)
                delivery.set_result(
                    (to_time(date) for date in sorted(
                        json.get('data'), key=to_time)))
                delivery.done()

    except (Exception, aiohttp.HttpProcessingError, HTTPAPIException) as ex:
        delivery.set_exception(ex)
        raise ex


def await_min_date(delivery: asyncio.Future, tasks: list,
                   loop: asyncio.AbstractEventLoop=None):
    dates = []

    def done_callback(future):
        awaited_dates = future.result()
        dates.extend(awaited_dates)
        future._state = asyncio.futures._PENDING

    delivery.add_done_callback(done_callback)
    loop.run_until_complete(asyncio.wait(tasks, loop=loop))
    delivery.done()
    return min(dates)


def get_signup_date(fbid, username, access_token,
                    loop: asyncio.AbstractEventLoop=None):
    """
    Calculates approximate date of signup
    :param fbid: User Facebook ID
    :type fbid: str
    :param username: User's name and surname
    :type username: str
    :param access_token: Facebook API Access Token
    :type access_token: str
    :param loop: asyncio event loop
    :type loop: asyncio.AbstractEventLoop
    :return: None
    """
    delivery = asyncio.Future(loop=loop)
    tasks = [
        find_earliest_activity(delivery, PHOTOS_URL.format(
            fbid, access_token), loop=loop),
        find_earliest_activity(delivery, POSTS_URL.format(
            fbid, access_token), loop=loop)
    ]

    result = await_min_date(delivery, tasks, loop=loop)
    print("{},{},{}".format(username, fbid, to_string_time(result)))


def generate_from_frame(df: pandas.DataFrame, facebook_access_token: str,
                        loop: asyncio.AbstractEventLoop=None):
    """
    Generates user's signup date though whole data frame
    :param df: pandas data frame
    :type df: pandas.DataFrame
    :param facebook_access_token: Facebook API Access Token
    :type facebook_access_token: str
    :param loop: asyncio event loop
    :type loop: asyncio.AbstractEventLoop
    :return: generator
    :rtype: typing.Generator
    """
    for index, row in df.iterrows():
        yield get_signup_date(row['fbid'], row['username'],
                              facebook_access_token, loop=loop)
