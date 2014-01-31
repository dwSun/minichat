# Micro gevent chatroom.
# ----------------------
# Make things as simple as possible, but not simpler.
from gevent import monkey; monkey.patch_all()
from flask import Flask, render_template, request, json

from gevent import queue
from gevent.pywsgi import WSGIServer

app = Flask(__name__)
app.debug = True


class Room(object):

    def __init__(self):
        self.users = set()
        self.messages = []

    def backlog(self, size=25):
        return self.messages[-size:]

    def subscribe(self, new_user):
        self.users.add(new_user)
        for user in self.users:
            user.queue.put_nowait({'user': new_user.nick})

    def add(self, message):
        for user in self.users:
            print user
            user.queue.put_nowait({'message': message})
        self.messages.append(message)


class User(object):

    def __init__(self, nick):
        self.queue = queue.Queue()
        self.nick = nick

rooms = {
    'python': Room(),
    'django': Room(),
}

users = {}


@app.route('/')
def choose_name():
    return render_template('choose.html')


@app.route('/<uid>')
def main(uid):
    return render_template(
        'main.html',
        uid=uid,
        rooms=rooms.keys()
    )


@app.route('/<room>/<uid>')
def join(room, uid):
    user = users.get(uid, None)

    if not user:
        users[uid] = user = User(uid)

    active_room = rooms[room]
    active_room.subscribe(user)
    print 'subscribe', active_room, user

    messages = active_room.backlog()
    room_users = [u.nick for u in active_room.users]

    return render_template('room.html',
        room=room, uid=uid, messages=messages, users=room_users)


@app.route("/put/<room>/<uid>", methods=["POST"])
def put(room, uid):
    # user = users[uid]
    room = rooms[room]

    message = request.form['message']
    room.add(':'.join([uid, message]))

    return ''


@app.route("/poll/<uid>", methods=["POST"])
def poll(uid):
    message = {'message': [], 'user': []}
    try:
        queued = users[uid].queue.get(timeout=10)
    except queue.Empty:
        queued = {}
    message.update(queued)

    return json.dumps(message)


if __name__ == "__main__":
    http = WSGIServer(('', 5000), app)
    http.serve_forever()
