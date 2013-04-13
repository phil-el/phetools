# -*- coding: utf-8 -*-

import sys
sys.path.append("/home/phe/pywikipedia")
import query
import wikipedia
import time
import datetime
import re

class UnormalizedTitle(Exception):
    """Some title are not normalized"""

def getSite(site):
    if site == None:
        # FIXME: this is really wrong but nowadays many script depends on this
        # behavior, fix them first.
        return wikipedia.getSite(code = 'fr')
    return site

# FIXME: add a function to check for any warning, print them; and throw on
# error

def diff_time(a, b):
    d = a - b
    diff = d.days * 86400.0
    diff += d.seconds
    diff /= 86400
    return diff

def empty_result(data):
    return len(data) == 1 and data.has_key('error') and data['error']['*'] == 'emptyresult'

def handle_normalized_title(data):
    from_to = {}
    if data.has_key(u'normalized'):
        for p in data[u'normalized']:
            from_to[p[u'to']] = p[u'from']
    for p in data[u'pages'].itervalues():
        p[u'orig_title'] = from_to.get(p[u'title'], p[u'title'])

def GetHistory( site, titles, extraParams = None ):
    """
    titles may be either a title (as a string), or a list of strings
    extraParams if given must be a dict() as taken by query.GetData()
    """
    params = { u'action' : u'query' , u'prop' : u'revisions' }
    params[u'titles'] = query.ListToParam(titles)
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingHistory:
    """
    Wraps around another generator. Retrieves history of as many pages as
    stated by pageNumber from that generator, and yields them one after the
    other. Then retrieves more pages, etc.
    """
    # when contents == True, I got shortened results with pageNumber > 50
    def __init__(self, generator, depth, pageNumber=50, site = None, contents = False):
        self.site = getSite(site)
        self.generator = []
        for p in generator:
            if type(p) == wikipedia.Page:
                print >> sys.stderr, "warning: using obsolete Page object"
                self.generator.append(p.title())
            else:
                self.generator.append(p)
        self.pageNumber = pageNumber
        self.extraParams = { u'rvprop' : u'timestamp|ids' }
        # if depth != 1 ==> len(titles) == 1
        if depth != 1:
            # can't be checked, we don't know if len(generator) is supported
            #if len(generator) != 1:
            #    raise ValueError(u"PreloadingHistory, bad parms, depth != 1 and multiple titles")
            self.extraParams = { u'rvlimit' : str(depth) }
        if contents:
            self.extraParams[u'rvprop'] += u'|content'

    def preload(self, pages):
        data = GetHistory(self.site, pages, self.extraParams)
        if data.has_key('query-continue'):
            print "ERROR PreloadingHistory: query-continue not handled"
        return data[u'query'][u'pages']

    def __iter__(self):
        # FIXME : not complete, given the depth param we must iterate over
        # each history which is 1) not complete 2) with cur_depth < depth

        # this array will contain up to pageNumber pages and will be flushed
        # after these pages have been preloaded and yielded.
        somePages = []
        for page in self.generator:
            somePages.append(page)
            if len(somePages) >= self.pageNumber:
                result = self.preload(somePages)
                for refpage in result.keys():
                    yield result[refpage]
                somePages = []
        # preload remaining pages
        if len(somePages):
            result = self.preload(somePages)
            for refpage in result.keys():
                yield result[refpage]


def GetPageinfoFromIds(site, pageids, extraParams = None ):
    """
    titles may be either a title (as a string), or a list of strings
    extraParams if given must be a dict() as taken by query.GetData()
    """
    params = { u'action' : u'query',
               u'pageids' : query.ListToParam(pageids) }
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingPageinfoFromIds:
    """
    Wraps around another generator. Retrieves page info from a list of page id.
    """
    # FIXME: is 500 ok for non bot account ?
    def __init__(self, generator, pageNumber=500, site = None):
        self.site = getSite(site)
        self.generator = []
        self.pageNumber = pageNumber
        for p in generator:
            if type(p) == wikipedia.Page:
                print >> sys.stderr, "warning: using obsolete Page object"
                self.generator.append(p.title())
            else:
                self.generator.append(p)

    def preload(self, pages):
        data = GetPageinfoFromIds(self.site, pages)
        return data[u'query'][u'pages']

    def __iter__(self):
        somePages = []
        for page in self.generator:
            somePages.append(page)
            if len(somePages) >= self.pageNumber:
                result = self.preload(somePages)
                for refpage in result.keys():
                    yield result[refpage]
                somePages = []
        # preload remaining pages
        if len(somePages):
            result = self.preload(somePages)
            for refpage in result.keys():
                yield result[refpage]

def GetPageinfoFromTitles(site, titles, extraParams = None ):
    """
    titles may be either a title (as a string), or a list of strings
    extraParams if given must be a dict() as taken by query.GetData()
    """
    params = { u'action' : u'query',
               # FIXME: in some case we don't even need prop=info
               u'prop' : u'info',
               u'titles' : query.ListToParam(titles) }
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingPageinfoFromTitles:
    """
    Wraps around another generator. Retrieves history of as many pages as
    stated by pageNumber from that generator, and yields them one after the
    other. Then retrieves more pages, etc.
    """
    def __init__(self, generator, pageNumber=50, site = None, extraParams = None):
        self.site = getSite(site)
        self.generator = []
        self.pageNumber = pageNumber
        self.extraParams = extraParams
        for p in generator:
            if type(p) == wikipedia.Page:
                print >> sys.stderr, "warning: using obsolete Page object"
                self.generator.append(p.title())
            else:
                self.generator.append(p)

    def preload(self, pages):
        data = GetPageinfoFromTitles(self.site, pages, self.extraParams)
        handle_normalized_title(data[u'query'])
        return data[u'query'][u'pages']

    def __iter__(self):
        somePages = []
        for page in self.generator:
            somePages.append(page)
            if len(somePages) >= self.pageNumber:
                result = self.preload(somePages)
                for refpage in result.keys():
                    yield result[refpage]
                somePages = []
        # preload remaining pages
        if len(somePages):
            result = self.preload(somePages)
            for refpage in result.keys():
                yield result[refpage]

