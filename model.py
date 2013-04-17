
from google.appengine.ext import db

PEOPLE = 'thisiswei Kitchhock Mohetin user895703 amonofocus arvidniklasson brentdroog chamonix davidaltobeli houseofradon mikestaniforthfilmmaker'.split()
URL = 'http://vimeo.com/api/v2/%s/likes.json?page=%s'
IP_BASE = 'http://api.hostip.info/?ip='

class Video(db.Model):
    user_id = db.IntegerProperty()
    person = db.StringProperty()
    title = db.StringProperty(required = True)
    video_id = db.IntegerProperty()
    thumbnail = db.LinkProperty(required = True)
    likes = db.IntegerProperty()
    plays = db.IntegerProperty()
    liked_on = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def latest(cls, person):
        vs = Video.all().filter('person =', person).order('-liked_on').get()
        try:
            return vs.liked_on
        except Exception:
            return None
        
    @classmethod
    def by_title(cls, title):
        v = Video.all().filter('title =', title).get()
        return v

    def as_dict(self):
        d = db.to_dict(self)
        d['created'] = self.created.strftime('%c')
        return d

class Person(db.Model):
    name = db.StringProperty()
    
    @classmethod
    def by_name(cls, name):
        n = Person.all().filter('name =', name).get()
        return n
