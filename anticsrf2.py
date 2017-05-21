from api_helper import millitime, random_key
import threading


class token_clerk():
    '''
        handle registering, validating and expiring antiCSRF tokens
    '''

    def __init__(self, preset_tokens=None, expire_after=None, keysize=None):
        # currently valid tokens
        self.current_tokens = preset_tokens or dict()
        # up to 50 expired tokens
        self.expired_tokens = dict()
        # after how long tokens should expire
        self.expire_after   = expire_after or 1000 * 60 * 60
        # key size to use for the tokens
        # life, the universe and everything --
        # a number between 32 (too short) and 64 (too long)
        self.keysize        = keysize or 42

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
        now = millitime()
        tok = random_key(self.keysize)
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
        plen = len(self.current_tokens)
        with threading.Lock():
            self._log_expired_tokens(self.current_tokens.copy())
            self.current_tokens = dict()
        return plen

    def unregister(self, *tokens):
        '''
            Arguments:  tokens (strings)
            Returns:    the total number of removed tokens, after the
                        clean_expired job is completed and its value added
            Throws:     anything thrown by clean_expired()
            Effects:    modifies the module-global registry of tokens, possibly
                        deleting the given token, and any side effects of
                        clean_expired()

            Manually expire a token before its 1 hour limit.
            Tail-called and included in the return value is clean_expired(), so
                that we can expire old tokens at every possible moment.
        '''
        expd = self.clean_expired()
        if not tokens or tokens is None:
            return

        expire = dict()

        with threading.Lock():
            for t in tokens:
                if t in self.current_tokens:
                    expire.update( { t: self.current_tokens[t] } )
                    del self.current_tokens[t]

        self._log_expired_tokens(expire)
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
        plen = len(self.current_tokens)

        if not plen:
            return

        now = millitime()
        expire = dict()

        with threading.Lock():
            for tok, exp in self.current_tokens.items():
                if now >= exp:
                    expire.update({tok: exp})
                    del self.current_tokens[tok]

        self._log_expired_tokens(expire)

        return abs(len(self.current_tokens) - plen)

    def is_registered(self, tok):
        '''
            Arguments:  a token (string)
            Returns:    True or False, based on whether the given token is in
                        fact registered and valid
            Throws:     TypeError if the value at ANTICSRF_REGISTER[tok] is not
                        orderable with int (i.e, not a number), and anything
                        thrown by clean_expired()
            Effects:    any side effects of clean_expired()

            Test whether a token is valid (registered).
            Unpythonically, this function does not let a KeyError be raised if
                the token is not a key; this is because we clean out expired
                tokens first, so they no longer exist by the time the condition
                is tested.
            While it is possible a token could expire after the call to
                clean_expired() but before the condition is checked, this is
                extremely unlikely -- but the code is probably redundant just
                to be safe anyways.
        '''
        self.clean_expired()

        exist = tok in self.current_tokens
        old   = tok in self.expired_tokens

        if exist:
            exp = self.current_tokens[tok]
            return exp > millitime(), exp
        elif old:
            old_exp = self.expired_tokens[tok]
            return False, old_exp
        else:
            return False, 0

    def _log_expired_tokens(self, tokens):
        '''
            Arguments:  tokens (a dict<string, int>)
            Returns:    None
            Throws:     no
            Effects:    modifies self.expired_tokens, deleting and adding keys

            Record tokens that have expired in another dictionary.
        '''
        self._clear_expired_kept(trash=len(tokens))
        with threading.Lock():
            self.expired_tokens.update(tokens)

    def _clear_expired_kept(self, trash=30):
        '''
            Arguments:  trash (an int)
            Returns:    None
            Throws:     no
            Effects:    modifies self.expired_tokens, deleting keys

            Trash the oldest kept-expired tokens.
        '''
        stoks = sorted(self.expired_tokens.items(), key=lambda x: x[1])
        with threading.Lock():
            self.expired_tokens = dict(stoks[trash:])