def last_modified_since(pages):
    for p in PreloadingHistory(pages, 1):
        if not p.has_key(u'missing'):
            time_text = p[u'revisions'][0][u'timestamp']
            t = time.strptime(time_text, '%Y-%m-%dT%H:%M:%SZ')
            now = datetime.datetime(2005, 1, 1).utcnow()
            d = datetime.datetime(t[0], t[1], t[2], t[3], t[4], t[5], t[6])
            diff = diff_time(now, d)
            yield (p[u'title'], diff)

def elapsed_seconds(pages):
    for p in PreloadingHistory(pages, 1):
        time_text = p[u'revisions'][0][u'timestamp']
        t = time.strptime(time_text, '%Y-%m-%dT%H:%M:%SZ')
        yield time.mktime(t)

def GetCategoryMember( site, title, extraParams = None ):
    """ Usage example: data = GetCategoryMember('ru','Date')
    extraParams if given must be a dict() as taken by query.GetData()
    """
    params = { u'action' : u'query', u'generator' : u'categorymembers' }
    params[u'prop'] = u'info'
    params[u'gcmtitle'] = query.ListToParam(title)
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

# FIXME: handle inexistant category ?
# This is an internal function to query_ext, use PreloadingCategoryMember
# instead
class _PreloadingCategoryMember:
    """
    Wraps around a category contents generator. Retrieves as many pages as
    stated by pageNumber and yields them one after the other. Then retrieves
    more pages, etc.
    """
    def __init__(self, title, pageNumber=200, site = None, extraParams = None):
        self.site = getSite(site)
        self.title = title
        self.pageNumber = pageNumber
        self.gcmcontinue = None
        self.extraParams = extraParams
        if not self.extraParams:
            self.extraParams = {}

    def preload(self):
        extraParams =  { 'gcmlimit' : str(self.pageNumber) }
        if self.gcmcontinue:
            extraParams['gcmcontinue'] = self.gcmcontinue
            self.gcmcontinue = None # to stop iteration in __iter__()
        extraParams = query.CombineParams( extraParams, self.extraParams )
        result = GetCategoryMember(self.site, self.title, extraParams)
        if type(result) == type([]):
            return {}
        if result.has_key('query-continue'):
            self.gcmcontinue = result['query-continue']['categorymembers']['gcmcontinue']
        return result[u'query'][u'pages']

    def __iter__(self):
        datas = self.preload()
        while self.gcmcontinue:
            for p in datas.keys():
                yield datas[p]
            datas = self.preload()
        for p in datas.keys():
            yield datas[p]

class PreloadingCategoryMember:
    """
    Identical to _PreloadingCategoryMember but can recurse in category.
    """
    def __init__(self, title, recurse = 0, filtered_cat = None, site = None, pageNumber = 200, extraParams = None):
        self.site = getSite(site)
        self.recurse = recurse
        self.cats_todo = [ (title, 0) ]
        self.cats_done = filtered_cat
        self.pageNumber = pageNumber
        self.extraParams = extraParams
        if self.cats_done == None:
            self.cats_done = []

    def __iter__(self):
        while self.cats_todo:
            title, level = self.cats_todo.pop()
            if title in self.cats_done:
                continue
            if level > self.recurse:
                continue
            print >> sys.stderr, "getting", title.encode('utf-8')
            self.cats_done.append(title)
            preloader_generator = _PreloadingCategoryMember(title, site = self.site, pageNumber = self.pageNumber, extraParams = self.extraParams)
            for x in preloader_generator:
                if self.recurse and x['ns'] == 14:
                    self.cats_todo.append((x['title'], level + 1))
                yield x


# http://fr.wikipedia.org/w/api.php?action=query&prop=categories&titles=Albert%20Einstein|Albert&cllimit=28&clprop=hidden
# http://fr.wikipedia.org/w/api.php?action=query&generator=categories&titles=Albert_Einstein|Albert&prop=info&gcllimit=50&clprop=hidden
def GetCategories( site, titles, extraParams = None ):
    """
    Usage example: data = GetCategories(site, ['user:yurik', [...] ])
    titles may be either a title (as a string), or a list of strings
    extraParams if given must be a dict() as taken by query.GetData()
    """
    params = { u'action' : u'query', u'generator' : u'categories' }
    params[u'prop'] = u'info'
    params[u'titles'] = query.ListToParam(titles)
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingCategories:
    """
    Wraps around another generator. Retrieves categories of as many pages as
    stated by pageNumber from that generator, and yields them one after the
    other. Then retrieves more pages, etc.
    """
    def __init__(self, generator, pageNumber=200, site = None):
        self.site = getSite(site)
        self.generator = []
        for p in generator:
            if type(p) == wikipedia.Page:
                print >> sys.stderr, "warning: using obsolete Page object"
                self.generator.append(p.title())
            else:
                self.generator.append(p)
        self.pageNumber = pageNumber
        self.next = None

    def preload(self):
        extraParams =  { 'gcllimit' : str(self.pageNumber) }
        if self.next:
            extraParams['gclcontinue'] = self.next
            self.next = None # to stop iteration in __iter__()
        result = GetCategories(self.site, self.generator, extraParams)
        if type(result) == type([]):
            return {}
        if result.has_key('query-continue'):
            self.next = result['query-continue']['categories']['gclcontinue']
            #print self.next
        return result[u'query'][u'pages']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas.keys():
                yield datas[p]
            datas = self.preload()
        for p in datas.keys():
            yield datas[p]


