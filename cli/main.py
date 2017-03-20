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
import click
import pandas as pd
import sys
import uvloop

from repnup import actions


@click.command('facebook')
@click.option('--fapikey',
              help="Facebook Access Token", envvar='FAPIKEY')
@click.argument("csv-file", type=click.Path())
def facebook(fapikey, csv_file):
    sys.tracebacklimit = 0
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    event_loop = asyncio.get_event_loop()

    df = pd.read_csv(csv_file, sep=",",
                     names=["fbid", "token", "username"],
                     low_memory=False)
    df_g = actions.generate_from_frame(df, fapikey, loop=event_loop)

    try:
        while True:
            next(df_g)
            click.confirm("Next item?", abort=True)
    except (actions.HTTPAPIException, KeyboardInterrupt, StopIteration) as ex:
        if isinstance(ex, StopIteration):
            print("--------End of dataframe--------")
        if isinstance(ex, actions.HTTPAPIException):
            print(ex.final_message)
    finally:
        event_loop.close()


if __name__ == "__main__":
    facebook()
