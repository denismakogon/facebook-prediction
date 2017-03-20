Facebook user signup date prediction
====================================

Prediction criteria
-------------------
Each user has pretty big activity history within his profile.
In order to detect approximate signup date it's necessary to define what kind of activities can be used as prediction bases.
For our particular case:
 * photos activities
 * posts activities

Both activity types are supplied with timestamps that can be used to determine approximate signup date by finding earliest activity.


Prediction precision
--------------------
Facebook shows user's signup month, so it's not possible to get day of the month when user signed up.
Using [Facebook Graph API](https://developers.facebook.com/docs/graph-api/reference) it is possible to get user earliest activity dates.
Each timestamp is defines within following format:

    2017-03-11T17:12:03+0000

So the prediction is based on earliest activity timestamp and based on it we can say that user signed up before that date.


Accessing posts and photos
--------------------------
Using following URLs Facebook Graph API allows to get list of activities.
For photos:

    curl -i -X GET https://graph.facebook.com/v2.8/me/photos?fields=created_time&type=uploaded&limit=100"

For posts:

    curl -i -X GET https://graph.facebook.com/v2.8/me/posts?fields=created_time&limit=100"

Each response supplied with `paging` data

    "paging": {
        "previous": "https://graph.facebook.com/v2.8/...",
        "next": "https://graph.facebook.com/v2.8/..."
    }

unless specified `limit` query parameter does not cover full range of activities.
Basically, we're interested in `"next"` field because it shows that there more data to get.


Algorithm
---------
As it can be seen each response from Facebook Graph can be supplied with next redirect URL, so prediction algorithm should be aware of how to handle such case.
Here are details how algorithm works:

 * try to get first 100 activities using incoming URL
 * if `"next"` found go back to previous step with new activity URL
 * if not, try to read/sort data by timestamp
 * for photos/posts activities - get very first timestamp
 * compare earliest photo and post activity timestamps and pick earliest

Algorithm: Edge cases
---------------------

It may appear that last redirect from `"next"` field would lead to an empty data, so algorithm should be able to handle this edge case by going back to previous URL stored in cache.

System requirements
-------------------

Python version: Python3.5 or greater
Dependencies can be found [here](requirements.txt).

Installation
------------

Clone repo:

    git clone git@github.com:denismakogon/facebook-prediction.git

If you're using `virtualenv`:

    python3 -mvenv .venv
    source .venv/bin/activate

Install app:

    pip install .

Usage
-----

Once app installed, you'll be able to find CLI tool:

    facebook-prediction

To see its usage information use following command:

    facebook-prediction --help
    Usage: facebook-prediction [OPTIONS] CSV_FILE
    
    Options:
      --fapikey TEXT  Facebook API Key
      --help          Show this message and exit.

Disclaimer
----------

To make app work it is necessary to [obtain Facebook Access Token](https://developers.facebook.com/docs/facebook-login/access-tokens).
According to Facebook policies Facebook app (this app in fact is Facebook app because it uses Facebook API with app-bound access token) 
should be authorized by users to grand an access to their account info (photos, posts, likes, etc.).
See more details on [bug report #1502515636638396](https://developers.facebook.com/bugs/1502515636638396/).