def GetBackLinks(site, titles, next, limit, extraParams = None):
    """
    Usage example: data = GetBackLinks('ru','user:yurik')
    titles may be either a title (as a string), or a list of strings
    extraParams if given must be a dict() as taken by query.GetData()
    """
    params = {'action' : 'query', 'bltitle' : query.ListToParam(titles), 'list' : 'backlinks'}
    if next:
        extraParams['blcontinue'] = next
    params['bllimit'] = limit
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)


# This doest not get included template
class PreloadingBackLinks:
    """
    Wraps around another generator. Retrieves backlinks of one pages, and
    yields them one after the other.
    """
    def __init__(self, title, depth=500, site = None, extraParams = None):
        self.site = getSite(site)
        self.title = title
        self.extraParams = extraParams
        # FIXME: backward compatibility, must be removed
        if self.extraParams == None:
            self.extraParams = { 'blfilterredir' : 'all' }
        if type(title) == wikipedia.Page:
            print >> sys.stderr, "warning: using obsolete Page object"
            self.title = p.title()
        self.depth = depth
        self.next =  None

    def preload(self):
        result = GetBackLinks(self.site, self.title, self.next, self.depth,
                              self.extraParams)
        self.next = None  # to stop iteration in __iter__() while loop
        if result.has_key('query-continue'):
            self.next = result['query-continue']['backlinks']['blcontinue']
        return result[u'query'][u'backlinks']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()

        for p in datas:
            yield p


def GetEmbeddedIn(site, titles, next, limit, extraParams = None):
    """
    Usage example: data = GetEmbeddedIn('ru','user:yurik')
    titles may be either a title (as a string), or a list of strings
    extraParams if given must be a dict() as taken by query.GetData()
    """
    params = {'action' : 'query', 'eititle' : query.ListToParam(titles), 'list' : 'embeddedin'}
    if next:
        extraParams['eicontinue'] = next
    params['eilimit'] = limit
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)


# http://fr.wikipedia.org/w/api.php?action=query&list=embeddedin&eilimit=500&eititle=Modèle:Portail_histoire_de_la_zoologie_et_de_la_botanique
class PreloadingEmbeddedIn:
    """
    Wraps around another generator. Retrieves EmbeddedIn of one page, and
    yields them one after the other.
    """
    def __init__(self, title, depth=500, site = None, extraParams = None):
        self.site = getSite(site)
        self.title = title
        self.extraParams = extraParams
        # FIXME: backward compatibility, must be removed
        if self.extraParams == None:
            self.extraParams = { 'eifilterredir' : 'all' }
        if type(title) == wikipedia.Page:
            print >> sys.stderr, "warning: using obsolete Page object"
            self.title = p.title()
        self.depth = depth
        self.next =  None

    def preload(self):
        result = GetEmbeddedIn(self.site, self.title, self.next, self.depth,
                               self.extraParams)
        self.next = None  # to stop iteration in __iter__() while loop
        if result.has_key('query-continue'):
            self.next = result['query-continue']['embeddedin']['eicontinue']
        return result[u'query'][u'embeddedin']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()

        for p in datas:
            yield p

# FIXME: see test_page_startswith_1(), when given a title ends with / the
# iterator doesn't iterate after the first page of result
# FIXME: using gapprefix doesn't work as expected (2009/07/03) debug it
#/w/api.php?action=query&generator=allpages&gaplimit=4&gapfrom=T&prop=info
#/w/api.php?gaplimit=500&generator=allpages&format=json&gapfrom=Restauration&gapnamespace=102&action=query
def GetPagesStartswith(site, title, extraParams = None, depth = 500):
    params = {'action' : 'query', 'generator' : 'allpages', 'gapfrom':query.ListToParam(title), 'gaplimit' : depth}
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingPagesStartswith:
    """
    Retrieves pages starting by a given title and yields them one after
    the other.
    """
    def __init__(self, title, depth=500, extraParams = None, site = None):
        self.site = getSite(site)
        if type(title) == wikipedia.Page:
            print >> sys.stderr, "warning: using obsolete Page object"
            title = p.title()
        self.start_title = title
        if len(title) == 0:
            title = u'!'
        if title.endswith(u'/'):
            title = title[:len(title)-1]
        p = wikipedia.Page(self.site, title)
        self.title = p.titleWithoutNamespace()
        self.extraParams = {}
        if extraParams != None:
            self.extraParams = extraParams
        self.extraParams['gapnamespace'] = p.namespace()
        self.depth = depth
        self.next =  self.title

    def preload(self):
        result = GetPagesStartswith(self.site, self.next,
                                    self.extraParams, self.depth)
        self.next = None
        if result.has_key('query-continue'):
            # prior to 1.20wmf8 this was called gapfrom
            if result['query-continue']['allpages'].has_key('gapfrom'):
                self.next = result['query-continue']['allpages']['gapfrom']
            else:
                self.next = result['query-continue']['allpages']['gapcontinue']
        return result[u'query'][u'pages']

    def __iter__(self):
        datas = self.preload()
        found = True
        while self.next and found:
            for p in datas.keys():
                title = datas[p][u'title']
                if not title.startswith(self.start_title):
                    found = False
                    continue
                yield datas[p]
            if found:
                datas = self.preload()
        if found:
            for p in datas.keys():
                title = datas[p][u'title']
                if not title.startswith(self.start_title):
                    continue
                yield datas[p]

