#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
import urllib2
import json

def do_http(method, url, params={}, headers={}, timeout=60):
    """
    do http request
    """
    method = method.upper()
    if not isinstance(params, dict) or not isinstance(headers, dict):
        raise Exception('params and headers must be dict')
    if len(params) > 0:
        if method == 'GET':
            data = urllib.urlencode(params)
            request = urllib2.Request('%s?%s' %(url, data))
        else:
            if headers.get('Content-Type', '').lower() == 'application/json':
                data = json.dumps(params)
            else:
                data = urllib.urlencode(params)
            request = urllib2.Request(url, data=data)
    else:
        request = urllib2.Request(url)
    for key,val in headers.items():
        request.add_header(key, val)
    request.get_method = lambda: method
    response = urllib2.urlopen(request, timeout=timeout)
    data = response.read()
    response.close()
    return data


def do_api_request(method, url, params={}, headers={}, timeout=10):
    headers['Content-Type'] = 'application/json'
    data = do_http(method, url, params, headers, timeout)
    return json.loads(data)


if __name__ == '__main__':
    print do_api_request('GET', 'http://192.168.100.15:8088/api/v1/sla/business', headers={'org': 8888})


    