# Libraries which are used:
#  socket - for sending data between clients
#  threading - for running a listening script in the background; this means
#      that the code can wait for your input AND listen to messages sent
#  datetime - so code knows how long to wait until the start of next minute
#  time - so code can wait for start of next minute
#  urllib - for making http requests; this is needed to get your public ip
import socket
import threading
import time
import urllib.request
from datetime import datetime

import urwid

JOIN_CODE = "join".encode("utf-8")
ACKNOWLEDGE_JOIN_CODE = "joinrcv".encode("utf-8")
LEAVE_CODE = "leave".encode("utf-8")

# These ports should be switched around for other client if different
SRC_PORT = 50007 # "Source port" this is the port you will open
DEST_PORT = 50007 # "Destination port" this is the port you will send to

alive = False
joined = False
waiting = False

palette = [
  ("prompt", "", "", "", "#fff", "#099"),
  ("bg", "", "", "", "", "#244"),
  ("header", "", "", "", "#000", "#299"),
  ("textcol1", "", "", "", "#fbf", "#244"),
  ("textcol2", "", "", "", "#bff", "#244"),
  ("textcol3", "", "", "", "#fbb", "#244"),
  ("textcol4", "", "", "", "#bfb", "#244"),
  ("textcol5", "", "", "", "#bbf", "#244"),
  ("join", "", "", "", "#ffb", "#244")
]

def client(chatroom):
  global alive, joined, waiting
  # Gets your public IP and prints it so you can share. External website is
  # the only way to get this information becuase the router (NAT) hides this
  # from the server, I use api.ipify.org
  request = urllib.request.Request("https://api.ipify.org", method="GET")
  with urllib.request.urlopen(request) as response:
    # Decodes the output from server in utf-8
    my_ip = response.read().decode("utf-8")
  
  chatroom.your_ip_is(my_ip)
  chatroom.add_text("Enter the IP of the person you want to connect to.")
  chatroom.update_screen()

  chatroom.register_next_input(lambda chatroom, ip: on_recieve_ip(chatroom, ip, my_ip))

def on_recieve_ip(chatroom, ip, my_ip):
  global alive, joined, waiting
  # Calculates how long until start of next minute
  seconds = 60 - datetime.now().second + (datetime.now().microsecond / 1000000)

  # If only five seconds left will wait until next minute
  if seconds < 5:
    seconds = seconds + 60

  waiting = True

  # Outputs how long it will wait (rounded to nearest tenth) and waits it
  chatroom.add_text(f"Waiting {round(seconds, 1)} seconds")
  chatroom.update_screen()
  for _ in range(int(seconds)):
    time.sleep(1)
    if not waiting:
      return
  time.sleep(seconds % 1)

  waiting = False
  alive = True

  # "Punches hole" this means that it will send a message to the other client
  # or peer. After sending this the router (NAT) will allow incoming connections
  # to this port for around 20 seconds.
  chatroom.add_text("Establishing Connection...")
  chatroom.update_screen()
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Creates UDP socket
  # deepcode ignore BindToAllNetworkInterfaces: Binding to all networks is necessary for this application; ip checks made further on
  sock.bind(("0.0.0.0", SRC_PORT))  # Opens source port
  sock.sendto(JOIN_CODE, (ip, DEST_PORT)) # Sends a message so that the other client
                                          # has something to recieve on desination port

  chatroom.register_all_input(
    lambda chatroom, message: send_message(chatroom, message, sock, ip, my_ip)
  )

  sock.settimeout(2) # Socket will raise error if no input for 2 seconds
  while alive:
    try:
      data, (addr, _) = sock.recvfrom(1024) # Recieve 1024 bytes from socket
    except TimeoutError: # If error is raised
      continue # Skip to next iteration of loop

    if addr == ip:
      if not joined:
        joined = True
        chatroom.clear()
        chatroom.add_join_leave(ip, join=True)
        chatroom.update_screen()

      if data == JOIN_CODE:
        sock.sendto(ACKNOWLEDGE_JOIN_CODE, (ip, DEST_PORT))
      elif data == LEAVE_CODE:
        chatroom.add_join_leave(ip, join=False)
        chatroom.update_screen()
        disconnect(chatroom)
      elif data != ACKNOWLEDGE_JOIN_CODE:
        chatroom.add_message(ip, data.decode())
        chatroom.update_screen()
  sock.sendto(LEAVE_CODE, (ip, DEST_PORT))
  sock.close() # Closes socket once alive is set to false
  try:
    chatroom.add_text("Disconnected") # Feedback to user
    chatroom.update_screen()
  except RuntimeError:
    pass

def send_message(chatroom, message, sock, ip, my_ip):
  if alive and joined:
    sock.sendto(message.encode(), (ip, DEST_PORT))
    chatroom.add_message(my_ip, message)
    chatroom.update_screen()