#/w/api.php?action=query&generator=allpages&gaplimit=4&gapfrom=T&prop=info
#/w/api.php?gaplimit=500&generator=allpages&format=json&gapfrom=Restauration&gapnamespace=102&action=query
def GetPagesAllpages(site, title, extraParams = None, depth = 500):
    params = {'action' : 'query', 'generator' : 'allpages', 'gaplimit' : depth}
    if len(title):
        params['gapfrom'] = query.ListToParam(title)
    
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

# use PreloadingAlldeletedrevs to get deleted revs
class PreloadingAllpages:
    """
    Retrieves all pages from a given namespace.
    """
    def __init__(self, namespace = 0, depth=500, extraParams = None,
                 site = None):
        self.site = getSite(site)
        self.extraParams = {}
        if extraParams != None:
            self.extraParams = extraParams
        self.extraParams['gapnamespace'] = namespace
        self.depth = depth
        self.next =  '' # To start iteration

    def preload(self):
        result = GetPagesAllpages(self.site, self.next,
                                  self.extraParams, self.depth)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['allpages']['gapcontinue']
        return result[u'query'][u'pages']

    def __iter__(self):
        datas = self.preload()
        while self.next != None:
            for p in datas.keys():
                yield datas[p]
            datas = self.preload()
        for p in datas.keys():
            title = datas[p][u'title']
            yield datas[p]


#/w/api.php?action=query&generator=allpages&gaplimit=4&gapfrom=T&prop=info
#/w/api.php?gaplimit=500&generator=allpages&format=json&gapfrom=Restauration&gapnamespace=102&action=query
def GetPagesAlldeletedrevs(site, title, extraParams = None, depth = 500):
    params = {'action' : 'query', 'generator' : 'allpages', 'gaplimit' : depth}
    params['list'] = 'deletedrevs'
    params['drlimit'] = 200
    if len(title):
        params['gapfrom'] = query.ListToParam(title)
    
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingAlldeletedrevs:
    """
    Retrieves all pages from a given namespace.
    """
    def __init__(self, namespace = 0, depth=500, extraParams = None,
                 site = None):
        self.site = getSite(site)
        self.extraParams = {}
        if extraParams != None:
            self.extraParams = extraParams
        self.extraParams['gapnamespace'] = namespace
        self.depth = depth
        self.next =  '' # To start iteration

    def preload(self):
        result = GetPagesAlldeletedrevs(self.site, self.next,
                                        self.extraParams, self.depth)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['allpages']['gapfrom']
        return result[u'query'][u'deletedrevs']

    def __iter__(self):
        datas = self.preload()
        while self.next != None:
            for p in datas:
                yield p
            datas = self.preload()
        for p in datas:
            yield p

#http://fr.wikipedia.org/w/api.php?action=query&list=usercontribs&ucuser=YurikBot
#http://fr.wikipedia.org/w/api.php?action=query&list=usercontribs&ucnamespace=0&ucuser=Flot2
#http://fr.wikipedia.org/w/api.php?action=query&list=usercontribs&ucstart=20060303000000&ucuser=YurikBot
def GetUserContrib(site, username, start, extraParams = None, direction = 'newer'):
    params = {
        'action' : 'query',
        'list' : 'usercontribs',
        'ucuser': username,
        'ucstart' : str(start),
        'uclimit' : 500,
        'ucdir' : direction,
        }
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingUserContrib:
    """
    Wraps around another generator. Retrieves user contrib, optionnaly starting
    at a given offset and yields them one after the other.
    """
    def __init__(self, username, start = u'', namespace = None, depth=500, site = None):
        self.site = getSite(site)
        self.username = username
        p = wikipedia.Page(site, username)
        self.namespace = namespace
        self.title = p.titleWithoutNamespace()
        self.depth = depth
        self.next =  start
        self.dir = 'older'
        if self.next:
            self.dir = 'newer'

    def preload(self):
        extraParams = {}
        if self.namespace != None:
            extraParams =  { 'ucnamespace' : str(self.namespace) }
        result = GetUserContrib(self.site, self.username, self.next, extraParams, self.dir)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['usercontribs']['ucstart']
        return result[u'query'][u'usercontribs']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()
        for p in datas:
            yield p

#http://fr.wikipedia.org/w/api.php?action=query&list=recentchanges&rctype=new&rcprop=sizes|title|timestamp&rcnamespace=0&rcdir=newer&rclimit=1000
# user|comment|flags|timestamp|title|ids|sizes|redirect|patrolled
def GetRecentchanges(site, start, extraParams = None):
    params = {
        'action' : 'query',
        'list' : 'recentchanges',
        'rcdir' : 'older',
        'rclimit' : 500,
        # needs special right for patrolled prop
        'rcprop' : 'user|comment|flags|timestamp|title|ids|sizes|redirect'
        }
    if start != None:
        extraParams['rcstart'] = start
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingRecentchanges:
    """
    Wraps around another generator. Retrieves recent change, optionnaly
    starting at a given offset and yields them one after the other.
    """
    def __init__(self, extraParams = None, site = None):
        self.site = getSite(site)
        self.extraParams = extraParams
        self.next =  None

    def preload(self):
        result = GetRecentchanges(self.site, self.next, self.extraParams)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['recentchanges']['rccontinue']
            # FIXME 2013/03/27, it's not normal server return a value considered
            # as invalid
            self.next = self.next.split(u'|')[0]
        return result[u'query'][u'recentchanges']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()
        for p in datas:
            yield p

