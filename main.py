import webapp2
import json
import jinja2
import os
from url import gravatar_base, SCORES, github_base
from google.appengine.ext import db
from google.appengine.api import urlfetch, memcache
from model import Video, Person, PEOPLE, URL, IP_BASE
from xml.dom import minidom
import random


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
        autoescape = True)

def get_or_set_memcache(key, update=False):
    results = memcache.get(key)
    if update or results is None:
        val = (Video.all() if key == 'videos'
                                 else Person.all() if key == 'people' 
                                 else GitHub.all())
        val = list(val)
        memcache.set(key, val)
        return val
    return results

def get_geo(ip):
    url = IP_BASE + ip
    r = urlfetch.fetch(url)
    print r
    if r.status_code != 200:
        return 
    d = minidom.parseString(r.content)
    g = d.getElementsByTagName('gml:coordinates')
    if g:
        val = g[0].childNodes[0].nodeValue
        lng, lat = val.split(',')
        return db.GeoPt(lat, lng)

class MainHandler(webapp2.RequestHandler):
    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        if self.request.url.endswith('json'):
            self.format = 'json'
        else:
            self.format = 'html'

    def render(self, template, **params):
        t = jinja_env.get_template(template)
        self.response.write(t.render(params))

    def render_front(self, v):
        self.render('video.html', videos=v)

    def render_json(self, d):
        js = json.dumps(d)
        self.response.headers['Content-Type'] == 'application/json; charset=UTF-8'
        self.response.write(js)

    def update_people(self):
        ps = list(Person.all())
        if len(ps) == 0:
            [Person(key_name=p).put() for p in PEOPLE]
            ps = Person.all()
        for p in ps:
            self.update_person(p.name)
        vs =  list(Video.all())
        memcache.set('videos', vs)

    def update_person(self, p, new_record=False):
        for i in range(1, 4):
            r = urlfetch.fetch(URL%(p, i))
            if r.status_code == 200:
                print 'bitch'
                if new_record and i == 1:
                    Person(key_name=p).put()
                js = json.loads(r.content)
                for j in js:
                    t = j['title']
                    v = Video.by_title(t)
                    if v:
                        'print exist'
                        return 
                    else:
                        v = Video(user_id=j['user_id'],
                                  person=p,
                                  title=t,
                                  video_id=j['id'],
                                  thumbnail=j['thumbnail_medium'],
                                  likes=j['stats_number_of_likes'],
                                  plays=j['stats_number_of_plays'],
                                  liked_on=j['liked_on'])
                        v.put() 

    def get_score(self, name, ip):
        url = github_base % name
        c = urlfetch.fetch(url)
        coords = get_geo(ip)
        if c.status_code != 200:
            return
        record = GitHub.all().filter('username =', name).get()
        if not record:
            js = json.loads(c.content)
            events = [j['type'] for j in js]
            scores = sum(SCORES.get(e, 0) for e in events)
            gravatar_id = js[0]['actor_attributes']['gravatar_id']
            GitHub(geo = coords, username=name, grava_id = gravatar_id, score = scores).put()
            get_or_set_memcache('github', True)
            return scores
        else:
            return record.score

class Updater(MainHandler):
    def get(self):
        self.update_people()
        self.redirect('/')

class AddPerson(MainHandler):
    def get(self, person):
        if not Person.by_name(person): 
            self.update_person(person, True) 
        self.redirect('/')


class GitHub(db.Model):
    username = db.StringProperty(required=True)
    grava_id = db.StringProperty(required=True)
    score = db.IntegerProperty(required=True)
    geo = db.GeoPtProperty()


class BlogHandler(MainHandler):
    def get(self):
        p = Video.all().order('-created')
        self.render('index.html', post=p)

    def post(self):
        t = self.request.get('title')
        b = self.request.get('body')
        p = Post(title=t, body=b)
        p.put()
        self.redirect('/blog')

class VideoHandler(MainHandler): 
    def get(self):
        vs = get_or_set_memcache('videos')
        v = random.sample(vs, 15)
        v = sorted(v, key = lambda x: x.likes)
        if self.format == 'html':
            self.render_front(v)
        else:
            self.render_json([x.as_dict() for x in v])

class GitHandler(MainHandler):
    def get(self):
        records = get_or_set_memcache('github')
        self.render('github.html', gs=records, base_url=gravatar_base)

    def post(self):
        ip = self.request.remote_addr
        name = self.request.get('username')
        self.get_score(name, ip)
        self.redirect('/github')

app = webapp2.WSGIApplication([
    ('/(?:\.json)?', VideoHandler),
    ('/blog', BlogHandler),
    ('/update', Updater),
    ('/github', GitHandler),
    ('/add/([A-Za-z1-9-]+)', AddPerson) 
], debug=True)
