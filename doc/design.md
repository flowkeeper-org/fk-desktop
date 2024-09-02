# Flowkeeper design considerations

## Client / server architecture

1. Flowkeeper clients are "fat", and the backends are "thin". All messages are sent by 
the clients, while the servers are passive. This is done to simplify servers, allow generic 
messaging protocols like XMPP or AMQP, and enable "dumb" backends like plain files. 
2. A client may safely disconnect or shut down at any moment. Most importantly, there can 
be _zero_ clients running in the middle of a Pomodoro. A client which "reconnects" will 
see the Pomodoro in the correct state, as if it was running on the server. A Pomodoro, 
which ended while the clients were offline, is considered completed successfully.
3. The server should work correctly with all "business" content e2e-encrypted. Any 
unencrypted messages are all related to the client's communication, i.e. Authenticate,
Ping/Pong, Error, Replay, and DeleteAccount.
4. As a consequence of (2) and (3), all messages in the system are recorded end-user events.
Neither the client, nor the server generate any "business" events of their own. This makes
client synchronization much easier, since the events like FinishPomodoro are computed and 
fired internally, and never go on the wire.

## Event sourcing data model

When a client connects to a backend, it replays all events since the last known state.

5. Two clients must synchronize their changes in real time, meaning that they can't make
conflicting changes offline. This is achieved via message sequencing. This design 
consideration is temporary, and will be removed in the future, as we allow "offline mode"
for connected sources. In the future, data from multiple clients can be merged via one of 
two Import mechanisms.
6. Some messages might be missing from the end of the list (e.g. the client is offline and
they haven't arrived yet), but we can't have gaps in the middle of the history. It means
that the history must always be consistent. If we detect an inconsistency in the hisory
(e.g. 5 minutes of rest start on a pomodoro in "new" state, i.e. we missed the "work" state
completely), such inconsistencies result in the parsing failure, crashing the client.
We don't try to "fix" the history by adding records retroactively. 
7. The history is immutable, but we can create a new one, which is a compressed version
of the original, as long as it results in the exact same final state of the data model.
8. If a user tries to delete or complete a workitem in the middle of its own pomodoro, the
core will void this pomodoro, emitting correct events.
9. The history preserves all data, so we don't have to be too careful about deleting things.
If a backlog, workitem or user is deleted -- the object simply gets deleted. We don't use
"is_deleted" flags, and we don't move things to "orphaned" storage. If we need to restore
a deleted object -- we'll find a way how to do it by processing the history.
10. Strategies are only executed as a result of users' actions or timer events. Client
startup or shutdown won't add any strategies to the history.
11. The Timer never fires "in the past".
12. All Pomodoros run and end implicitly. They can only be started and voided explicitly.