#http://fr.wikipedia.org/w/api.php?action=query&list=imageusage&iutitle=Image:Albert%20Einstein%20Head.jpg
#  iutitle iucontinue iunamespace  iufilterredir iulimit iuredirect
def GetImageusage(name, site, start, extraParams = None):
    params = {
        'action' : 'query',
        'list' : 'imageusage',
        'iulimit' : 500,
        'iutitle' : name
        }
    if start != None:
        params['iucontinue'] = start
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingImageusage:
    """
    Wraps around another generator. Retrieves image usage, optionnaly
    starting at a given offset and yields them one after the other.
    """
    def __init__(self, name, extraParams = None, site = None):
        self.site = getSite(site)
        self.extraParams = extraParams
        self.next =  None
        self.name = name

    def preload(self):
        result = GetImageusage(self.name, self.site,
                               self.next, self.extraParams)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['imageusage']['iucontinue']
        return result[u'query'][u'imageusage']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()
        for p in datas:
            yield p

#http://fr.wikisource.org/w/api.php?action=query&generator=allimages&gailimit=5&gaiprefix=T&prop=imageinfo
#  iutitle iucontinue iunamespace  iufilterredir iulimit iuredirect
def GetAllImages(prefix, site, start, extraParams = None):
    params = {
        'action' : 'query',
        'generator' : 'allimages',
        'gailimit' : 200,
        'gaiprefix' : prefix,
        }
    if start != None:
        params['gaifrom'] = start
    params = query.CombineParams( params, extraParams )
    return query.GetData(params, site = site, useAPI = True)

class PreloadingAllImages:
    """
    Wraps around another generator. Retrieves image usage, optionnaly
    starting at a given offset and yields them one after the other.
    """
    def __init__(self, prefix, extraParams = None, site = None):
        self.site = getSite(site)
        self.extraParams = extraParams
        self.next =  None
        self.prefix = prefix

    def preload(self):
        result = GetAllImages(self.prefix, self.site,
                              self.next, self.extraParams)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['allimages']['gaifrom']
        return result[u'query'][u'pages']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield datas[p]
            datas = self.preload()
        for p in datas:
            yield datas[p]

#http://fr.wikipedia.org/w/api.php?action=query&list=logevents&letype=block&letitle=Utilisateur:166.70.207.2&lelimit=50
#  leprop  ids, title, type, user, timestamp, comment, details
#  letype  block, protect, rights, delete, upload, move, import, patrol, merge, suppress, renameuser, globalauth, newusers, makebot
#  lestart        - The timestamp to start enumerating from.
#  leend          - The timestamp to end enumerating.
#  ledir          newer, older Default: older
#  leuser         - Filter entries to those made by the given user.
#  letitle        - Filter entries to those related to a page.
#  lelimit     
def GetLogevents(site, start, extraParams = None):
    params = {
        'action' : 'query',
        'list' : 'logevents',
        }
    if start != None:
        params['lestart'] = start
    params = query.CombineParams( params, extraParams )
    if not params.has_key('lelimit'):
        params['lelimit'] = 500
    return query.GetData(params, site = site, useAPI = True)

class PreloadingLogevents:
    """
    Wraps around another generator. Retrieves entry in logevents, optionnaly
    starting at a given offset and yields them one after the other.
    """
    def __init__(self, extraParams = None, site = None):
        self.site = getSite(site)
        self.extraParams = extraParams
        self.next =  None

    def preload(self):
        result = GetLogevents(self.site, self.next, self.extraParams)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['logevents']['lestart']
        return result[u'query'][u'logevents']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()
        for p in datas:
            yield p

# http://fr.wikipedia.org/w/api.php?action=query&prop=langlinks&titles=Main%20Page|France&redirects
def GetLanglinks(site, titles):
    params = {
        'action' : 'query',
        'prop'   : 'langlinks',
        'redirects' : None,
        'lllimit' : 500
        }
    params['titles'] = query.ListToParam(titles)
    return query.GetData(params, site = site, useAPI = True)

class PreloadingLanglinks:
    """
    Wraps around another generator. Retrieves langlinks from a set of pages.
    """
    def __init__(self, titles, site = None):
        self.site = getSite(site)
        self.generator = titles
        self.redirects = {}
        self.pageNumber = 30

    def preload(self, titles):
        result = GetLanglinks(self.site, titles)
        #print result[u'query'][u'normalized']
        if result[u'query'].has_key(u'redirects'):
            for k in result[u'query'][u'redirects']:
                self.redirects[k[u'to']] = k[u'from']
        return result[u'query'][u'pages']

    def to_orig_name(self, title):
        if self.redirects.has_key(title):
            title = self.redirects[title]
        return title

    def __iter__(self):
        somePages = []
        for page in self.generator:
            somePages.append(page)
            if len(somePages) >= self.pageNumber:
                result = self.preload(somePages)
                for refpage in result.keys():
                    yield result[refpage]
                somePages = []
        # preload remaining pages
        if len(somePages):
            result = self.preload(somePages)
            for refpage in result.keys():
                yield result[refpage]

# http://fr.wikipedia.org/w/api.php?action=query&generator=links&prop=info&titles=Main%20Page|France&redirects
def GetAllLinksTo(site, namespace, next, from_title, to_title):
    params = {
        'action' : 'query',
        'list' : 'alllinks',
        #'alunique' : '1',
        'alprop': 'ids|title',
        'allimit' : 5000,
        }
    if from_title:
        params['alfrom'] = from_title
    elif next:
        params['alcontinue'] = next
    if to_title:
        params['alto'] = to_title
    params['alnamespace'] = str(namespace)
    return query.GetData(params, site = site, useAPI = True)

