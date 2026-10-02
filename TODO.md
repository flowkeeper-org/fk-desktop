# Online data sync BETA

1. Simplify -- file sources never have encryption, websocket -- always have it
2. Remove settings for
   1. DONE: Salt (SOURCE_ENCRYPTION_SALT)
   2. DONE: Encryption enabled / disabled (SOURCE_ENCRYPTION_ENABLED)
   3. E2e key (we'll ask for it if we can't decode) (SOURCE_ENCRYPTION_KEY)
   4. DONE: Username and email (1st CreateUser is us) (WEBSOCKETEVENTSOURCE_USERNAME, SOURCE_FULLNAME, WebsocketEventSource.userpic)
3. Logout should call KC logout endpoint
4. ConfigureStrategy version defines PBKDF2HMAC settings
5. WebSocket -- when we read the 2nd strategy, it must be CreateUser. If not --
we ask the user for e2e key. We compute the Fernet key on the fly, try to decode,
and on success save it in settings, then retry.
6. File event source -- can omit ConfigureStrategy altogether
7. Four de-facto data sources, with their unique setting names, which ensures that
they don't overwrite each other

------------

A single cryptograph instance in the app, created at startup
