from api_helper import millitime, random_key
import threading


class token_clerk():
    '''
        handle registering, validating and expiring antiCSRF tokens
    '''

    def __init__(self):
        # currently valid tokens
        self.current_tokens = {}
        # up to 50 expired tokens
        self.expired_tokens = {}
        # after how long tokens should expire
        self.expire_after   = 1000 * 60 * 60
        # key size to use for the tokens
        self.keysize        = 42  # life, the universe and everything

    def register_new(self):
        '''
            Arguments:  none
            Returns:    a dict with three keys: tok (a token), iat (issued at,
                        a number), and exp (expires at, a number)
            Throws:     no
            Effects:    modifies the module-global registry of tokens, updating
                        it with a new key

            Register a new anti-CSRF token with the dictionary.
            Tokens expire 1 hour (3600 seconds) after they are issued.
            Before registering the new token, expired ones are purged.
        '''
        self.clean_expired()
        tok = random_key(self.keysize)
        now = millitime()
        exp = now + self.expire_after
        with threading.Lock():
            self.current_tokens[tok] = exp
        return {"tok": tok, "iat": now, "exp": exp}

    def unregister_all(self):
        '''
            Arguments:  none
            Returns:    the total number of removed tokens
            Throws:     no
            Effects:    modifies the registry of tokens, clearing it
        '''
        ol = len(self.current_tokens)
        lock = threading.Lock()
        with lock:
            self._log_expired_tokens(self.current_tokens.copy())
            self.current_tokens = {}
        return ol

    def unregister(self, *tokens):
        expd = self.clean_expired()
        if not tokens or tokens is None:
            return

        self._log_expired_tokens(tokens)
        self.current_tokens = dict(filter(
            lambda t: t[0] not in tokens,
            self.current_tokens.items()
        ))
        return len(tokens) + expd

    def clean_expired(self):
        '''
            Arguments:  none
            Returns:    the number of tokens which were expired
            Throws:     no
            Effects:    modifies the module-global registry of tokens, possibly
                        deleting any tokens found to have expired

            Filter out expired tokens from the registry, by only leaving those
                tokens which expire in the future.
            The return value is the difference in length from before and after
                this operation.
        '''
        lock = threading.Lock()
        ol = len(self.current_tokens)
        with lock:
            self.current_tokens = dict(filter(
                lambda o: o[1] > millitime(),
                self.current_tokens.items()
            ))
        return abs(len(self.current_tokens) - ol)