class PreloadingAllLinksTo:
    """
    Wraps around another generator. Retrieves link info from pages links
    """
    def __init__(self, namespace, site = None, from_title = None, to_title = None):
        self.site = getSite(site)
        self.namespace = namespace
        self.next = None
        self.from_title = from_title
        self.to_title = to_title

    def preload(self):
        result = GetAllLinksTo(self.site, self.namespace, self.next,
                               self.from_title, self.to_title)
        self.from_title = None
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['alllinks']['alcontinue']
        return result[u'query'][u'alllinks']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()
        for p in datas:
            yield p

# http://fr.wikipedia.org/w/api.php?action=query&generator=links&prop=info&titles=Main%20Page|France&redirects
def GetLinkedPage(site, titles, next, extraParams = None):
    params = {
        'action' : 'query',
        'generator' : 'links',
        #'prop'   : 'info',
        'gpllimit' : 5000,
        }
    if next:
        params['gplcontinue'] = next
    params = query.CombineParams( params, extraParams )
    params['titles'] = query.ListToParam(titles)
    return query.GetData(params, site = site, useAPI = True)

# FXIME: share the redirects things with other place
class PreloadingLinkedPage:
    """
    Wraps around another generator. Retrieves link info from pages links
    """
    def __init__(self, titles, site = None, extraParams = None):
        self.extraParams = extraParams
        self.site = getSite(site)
        self.redirects = {}
        if type(titles) == type(u''):
            titles = [ titles ]
        self.titles = titles
        self.next = None

    def preload(self):
        result = GetLinkedPage(self.site, self.titles, self.next, self.extraParams)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['links']['gplcontinue']
        #titles = self.titles[0:60]
        #self.titles = self.titles[60:]
        #result = GetLinkedPage(self.site, titles)
        if result[u'query'].has_key(u'redirects'):
            for k in result[u'query'][u'redirects']:
                self.redirects[k[u'to']] = k[u'from']
        return result[u'query'][u'pages']

    def to_orig_name(self, title):
        if self.redirects.has_key(title):
            title = self.redirects[title]
        return title

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield datas[p]
            datas = self.preload()
        for p in datas:
            yield datas[p]

# http://fr.wikipedia.org/w/api.php?action=sitematrix
def GetSitematrix(site = None):
    params = {
        'action' : 'sitematrix',
        }
    site = getSite(site)
    data = query.GetData(params, site = site, useAPI = True)
    return data[u'sitematrix']

#http://fr.wikipedia.org/w/api.php?action=query&list=deletedrevs&drlimit=10&titles=Paris|France&drprop=user|comment
#   drstart        - The timestamp to start enumerating from
#   drend          - The timestamp to stop enumerating at
#   drdir          - The direction in which to enumerate
#                    One value: newer, older
#                    Default: older
#   drlimit        - The maximum amount of revisions to list
#                    No more than 500 (5000 for bots) allowed.
#                    Default: 10
#   drprop         - Which properties to get
#                    Values (separate with '|'): revid, user, comment, minor,
#                       len, content, token
#                    Default: user|comment

def GetDeletedrevs(site, start, extraParams = None):
    params = {
        'action' : 'query',
        'list' : 'deletedrevs',
        }
    if start != None:
        params['drstart'] = start
    params = query.CombineParams( params, extraParams )
    if not params.has_key('drlimit'):
        params['drlimit'] = 500
    return query.GetData(params, site = site, useAPI = True, sysop = True)

class PreloadingDeletedrevs:
    """
    Wraps around another generator. Retrieves deletedrevs, optionnaly
    starting at a given offset and yields them one after the other.
    """
    # FIXME, actually caller must take care to not pass too many title
    def __init__(self, extraParams = None, site = None):
        self.site = getSite(site)
        #self.site.forceLogin(sysop = False)
        self.extraParams = extraParams
        self.next =  None

    def preload(self):
        result = GetDeletedrevs(self.site, self.next, self.extraParams)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['deletedrevs']['drstart']
        return result[u'query'][u'deletedrevs']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()
        for p in datas:
            yield p

def undelete(title, token, comment, site):
    params = {
        u'action' : u'undelete',
        u'title' : query.ListToParam(title),
        u'token': token,
        u'reason': comment,
        }
    return query.GetData(params, site = site, useAPI = True, sysop = True)

def revert_last_edit(title, token, undo, comment, site):
    params = {
        u'action' : u'edit',
        u'title' : query.ListToParam(title),
        u'undo' : undo,
        #u'undoafter' : undoafter,
        u'token': token,
        u'summary': comment,
        }
    return query.GetData(params, site = site, useAPI = True, sysop = False)

#http://fr.wikipedia.org/w/api.php?action=query&list=abuselog&afltitle=API
#  aflstart       - The timestamp to start enumerating from
#  aflend         - The timestamp to stop enumerating at
#  afldir         - The direction in which to enumerate
#                   One value: newer, older
#                   Default: older
#  afluser        - Show only entries done by a given user or IP address.
#  afltitle       - Show only entries occurring on a given page.
#  aflfilter      - Show only entries that were caught by a given filter ID
#  afllimit       - The maximum amount of entries to list
#                   No more than 500 (5000 for bots) allowed.
#                   Default: 10
#  aflprop        - Which properties to get
#                   Values (separate with '|'): ids, filter, user, ip, title, action, details, result, timestamp
#                   Default: ids|user|title|action|result|timestamp
def GetAbuseLog(site, title, start, extraParams = None):
    params = {
        'action' : 'query',
        'list' : 'abuselog',
        }
    if start != None:
        params['aflstart'] = start

    if title:
        params['afltitle'] =  query.ListToParam(title)
    params = query.CombineParams( params, extraParams )
    if not params.has_key('afllimit'):
        params['afllimit'] = 500
    return query.GetData(params, site = site, useAPI = True)

