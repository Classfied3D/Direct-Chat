Direct chat is a peer-to-peer python terminal based chat app which doesn't rely on a third party server.

# FAQ
### Q: How do I use it?

A: Exchange IPs with someone else. Then enter them within the same minute.


### Q: Is it encrypted?

A: Not yet.


### Q: How does it work?

A: Via [UDP holepunching](https://en.wikipedia.org/wiki/UDP_hole_punching), without a rendezvous server. Both peers send a UDP packet to each other at around the same time, and both NATs think that the recieved packet is a response to the packet that was sent, so they allow more incoming packets from the other peer, establishing a connection.


### Q: Why is it not working?

A: Firstly, make both sides entered the correct IP. If you're sure of that, symmetric NATs, cellular networks, VPNs and firewalls may not allow this work.

### Q: Can I connect two devices on the same network?

A: Not yet, this will be added in the future.

### Q: How fast is the connection?

A: Very fast, since the packet is sent directly from one peer to another, without having to go through a server.