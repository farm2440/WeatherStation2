# https://maxhalford.github.io/blog/flask-sse-no-deps/
# https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#event_stream_format
# https://github.com/MaxHalford/flask-sse-no-deps !!!!!
import queue
from flask import request, render_template, send_from_directory
import flask
import json
import os
import logging
from datetime import datetime

app = flask.Flask(__name__)


@app.route('/')
def top_page():
    return render_template('index.html')



@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, './static/images'), 'cloud.ico', mimetype='image/vnd.microsoft.icon')


class MessageAnnouncer:

    def __init__(self):
        self.listeners = []

    def listen(self):
        self.listeners.append(queue.Queue(maxsize=5))
        return self.listeners[-1]

    def announce(self, msg):
        # We go in reverse order because we might have to delete an element, which will shift the
        # indices backward
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]


announcer = MessageAnnouncer()


def format_sse(data: str, event=None) -> str:
    """Formats a string and an event name in order to follow the event stream convention.
    >>> format_sse(data=json.dumps({'abc': 123}), event='Jackson 5')
    'event: Jackson 5\\ndata: {"abc": 123}\\n\\n'
    """
    msg = f'data: {data}\n\n'
    if event is not None:
        msg = f'event: {event}\n{msg}'
    return msg


# От web_emit.py тук се POST-ват данните-съобщения dt. Те се оформят от функцията format_sse() в msg.
# После през announcer се изпращат в потока
@app.route('/stream', methods=['POST'])
def input_stream():
    dt = request.data
    msg = format_sse(data=dt.decode())
    print('SSE INPUT:', msg)
    announcer.announce(msg=msg)
    return {}, 200


# От web страницата с
# const eventSource = new EventSource('http://localhost:5000/sse');
# се прихваща потока от данни по SSE
@app.route('/sse', methods=['GET'])
def sse():
    def stream():
        messages = announcer.listen()  # returns a queue.Queue
        while True:
            msg = messages.get()  # blocks until a new message arrives
            yield msg
    return flask.Response(stream(), mimetype='text/event-stream')


pid = os.getpid()
print("web_interface.py PID:", pid)
now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
log_file = "./log/web_interface.log"
with open(log_file, "a") as file:
    file.write(f"PID:{pid}\n")
    file.write(f"Current date-time: {timestamp}\n")

# Disable request logging
app.logger.setLevel(logging.WARNING)
app.run(host='0.0.0.0', port=80)