def disconnect(chatroom):
  global alive, waiting
  if alive:
    alive = False
    try:
      chatroom.add_text("Disconnecting...") # Feedback to user
      chatroom.update_screen()
    except RuntimeError:
      pass
  waiting = False

def ip_to_color(ip):
  return "textcol" + str(int("{:02X}{:02X}{:02X}{:02X}".format(*map(int, ip.split("."))), 16) % 5 + 1)

class ScrollingListWalker(urwid.ListBox):
  def keypress(self, size, *args, **kwargs):
    self._process()
    return super(ScrollingListWalker, self).keypress(size, *args, **kwargs)

  def mouse_event(self, size, *args, **kwargs):
    self._process()
    return super(ScrollingListWalker, self).mouse_event(size, *args, **kwargs)

  def render(self, size, *args, **kwargs):
    self._process()
    return super(ScrollingListWalker, self).render(size, *args, **kwargs)

  def _process(self):
    if len(self.body.positions(True)) > 0:
      super(ScrollingListWalker, self).set_focus(self.body.positions(True)[0])

class Chatroom(urwid.WidgetWrap):
  def __init__(self):
    self.next_input = lambda _, __: None
    self.is_all_input = False
    self.loop = None
    self.prompt_text = urwid.Edit("", "")
    self.list_walker = urwid.SimpleListWalker([])
    self._w = urwid.AttrMap(urwid.Frame(
      header=urwid.Pile([
        urwid.AttrMap(urwid.Pile([
          urwid.Divider(),
          urwid.Text("Direct Chat - Serverless IRC", "center"), 
          urwid.Divider()
        ]), "header"),

        urwid.Divider()
      ]),
      body=ScrollingListWalker(self.list_walker),
      footer=urwid.Pile([
        urwid.Divider(),
        urwid.AttrMap(urwid.Pile([
          urwid.Columns([
            ("fixed", len(" > "), urwid.Text(" > ")),
            ("weight", 1, self.prompt_text),
          ]),
          urwid.Divider(),
        ]), "prompt")
      ]),
      focus_part="footer",
    ), "bg")

  def mouse_event(self, size, event, button, col, row, focus):
    pass
  
  def keypress(self, size, key):
    global client_thread
    if key == "esc":
      raise urwid.ExitMainLoop()
    if key == "enter":
      tmp_func = self.next_input
      tmp_input = self.prompt_text.edit_text
      self.prompt_text.edit_text = ""
      if not self.is_all_input:
        self.next_input = lambda _, __: None
      # deepcode ignore MissingAPI: Ignored becuase join() is called since this is global
      client_thread = threading.Thread(target=tmp_func, args=(self,tmp_input))
      client_thread.start()
      return
    super(Chatroom, self).keypress(size, key)
  
  def clear(self):
    self.list_walker.clear()
  
  def register_next_input(self, func):
    self.next_input = func
    self.is_all_input = False
  
  def register_all_input(self, func):
    self.next_input = func
    self.is_all_input = True

  def set_loop(self, loop):
    self.loop = loop
  
  def update_screen(self):
    if self.loop is not None:
      self.loop.draw_screen()

  def add_message(self, ip, message):
    prefix = " " + ip
    sep = "> "
    text = message
    self.list_walker.append(
      urwid.Columns([
        ("fixed", len(prefix), urwid.AttrMap(urwid.Text(prefix), ip_to_color(ip))),
        ("fixed", len(sep), urwid.Text(sep)),
        ("weight", 1, urwid.Padding(urwid.Text(text), width=("relative", 100))),
      ])
    )
  
  def add_text(self, message):
    self.list_walker.append(
      urwid.Padding(urwid.Text(" " + message), width=("relative", 100))
    )
  
  def add_join_leave(self, ip, join=True):
    prefix = " " + ip
    text = " " + ("joined" if join else "left") + " the chat."
    self.list_walker.append(
      urwid.Columns([
        ("fixed", len(prefix), urwid.AttrMap(urwid.Text(prefix), ip_to_color(ip))),
        ("fixed", len(text), urwid.AttrMap(urwid.Text(text), "join")),
      ])
    )
  
  def your_ip_is(self, ip):
    prefix = " Your IP is "
    self.list_walker.append(
      urwid.Columns([
        ("fixed", len(prefix), urwid.Text(prefix)),
        ("fixed", len(ip), urwid.AttrMap(urwid.Text(ip), ip_to_color(ip))),
      ])
    )

chatroom = Chatroom()
loop = urwid.MainLoop(chatroom, palette)
chatroom.set_loop(loop)
loop.screen.set_terminal_properties(colors=256)
client_thread = threading.Thread(target=client, args=(chatroom,))
client_thread.start()

try:
  loop.run()
except KeyboardInterrupt:
  pass
finally:
  disconnect(chatroom)
  client_thread.join()