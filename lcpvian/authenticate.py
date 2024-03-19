
class Authentication:
    
    def __init__(self, app: web.Application) -> None:
        self.app = app
        self.all_corpora = app.all_corpora
        
    def basic(self):
        pass

    def check_user_ok(self, user):
        pass
    
    def check_corpora_allowed(self, user):
        pass

    def query(self, corpora):
        self.check_user_ok()
        for c in self.all_corpora:
            assert c in user.projects