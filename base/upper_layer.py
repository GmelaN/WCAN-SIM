class UpperLayer:
    def __init__(self):
        self.m_env = None
        self.m_sscs = None
        self.m_app = None

    def set_env(self, m_env):
        self.m_env = m_env

    def get_env(self):
        return self.m_env

    def set_app(self, m_app):
        self.m_app = m_app

    def get_app(self):
        return self.m_app

    def set_sscs(self, m_sscs):
        self.m_sscs = m_sscs

    def get_sscs(self):
        return self.m_sscs