class PreloadingAbuseLog:
    """
    Wraps around another generator. Retrieves abuse log, optionnaly
    starting at a given offset and yields them one after the other.
    """
    def __init__(self, title, extraParams = None, site = None):
        self.site = getSite(site)
        self.title = title
        self.extraParams = extraParams
        self.next =  None

    def preload(self):
        result = GetAbuseLog(self.site, self.title,
                             self.next, self.extraParams)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['abuselog']['aflstart']
        return result[u'query'][u'abuselog']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()
        for p in datas:
            yield p


# api.php?action=query&list=abusefilters&abfprop=id|description|pattern
#  abfstartid     - The filter id to start enumerating from
#  abfendid       - The filter id to stop enumerating at
#  abfdir         - The direction in which to enumerate
#                   One value: older, newer
#                   Default: newer
#  abfshow        - Show only filters which meet these criteria
#                   Values (separate with '|'): enabled, !enabled, deleted, !deleted, private, !private
#  abflimit       - The maximum number of filters to list
#                   No more than 500 (5000 for bots) allowed.
#                   Default: 10
#  abfprop        - Which properties to get
#                   Values (separate with '|'): id, description, pattern, actions, hits, comments, lasteditor, lastedittime, status, private
#                   Default: id|description|actions|status
def GetAbuseFilter(site, start, extraParams = None):
    params = {
        'action' : 'query',
        'list' : 'abusefilters',
        }
    if start != None:
        params['abfstartid'] = start

    params = query.CombineParams( params, extraParams )
    if not params.has_key('abflimit'):
        params['abflimit'] = 500
    return query.GetData(params, site = site, useAPI = True)

class PreloadingAbuseFilter:
    """
    Wraps around another generator. Retrieves deletedrevs, optionnaly
    starting at a given offset and yields them one after the other.
    """
    def __init__(self, extraParams = None, site = None):
        self.site = getSite(site)
        self.extraParams = extraParams
        self.next =  None

    def preload(self):
        result = GetAbuseFilter(self.site, self.next, self.extraParams)
        self.next = None
        if result.has_key('query-continue'):
            self.next = result['query-continue']['abusefilters']['abfstartid']
        return result[u'query'][u'abusefilters']

    def __iter__(self):
        datas = self.preload()
        while self.next:
            for p in datas:
                yield p
            datas = self.preload()
        for p in datas:
            yield p

# api.php?action=purge&titles=...|...
def PurgeTitles(site, titles):
    params = { 'action' : 'purge' }
    params[u'titles'] = query.ListToParam(titles)
    return query.GetData(params, site = site, useAPI = True)

class PreloadingPurgeTitles:
    """
    Wraps around another generator. Purge all titles given by this generator.
    """
    def __init__(self, generator, site = None, page_number = 60):
        self.site = getSite(site)
        self.generator = generator
        self.pageNumber = page_number

    def preload(self, titles):
        result = PurgeTitles(self.site, titles)
        #print result
        return result[u'purge']

    def __iter__(self):
        somePages = []
        for page in self.generator:
            somePages.append(page)
            if len(somePages) >= self.pageNumber:
                result = self.preload(somePages)
                for refpage in result:
                    yield refpage
                somePages = []
        # preload remaining pages
        if len(somePages):
            result = self.preload(somePages)
            for refpage in result:
                yield refpage

class PreloadingContents:
    """
    Wraps around another generator to mass load pages.
    """
    def __init__(self, generator, site = None, page_number = 50):
        self.site = getSite(site)
        self.generator = generator
        self.pageNumber = page_number

    def __iter__(self):
        somePages = []
        for page in self.generator:
            somePages.append(page[u'title'])
            if len(somePages) >= self.pageNumber:
                result = PreloadingHistory(somePages, depth = 1, site = self.site, contents = True)
                for refpage in result:
                    yield refpage
                somePages = []
        # preload remaining pages
        if len(somePages):
            result = PreloadingHistory(somePages, depth = 1, site = self.site, contents = True)
            for refpage in result:
                yield refpage

def test_backlinks():
    preload = PreloadingBackLinks(u':Modèle:Ébauche', 500)
    count = 0
    for k in preload:
        count += 1
        #print k
        print k[u'title'].encode('utf-8')
    print count

def test_embeddedin():
    preload = PreloadingEmbeddedIn(u'Modèle:Portail_histoire_de_la_zoologie_et_de_la_botanique', 500)
    count = 0
    for k in preload:
        count += 1
        #print k
        print k[u'title'].encode('utf-8')
    print count

def test_page_startswith_1():
    #preload =  PreloadingPagesStartswith(u'Utilisateur:Phe/Projet:Restauration lien rouge/par distance')
    site = wikipedia.getSite(code = 'fr', fam = 'wikisource')
    preload = PreloadingPagesStartswith(u'L’Encyclopédie/1re édition/', extraParams = { 'prop' : 'info' }, site = site)
    count = 0
    for k in preload:
        count += 1
        print k
        #print k[u'title'].encode('utf-8')
    #preload =  PreloadingPagesStartswith(u'Projet:Restauration lien rouge/par distance/Exceptions/Q/')
    #for k in preload:
    #    print k[u'title'].encode('utf-8')
    #    pass
    print count

def test_page_startswith():
    #preload =  PreloadingPagesStartswith(u'Utilisateur:Phe/Projet:Restauration lien rouge/par distance')
    site = wikipedia.getSite(code = 'fr', fam = 'wikisource')
    preload = PreloadingPagesStartswith(u'Page:Revue des D', extraParams = { 'gapfilterredir' : 'nonredirects' }, site = site)
    count = 0
    for k in preload:
        count += 1
        #print k
        #print k[u'title'].encode('utf-8')
    #preload =  PreloadingPagesStartswith(u'Projet:Restauration lien rouge/par distance/Exceptions/Q/')
    #for k in preload:
    #    print k[u'title'].encode('utf-8')
    #    pass
    print count

