from streamlit_app.config import Config
from streamlit_app.interface.main_panel import MainPanel
from streamlit_app.interface.side_panel import SidePanel
from streamlit_app.utils.embeddings import build_embeddings_model
from streamlit_app.vector import build_provider_vector_store


class StreamlitInterface:
    def __init__(self):
        self.cfg = Config.from_env()
        self.embeddings = build_embeddings_model()
        self.vector_store = build_provider_vector_store(
            cfg=self.cfg,
            embeddings=self.embeddings,
        )

        SidePanel(self.vector_store)
        MainPanel(self.vector_store)
