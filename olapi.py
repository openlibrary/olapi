r"""Open Library API Client.

    ol = OpenLibrary("http://0.0.0.0:8080")
    ol.login('joe', 'secret')
    
    page = ol.get("/sandbox")
    print page["body"]

    page["body"] += "\n\nTest from API"
    ol.save("/sandbox", page, "test from api")
"""

__version__ = "0.1"
__author__ = "Anand Chitipothu <anandology@gmail.com>"

import urllib, urllib2
import simplejson
import datetime
import re

class OpenLibrary:
    def __init__(self, base_url="http://openlibrary.org"):
        self.base_url = base_url
        self.cookie = None

    def _request(self, path, method='GET', data=None, headers=None):
        url = self.base_url + path
        
        headers = headers or {}
        if self.cookie:
            headers['Cookie'] = self.cookie
        
        req = urllib2.Request(url, data, headers)
        req.get_method = lambda: method
        return urllib2.urlopen(req)

    def login(self, username, password):
        """Login to Open Library with given credentials.
        """
        headers = {'Content-Type': 'application/json'}  
        try:      
            data = simplejson.dumps(dict(username=username, password=password))
            response = self._request('/account/login', method='POST', data=data, headers=headers)
        except urllib2.HTTPError, e:
            response = e
        
        if 'Set-Cookie' in response.headers:
            cookies = response.headers['Set-Cookie'].split(',')
            self.cookie =  ';'.join([c.split(';')[0] for c in cookies])

    def get(self, key):
        data = self._request(key + '.json').read()
        return unmarshal(simplejson.loads(data))

    def save(self, key, data, comment=None):
        headers = {'Content-Type': 'application/json'}
        data = marshal(data)
        data["_comment"] = comment
        data = simplejson.dumps(data)
        return self._request(key, method="PUT", data=data, headers=headers).read()

    def save_many(self, query, comment=None, action=None):
        headers = {'Content-Type': 'application/json'}
        query = marshal(query)
        data = dict(query=simplejson.dumps(query), comment=comment, action=action)
        return self._request("/api/save_many", method="POST", data=urllib.urlencode(data)).read()
        
    def write(self, query, comment="", action=""):
        """Internal write API."""
        query = marshal(query)
        data = dict(query=simplejson.dumps(query), comment=comment, action=action)
        response = self._request('/api/write', method='POST', data=urllib.urlencode(data))
        return simplejson.loads(response.read())

def marshal(data):
    """Serializes the specified data in the format required by OL.

        >>> marshal(datetime.datetime(2009, 1, 2, 3, 4, 5, 6789))
        {'type': '/type/datetime', 'value': '2009-01-02T03:04:05.006789'}
    """
    if isinstance(data, list):
        return [marshal(d) for d in data]
    elif isinstance(data, dict):
        return dict((k, marshal(v)) for k, v in data.iteritems())
    elif isinstance(data, datetime.datetime):
        return {"type": "/type/datetime", "value": data.isoformat()}
    elif isinstance(data, Text):
        return {"type": "/type/text", "value": unicode(data)}
    elif isinstance(data, Reference):
        return {"key": unicode(data)}
    else:
        return data

def unmarshal(d):
    u"""Converts OL serialized objects to python.

    >>> unmarshal({"type": "/type/text", "value": "hello, world"})
    <text: u'hello, world'>
    >>> unmarshal({"type": "/type/datetime", "value": "2009-01-02T03:04:05.006789"})
    datetime.datetime(2009, 1, 2, 3, 4, 5, 6789)
    """
    if isinstance(d, list):
        return [unmarshal(v) for v in d]
    elif isinstance(d, dict):
        if 'key' in d and len(d) == 1:
            return Reference(d['key'])
        elif 'value' in d and 'type' in d:
            if d['type'] == '/type/text':
                return Text(d['value'])
            elif d['type'] == '/type/datetime':
                return parse_datetime(d['value'])
            else:
                return d['value']
        else:
            return dict([(k, unmarshal(v)) for k, v in d.iteritems()])
    else:
        return d

def parse_datetime(value):
    """Parses ISO datetime formatted string.

        >>> parse_datetime("2009-01-02T03:04:05.006789")
        datetime.datetime(2009, 1, 2, 3, 4, 5, 6789)
    """
    if isinstance(value, datetime.datetime):
        return value
    else:
        tokens = re.split('-|T|:|\.| ', value)
        return datetime.datetime(*map(int, tokens))

class Text(unicode):
    def __repr__(self):
        return "<text: %s>" % unicode.__repr__(self)

class Reference(unicode):
    def __repr__(self):
        return "<ref: %s>" % unicode.__repr__(self)