def test_user_contrib(username):
    preload = PreloadingUserContrib(username, '20080310000000', 0)
    count = 0
    for k in preload:
        count += 1
        if count >= 500:
            break
    print count

def test_recentchanges(rctype):
    extraParams =  { 'rcnamespace' : '0', 'rctype' : rctype }
    preload = PreloadingRecentchanges(extraParams)
    for k in preload:
        print k

def test_imageusage(name):
    preload = PreloadingImageusage(name)
    for k in preload:
        print k

def test_logevents(extraParams):
    preload = PreloadingLogevents(extraParams)
    for k in preload:
        print k

def test_langlinks():
    titles = [ u'2005', u'france', u'Université du bosphore' ]
    gen = PreloadingLanglinks(titles)
    for p in gen:
        print p[u'title']
        for k in p[u'langlinks']:
            print k

def test_all_links_to():
    site = wikipedia.getSite(code = 'en', fam = 'wikisource')
    gen = PreloadingAllLinksTo(102, site)
    count = 0
    for p in gen:
        count += 1
        print p[u'title']
    print count

def test_preloading_linked_page_info():
    titles = [ u'2005', u'France', u'Université du bosphore' ]
    gen = PreloadingLinkedPage(titles)
    for p in gen:
        print p

def test_preloading_interwikies():
    titles = [ u'2005', u'France', u'Université du Bosphore' ]
    gen = PreloadingInterwikies(titles)
    for p in gen:
        print p[u'title']
        for k in p[u'langlinks']:
            print k

def test_sitematrix():
    data = GetSitematrix()
    for k in data:
        print k, data[k]

def test_deletedrevs():
    titles = [ u'France', u'Paris' ]
    #extraParams = { 'drlimit' : 2 }
    gen = PreloadingDeletedrevs(titles) #, extraParams = extraParams)
    for p in gen:
        print p[u'title']
        for k in p[u'revisions']:
            print k

def test_all_pages():
    extraParams = { } #'list' : 'deletedrevs', 'drlimit' : 200 }
    gen = PreloadingAllpages(extraParams = extraParams)
    for p in gen:
        pass
        #print p[u'title']
        #print p
        #for k in p[u'revisions']:
        #    print k

def test_all_deletedrevs():
    extraParams = { } # 'gapfilterredir' : 'nonredirects' }
    gen = PreloadingAlldeletedrevs(extraParams = extraParams)
    for p in gen:
        print len(p[u'revisions']), p[u'title']
        pass
        #print p[u'title']
        #print p
        #for k in p[u'revisions']:
        #    print k

def test_preloading_history(pagenames, site = None):
    gen = PreloadingHistory(pagenames, 5000, 1, site)
    count = 0
    for k in gen:
        for p in k[u'revisions']:
            print p
            count += 1
    print count

def test_abuse_log(pagename = None, site = None):
    gen = PreloadingAbuseLog(pagename, site = site)
    count = 0
    for k in gen:
        if not re.match(u'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]', k[u'user']):
            print k
        count += 1
    print count

def test_abuse_filter(site = None):
    gen = PreloadingAbuseFilter(site = site)
    count = 0
    for k in gen:
        print k
        count += 1
    print count

def test_preloading_pageinfo_from_ids(site = None):
    gen = PreloadingPageinfoFromIds(site = site, generator = range(1, 1000))
    for p in gen:
        print p

def test_preloading_pageinfo_from_titles(site = None):
    gen = PreloadingPageinfoFromTitles(site = site, generator = [ u'France', u'Foo', u'not existing', u'not existing 2', u':Catégorie: Linguistique' ])
    for p in gen:
        print p

def test_preloading_all_image(site = None, prefix = u'T'):
    if not site:
        site = wikipedia.getSite(code = 'fr', fam = 'wikisource')
    extraParams = { u'prop' : u'imageinfo', u'iiprop' : u'sha1' }
    gen = PreloadingAllImages(site = site, prefix = prefix,
                              extraParams = extraParams)
    for k in gen:
        print k

def test_image_info_from_cat(site = None, cat = u'Category:Illustrations de Montégut'):
    if not site:
        site = wikipedia.getSite(code = 'fr', fam = 'wikisource')
    extraParams = { u'prop' : u'imageinfo', u'iiprop' : u'sha1' }
    gen = PreloadingCategoryMember(site = site, title = cat,
                                   extraParams = extraParams)
    for k in gen:
        print k

if __name__ == "__main__":
    try:
        #test_backlinks()
        #test_embeddedin()
        #test_page_startswith()
        test_page_startswith_1()
        #test_image_info_from_cat()
        #test_preloading_all_image()
        #test_user_contrib(unicode(sys.argv[1], 'utf-8'))
        #test_recentchanges('new')
        #test_imageusage(u'Image:Albert Einstein Head.jpg')
        #test_logevents(None)
        #test_logevents( { 'letype' : 'block', 'letitle': 'user:166.70.207.2' } )
        #test_langlinks()
        #est_preloading_linked_page_info()
        #test_preloading_interwikies()
        #test_sitematrix()
        #test_deletedrevs()
        #test_all_pages()
        #test_all_deletedrevs()
        #test_preloading_history([ u"Apple" ],
        #                        site = wikipedia.getSite(code = 'en'))
        #test_abuse_log()
        #test_all_links_to()
        #test_abuse_filter()
        #test_preloading_pageinfo_from_ids()
        #test_preloading_pageinfo_from_titles()
    finally:
        wikipedia.stopme()
